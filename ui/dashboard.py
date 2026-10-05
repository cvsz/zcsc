from __future__ import annotations

import json
import logging
import ntpath
import os
import threading
import tkinter as tk
from typing import Optional
from tkinter import colorchooser, filedialog, messagebox

import customtkinter as ctk

from automation.rotation import RotationWorker
from automation.marquee import MarqueeWorker
from camfrog.auto_respond import AutoRespondWorker
from camfrog.bad_word_moderation import BadWordMatch, BadWordMonitorWorker, submit_bad_word_kick
from automation.intervals import interval_to_seconds, seconds_to_interval, format_interval
from camfrog.controller import CamfrogController
from camfrog.detector import discover_executable
from camfrog.room_actions import CamfrogRoomActionController
from camfrog.room_events import RoomEventMatch, RoomEventMonitorWorker
from camfrog.profile_links import (
    open_camfrog_profile,
    open_camfrog_profile_directory,
    profile_url_for_nickname,
)
from camfrog.registry_status import merge_presets, read_camfrog_custom_statuses
from system.config_store import DEFAULT_BAD_WORD_TERMS
from system.startup import set_start_with_windows
from system.tray import resource_path
from ui.clipboard import get_clipboard_text, set_clipboard_text
from status_catalog import (
    DEFAULT_STANDARD_STATUS_ID,
    STATUS_CATEGORY_LABELS,
    category_key_from_label,
    filter_standard_statuses,
    find_standard_status_by_label,
    get_standard_status,
    standard_status_category_values,
)
from status_styles import apply_styles, color_template_error

log = logging.getLogger(__name__)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")


def windows_path(path: str) -> str:
    """Normalize a Windows executable path regardless of slash style."""
    return ntpath.normpath(os.fspath(path))


class AppUI(ctk.CTk):
    def __setattr__(self, name, value):
        # Keep the inherited Tk title() method callable if a non-method value
        # is assigned to the same instance attribute by UI code or plugins.
        if name == "title" and not callable(value):
            object.__setattr__(self, "title_label", value)
            return
        super().__setattr__(name, value)

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.config_data = store.load()
        self.controller = CamfrogController(self.config_data)
        self.rotation = RotationWorker(self._apply_status_background)
        self.marquee_animation = MarqueeWorker(self._apply_status_background)
        self.auto_responder = AutoRespondWorker(
            self.controller,
            self.store.load,
            self._auto_respond_state_changed,
        )
        self.room_action_controller = CamfrogRoomActionController(self.controller)
        self.bad_word_monitor = BadWordMonitorWorker(
            self.controller,
            self.store.load,
            self._bad_word_matches_received,
            self._bad_word_state_changed,
        )
        self.room_event_monitor = RoomEventMonitorWorker(
            self.controller,
            self.store.load,
            self._room_events_received,
            self._room_event_state_changed,
        )
        self._room_event_activity: list[str] = []
        self._tray_icon = None
        self._tray_thread: Optional[threading.Thread] = None
        self._exiting = False
        self._marquee_offset = 0
        self._marquee_current_text = ""
        self._style_lock = threading.Lock()

        self.title("Camfrog Status Changer")
        self._set_application_icon()
        self.geometry("760x590")
        self.minsize(720, 560)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        self._install_clipboard_shortcuts()
        self._load_config_to_ui()
        self.after(300, self._auto_detect_if_needed)
        self.after(500, self._start_tray)
        self.after(650, self._auto_import_registry_presets)
        self.after(800, self._auto_start_camfrog_if_configured, self._resume_background_automation)
        self.after(1000, self._monitor_tray)


    def _set_application_icon(self):
        if os.name != "nt":
            return
        icon_path = resource_path("app.ico")
        if not icon_path.is_file():
            log.warning("Application icon not found: %s", icon_path)
            return
        try:
            self.iconbitmap(default=str(icon_path))
        except Exception:
            log.exception("Could not set application window icon")

    def _new_feature_tab(self, name: str):
        tab = self.tabs.add(name)
        page = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        page.pack(fill="both", expand=True, padx=4, pady=4)
        return page

    def _install_clipboard_shortcuts(self):
        """Bind shortcuts to the actual Tk editor widgets before class defaults."""
        actions = {
            "c": "copy",
            "C": "copy",
            "x": "cut",
            "X": "cut",
            "v": "paste",
            "V": "paste",
            "a": "select_all",
            "A": "select_all",
        }

        targets = []

        def collect_editors(parent):
            for child in parent.winfo_children():
                if isinstance(child, (tk.Entry, tk.Text)):
                    targets.append(child)
                collect_editors(child)

        collect_editors(self)
        custom_tags = set()
        for widget in targets:
            widget_class = "CamfrogStatusChangerClipboardText" if isinstance(widget, tk.Text) else "CamfrogStatusChangerClipboardEntry"
            custom_tags.add(widget_class)
            tags = widget.bindtags()
            if widget_class not in tags:
                widget.bindtags((tags[0], widget_class, *tags[1:]))

        for widget_class in custom_tags:
            for key, action in actions.items():
                self.bind_class(
                    widget_class,
                    f"<Control-{key}>",
                    lambda event, action=action: self._clipboard_action(event, action),
                    add="+",
                )

    def _clipboard_action(self, event, action: str):
        widget = getattr(event, "widget", None) or self.focus_get()
        if widget is None:
            return None
        try:
            if action == "select_all":
                # tkinter Entry / ttk Entry / CTkEntry's internal Entry
                if hasattr(widget, "selection_range") and hasattr(widget, "icursor"):
                    widget.selection_range(0, "end")
                    widget.icursor("end")
                    return "break"
                # tkinter Text / CTkTextbox's internal Text
                if hasattr(widget, "tag_add"):
                    widget.tag_add("sel", "1.0", "end-1c")
                    widget.mark_set("insert", "end-1c")
                    widget.see("insert")
                    return "break"
                return None

            is_text = isinstance(widget, tk.Text)
            if action in {"copy", "cut"}:
                if is_text:
                    try:
                        selected = widget.get("sel.first", "sel.last")
                    except tk.TclError:
                        return "break"
                else:
                    if not widget.selection_present():
                        return "break"
                    first = widget.index("sel.first")
                    last = widget.index("sel.last")
                    selected = widget.get()[first:last]
                try:
                    set_clipboard_text(self, selected)
                except Exception as exc:
                    log.warning("Clipboard %s failed (%s)", action, type(exc).__name__)
                    return "break"
                if action == "cut":
                    if is_text:
                        widget.delete("sel.first", "sel.last")
                    else:
                        widget.delete(first, last)
                return "break"

            if action == "paste":
                try:
                    value = get_clipboard_text(self)
                except Exception as exc:
                    log.warning("Clipboard paste failed (%s)", type(exc).__name__)
                    return "break"
                if is_text:
                    try:
                        first = widget.index("sel.first")
                        last = widget.index("sel.last")
                    except tk.TclError:
                        pass
                    else:
                        widget.delete(first, last)
                        widget.mark_set("insert", first)
                    widget.insert("insert", value)
                else:
                    if widget.selection_present():
                        first = widget.index("sel.first")
                        last = widget.index("sel.last")
                        widget.delete(first, last)
                        widget.icursor(first)
                    widget.insert("insert", value)
                return "break"
            return "break"
        except (tk.TclError, AttributeError, TypeError):
            return None

    def _build(self):
        root = ctk.CTkFrame(self)
        root.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(root, text="Camfrog Status Changer", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 12))

        self.state_label = ctk.CTkLabel(root, text="Ready")
        self.state_label.pack(anchor="w", pady=(0, 10))

        self.tabs = ctk.CTkTabview(root)
        self.tabs.pack(fill="both", expand=True)
        self.setup_tab = self._new_feature_tab("Setup")
        self.status_tab = self._new_feature_tab("Status")
        self.history_tab = self._new_feature_tab("History")
        self.rotation_tab = self._new_feature_tab("Rotation")
        self.auto_respond_tab = self._new_feature_tab("Auto reply")
        self.room_commands_tab = self._new_feature_tab("Room commands")
        self.bad_words_tab = self._new_feature_tab("Bad words")
        self.room_events_tab = self._new_feature_tab("Room events")
        self.tov_tab = self._new_feature_tab("Video overlay")
        self.profile_tab = self._new_feature_tab("Web")

        exe_frame = ctk.CTkFrame(self.setup_tab)
        exe_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(exe_frame, text="Camfrog executable").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.exe_var = tk.StringVar()
        ctk.CTkEntry(exe_frame, textvariable=self.exe_var).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkButton(exe_frame, text="Browse", width=90, command=self._browse).grid(row=1, column=1, padx=(0, 10), pady=(0, 10))
        ctk.CTkButton(exe_frame, text="Detect", width=90, command=self._detect).grid(row=1, column=2, padx=(0, 6), pady=(0, 10))
        ctk.CTkButton(exe_frame, text="Native profile", width=110, command=self._show_native_profile).grid(row=1, column=3, padx=(0, 10), pady=(0, 10))
        exe_frame.grid_columnconfigure(0, weight=1)

        runtime_frame = ctk.CTkFrame(self.setup_tab)
        runtime_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(runtime_frame, text="Camfrog Runtime", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", padx=10, pady=(10, 4)
        )
        self.camfrog_pid_var = tk.StringVar(value="PID: not connected")
        self.camfrog_pid_entry_var = tk.StringVar()
        ctk.CTkLabel(runtime_frame, textvariable=self.camfrog_pid_var).grid(
            row=1, column=0, sticky="w", padx=10, pady=(0, 10)
        )
        ctk.CTkEntry(
            runtime_frame,
            textvariable=self.camfrog_pid_entry_var,
            width=110,
            placeholder_text="PID",
        ).grid(row=1, column=1, padx=(4, 6), pady=(0, 10))
        ctk.CTkButton(
            runtime_frame,
            text="Bind PID",
            width=90,
            command=self._bind_camfrog_pid,
        ).grid(row=1, column=2, padx=(0, 6), pady=(0, 10))
        ctk.CTkButton(
            runtime_frame,
            text="Start / Connect",
            width=120,
            command=self._start_or_connect_camfrog,
        ).grid(row=1, column=3, padx=(0, 6), pady=(0, 10))
        ctk.CTkButton(
            runtime_frame,
            text="Disconnect",
            width=100,
            command=self._disconnect_camfrog,
        ).grid(row=1, column=4, padx=(0, 10), pady=(0, 10))
        runtime_frame.grid_columnconfigure(0, weight=1)

        target_frame = ctk.CTkFrame(self.setup_tab)
        target_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(target_frame, text="UI Automation target", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 4))
        self.control_type_var = tk.StringVar(value="ComboBox")
        self.automation_id_var = tk.StringVar()
        self.title_re_var = tk.StringVar(value=".*")
        ctk.CTkLabel(target_frame, text="Control type").grid(row=1, column=0, sticky="w", padx=10)
        ctk.CTkEntry(target_frame, textvariable=self.control_type_var, width=130).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
        ctk.CTkLabel(target_frame, text="Automation ID (optional)").grid(row=1, column=1, sticky="w", padx=10)
        ctk.CTkEntry(target_frame, textvariable=self.automation_id_var).grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(target_frame, text="Title regex").grid(row=1, column=2, sticky="w", padx=10)
        ctk.CTkEntry(target_frame, textvariable=self.title_re_var).grid(row=2, column=2, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkButton(target_frame, text="Inspect", command=self._inspect).grid(row=2, column=3, padx=(0, 10), pady=(0, 10))

        self.fallback_x_var = tk.StringVar(value="0.50")
        self.fallback_y_var = tk.StringVar(value="0.19")
        ctk.CTkLabel(target_frame, text="Fallback X (relative)").grid(row=3, column=0, sticky="w", padx=10)
        ctk.CTkEntry(target_frame, textvariable=self.fallback_x_var, width=130).grid(row=4, column=0, padx=10, pady=(0, 10), sticky="w")
        ctk.CTkLabel(target_frame, text="Fallback Y (relative)").grid(row=3, column=1, sticky="w", padx=10)
        ctk.CTkEntry(target_frame, textvariable=self.fallback_y_var).grid(row=4, column=1, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkButton(target_frame, text="Capture target (3s)", command=self._capture_target).grid(row=4, column=2, columnspan=2, padx=(10, 10), pady=(0, 10), sticky="ew")
        target_frame.grid_columnconfigure(1, weight=1)
        target_frame.grid_columnconfigure(2, weight=1)

        status_frame = ctk.CTkFrame(self.status_tab)
        status_frame.pack(fill="x", pady=6)
        self.messages_title = ctk.CTkLabel(status_frame, text="Messages (1 message = 1 apply)", font=ctk.CTkFont(weight="bold"))
        self.messages_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 4))
        self.status_message_vars = [tk.StringVar() for _ in range(4)]
        self.message_labels = []
        self.message_apply_buttons = []
        for idx, var in enumerate(self.status_message_vars, start=1):
            lbl = ctk.CTkLabel(status_frame, text=f"Message {idx}", width=80)
            lbl.grid(row=idx, column=0, sticky="w", padx=(10, 4), pady=(2, 4))
            entry = ctk.CTkEntry(status_frame, textvariable=var)
            entry.grid(row=idx, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
            entry.bind("<KeyRelease>", lambda _event: self._refresh_status_preview())
            for key_sequence in ("<Return>", "<KP_Enter>"):
                entry.bind(
                    key_sequence,
                    lambda event, message_index=idx - 1: self._apply_message_from_enter(event, message_index),
                    add="+",
                )
            btn = ctk.CTkButton(status_frame, text="Apply", width=90, command=lambda i=idx-1: self._apply_message_clicked(i))
            btn.grid(row=idx, column=2, padx=(0, 10), pady=(2, 4))
            self.message_labels.append(lbl)
            self.message_apply_buttons.append(btn)

        self.standard_status_id_var = tk.StringVar(value=DEFAULT_STANDARD_STATUS_ID)
        self.standard_status_display_var = tk.StringVar()
        self.language_var = tk.StringVar(value="EN")
        self.standard_status_search_var = tk.StringVar()
        self.standard_status_category_key = "all"
        self.standard_status_category_var = tk.StringVar(value=STATUS_CATEGORY_LABELS["all"]["EN"])
        self.standard_status_filter_row = ctk.CTkFrame(status_frame, fg_color="transparent")
        self.standard_status_filter_row.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=(8, 2))
        self.standard_status_category_menu = ctk.CTkOptionMenu(
            self.standard_status_filter_row,
            values=standard_status_category_values("EN"),
            variable=self.standard_status_category_var,
            command=self._standard_status_category_changed,
            width=150,
        )
        self.standard_status_category_menu.pack(side="left", padx=(0, 8))
        self.standard_status_search_entry = ctk.CTkEntry(
            self.standard_status_filter_row,
            textvariable=self.standard_status_search_var,
            placeholder_text="Search EN/TH statuses",
        )
        self.standard_status_search_entry.pack(side="left", fill="x", expand=True)
        self.standard_status_search_var.trace_add("write", lambda *_args: self._refresh_standard_status_dropdown())
        self.standard_status_row = ctk.CTkFrame(status_frame, fg_color="transparent")
        self.standard_status_row.grid(row=6, column=0, columnspan=3, sticky="ew", padx=10, pady=(2, 2))
        self.standard_status_title = ctk.CTkLabel(self.standard_status_row, text="Standard status (50 pairs)")
        self.standard_status_title.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.standard_status_menu = ctk.CTkOptionMenu(
            self.standard_status_row,
            values=["Available"],
            variable=self.standard_status_display_var,
            command=self._standard_status_selected,
            width=330,
        )
        self.standard_status_menu.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.standard_status_favorite_button = ctk.CTkButton(
            self.standard_status_row,
            text="☆ Favorite",
            width=100,
            command=self._toggle_standard_status_favorite,
        )
        self.standard_status_favorite_button.grid(row=0, column=2, padx=(0, 8))
        self.standard_status_apply_button = ctk.CTkButton(
            self.standard_status_row,
            text="Send to Camfrog",
            width=120,
            command=self._apply_standard_status_clicked,
        )
        self.standard_status_apply_button.grid(row=0, column=3, sticky="e")
        self.standard_status_stage_button = ctk.CTkButton(
            self.standard_status_row,
            text="Stage only (no Enter)",
            width=150,
            command=self._stage_standard_status_clicked,
        )
        self.standard_status_stage_button.grid(row=0, column=4, sticky="e", padx=(8, 0))
        self.standard_status_row.grid_columnconfigure(1, weight=1)

        style_row = ctk.CTkFrame(status_frame, fg_color="transparent")
        style_row.grid(row=7, column=0, columnspan=3, sticky="ew", padx=10, pady=(8, 8))
        self.random_color_var = tk.BooleanVar(value=False)
        self.custom_color_var = tk.BooleanVar(value=False)
        self.custom_color_value = tk.StringVar(value="#00C7BE")
        self.marquee_var = tk.BooleanVar(value=False)
        self.marquee_single_character_var = tk.BooleanVar(
            value=bool(self.config_data.get("status", {}).get("styles", {}).get("marquee_single_character", True))
        )
        self.random_color_check = ctk.CTkCheckBox(style_row, text="Random Color", variable=self.random_color_var, command=self._random_color_toggled)
        self.random_color_check.pack(side="left", padx=(0, 14))
        self.custom_color_check = ctk.CTkCheckBox(style_row, text="Custom Color", variable=self.custom_color_var, command=self._custom_color_toggled)
        self.custom_color_check.pack(side="left", padx=(0, 6))
        self.custom_color_button = ctk.CTkButton(style_row, text="#00C7BE", width=82, command=self._choose_status_color)
        self.custom_color_button.pack(side="left", padx=(0, 14))
        self.marquee_check = ctk.CTkCheckBox(style_row, text="Marquee", variable=self.marquee_var, command=self._marquee_toggled)
        self.marquee_check.pack(side="left", padx=(0, 14))
        self.marquee_single_character_check = ctk.CTkCheckBox(
            style_row,
            text="One character per frame",
            variable=self.marquee_single_character_var,
            command=self._marquee_toggled,
        )
        self.marquee_single_character_check.pack(side="left", padx=(0, 10))
        self.marquee_frame_label = ctk.CTkLabel(style_row, text="Step s")
        self.marquee_frame_label.pack(side="left", padx=(0, 4))
        self.marquee_frame_interval_var = tk.StringVar(
            value=str(self.config_data.get("status", {}).get("styles", {}).get("marquee_frame_interval_seconds", 5))
        )
        ctk.CTkEntry(style_row, textvariable=self.marquee_frame_interval_var, width=55).pack(side="left", padx=(0, 8))
        self.language_label = ctk.CTkLabel(style_row, text="Language")
        self.language_label.pack(side="left", padx=(10, 6))
        self.language_menu = ctk.CTkOptionMenu(style_row, values=["EN", "TH"], variable=self.language_var, width=80, command=self._language_changed)
        self.language_menu.pack(side="left")
        self.status_style_note = ctk.CTkLabel(
            status_frame,
            text="One-character marquee sends one verified frame and one Enter per update. Delay steps are the configured interval multiplied by 1–5 (default 5 seconds); Camfrog acceptance is not independently confirmed.",
            wraplength=700,
            anchor="w",
        )
        self.status_style_note.grid(row=8, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 3))
        self.status_preview_label = ctk.CTkLabel(status_frame, text="", wraplength=700, anchor="w", justify="left")
        self.status_preview_label.grid(row=9, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 8))
        status_frame.grid_columnconfigure(1, weight=1)

        preset_frame = ctk.CTkFrame(self.history_tab)
        preset_frame.pack(fill="x", pady=6)
        preset_header = ctk.CTkFrame(preset_frame, fg_color="transparent")
        preset_header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(preset_header, text="Presets (one per line)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        preset_actions = ctk.CTkFrame(preset_header, fg_color="transparent")
        preset_actions.pack(side="right")
        self.import_presets_button = ctk.CTkButton(preset_actions, text="Import presets", width=115, command=self._import_presets_file)
        self.import_presets_button.pack(side="left", padx=(0, 6))
        self.export_presets_button = ctk.CTkButton(preset_actions, text="Export presets", width=115, command=self._export_presets_file)
        self.export_presets_button.pack(side="left", padx=(0, 6))
        ctk.CTkButton(preset_actions, text="Read Camfrog History", width=155, command=self._read_registry_clicked).pack(side="left")
        self.registry_auto_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(preset_frame, text="Read Camfrog status history on startup (read-only)", variable=self.registry_auto_var).pack(anchor="w", padx=10, pady=(0, 6))
        self.presets_box = ctk.CTkTextbox(preset_frame, height=100)
        self.presets_box.pack(fill="x", padx=10, pady=(0, 8))

        history_header = ctk.CTkFrame(preset_frame, fg_color="transparent")
        history_header.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(history_header, text="Camfrog History (read-only)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(history_header, text="Import all → Presets", width=145, command=self._import_history_all).pack(side="right")
        self.history_box = ctk.CTkTextbox(preset_frame, height=105)
        self.history_box.pack(fill="x", padx=10, pady=(0, 10))
        self.history_box.configure(state="disabled")
        self._history_values = []

        auto_frame = ctk.CTkFrame(self.rotation_tab)
        auto_frame.pack(fill="x", pady=6)
        self.rotation_var = tk.BooleanVar()
        self.start_windows_var = tk.BooleanVar()
        self.autostart_camfrog_var = tk.BooleanVar()
        self.restore_state_var = tk.BooleanVar(value=True)
        self.foreground_fallback_var = tk.BooleanVar(value=False)
        self.mode_var = tk.StringVar(value="sequential")
        self.interval_var = tk.StringVar(value="10")
        self.interval_unit_var = tk.StringVar(value="minutes")
        self.rotation_source_var = tk.StringVar(value="Messages 1–4")
        self.schedule_enabled_var = tk.BooleanVar(value=False)
        self.schedule_start_var = tk.StringVar(value="08:00")
        self.schedule_end_var = tk.StringVar(value="23:00")
        self.quiet_hours_enabled_var = tk.BooleanVar(value=False)
        self.quiet_start_var = tk.StringVar(value="22:00")
        self.quiet_end_var = tk.StringVar(value="08:00")
        self.background_control_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(auto_frame, text="Enable status rotation", variable=self.rotation_var).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        ctk.CTkLabel(auto_frame, text="Interval").grid(row=0, column=1, sticky="e")
        ctk.CTkEntry(auto_frame, textvariable=self.interval_var, width=70).grid(row=0, column=2, padx=(10, 4))
        self.interval_unit_menu = ctk.CTkOptionMenu(auto_frame, values=["seconds", "minutes", "hours"], variable=self.interval_unit_var, width=105, command=self._interval_unit_changed)
        self.interval_unit_menu.grid(row=0, column=3, padx=(0, 8))
        self.mode_menu = ctk.CTkOptionMenu(auto_frame, values=["sequential", "random"], variable=self.mode_var, width=120)
        self.mode_menu.grid(row=0, column=4, padx=(0, 10))
        ctk.CTkCheckBox(auto_frame, text="Start with Windows", variable=self.start_windows_var).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkCheckBox(auto_frame, text="Start Camfrog if not running", variable=self.autostart_camfrog_var).grid(row=1, column=1, columnspan=2, sticky="w", pady=(0, 10))
        self.rotation_source_label = ctk.CTkLabel(auto_frame, text="Source")
        self.rotation_source_label.grid(row=1, column=3, sticky="e", padx=(6, 4), pady=(0, 10))
        self.rotation_source_menu = ctk.CTkOptionMenu(
            auto_frame,
            values=["Messages 1–4", "Camfrog Status History (random)"],
            variable=self.rotation_source_var,
            width=205,
            command=self._rotation_source_changed,
        )
        self.rotation_source_menu.grid(row=1, column=4, sticky="w", padx=(0, 10), pady=(0, 10))
        self.status_commit_note = ctk.CTkLabel(auto_frame, text="UIA verified commit brings Camfrog forward; background Win32 is a fallback only")
        self.status_commit_note.grid(row=2, column=0, columnspan=5, sticky="w", padx=10, pady=(0, 6))
        self.background_control_check = ctk.CTkCheckBox(
            auto_frame,
            text="Allow background Win32 fallback when UIA cannot verify (keeps Camfrog in background)",
            variable=self.background_control_var,
        )
        self.background_control_check.grid(row=3, column=0, columnspan=5, sticky="w", padx=10, pady=(0, 6))
        self.foreground_fallback_check = ctk.CTkCheckBox(auto_frame, text="Allow coordinate fallback if UIA text cannot be verified (focuses Camfrog)", variable=self.foreground_fallback_var)
        self.foreground_fallback_check.grid(row=4, column=0, columnspan=5, sticky="w", padx=10, pady=(0, 10))
        self.schedule_check = ctk.CTkCheckBox(auto_frame, text="Daily schedule (local time)", variable=self.schedule_enabled_var)
        self.schedule_check.grid(row=5, column=0, sticky="w", padx=10, pady=(0, 6))
        ctk.CTkEntry(auto_frame, textvariable=self.schedule_start_var, width=68, placeholder_text="08:00").grid(row=5, column=1, padx=(8, 2), pady=(0, 6))
        self.schedule_range_label = ctk.CTkLabel(auto_frame, text="to")
        self.schedule_range_label.grid(row=5, column=2, padx=2, pady=(0, 6))
        ctk.CTkEntry(auto_frame, textvariable=self.schedule_end_var, width=68, placeholder_text="23:00").grid(row=5, column=3, padx=(2, 10), pady=(0, 6), sticky="w")
        self.quiet_hours_check = ctk.CTkCheckBox(auto_frame, text="Quiet hours", variable=self.quiet_hours_enabled_var)
        self.quiet_hours_check.grid(row=6, column=0, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkEntry(auto_frame, textvariable=self.quiet_start_var, width=68, placeholder_text="22:00").grid(row=6, column=1, padx=(8, 2), pady=(0, 10))
        self.quiet_range_label = ctk.CTkLabel(auto_frame, text="to")
        self.quiet_range_label.grid(row=6, column=2, padx=2, pady=(0, 10))
        ctk.CTkEntry(auto_frame, textvariable=self.quiet_end_var, width=68, placeholder_text="08:00").grid(row=6, column=3, padx=(2, 10), pady=(0, 10), sticky="w")

        reply_frame = ctk.CTkFrame(self.auto_respond_tab)
        reply_frame.pack(fill="x", pady=6)
        self.auto_respond_title = ctk.CTkLabel(
            reply_frame,
            text="Auto respond (private messages and room chat)",
            font=ctk.CTkFont(weight="bold"),
        )
        self.auto_respond_title.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 4))
        self.auto_respond_enabled_var = tk.BooleanVar(value=False)
        self.auto_respond_private_var = tk.BooleanVar(value=True)
        self.auto_respond_room_var = tk.BooleanVar(value=True)
        self.auto_respond_username_var = tk.StringVar()
        self.auto_respond_cooldown_var = tk.StringVar(value="60")
        self.auto_respond_poll_var = tk.StringVar(value="2")
        self.auto_respond_enabled_check = ctk.CTkCheckBox(
            reply_frame, text="Enable auto respond", variable=self.auto_respond_enabled_var
        )
        self.auto_respond_enabled_check.grid(row=1, column=0, sticky="w", padx=10, pady=4)
        self.auto_respond_private_check = ctk.CTkCheckBox(
            reply_frame, text="Private messages", variable=self.auto_respond_private_var
        )
        self.auto_respond_private_check.grid(row=1, column=1, sticky="w", padx=6, pady=4)
        self.auto_respond_room_check = ctk.CTkCheckBox(
            reply_frame, text="Room chat", variable=self.auto_respond_room_var
        )
        self.auto_respond_room_check.grid(row=1, column=2, sticky="w", padx=6, pady=4)
        self.auto_respond_state_label = ctk.CTkLabel(reply_frame, text="Disabled")
        self.auto_respond_state_label.grid(row=1, column=3, sticky="e", padx=10, pady=4)

        self.auto_respond_reply_label = ctk.CTkLabel(reply_frame, text="Reply text (new lines are kept)")
        self.auto_respond_reply_label.grid(row=2, column=0, sticky="w", padx=10, pady=4)
        self.auto_respond_reply_box = ctk.CTkTextbox(reply_frame, height=76, wrap="word")
        self.auto_respond_reply_box.grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=10, pady=4
        )
        self.auto_respond_reply_box.insert("1.0", "Thanks for your message.")
        ctk.CTkLabel(reply_frame, text="Your Camfrog nickname").grid(row=3, column=0, sticky="w", padx=10, pady=4)
        ctk.CTkEntry(reply_frame, textvariable=self.auto_respond_username_var).grid(
            row=3, column=1, sticky="ew", padx=10, pady=4
        )
        ctk.CTkLabel(reply_frame, text="Cooldown seconds").grid(row=3, column=2, sticky="e", padx=(8, 4), pady=4)
        ctk.CTkEntry(reply_frame, textvariable=self.auto_respond_cooldown_var, width=72).grid(
            row=3, column=3, sticky="e", padx=10, pady=4
        )
        self.auto_respond_inspect_button = ctk.CTkButton(
            reply_frame, text="Inspect chat controls", command=self._inspect_auto_respond_controls
        )
        self.auto_respond_inspect_button.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))
        ctk.CTkLabel(reply_frame, text="Poll seconds").grid(row=4, column=2, sticky="e", padx=(8, 4), pady=(0, 6))
        ctk.CTkEntry(reply_frame, textvariable=self.auto_respond_poll_var, width=72).grid(
            row=4, column=3, sticky="e", padx=10, pady=(0, 6)
        )

        self.auto_respond_selector_vars = {}
        self.auto_respond_selector_labels = {}
        for row, kind, kind_label in (
            (5, "private", "Private chat UIA mapping"),
            (6, "room", "Room chat UIA mapping"),
        ):
            mapping = ctk.CTkFrame(reply_frame, fg_color="transparent")
            mapping.grid(row=row, column=0, columnspan=4, sticky="ew", padx=6, pady=(2, 4))
            heading = ctk.CTkLabel(mapping, text=kind_label, font=ctk.CTkFont(weight="bold"))
            heading.grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 2))
            self.auto_respond_selector_labels[kind] = heading
            fields = (
                ("window_title_contains", "Window title contains"),
                ("history_automation_id", "History Automation ID"),
                ("input_automation_id", "Message input Automation ID"),
                ("send_automation_id", "Send button Automation ID"),
            )
            self.auto_respond_selector_vars[kind] = {}
            for index, (key, label) in enumerate(fields):
                column = index % 2
                base_row = 1 + (index // 2) * 2
                var = tk.StringVar()
                self.auto_respond_selector_vars[kind][key] = var
                widget = ctk.CTkLabel(mapping, text=label)
                widget.grid(row=base_row, column=column, sticky="w", padx=4, pady=(2, 0))
                self.auto_respond_selector_labels[f"{kind}:{key}"] = widget
                ctk.CTkEntry(mapping, textvariable=var).grid(
                    row=base_row + 1, column=column, sticky="ew", padx=4, pady=(0, 3)
                )
            mapping.grid_columnconfigure(0, weight=1)
            mapping.grid_columnconfigure(1, weight=1)

        self.auto_respond_note = ctk.CTkLabel(
            reply_frame,
            text=("Configure exact UIA IDs for each chat type. Only new visible 'sender: message' lines are considered; "
                  "your nickname is ignored and unsent drafts are never overwritten."),
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self.auto_respond_note.grid(row=7, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 8))
        reply_frame.grid_columnconfigure(1, weight=1)
        reply_frame.grid_columnconfigure(2, weight=1)

        room_actions_frame = ctk.CTkFrame(self.room_commands_tab)
        room_actions_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(
            room_actions_frame,
            text="Room owner controls (manual confirmation; bad-word auto-kick is configurable)",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 4))
        self.room_action_enabled_var = tk.BooleanVar(value=False)
        self.room_action_var = tk.StringVar(value="kick")
        self.room_action_target_var = tk.StringVar()
        self.room_action_room_title_var = tk.StringVar()
        self.room_action_owner_var = tk.StringVar()
        self.room_action_target_nicknames = {}
        self._last_room_action_selection = self.room_action_var.get()
        self.room_action_template_vars = {}
        self.room_action_enabled_check = ctk.CTkCheckBox(
            room_actions_frame,
            text="Enable configured room commands",
            variable=self.room_action_enabled_var,
        )
        self.room_action_enabled_check.grid(row=1, column=0, sticky="w", padx=10, pady=4)
        ctk.CTkLabel(
            room_actions_frame,
            text="Commands and moderation are restricted to the exact room title below.",
            wraplength=650,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=4)
        ctk.CTkLabel(room_actions_frame, text="Room name").grid(row=3, column=0, sticky="w", padx=10, pady=4)
        ctk.CTkEntry(room_actions_frame, textvariable=self.room_action_room_title_var).grid(
            row=3, column=1, sticky="ew", padx=6, pady=4
        )
        ctk.CTkLabel(room_actions_frame, text="Owner nickname").grid(row=3, column=2, sticky="e", padx=6, pady=4)
        ctk.CTkEntry(room_actions_frame, textvariable=self.room_action_owner_var).grid(
            row=3, column=3, sticky="ew", padx=(6, 10), pady=4
        )
        ctk.CTkLabel(room_actions_frame, text="Target nickname").grid(row=4, column=0, sticky="w", padx=10, pady=4)
        ctk.CTkEntry(room_actions_frame, textvariable=self.room_action_target_var).grid(
            row=4, column=1, sticky="ew", padx=6, pady=4
        )
        self.room_action_menu = ctk.CTkOptionMenu(
            room_actions_frame,
            values=["op", "friend", "admin", "owner", "mute", "kick", "ban"],
            variable=self.room_action_var,
            width=110,
            command=self._room_action_selected,
        )
        self.room_action_menu.grid(row=4, column=2, padx=6, pady=4)
        ctk.CTkButton(
            room_actions_frame,
            text="Confirm and send",
            command=self._send_room_action,
        ).grid(row=4, column=3, padx=(6, 10), pady=4)

        ctk.CTkLabel(
            room_actions_frame,
            text="Command templates (start with / and include {username} exactly once)",
        ).grid(row=5, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 2))
        for row, action in enumerate(("op", "friend", "admin", "owner", "mute", "kick", "ban"), start=6):
            ctk.CTkLabel(room_actions_frame, text=action.upper(), width=75).grid(
                row=row, column=0, sticky="w", padx=10, pady=2
            )
            variable = tk.StringVar()
            self.room_action_template_vars[action] = variable
            ctk.CTkEntry(room_actions_frame, textvariable=variable).grid(
                row=row, column=1, columnspan=3, sticky="ew", padx=(6, 10), pady=2
            )

        self.bad_word_enabled_var = tk.BooleanVar(value=False)
        bad_word_frame = ctk.CTkFrame(self.bad_words_tab)
        bad_word_frame.pack(fill="x", pady=6)
        self.bad_word_enabled_check = ctk.CTkCheckBox(
            bad_word_frame,
            text="Watch new room messages for configured bad words",
            variable=self.bad_word_enabled_var,
        )
        self.bad_word_enabled_check.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 4))
        self.bad_word_auto_kick_var = tk.BooleanVar(value=False)
        self.bad_word_auto_kick_check = ctk.CTkCheckBox(
            bad_word_frame,
            text="Automatically kick a match without confirmation (uses the configured kick template)",
            variable=self.bad_word_auto_kick_var,
        )
        self.bad_word_auto_kick_check.grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=4)
        ctk.CTkLabel(
            bad_word_frame,
            text="Bad-word terms (one phrase per line; matching ignores case)",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 2))
        ctk.CTkButton(
            bad_word_frame,
            text="Add all categorized terms",
            width=190,
            command=self._load_bad_word_starter_terms,
        ).grid(row=2, column=3, sticky="e", padx=10, pady=(2, 2))
        self.bad_word_terms_box = ctk.CTkTextbox(bad_word_frame, height=170)
        self.bad_word_terms_box.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 4))
        self.bad_word_cooldown_var = tk.StringVar(value="60")
        ctk.CTkLabel(bad_word_frame, text="Bad-word cooldown seconds").grid(
            row=4, column=0, sticky="w", padx=10, pady=2
        )
        ctk.CTkEntry(bad_word_frame, textvariable=self.bad_word_cooldown_var, width=90).grid(
            row=4, column=1, sticky="w", padx=6, pady=2
        )
        self.bad_word_state_label = ctk.CTkLabel(bad_word_frame, text="Bad-word monitor is disabled")
        self.bad_word_state_label.grid(row=5, column=0, columnspan=4, sticky="w", padx=10, pady=(2, 2))
        ctk.CTkLabel(
            bad_word_frame,
            text="Detection checks new visible lines only. Automatic kick is opt-in and uses the saved kick command, room selectors, and cooldown.",
            wraplength=650,
            justify="left",
        ).grid(row=6, column=0, columnspan=4, sticky="w", padx=10, pady=(2, 8))

        room_events_frame = ctk.CTkFrame(self.room_events_tab)
        room_events_frame.pack(fill="x", pady=6)
        self.room_event_enabled_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            room_events_frame,
            text="Notify on configured room events",
            variable=self.room_event_enabled_var,
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(
            room_events_frame,
            text="Room event phrases (one case-insensitive phrase per line; only new visible history lines trigger)",
            wraplength=650,
            justify="left",
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        self.room_event_phrases_box = ctk.CTkTextbox(room_events_frame, height=140)
        self.room_event_phrases_box.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=2)
        self.room_event_state_label = ctk.CTkLabel(room_events_frame, text="Room event notifications are disabled")
        self.room_event_state_label.grid(row=3, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        ctk.CTkLabel(room_events_frame, text="Recent room event activity (in memory only)").grid(
            row=4, column=0, columnspan=4, sticky="w", padx=10, pady=(4, 2)
        )
        self.room_event_log_box = ctk.CTkTextbox(room_events_frame, height=100)
        self.room_event_log_box.configure(state="disabled")
        self.room_event_log_box.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 8))
        for section in (room_actions_frame, bad_word_frame, room_events_frame):
            section.grid_columnconfigure(1, weight=1)
            section.grid_columnconfigure(2, weight=0)
            section.grid_columnconfigure(3, weight=0)

        profile_frame = ctk.CTkFrame(self.profile_tab)
        profile_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(
            profile_frame,
            text="Camfrog web profile",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 4))
        ctk.CTkLabel(profile_frame, text="Camfrog nickname").grid(
            row=1, column=0, sticky="w", padx=10, pady=4
        )
        self.profile_nickname_var = tk.StringVar()
        ctk.CTkEntry(profile_frame, textvariable=self.profile_nickname_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=4
        )
        ctk.CTkButton(profile_frame, text="Open profile", command=self._open_camfrog_profile).grid(
            row=2, column=0, sticky="w", padx=10, pady=(4, 8)
        )
        ctk.CTkButton(profile_frame, text="Copy profile link", command=self._copy_camfrog_profile_link).grid(
            row=2, column=1, sticky="w", padx=6, pady=(4, 8)
        )
        ctk.CTkButton(profile_frame, text="Open profiles & leaderboard", command=self._open_camfrog_profile_directory).grid(
            row=2, column=2, sticky="w", padx=6, pady=(4, 8)
        )
        ctk.CTkLabel(
            profile_frame,
            text=(
                "Profile editing, preview, sharing, and sign-in happen on the official Camfrog website. "
                "This app never asks for your password. Treat profile details as public."
            ),
            wraplength=680,
            justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))
        profile_frame.grid_columnconfigure(1, weight=1)

        tov_frame = ctk.CTkFrame(self.tov_tab)
        tov_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(tov_frame, text="Text Over Video settings", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(12, 6))
        ctk.CTkLabel(
            tov_frame,
            text=("The 2026-10-02 recording visually confirms the enable checkbox, text field, background/text color pickers, horizontal/vertical alignment, transparency, font dialog, preview, and Apply button. Editing stays disabled until the live control identifiers and saved value formats are verified."),
            wraplength=680,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))
        self.tov_inspect_button = ctk.CTkButton(
            tov_frame,
            text="Inspect visible Camfrog Settings controls",
            command=self._inspect_video_overlay_controls,
        )
        self.tov_inspect_button.pack(anchor="w", padx=12, pady=(0, 6))
        self.tov_inspect_state_label = ctk.CTkLabel(
            tov_frame,
            text="Open the Text Over Video page in Camfrog before inspecting. The report omits Edit and ComboBox values and does not change settings.",
            wraplength=680,
            justify="left",
            anchor="w",
        )
        self.tov_inspect_state_label.pack(fill="x", padx=12, pady=(0, 12))

        buttons = ctk.CTkFrame(root, fg_color="transparent")
        buttons.pack(fill="x", pady=12)
        ctk.CTkButton(buttons, text="Save settings", command=self._save).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text="Start rotation", command=self._start_rotation).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Stop rotation", command=self._stop_rotation).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Open config folder", command=self._open_config_dir).pack(side="right")

    def _tr(self, en: str, th: str) -> str:
        return th if getattr(self, "language_var", None) is not None and self.language_var.get() == "TH" else en

    def _load_bad_word_starter_terms(self):
        current = [
            line.strip()
            for line in self.bad_word_terms_box.get("1.0", "end-1c").splitlines()
            if line.strip()
        ]
        seen = {term.casefold() for term in current}
        merged = list(current)
        for term in DEFAULT_BAD_WORD_TERMS:
            key = term.casefold()
            if key not in seen:
                merged.append(term)
                seen.add(key)
        self.bad_word_terms_box.delete("1.0", "end")
        self.bad_word_terms_box.insert("1.0", "\n".join(merged))

    @staticmethod
    def _unit_internal(value: str) -> str:
        return {"วินาที":"seconds", "นาที":"minutes", "ชั่วโมง":"hours"}.get(value, value)

    @staticmethod
    def _mode_internal(value: str) -> str:
        return {"ตามลำดับ":"sequential", "สุ่ม":"random"}.get(value, value)

    @staticmethod
    def _rotation_source_internal(value: str) -> str:
        normalized = " ".join(str(value).casefold().split())
        if normalized in {
            "camfrog status history (random)",
            "camfrog status history",
            "สุ่มจากประวัติสถานะ camfrog",
        }:
            return "camfrog_history"
        return "messages"

    @staticmethod
    def _rotation_source_label(source: str, language: str = "EN") -> str:
        if str(source).casefold() == "camfrog_history":
            return "สุ่มจากประวัติสถานะ Camfrog" if str(language).upper() == "TH" else "Camfrog Status History (random)"
        return "ข้อความ 1–4" if str(language).upper() == "TH" else "Messages 1–4"

    def _rotation_source_changed(self, _value=None):
        source = self._rotation_source_internal(self.rotation_source_var.get())
        if source == "camfrog_history":
            language = self.language_var.get()
            self.mode_var.set("สุ่ม" if language == "TH" else "random")
            self.mode_menu.configure(state="disabled")
        else:
            self.mode_menu.configure(state="normal")
        try:
            self._sync_ui_to_config()
        except Exception:
            pass
        if self.rotation.running:
            self._start_rotation()

    def _rotation_messages(self, config: dict) -> list[str]:
        rotation = config.get("status", {}).get("rotation", {})
        source = self._rotation_source_internal(
            self.rotation_source_var.get()
            if hasattr(self, "rotation_source_var")
            else rotation.get("source", "messages")
        )
        if source != "camfrog_history":
            return [
                str(value).strip()
                for value in config.get("status", {}).get("editor_messages", [])
                if str(value).strip()
            ]

        values = list(getattr(self, "_history_values", []))
        if not values and os.name == "nt":
            try:
                result = read_camfrog_custom_statuses()
                values = list(result.statuses or [])
                self._history_values = values
            except Exception:
                log.warning("Could not read Camfrog status history for rotation", exc_info=True)
        return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))

    def _style_changed(self):
        self._refresh_status_preview()
        try:
            self._sync_ui_to_config()
        except Exception:
            pass

    def _marquee_toggled(self):
        self._style_changed()
        if not self.marquee_var.get():
            self.marquee_animation.stop()
        if self.rotation.running:
            c = self.config_data
            messages = self._rotation_messages(c)
            if messages:
                self.rotation.start(
                    messages,
                    int(c["status"]["rotation"].get("interval_seconds", 600)),
                    "random" if c["status"]["rotation"].get("source") == "camfrog_history" else c["status"]["rotation"].get("mode", "sequential"),
                    schedule=c["status"]["rotation"],
                    marquee_enabled=bool(self.marquee_var.get()),
                    marquee_frame_interval_seconds=self._marquee_interval_seconds(c),
                    marquee_progressive_delays=bool(c["status"].get("styles", {}).get("marquee_single_character", False)),
                    minimum_interval_seconds=int(c.get("advanced", {}).get("minimum_interval_seconds", 5)),
                )
            else:
                self.rotation.stop()

    @staticmethod
    def _marquee_interval_seconds(config: dict) -> int:
        minimum = max(1, int(config.get("advanced", {}).get("minimum_interval_seconds", 5)))
        styles = config.get("status", {}).get("styles", {})
        try:
            configured = int(styles.get("marquee_frame_interval_seconds", 5))
        except (TypeError, ValueError):
            configured = 5
        return min(3600, max(minimum, configured))

    def _random_color_toggled(self):
        if self.random_color_var.get():
            self.custom_color_var.set(False)
        self._style_changed()

    def _custom_color_toggled(self):
        if self.custom_color_var.get():
            self.random_color_var.set(False)
        self._style_changed()

    def _choose_status_color(self):
        _rgb, value = colorchooser.askcolor(
            color=self.custom_color_value.get(),
            title="Choose custom status color",
            parent=self,
        )
        if not value:
            return
        self.custom_color_value.set(value.upper())
        self.custom_color_button.configure(text=value.upper(), fg_color=value)
        self.custom_color_var.set(True)
        self.random_color_var.set(False)
        self._style_changed()

    def _refresh_status_preview(self):
        if not hasattr(self, "status_preview_label"):
            return
        styles = self.config_data.get("status", {}).get("styles", {})
        color_template = str(styles.get("color_template", "[color={color}]{text}[/color]"))
        invalid_template = color_template_error(color_template) is not None
        warning = ""
        if invalid_template:
            warning = (
                "เทมเพลตสีไม่ถูกต้อง; จะส่งข้อความโดยไม่มีมาร์กอัปสี"
                if self.language_var.get() == "TH"
                else "Invalid color template; text will be sent without color markup."
            )
        values = self._message_values() if hasattr(self, "status_message_vars") else []
        if not values:
            empty = "ตัวอย่าง payload ที่จะส่ง: (กรอกข้อความ)" if self.language_var.get() == "TH" else "Outgoing payload preview: (enter a message)"
            self.status_preview_label.configure(text=f"{empty}\n{warning}" if warning else empty)
            return
        payload, _next_offset, _color = apply_styles(
            values[0],
            random_color_enabled=bool(self.random_color_var.get()),
            custom_color_enabled=bool(self.custom_color_var.get()),
            custom_color=self.custom_color_value.get(),
            marquee_enabled=bool(self.marquee_var.get()),
            marquee_offset=self._marquee_offset,
            marquee_width=int(styles.get("marquee_width", 28)),
            marquee_single_character=bool(self.marquee_single_character_var.get()),
            color_template=color_template,
            palette=styles.get("palette", []),
        )
        prefix = "ตัวอย่าง payload ที่จะส่ง: " if self.language_var.get() == "TH" else "Outgoing payload preview: "
        preview = f"{prefix}{payload}"
        self.status_preview_label.configure(text=f"{preview}\n{warning}" if warning else preview)

    def _language_changed(self, value=None):
        lang = "TH" if str(value or self.language_var.get()).upper() == "TH" else "EN"
        self.language_var.set(lang)
        th = lang == "TH"
        self.title("ตัวเปลี่ยนสถานะ Camfrog" if th else "Camfrog Status Changer")
        if hasattr(self, "_auto_respond_last_state"):
            self._render_auto_respond_state()
        if hasattr(self, "messages_title"):
            self.messages_title.configure(text="ข้อความ (1 ข้อความ = 1 ครั้ง)" if th else "Messages (1 message = 1 apply)")
            for i, lbl in enumerate(self.message_labels, 1):
                lbl.configure(text=(f"ข้อความ {i}" if th else f"Message {i}"))
            for btn in self.message_apply_buttons:
                btn.configure(text="ใช้" if th else "Apply")
            self.random_color_check.configure(text="สุ่มสีข้อความ" if th else "Random Color")
            self.custom_color_check.configure(text="กำหนดสี" if th else "Custom Color")
            self.marquee_check.configure(text="ข้อความวิ่ง" if th else "Marquee")
            self.marquee_single_character_check.configure(
                text="ส่งทีละ 1 ตัวอักษร" if th else "One character per frame"
            )
            self.status_style_note.configure(
                text=("โหมดทีละตัวอักษรส่งหนึ่งเฟรมและกด Enter หนึ่งครั้ง โดยหน่วงตามค่า Step × 1–5 (ค่าเริ่มต้น 5 วินาที); ยังยืนยันผลตอบรับจาก Camfrog ไม่ได้."
                      if th else "One-character marquee sends one verified frame and one Enter per update. Delay steps are the configured interval multiplied by 1–5 (default 5 seconds); Camfrog acceptance is not independently confirmed.")
            )
            self.standard_status_title.configure(text="สถานะมาตรฐาน (50 คู่)" if th else "Standard status (50 pairs)")
            self.standard_status_apply_button.configure(text="ส่งไป Camfrog" if th else "Send to Camfrog")
            self.standard_status_stage_button.configure(
                text="ใส่ข้อความเท่านั้น (ไม่กด Enter)" if th else "Stage only (no Enter)"
            )
            self.import_presets_button.configure(text="นำเข้า Presets" if th else "Import presets")
            self.export_presets_button.configure(text="ส่งออก Presets" if th else "Export presets")
            self.schedule_check.configure(text="ช่วงเวลาแต่ละวัน (เวลาท้องถิ่น)" if th else "Daily schedule (local time)")
            self.quiet_hours_check.configure(text="ช่วงงดทำงาน" if th else "Quiet hours")
            self.standard_status_search_entry.configure(placeholder_text="ค้นหาสถานะ TH/EN" if th else "Search EN/TH statuses")
            self.standard_status_category_var.set(STATUS_CATEGORY_LABELS[self.standard_status_category_key][lang])
            self.standard_status_category_menu.configure(values=standard_status_category_values(lang))
            self.language_label.configure(text="ภาษา" if th else "Language")
            self.schedule_range_label.configure(text="ถึง" if th else "to")
            self.quiet_range_label.configure(text="ถึง" if th else "to")
            self.marquee_frame_label.configure(text="ขั้น/วินาที" if th else "Step s")
            if hasattr(self, "rotation_source_menu"):
                source = self._rotation_source_internal(self.rotation_source_var.get())
                self.rotation_source_label.configure(text="แหล่งข้อความ" if th else "Source")
                self.rotation_source_menu.configure(
                    values=(
                        ["ข้อความ 1–4", "สุ่มจากประวัติสถานะ Camfrog"]
                        if th
                        else ["Messages 1–4", "Camfrog Status History (random)"]
                    )
                )
                self.rotation_source_var.set(self._rotation_source_label(source, lang))
            self.auto_respond_title.configure(
                text="ตอบกลับอัตโนมัติ (ข้อความส่วนตัวและแชตห้อง)" if th else "Auto respond (private messages and room chat)"
            )
            self.auto_respond_enabled_check.configure(text="เปิดตอบกลับอัตโนมัติ" if th else "Enable auto respond")
            self.auto_respond_private_check.configure(text="ข้อความส่วนตัว" if th else "Private messages")
            self.auto_respond_room_check.configure(text="แชตห้อง" if th else "Room chat")
            self.auto_respond_reply_label.configure(
                text="ข้อความตอบกลับ (คงการขึ้นบรรทัดใหม่)" if th else "Reply text (new lines are kept)"
            )
            self.auto_respond_inspect_button.configure(text="ตรวจ Control แชต" if th else "Inspect chat controls")
            for widget, en, thai in (
                (self.auto_respond_selector_labels["private"], "Private chat UIA mapping", "UIA สำหรับแชตส่วนตัว"),
                (self.auto_respond_selector_labels["room"], "Room chat UIA mapping", "UIA สำหรับแชตห้อง"),
            ):
                widget.configure(text=thai if th else en)
            selector_text = {
                "window_title_contains": ("ข้อความในชื่อหน้าต่าง", "Window title contains"),
                "history_automation_id": ("History Automation ID", "History Automation ID"),
                "input_automation_id": ("Message input Automation ID", "Message input Automation ID"),
                "send_automation_id": ("Send button Automation ID", "Send button Automation ID"),
            }
            for kind in ("private", "room"):
                for key, (thai, english) in selector_text.items():
                    self.auto_respond_selector_labels[f"{kind}:{key}"].configure(text=thai if th else english)
            self.auto_respond_note.configure(
                text=("กำหนด UIA ID ของแต่ละหน้าต่างแชต ระบบอ่านเฉพาะบรรทัดใหม่รูปแบบ 'ผู้ส่ง: ข้อความ' "
                      "ละเว้นชื่อบัญชีของคุณ และจะไม่เขียนทับข้อความร่างที่ยังไม่ส่ง."
                      if th else
                      "Configure exact UIA IDs for each chat type. Only new visible 'sender: message' lines are considered; "
                      "your nickname is ignored and unsent drafts are never overwritten.")
            )
        if hasattr(self, "standard_status_menu"):
            self._refresh_standard_status_dropdown()
        # Translate all static widgets by their current EN/TH text.
        pairs = {
            "Camfrog executable":"ไฟล์โปรแกรม Camfrog", "Browse":"เลือกไฟล์", "Detect":"ตรวจหา", "Native profile":"โปรไฟล์ Native",
            "Camfrog Runtime":"การทำงาน Camfrog", "Bind PID":"ผูก PID", "Start / Connect":"เปิด / เชื่อมต่อ", "Disconnect":"ยกเลิกการเชื่อมต่อ",
            "Camfrog web profile":"โปรไฟล์ Camfrog บนเว็บ", "Camfrog nickname":"ชื่อบัญชี Camfrog",
            "Open profile":"เปิดโปรไฟล์", "Copy profile link":"คัดลอกลิงก์โปรไฟล์",
            "Open profiles & leaderboard":"เปิดโปรไฟล์และอันดับสมาชิก",
            "Profile editing, preview, sharing, and sign-in happen on the official Camfrog website. This app never asks for your password. Treat profile details as public.":"แก้ไข ดูตัวอย่าง แชร์ และลงชื่อเข้าใช้บนเว็บไซต์ทางการ Camfrog เท่านั้น แอปนี้ไม่ถามรหัสผ่าน และควรมองว่าข้อมูลโปรไฟล์เป็นข้อมูลสาธารณะ",
            "UI Automation target":"เป้าหมาย UI Automation", "Control type":"ชนิด Control", "Automation ID (optional)":"Automation ID (ไม่บังคับ)",
            "Title regex":"Title regex", "Inspect":"ตรวจ Control", "Fallback X (relative)":"Fallback X (สัมพัทธ์)", "Fallback Y (relative)":"Fallback Y (สัมพัทธ์)",
            "Capture target (3s)":"จับตำแหน่ง (3 วิ)", "Presets (one per line)":"Presets (หนึ่งข้อความต่อบรรทัด)", "Read Camfrog History":"อ่านประวัติ Camfrog",
            "Standard status (50 pairs)":"สถานะมาตรฐาน (50 คู่)", "Send to Camfrog":"ส่งไป Camfrog",
            "Read Camfrog status history on startup (read-only)":"อ่านประวัติสถานะ Camfrog ตอนเปิดโปรแกรม (อ่านอย่างเดียว)",
            "Camfrog History (read-only)":"ประวัติ Camfrog (อ่านอย่างเดียว)", "Import all → Presets":"นำเข้าทั้งหมด → Presets",
            "Enable status rotation":"เปิดการหมุนข้อความ", "Interval":"ช่วงเวลา", "Start with Windows":"เริ่มพร้อม Windows",
            "Daily schedule (local time)":"ช่วงเวลาแต่ละวัน (เวลาท้องถิ่น)", "Quiet hours":"ช่วงงดทำงาน", "to":"ถึง",
            "Import presets":"นำเข้า Presets", "Export presets":"ส่งออก Presets",
            "Start Camfrog if not running":"เปิด Camfrog หากยังไม่ทำงาน",
            "UIA verified commit brings Camfrog forward; background Win32 is a fallback only":"UIA ที่ยืนยันข้อความแล้วจะดึง Camfrog ขึ้นหน้า; Win32 เบื้องหลังใช้เป็น fallback เท่านั้น",
            "Allow background Win32 fallback when UIA cannot verify (keeps Camfrog in background)":"อนุญาต Win32 เบื้องหลังเมื่อ UIA ตรวจข้อความไม่ได้ (Camfrog ไม่ถูกดึงขึ้นหน้า)",
            "Allow coordinate fallback if UIA text cannot be verified (focuses Camfrog)":"อนุญาต fallback ตามพิกัดเมื่อ UIA ตรวจข้อความไม่ได้ (ดึง Camfrog ขึ้นหน้า)",
            "Save settings":"บันทึกการตั้งค่า", "Start rotation":"เริ่มหมุนข้อความ", "Stop rotation":"หยุดหมุนข้อความ", "Open config folder":"เปิดโฟลเดอร์ config",
            "Auto respond (private messages and room chat)":"ตอบกลับอัตโนมัติ (ข้อความส่วนตัวและแชตห้อง)",
            "Enable auto respond":"เปิดตอบกลับอัตโนมัติ", "Private messages":"ข้อความส่วนตัว", "Room chat":"แชตห้อง",
            "Reply text (new lines are kept)":"ข้อความตอบกลับ (คงการขึ้นบรรทัดใหม่)", "Your Camfrog nickname":"ชื่อบัญชี Camfrog ของคุณ",
            "Cooldown seconds":"พักก่อนตอบซ้ำ (วินาที)", "Poll seconds":"ช่วงตรวจข้อความ (วินาที)", "Disabled":"ปิดอยู่",
            "Inspect chat controls":"ตรวจ Control แชต",
            "Private chat UIA mapping":"UIA สำหรับแชตส่วนตัว", "Room chat UIA mapping":"UIA สำหรับแชตห้อง",
            "Window title contains":"ข้อความในชื่อหน้าต่าง", "History Automation ID":"History Automation ID",
            "Message input Automation ID":"Message input Automation ID", "Send button Automation ID":"Send button Automation ID",
            "Room owner controls (manual confirmation; bad-word auto-kick is configurable)":"การควบคุมห้อง (ยืนยันด้วยตนเอง; ตั้งค่า kick อัตโนมัติจากคำได้)",
            "Enable configured room commands":"เปิดใช้คำสั่งห้องที่ตั้งค่าไว้",
            "Commands and moderation are restricted to the exact room title below.":"คำสั่งและการตรวจข้อความจำกัดอยู่ในห้องที่ระบุชื่อตรงกันด้านล่าง",
            "Room name":"ชื่อห้อง", "Owner nickname":"ชื่อบัญชีเจ้าของห้อง",
            "Target nickname":"ชื่อบัญชีเป้าหมาย", "Confirm and send":"ยืนยันและส่ง",
            "Command templates (start with / and include {username} exactly once)":"แม่แบบคำสั่ง (ขึ้นต้นด้วย / และมี {username} หนึ่งตำแหน่ง)",
            "Watch new room messages for configured bad words":"ตรวจข้อความใหม่ในห้องสำหรับคำที่ตั้งไว้",
            "Automatically kick a match without confirmation (uses the configured kick template)":"kick อัตโนมัติเมื่อพบคำ โดยไม่ถามยืนยัน (ใช้แม่แบบ kick ที่ตั้งไว้)",
            "Bad-word terms (one phrase per line; matching ignores case)":"คำที่ต้องตรวจ (หนึ่งวลีต่อบรรทัด; ไม่แยกตัวพิมพ์ใหญ่เล็ก)",
            "Add all categorized terms":"เพิ่มคำเริ่มต้นทุกหมวด",
            "Bad-word cooldown seconds":"ช่วงพักการแจ้งคำซ้ำ (วินาที)",
            "Bad-word monitoring is disabled":"ปิดการตรวจคำในแชต",
            "Detection checks new visible lines only. Automatic kick is opt-in and uses the saved kick command, room selectors, and cooldown.":"ตรวจเฉพาะบรรทัดใหม่ที่มองเห็น การ kick อัตโนมัติต้องเปิดใช้เอง และใช้คำสั่ง kick, ตัวเลือกห้อง และช่วงพักที่บันทึกไว้",
            "Notify on configured room events":"แจ้งเตือนเหตุการณ์ห้องตามคำที่ตั้งไว้",
            "Room event phrases (one case-insensitive phrase per line; only new visible history lines trigger)":"วลีเหตุการณ์ห้อง (หนึ่งวลีต่อบรรทัด; ไม่สนตัวพิมพ์เล็กใหญ่; ตรวจเฉพาะบรรทัดประวัติใหม่ที่มองเห็น)",
            "Recent room event activity (in memory only)":"กิจกรรมเหตุการณ์ห้องล่าสุด (เก็บในหน่วยความจำเท่านั้น)"
        }
        reverse = {v:k for k,v in pairs.items()}
        def walk(w):
            for child in w.winfo_children():
                try:
                    text = child.cget("text")
                    if th and text in pairs:
                        child.configure(text=pairs[text])
                    elif not th and text in reverse:
                        child.configure(text=reverse[text])
                except Exception:
                    pass
                walk(child)
        walk(self)
        if hasattr(self, "interval_unit_menu"):
            internal_unit = self._unit_internal(self.interval_unit_var.get())
            internal_mode = self._mode_internal(self.mode_var.get())
            internal_source = self._rotation_source_internal(self.rotation_source_var.get())
            if internal_source == "camfrog_history":
                internal_mode = "random"
            unit_map = {"seconds":"วินาที", "minutes":"นาที", "hours":"ชั่วโมง"}
            mode_map = {"sequential":"ตามลำดับ", "random":"สุ่ม"}
            self.interval_unit_menu.configure(values=["วินาที","นาที","ชั่วโมง"] if th else ["seconds","minutes","hours"])
            self.interval_unit_var.set(unit_map.get(internal_unit, "นาที") if th else internal_unit)
            self.mode_menu.configure(values=["ตามลำดับ","สุ่ม"] if th else ["sequential","random"])
            self.mode_var.set(mode_map.get(internal_mode, "ตามลำดับ") if th else internal_mode)
            self.mode_menu.configure(state="disabled" if internal_source == "camfrog_history" else "normal")
        try:
            self._sync_ui_to_config()
        except Exception:
            pass
        self._refresh_status_preview()
        if hasattr(self, "bad_word_state_label"):
            self._render_bad_word_state()

    def _styled_value(self, value: str, advance: bool = False) -> str:
        styles = self.config_data.get("status", {}).get("styles", {})
        random_color_enabled = bool(self.random_color_var.get()) if hasattr(self, "random_color_var") else bool(styles.get("random_color", False))
        custom_color_enabled = bool(self.custom_color_var.get()) if hasattr(self, "custom_color_var") else bool(styles.get("custom_color_enabled", False))
        custom_color = self.custom_color_value.get() if hasattr(self, "custom_color_value") else str(styles.get("custom_color", "#00C7BE"))
        marquee_enabled = bool(self.marquee_var.get()) if hasattr(self, "marquee_var") else bool(styles.get("marquee", False))
        marquee_single_character = bool(
            self.marquee_single_character_var.get()
            if hasattr(self, "marquee_single_character_var")
            else styles.get("marquee_single_character", True)
        )
        with self._style_lock:
            styled, next_offset, _ = apply_styles(
                value,
                random_color_enabled=random_color_enabled,
                custom_color_enabled=custom_color_enabled,
                custom_color=custom_color,
                marquee_enabled=marquee_enabled,
                marquee_offset=self._marquee_offset,
                marquee_width=int(styles.get("marquee_width", 28)),
                marquee_single_character=marquee_single_character,
                color_template=str(styles.get("color_template", "[color={color}]{text}[/color]")),
                palette=styles.get("palette", []),
            )
            if advance and marquee_enabled:
                self._marquee_offset = next_offset
        return styled

    def _message_values(self) -> list[str]:
        return [v.get().replace("\x00", "").strip() for v in self.status_message_vars if v.get().replace("\x00", "").strip()]

    def _refresh_standard_status_dropdown(self):
        status = get_standard_status(self.standard_status_id_var.get()) or get_standard_status(DEFAULT_STANDARD_STATUS_ID)
        self.standard_status_id_var.set(status.id)
        language = self.language_var.get()
        favorite_ids = self.config_data.get("status", {}).get("favorite_standard_ids", [])
        matches = filter_standard_statuses(
            self.standard_status_search_var.get(),
            self.standard_status_category_key,
            favorite_ids,
        )
        labels = [item.dropdown_label(language) for item in matches]
        self.standard_status_menu.configure(values=labels or [self._tr("No matching statuses", "ไม่พบสถานะที่ตรงกัน")])
        self.standard_status_display_var.set(status.dropdown_label(language))
        self._refresh_standard_status_favorite_button()

    def _standard_status_category_changed(self, label: str):
        self.standard_status_category_key = category_key_from_label(label, self.language_var.get())
        self._refresh_standard_status_dropdown()

    def _refresh_standard_status_favorite_button(self):
        if not hasattr(self, "standard_status_favorite_button"):
            return
        status_id = self.standard_status_id_var.get()
        favorites = self.config_data.get("status", {}).get("favorite_standard_ids", [])
        favorite = status_id in favorites
        self.standard_status_favorite_button.configure(
            text=("★ รายการโปรด" if favorite else "☆ รายการโปรด")
            if self.language_var.get() == "TH"
            else ("★ Favorite" if favorite else "☆ Favorite")
        )

    def _toggle_standard_status_favorite(self):
        status_id = self.standard_status_id_var.get()
        favorites = list(self.config_data.setdefault("status", {}).get("favorite_standard_ids", []))
        if status_id in favorites:
            favorites.remove(status_id)
        else:
            favorites.append(status_id)
        self.config_data["status"]["favorite_standard_ids"] = favorites
        self.store.save(self.config_data)
        self._refresh_standard_status_dropdown()

    def _standard_status_selected(self, label: str):
        status = find_standard_status_by_label(label, self.language_var.get())
        if status is None:
            return
        self.standard_status_id_var.set(status.id)
        value = status.text_for(self.language_var.get())
        self.status_message_vars[0].set(value)
        self._refresh_standard_status_favorite_button()
        self._sync_ui_to_config()
        self._refresh_status_preview()

    def _apply_standard_status_clicked(self):
        status = get_standard_status(self.standard_status_id_var.get())
        if status is None:
            messagebox.showwarning("Status", "เลือกสถานะมาตรฐานก่อน" if self.language_var.get() == "TH" else "Select a standard status first.")
            return
        self.status_message_vars[0].set(status.text_for(self.language_var.get()))
        self._apply_message_clicked(0)

    def _stage_standard_status_clicked(self):
        status = get_standard_status(self.standard_status_id_var.get())
        if status is None:
            messagebox.showwarning("Status", "เลือกสถานะมาตรฐานก่อน" if self.language_var.get() == "TH" else "Select a standard status first.")
            return
        value = status.text_for(self.language_var.get())
        self.status_message_vars[0].set(value)
        self._sync_ui_to_config()
        self.state_label.configure(
            text="กำลังใส่ข้อความลงช่อง status โดยไม่กด Enter..."
            if self.language_var.get() == "TH"
            else "Staging status text without Enter..."
        )
        threading.Thread(target=self._stage_status_worker, args=(value,), daemon=True).start()

    def _stage_status_worker(self, value):
        result = self.controller.stage_status_text(value)
        self.after(0, lambda: self._show_result(result))

    def _apply_message_clicked(self, index: int):
        self._sync_ui_to_config()
        value = self.status_message_vars[index].get().replace("\x00", "").strip()
        if not value:
            messagebox.showwarning("Status", "กรอกข้อความก่อน" if self.language_var.get() == "TH" else "Enter a message first.")
            return
        if self.marquee_var.get() and not self.rotation.running:
            styles = self.config_data.get("status", {}).get("styles", {})
            single_character = bool(styles.get("marquee_single_character", True))
            self._marquee_offset = 0 if single_character else int(styles.get("marquee_width", 28))
            interval = self._marquee_interval_seconds(self.config_data)
            self.marquee_animation.start(
                value,
                interval,
                progressive_delays=single_character,
                minimum_interval_seconds=int(self.config_data.get("advanced", {}).get("minimum_interval_seconds", 5)),
            )
            if single_character:
                steps = ", ".join(str(interval * n) for n in range(1, 6))
                state_text = (
                    f"เริ่มข้อความวิ่งทีละตัวอักษร; หน่วง {steps} วินาทีวนซ้ำ — ยกเลิก Marquee เพื่อหยุด"
                    if self.language_var.get() == "TH"
                    else f"One-character marquee started; delay steps: {steps}s, repeating. Uncheck Marquee to stop."
                )
            else:
                state_text = (
                    f"เริ่มข้อความวิ่ง; อัปเดตทุก {interval} วินาที — ยกเลิก Marquee เพื่อหยุด"
                    if self.language_var.get() == "TH"
                    else f"Marquee started; Camfrog status updates every {interval}s. Uncheck Marquee to stop."
                )
            self.state_label.configure(text=state_text)
            return
        self.marquee_animation.stop()
        value = self._styled_value(value, advance=bool(self.marquee_var.get()))
        self.state_label.configure(text=(f"กำลังเปลี่ยนเป็นข้อความ {index+1}..." if self.language_var.get() == "TH" else f"Applying message {index+1}..."))
        threading.Thread(target=self._apply_worker, args=(value,), daemon=True).start()

    def _apply_message_from_enter(self, _event, index: int):
        """Apply the message from the focused row when Enter is pressed."""
        self._apply_message_clicked(index)
        return "break"

    def _load_config_to_ui(self):
        c = self.config_data
        self.profile_nickname_var.set(str(c.get("profile_links", {}).get("nickname", "")))
        self.exe_var.set(c["camfrog"].get("executable", ""))
        self.control_type_var.set(c["target"].get("control_type", "ComboBox"))
        self.automation_id_var.set(c["target"].get("automation_id", ""))
        self.title_re_var.set(c["target"].get("title_regex", ".*"))
        self.fallback_x_var.set(str(c["target"].get("fallback_relative_x", 0.50)))
        self.fallback_y_var.set(str(c["target"].get("fallback_relative_y", 0.19)))
        self.rotation_var.set(bool(c["status"]["rotation"].get("enabled", False)))
        interval_seconds = int(c["status"]["rotation"].get("interval_seconds", 600))
        interval_amount, interval_unit = seconds_to_interval(interval_seconds)
        self.interval_var.set(str(interval_amount))
        self.interval_unit_var.set(interval_unit)
        self.mode_var.set(c["status"]["rotation"].get("mode", "sequential"))
        rotation = c["status"]["rotation"]
        self.rotation_source_var.set(
            self._rotation_source_label(
                rotation.get("source", "messages"),
                str(c.get("ui", {}).get("language", "EN")).upper(),
            )
        )
        self.schedule_enabled_var.set(bool(rotation.get("schedule_enabled", False)))
        self.schedule_start_var.set(str(rotation.get("schedule_start", "08:00")))
        self.schedule_end_var.set(str(rotation.get("schedule_end", "23:00")))
        self.quiet_hours_enabled_var.set(bool(rotation.get("quiet_hours_enabled", False)))
        self.quiet_start_var.set(str(rotation.get("quiet_start", "22:00")))
        self.quiet_end_var.set(str(rotation.get("quiet_end", "08:00")))
        self.start_windows_var.set(bool(c["startup"].get("windows_startup", False)))
        self.autostart_camfrog_var.set(bool(c["camfrog"].get("auto_start", False)))
        self.restore_state_var.set(bool(c["camfrog"].get("restore_window_state", True)))
        self.foreground_fallback_var.set(bool(c.get("advanced", {}).get("fallback_enabled", False)))
        self.background_control_var.set(bool(c.get("target", {}).get("background_enabled", True)))
        self.registry_auto_var.set(bool(c.get("registry", {}).get("import_presets_on_start", True)))
        styles = c.get("status", {}).get("styles", {})
        self.random_color_var.set(bool(styles.get("random_color", False)))
        self.custom_color_var.set(bool(styles.get("custom_color_enabled", False)) and not bool(styles.get("random_color", False)))
        self.custom_color_value.set(str(styles.get("custom_color", "#00C7BE")))
        self.custom_color_button.configure(text=self.custom_color_value.get(), fg_color=self.custom_color_value.get())
        self.marquee_var.set(bool(styles.get("marquee", False)))
        self.marquee_single_character_var.set(bool(styles.get("marquee_single_character", True)))
        self.marquee_frame_interval_var.set(str(styles.get("marquee_frame_interval_seconds", 5)))
        self.standard_status_id_var.set(c["status"].get("standard_status_id", DEFAULT_STANDARD_STATUS_ID))
        self.language_var.set(str(c.get("ui", {}).get("language", "EN")).upper())
        self.presets_box.delete("1.0", "end")
        self.presets_box.insert("1.0", "\n".join(c["status"].get("presets", [])))
        messages = c["status"].get("editor_messages", [])
        if not messages:
            messages = c["status"].get("presets", [])[:4]
        messages = list(messages)[:4] + [""] * max(0, 4 - len(messages))
        for var, value in zip(self.status_message_vars, messages[:4]):
            var.set(str(value))
        auto = c.get("auto_respond", {})
        self.auto_respond_enabled_var.set(bool(auto.get("enabled", False)))
        self.auto_respond_private_var.set(bool(auto.get("private_enabled", True)))
        self.auto_respond_room_var.set(bool(auto.get("room_enabled", True)))
        self.auto_respond_reply_box.delete("1.0", "end")
        self.auto_respond_reply_box.insert("1.0", str(auto.get("reply_text", "Thanks for your message.")))
        self.auto_respond_username_var.set(str(auto.get("own_username", "")))
        self.auto_respond_cooldown_var.set(str(auto.get("cooldown_seconds", 60)))
        self.auto_respond_poll_var.set(str(auto.get("poll_interval_seconds", 2)))
        for kind in ("private", "room"):
            selectors = auto.get(kind, {})
            for key, var in self.auto_respond_selector_vars[kind].items():
                var.set(str(selectors.get(key, "")))
        room_actions = c.get("room_actions", {})
        self.room_action_enabled_var.set(bool(room_actions.get("enabled", False)))
        self.room_action_room_title_var.set(str(room_actions.get("room_title", "")))
        self.room_action_owner_var.set(str(room_actions.get("owner_nickname", "")))
        targets = room_actions.get("target_nicknames", {})
        self.room_action_target_nicknames = dict(targets) if isinstance(targets, dict) else {}
        self._last_room_action_selection = str(self.room_action_var.get()).strip().casefold()
        self.room_action_target_var.set(
            str(self.room_action_target_nicknames.get(self._last_room_action_selection, ""))
        )
        templates = room_actions.get("command_templates", {})
        for action, var in self.room_action_template_vars.items():
            var.set(str(templates.get(action, "")))
        moderation = c.get("bad_word_moderation", {})
        self.bad_word_enabled_var.set(bool(moderation.get("enabled", False)))
        self.bad_word_auto_kick_var.set(bool(moderation.get("auto_kick", False)))
        self.bad_word_cooldown_var.set(str(moderation.get("cooldown_seconds", 60)))
        self.bad_word_terms_box.delete("1.0", "end")
        self.bad_word_terms_box.insert("1.0", "\n".join(str(term) for term in moderation.get("terms", [])))
        self._bad_word_last_state = (
            "Bad-word monitoring is disabled" if not self.bad_word_enabled_var.get()
            else "Saved; waiting for room chat selectors"
        )
        self._render_bad_word_state()
        room_events = c.get("room_event_notifications", {})
        self.room_event_enabled_var.set(bool(room_events.get("enabled", False)))
        self.room_event_phrases_box.delete("1.0", "end")
        self.room_event_phrases_box.insert("1.0", "\n".join(str(phrase) for phrase in room_events.get("phrases", [])))
        self._room_event_last_state = (
            "Room event notifications are disabled" if not self.room_event_enabled_var.get()
            else "Saved; waiting for room chat selectors"
        )
        self._render_room_event_state()
        self._auto_respond_last_state = (
            "Auto respond is disabled" if not self.auto_respond_enabled_var.get()
            else "Saved; waiting for UIA setup"
        )
        self._render_auto_respond_state()
        self._language_changed(self.language_var.get())
        self._refresh_status_preview()

    def _sync_ui_to_config(self):
        c = self.config_data
        c.setdefault("profile_links", {})["nickname"] = self.profile_nickname_var.get()
        c["camfrog"]["executable"] = self.exe_var.get().strip()
        c["camfrog"]["auto_start"] = bool(self.autostart_camfrog_var.get())
        c["camfrog"]["restore_window_state"] = bool(self.restore_state_var.get())
        c.setdefault("advanced", {})["fallback_enabled"] = bool(self.foreground_fallback_var.get())
        c.setdefault("target", {})["background_enabled"] = bool(self.background_control_var.get())
        c["target"]["control_type"] = self.control_type_var.get().strip() or "ComboBox"
        c["target"]["automation_id"] = self.automation_id_var.get().strip()
        c["target"]["title_regex"] = self.title_re_var.get().strip() or ".*"
        try:
            fx = float(self.fallback_x_var.get().strip())
            fy = float(self.fallback_y_var.get().strip())
        except ValueError:
            fx, fy = 0.50, 0.19
        c["target"]["fallback_relative_x"] = min(1.0, max(0.0, fx))
        c["target"]["fallback_relative_y"] = min(1.0, max(0.0, fy))
        presets = [x.strip() for x in self.presets_box.get("1.0", "end").splitlines() if x.strip()]
        c["status"]["presets"] = presets
        c["status"]["editor_messages"] = [var.get().replace("\x00", "").strip() for var in self.status_message_vars]
        selected_standard = get_standard_status(self.standard_status_id_var.get())
        c["status"]["standard_status_id"] = selected_standard.id if selected_standard else DEFAULT_STANDARD_STATUS_ID
        c["status"]["rotation"]["enabled"] = bool(self.rotation_var.get())
        unit = self._unit_internal(self.interval_unit_var.get())
        try:
            interval = interval_to_seconds(
                self.interval_var.get(),
                unit,
                minimum_seconds=int(c.get("advanced", {}).get("minimum_interval_seconds", 5)),
            )
        except ValueError:
            # Keep the prior known-good value instead of silently changing units.
            interval = int(c["status"]["rotation"].get("interval_seconds", 600))
        c["status"]["rotation"]["interval_seconds"] = interval
        rotation = c["status"]["rotation"]
        rotation_source = self._rotation_source_internal(
            self.rotation_source_var.get()
            if hasattr(self, "rotation_source_var")
            else rotation.get("source", "messages")
        )
        rotation["source"] = rotation_source
        rotation["mode"] = (
            "random" if rotation_source == "camfrog_history" else self._mode_internal(self.mode_var.get())
        )
        rotation["schedule_enabled"] = bool(self.schedule_enabled_var.get())
        rotation["schedule_start"] = self.schedule_start_var.get().strip()
        rotation["schedule_end"] = self.schedule_end_var.get().strip()
        rotation["quiet_hours_enabled"] = bool(self.quiet_hours_enabled_var.get())
        rotation["quiet_start"] = self.quiet_start_var.get().strip()
        rotation["quiet_end"] = self.quiet_end_var.get().strip()
        c["startup"]["windows_startup"] = bool(self.start_windows_var.get())
        c.setdefault("registry", {})["import_presets_on_start"] = bool(self.registry_auto_var.get())
        styles = c["status"].setdefault("styles", {})
        styles["random_color"] = bool(self.random_color_var.get())
        styles["custom_color_enabled"] = bool(self.custom_color_var.get()) and not bool(self.random_color_var.get())
        styles["custom_color"] = self.custom_color_value.get().strip().upper()
        styles["marquee"] = bool(self.marquee_var.get())
        styles["marquee_single_character"] = bool(
            self.marquee_single_character_var.get()
            if hasattr(self, "marquee_single_character_var")
            else styles.get("marquee_single_character", True)
        )
        try:
            styles["marquee_frame_interval_seconds"] = max(
                int(c.get("advanced", {}).get("minimum_interval_seconds", 5)),
                int(self.marquee_frame_interval_var.get().strip()),
            )
        except (AttributeError, TypeError, ValueError):
            styles["marquee_frame_interval_seconds"] = int(styles.get("marquee_frame_interval_seconds", 5))
        auto = c.setdefault("auto_respond", {})
        auto["enabled"] = bool(self.auto_respond_enabled_var.get())
        auto["private_enabled"] = bool(self.auto_respond_private_var.get())
        auto["room_enabled"] = bool(self.auto_respond_room_var.get())
        auto["reply_text"] = self.auto_respond_reply_box.get("1.0", "end-1c")
        auto["own_username"] = self.auto_respond_username_var.get()
        try:
            auto["cooldown_seconds"] = int(self.auto_respond_cooldown_var.get().strip())
        except ValueError:
            auto["cooldown_seconds"] = int(auto.get("cooldown_seconds", 60))
        try:
            auto["poll_interval_seconds"] = int(self.auto_respond_poll_var.get().strip())
        except ValueError:
            auto["poll_interval_seconds"] = int(auto.get("poll_interval_seconds", 2))
        for kind in ("private", "room"):
            auto[kind] = {
                key: var.get()
                for key, var in self.auto_respond_selector_vars[kind].items()
            }
        room_actions = c.setdefault("room_actions", {})
        room_actions["enabled"] = bool(self.room_action_enabled_var.get())
        room_actions["room_title"] = self.room_action_room_title_var.get()
        room_actions["owner_nickname"] = self.room_action_owner_var.get()
        targets = getattr(self, "room_action_target_nicknames", {})
        targets = dict(targets) if isinstance(targets, dict) else {}
        selected_action = str(self.room_action_var.get()).strip().casefold()
        targets[selected_action] = self.room_action_target_var.get()
        self._last_room_action_selection = selected_action
        room_actions["target_nicknames"] = targets
        room_actions["command_templates"] = {
            action: var.get()
            for action, var in self.room_action_template_vars.items()
        }
        moderation = c.setdefault("bad_word_moderation", {})
        moderation["enabled"] = bool(self.bad_word_enabled_var.get())
        moderation["auto_kick"] = bool(self.bad_word_auto_kick_var.get())
        moderation["terms"] = [
            line.strip()
            for line in self.bad_word_terms_box.get("1.0", "end-1c").splitlines()
            if line.strip()
        ]
        try:
            moderation["cooldown_seconds"] = int(self.bad_word_cooldown_var.get().strip())
        except (AttributeError, TypeError, ValueError):
            moderation["cooldown_seconds"] = int(moderation.get("cooldown_seconds", 60))
        room_events = c.setdefault("room_event_notifications", {})
        room_events["enabled"] = bool(self.room_event_enabled_var.get())
        room_events["phrases"] = [
            line.strip()
            for line in self.room_event_phrases_box.get("1.0", "end-1c").splitlines()
            if line.strip()
        ]
        c.setdefault("ui", {})["language"] = "TH" if self.language_var.get().upper() == "TH" else "EN"
        self.controller.config = c
        return c


    def _profile_link_invalid(self):
        messagebox.showwarning(
            self._tr("Camfrog profile", "โปรไฟล์ Camfrog"),
            self._tr(
                "Enter a valid Camfrog nickname (64 characters or fewer, without path separators).",
                "กรอกชื่อ Camfrog ให้ถูกต้อง (ไม่เกิน 64 ตัวอักษร และไม่มีเครื่องหมาย / หรือ \\)",
            ),
            parent=self,
        )

    def _open_camfrog_profile(self):
        try:
            opened = open_camfrog_profile(self.profile_nickname_var.get())
        except ValueError:
            self._profile_link_invalid()
            return
        except Exception as exc:
            messagebox.showerror(
                self._tr("Camfrog profile", "โปรไฟล์ Camfrog"),
                self._tr(f"Could not open the profile: {exc}", f"เปิดโปรไฟล์ไม่ได้: {exc}"),
                parent=self,
            )
            return
        if opened:
            self.state_label.configure(text=self._tr("Camfrog profile opened in your browser", "เปิดโปรไฟล์ Camfrog ในเบราว์เซอร์แล้ว"))
        else:
            messagebox.showwarning(
                self._tr("Camfrog profile", "โปรไฟล์ Camfrog"),
                self._tr("No default browser could be opened.", "เปิดเบราว์เซอร์เริ่มต้นไม่ได้"),
                parent=self,
            )

    def _copy_camfrog_profile_link(self):
        try:
            url = profile_url_for_nickname(self.profile_nickname_var.get())
        except ValueError:
            self._profile_link_invalid()
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.state_label.configure(text=self._tr("Camfrog profile link copied", "คัดลอกลิงก์โปรไฟล์ Camfrog แล้ว"))

    def _open_camfrog_profile_directory(self):
        try:
            opened = open_camfrog_profile_directory()
        except Exception as exc:
            messagebox.showerror(
                self._tr("Camfrog profiles", "โปรไฟล์ Camfrog"),
                self._tr(f"Could not open Camfrog profiles: {exc}", f"เปิดหน้าโปรไฟล์ Camfrog ไม่ได้: {exc}"),
                parent=self,
            )
            return
        if opened:
            self.state_label.configure(text=self._tr("Camfrog profiles opened in your browser", "เปิดหน้าโปรไฟล์ Camfrog ในเบราว์เซอร์แล้ว"))
        else:
            messagebox.showwarning(
                self._tr("Camfrog profiles", "โปรไฟล์ Camfrog"),
                self._tr("No default browser could be opened.", "เปิดเบราว์เซอร์เริ่มต้นไม่ได้"),
                parent=self,
            )

    def _show_native_profile(self):
        self._sync_ui_to_config()
        info = self.controller.native_profile_info()
        if info.get("matched"):
            anchors = info.get("anchors", {})
            displayed_anchors = (
                "Messages.ChangeStatus.vtable_assign",
                "CSToNet_SetSelfStatus.ctor",
                "CSToNet_SetSelfStatus.vtable_assign",
                "CSNet_SetSelfStatus.ctor",
                "CSNet_SetSelfStatus.vtable_assign",
            )
            summary = "\n".join(
                f"{name}: 0x{int(anchors[name]):X}"
                for name in displayed_anchors
                if name in anchors
            )
            image_base = info.get("image_base")
            image_base_text = f"0x{int(image_base):X}" if image_base is not None else "Unknown"
            messagebox.showinfo(
                "Camfrog Native Profile",
                "Exact SHA-256 profile match.\n\n"
                f"{info.get('name')}\n"
                f"Architecture: {info.get('architecture') or 'Unknown'}\n"
                f"Image base: {image_base_text}\n"
                f"SHA-256: {info.get('sha256')}\n\n"
                f"Known classes: {', '.join(info.get('classes', []))}\n\n"
                f"Diagnostic RVAs (static-analysis data; not invoked):\n{summary}\n\n"
                "Status changes continue through Camfrog's visible controls."
            )
            self.state_label.configure(text=self._tr("Known Camfrog native profile matched", "ตรงกับ Native profile ที่รู้จัก"))
        elif info.get("sha256"):
            messagebox.showwarning(
                "Camfrog Native Profile",
                f"Unknown Camfrog binary. Generic UI/Win32 integration will be used.\n\nSHA-256: {info.get('sha256')}"
            )
            self.state_label.configure(text=self._tr("Unknown Camfrog binary; generic integration mode", "ไม่รู้จัก Camfrog binary; ใช้โหมด generic integration"))
        else:
            messagebox.showwarning(self._tr("Camfrog Native Profile","โปรไฟล์ Native ของ Camfrog"), self._tr("Select or detect Camfrog Video Chat.exe first.","เลือกหรือตรวจหา Camfrog Video Chat.exe ก่อน"))

    def _auto_import_registry_presets(self):
        if not self.registry_auto_var.get():
            return
        self._read_registry_presets(silent=True)

    def _read_registry_clicked(self):
        self._read_registry_presets(silent=False)

    def _read_registry_presets(self, silent: bool = False):
        if os.name != "nt":
            if not silent:
                messagebox.showwarning(self._tr("Camfrog Registry","Registry ของ Camfrog"), self._tr("Registry import is available on Windows only.","อ่าน Registry ได้บน Windows เท่านั้น"))
            return
        self.state_label.configure(text=self._tr("Reading Camfrog custom statuses from Registry...","กำลังอ่านประวัติสถานะ Camfrog จาก Registry..."))
        threading.Thread(target=self._registry_worker, args=(silent,), daemon=True).start()

    def _registry_worker(self, silent: bool):
        try:
            result = read_camfrog_custom_statuses()
            self.after(0, lambda: self._registry_import_done(result, silent))
        except Exception as exc:
            log.exception("Registry status import failed")
            self.after(0, lambda exc=exc: self._registry_import_failed(exc, silent))

    def _registry_import_done(self, result, silent: bool):
        # History is displayed first and is not silently merged into Presets.
        # This makes it obvious what Camfrog actually exposed and prevents bad
        # registry candidates from contaminating user presets.
        self._history_values = list(result.statuses)
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        self.history_box.insert("1.0", "\n".join(self._history_values))
        self.history_box.configure(state="disabled")
        if result.statuses:
            self.state_label.configure(text=f"History: {len(result.statuses)} status value(s) found from {result.candidate_values} candidate value(s)")
            if not silent:
                sample_sources = "\n".join(dict.fromkeys(result.sources[:8]))
                messagebox.showinfo("Camfrog History", f"Found {len(result.statuses)} status history value(s).\nNothing was imported automatically.\nUse 'Import all → Presets' if the list is correct.\n\nSources:\n{sample_sources}")
        else:
            self.state_label.configure(text=f"History: none found (scanned {result.scanned_keys} keys, {result.candidate_values} candidates)")
            if not silent:
                messagebox.showinfo("Camfrog History", f"No custom-status history was decoded.\n\nScanned {result.scanned_keys} Camfrog registry keys and {result.candidate_values} explicit status/custom candidate values.\n\nThis build may serialize history in a different binary layout or outside Registry.")

    def _import_history_all(self):
        values = list(getattr(self, "_history_values", []))
        if not values:
            messagebox.showinfo("Camfrog History", "Read Camfrog History first; no decoded history is currently available.")
            return
        current = [x.strip() for x in self.presets_box.get("1.0", "end").splitlines() if x.strip()]
        merged = merge_presets(current, values)
        added = len(merged) - len(merge_presets(current, []))
        self.presets_box.delete("1.0", "end")
        self.presets_box.insert("1.0", "\n".join(merged))
        self.config_data["status"]["presets"] = merged
        self.store.save(self.config_data)
        self.state_label.configure(text=f"Imported {added} history item(s) into Presets")

    def _import_presets_file(self):
        path = filedialog.askopenfilename(
            title=self._tr("Import status presets", "นำเข้า Presets สถานะ"),
            filetypes=[("Preset files", "*.json *.txt"), ("JSON", "*.json"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            from system.preset_file import parse_preset_file_text

            with open(path, "r", encoding="utf-8-sig") as source:
                contents = source.read(2_000_001)
            if len(contents) > 2_000_000:
                raise ValueError(self._tr("Preset file is larger than 2 MB", "ไฟล์ Presets มีขนาดเกิน 2 MB"))
            incoming = parse_preset_file_text(contents)
            current = [line.strip() for line in self.presets_box.get("1.0", "end").splitlines() if line.strip()]
            before = merge_presets(current, [])
            merged = merge_presets(current, incoming)
            added = len(merged) - len(before)
            self.presets_box.delete("1.0", "end")
            self.presets_box.insert("1.0", "\n".join(merged))
            self._sync_ui_to_config()
            self.store.save(self.config_data)
            self.state_label.configure(text=self._tr(f"Imported {added} preset(s)", f"นำเข้า Presets {added} รายการแล้ว"))
        except Exception as exc:
            log.exception("Preset import failed")
            messagebox.showerror(self._tr("Preset import failed", "นำเข้า Presets ไม่สำเร็จ"), str(exc))

    def _export_presets_file(self):
        path = filedialog.asksaveasfilename(
            title=self._tr("Export status presets", "ส่งออก Presets สถานะ"),
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Text", "*.txt")],
        )
        if not path:
            return
        try:
            from system.preset_file import format_preset_file_text

            current = [line.strip() for line in self.presets_box.get("1.0", "end").splitlines() if line.strip()]
            payload = format_preset_file_text(current, text_only=os.path.splitext(path)[1].casefold() == ".txt")
            with open(path, "w", encoding="utf-8", newline="\n") as output:
                output.write(payload)
            self.state_label.configure(text=self._tr(f"Exported {len(current)} preset(s)", f"ส่งออก Presets {len(current)} รายการแล้ว"))
        except Exception as exc:
            log.exception("Preset export failed")
            messagebox.showerror(self._tr("Preset export failed", "ส่งออก Presets ไม่สำเร็จ"), str(exc))

    def _registry_import_failed(self, exc: Exception, silent: bool):
        self.state_label.configure(text=f"Registry read error: {exc}")
        if not silent:
            messagebox.showerror("Camfrog Registry", str(exc))

    def _auto_detect_if_needed(self):
        if not self.exe_var.get().strip():
            self._detect(silent=True)

    def _browse(self):
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.exe_var.set(path)

    def _detect(self, silent=False):
        path = discover_executable()
        if path:
            self.exe_var.set(path)
            self.state_label.configure(text=self._tr(f"Detected: {path}", f"ตรวจพบ: {path}"))
        elif not silent:
            messagebox.showwarning("Camfrog", self._tr("Camfrog executable/process was not detected. Use Browse to select Camfrog.exe.","ไม่พบโปรแกรม/process Camfrog กรุณาใช้ปุ่มเลือกไฟล์"))

    def _refresh_camfrog_pid(self, message: str = ""):
        pid = self.controller.bound_pid
        self.camfrog_pid_var.set(f"PID: {pid}" if pid else "PID: not connected")
        if pid:
            self.camfrog_pid_entry_var.set(str(pid))
        if message:
            self.state_label.configure(text=message)

    def _start_or_connect_camfrog(self):
        self._sync_ui_to_config()
        self.state_label.configure(text=self._tr("Starting/connecting Camfrog...", "กำลังเปิด/เชื่อมต่อ Camfrog..."))
        self._begin_start_or_connect()

    def _begin_start_or_connect(self, on_complete=None):
        threading.Thread(
            target=self._start_or_connect_camfrog_worker,
            args=(on_complete,),
            daemon=True,
        ).start()

    def _start_or_connect_camfrog_worker(self, on_complete=None):
        result = self.controller.start_or_connect()
        self.after(0, lambda: self._refresh_camfrog_pid(result.message))
        if not result.ok:
            self.after(0, lambda: messagebox.showerror("Camfrog Runtime", result.message))
        if on_complete is not None:
            self.after(0, on_complete)

    def _auto_start_camfrog_if_configured(self, on_complete=None):
        configured = bool(self.config_data.get("camfrog", {}).get("auto_start", False))
        has_executable = bool(self.exe_var.get().strip())
        if not configured or not has_executable:
            if on_complete is not None:
                on_complete()
            return
        # Push the (possibly just auto-detected) executable and options into the
        # controller config before connecting, matching the manual Start / Connect
        # path; otherwise the controller still sees an empty executable.
        self._sync_ui_to_config()
        # Launch/bind first, then resume persisted automation only after the
        # connection attempt finishes; never blocks the UI or aborts startup.
        self._begin_start_or_connect(on_complete)

    def _bind_camfrog_pid(self):
        self._sync_ui_to_config()
        try:
            pid = int(self.camfrog_pid_entry_var.get().strip())
        except ValueError:
            messagebox.showerror("Camfrog Runtime", "Enter a numeric Camfrog PID.")
            return
        result = self.controller.bind_pid(pid)
        self._refresh_camfrog_pid(result.message)
        if not result.ok:
            messagebox.showerror("Camfrog Runtime", result.message)

    def _disconnect_camfrog(self):
        result = self.controller.disconnect_pid()
        self._refresh_camfrog_pid(result.message)

    def _save(self):
        c = self._sync_ui_to_config()
        self.store.save(c)
        if c.get("auto_respond", {}).get("enabled", False):
            self.auto_responder.start()
        else:
            self.auto_responder.stop()
            self._auto_respond_last_state = "Auto respond is disabled"
            self._render_auto_respond_state()
        if c.get("bad_word_moderation", {}).get("enabled", False):
            self.bad_word_monitor.start()
        else:
            self.bad_word_monitor.stop()
            self._bad_word_last_state = "Bad-word monitoring is disabled"
            self._render_bad_word_state()
        if c.get("room_event_notifications", {}).get("enabled", False):
            self.room_event_monitor.start()
        else:
            self.room_event_monitor.stop()
            self._room_event_last_state = "Room event notifications are disabled"
            self._render_room_event_state()
        try:
            set_start_with_windows(c["startup"]["windows_startup"])
        except Exception as exc:
            messagebox.showwarning("Startup", f"Settings saved, but Windows startup could not be updated:\n{exc}")
            return
        self.state_label.configure(text=self._tr("Settings saved","บันทึกการตั้งค่าแล้ว"))

    def _apply_clicked(self):
        # Compatibility entry point: apply the first non-empty message only.
        for i, var in enumerate(self.status_message_vars):
            if var.get().strip():
                self._apply_message_clicked(i)
                return
        messagebox.showwarning("Status", "กรอกข้อความก่อน" if self.language_var.get() == "TH" else "Enter a message first.")

    def _room_action_selected(self, action):
        previous = str(getattr(self, "_last_room_action_selection", action)).strip().casefold()
        targets = getattr(self, "room_action_target_nicknames", {})
        if isinstance(targets, dict):
            targets[previous] = self.room_action_target_var.get()
            selected = str(action).strip().casefold()
            self._last_room_action_selection = selected
            self.room_action_target_var.set(str(targets.get(selected, "")))

    def _send_room_action(self):
        config = self._sync_ui_to_config()
        action = str(self.room_action_var.get()).strip().casefold()
        target = self.room_action_target_var.get()
        expected_room_title = str(config.get("room_actions", {}).get("room_title", "")).strip()
        result = self.room_action_controller.send_action(
            config,
            action,
            target,
            expected_room_title=expected_room_title,
            confirm=lambda command: messagebox.askyesno(
                self._tr("Confirm room command", "ยืนยันคำสั่งห้อง"),
                self._tr(
                    f"Send this command to the configured Camfrog room?\n\n{command}",
                    f"ส่งคำสั่งนี้ไปยังห้อง Camfrog ที่ตั้งค่าไว้หรือไม่?\n\n{command}",
                ),
                parent=self,
            ),
        )
        self.state_label.configure(text=result.message)

    def _bad_word_matches_received(self, matches: tuple[BadWordMatch, ...]):
        if self._exiting:
            return
        for match in matches:
            try:
                self.after(0, lambda current=match: self._handle_bad_word_match(current))
            except Exception:
                return

    def _handle_bad_word_match(self, match: BadWordMatch):
        if self._exiting:
            return
        config = self.store.load()
        moderation = config.get("bad_word_moderation", {})
        result = submit_bad_word_kick(
            config,
            match,
            self.room_action_controller,
            confirm=lambda command: messagebox.askyesno(
                    self._tr("Confirm bad-word kick", "ยืนยัน kick จากคำที่ตรวจพบ"),
                    self._tr(
                        f"A configured term was found in a new room message.\n\nRoom: {match.room_title}\n"
                        f"Sender: {match.sender}\nMatched term: {match.term}\nMessage: {match.body}\n\n"
                        f"Send the configured kick command?\n{command}",
                        f"พบคำที่ตั้งค่าไว้ในข้อความใหม่ของห้อง\n\nห้อง: {match.room_title}\n"
                        f"ผู้ส่ง: {match.sender}\nคำที่พบ: {match.term}\nข้อความ: {match.body}\n\n"
                        f"ส่งคำสั่ง kick ที่ตั้งค่าไว้หรือไม่?\n{command}",
                    ),
                    parent=self,
                ),
        )
        if result is None:
            return
        if (
            moderation.get("auto_kick") is True
            and result.message == "Auto kick disabled after reaching the per-minute action limit"
        ):
            self._disable_bad_word_auto_kick()
        if moderation.get("auto_kick") is True and result.ok:
            self._bad_word_last_state = (
                "Configured bad-word kick submitted; server authorization and result are not independently confirmed"
            )
        else:
            self._bad_word_last_state = result.message
        self._render_bad_word_state()

    def _disable_bad_word_auto_kick(self):
        """Persist the moderation kill switch and reflect it in the UI."""
        try:
            config = self.store.load()
            moderation = config.get("bad_word_moderation", {})
            if not isinstance(moderation, dict):
                moderation = {}
            moderation["auto_kick"] = False
            config["bad_word_moderation"] = moderation
            self.store.save(config)
        except Exception:
            log.exception("Could not persist the bad-word auto-kick kill switch")
        self.bad_word_auto_kick_var.set(False)
        self._bad_word_last_state = "Auto kick disabled after reaching the per-minute action limit"
        self._render_bad_word_state()

    def _bad_word_state_changed(self, state: str):
        if self._exiting:
            return
        self._bad_word_last_state = state
        try:
            self.after(0, self._render_bad_word_state)
        except Exception:
            pass

    def _room_events_received(self, events: tuple[RoomEventMatch, ...]):
        if self._exiting:
            return
        for event in events:
            try:
                self.after(0, lambda current=event: self._handle_room_event(current))
            except Exception:
                return

    def _handle_room_event(self, event: RoomEventMatch):
        if self._exiting:
            return
        from datetime import datetime

        entry = f"{datetime.now().strftime('%H:%M:%S')} | {event.room_title[:64]} | {event.trigger_phrase[:80]}"
        self._room_event_activity.append(entry)
        self._room_event_activity = self._room_event_activity[-50:]
        self.room_event_log_box.configure(state="normal")
        self.room_event_log_box.delete("1.0", "end")
        self.room_event_log_box.insert("1.0", "\n".join(self._room_event_activity))
        self.room_event_log_box.configure(state="disabled")
        self._room_event_last_state = f"Room event matched: {event.trigger_phrase}"
        self._render_room_event_state()
        notifier = getattr(self._tray_icon, "notify", None)
        if callable(notifier):
            try:
                notifier(f"{event.trigger_phrase} — {event.room_title[:80]}", "Camfrog room event")
            except Exception:
                log.debug("System tray room event notification failed")

    def _room_event_state_changed(self, state: str):
        if self._exiting:
            return
        self._room_event_last_state = state
        try:
            self.after(0, self._render_room_event_state)
        except Exception:
            pass

    def _render_room_event_state(self):
        if hasattr(self, "room_event_state_label"):
            state = getattr(self, "_room_event_last_state", "Room event notifications are disabled")
            self.room_event_state_label.configure(text=self._format_room_event_state(state))

    def _format_room_event_state(self, state: str) -> str:
        thai_states = {
            "Room event notifications are disabled": "ปิดการแจ้งเตือนเหตุการณ์ห้อง",
            "Room event notifications require Windows UI Automation": "การแจ้งเตือนเหตุการณ์ห้องต้องใช้ Windows UI Automation",
            "Add room event phrases to monitor": "เพิ่มวลีเหตุการณ์ที่ต้องการตรวจ",
            "Configure room chat UIA selectors first": "ตั้งค่า UIA selector ของแชตห้องก่อน",
            "Configure the room title and history UIA ID first": "ตั้งค่าชื่อห้องและ History UIA ID ก่อน",
            "Camfrog is not running": "Camfrog ยังไม่ทำงาน",
            "Could not inspect the selected Camfrog process": "ตรวจสอบ process Camfrog ที่เลือกไม่ได้",
            "New configured room event detected": "พบเหตุการณ์ห้องตามคำที่ตั้งไว้",
            "Room event monitor is watching configured room history": "กำลังตรวจประวัติห้องตามที่ตั้งไว้",
            "Waiting for the configured room chat window": "รอหน้าต่างแชตห้องที่ตั้งค่าไว้",
        }
        return thai_states.get(state, state) if self.language_var.get() == "TH" else state

    def _render_bad_word_state(self):
        if hasattr(self, "bad_word_state_label"):
            state = getattr(self, "_bad_word_last_state", "Bad-word monitoring is disabled")
            self.bad_word_state_label.configure(text=self._format_bad_word_state(state))

    def _format_bad_word_state(self, state: str) -> str:
        thai_states = {
            "Bad-word monitoring is disabled": "ปิดการตรวจคำในแชต",
            "Bad-word monitoring requires Windows UI Automation": "การตรวจคำในแชตต้องใช้ Windows UI Automation",
            "Enable configured room actions before bad-word monitoring": "เปิดคำสั่งห้องที่ตั้งค่าไว้ก่อนเริ่มตรวจคำ",
            "Configure room chat UIA selectors first": "ตั้งค่า UIA selector ของแชตห้องก่อน",
            "Configure the room title and history UIA ID first": "ตั้งค่าชื่อห้องและ History UIA ID ก่อน",
            "Enter your Camfrog nickname to ignore your own messages": "กรอกชื่อบัญชี Camfrog เพื่อข้ามข้อความของตัวเอง",
            "Add at least one bad-word term": "เพิ่มคำที่ต้องตรวจอย่างน้อยหนึ่งคำ",
            "Camfrog is not running": "Camfrog ยังไม่ทำงาน",
            "Could not inspect the selected Camfrog process": "ตรวจสอบ process Camfrog ที่เลือกไม่ได้",
            "Configured bad-word match detected; awaiting operator confirmation": "พบคำที่ตั้งค่าไว้; รอการยืนยันจากผู้ใช้",
            "Configured bad-word match detected; auto-kick enabled": "พบคำที่ตั้งค่าไว้; เปิด kick อัตโนมัติอยู่",
            "Auto kick disabled after reaching the per-minute action limit": "ปิด kick อัตโนมัติแล้วเนื่องจากถึงขีดจำกัดต่อหนึ่งนาที",
            "Room history structure is ambiguous; moderation paused": "โครงสร้างประวัติห้องกำกวม จึงพักการตรวจไว้ก่อน",
            "Configured bad-word kick submitted; server authorization and result are not independently confirmed": "ส่งคำสั่ง kick ตามกฎที่ตั้งไว้แล้ว แต่ยังยืนยันสิทธิ์หรือผลจากเซิร์ฟเวอร์ไม่ได้",
            "Bad-word monitor is watching configured room history": "กำลังตรวจประวัติแชตห้องตามที่ตั้งค่าไว้",
            "Waiting for the configured room chat window": "รอหน้าต่างแชตห้องที่ตั้งค่าไว้",
            "Room actions are disabled": "ปิดคำสั่งห้องอยู่",
            "Room action cancelled": "ยกเลิกคำสั่งห้องแล้ว",
            "Confirmed room command submitted through Camfrog UI; server authorization and result are not independently confirmed": "ส่งคำสั่งผ่าน UI ของ Camfrog แล้ว แต่ยังไม่ได้ยืนยันสิทธิ์หรือผลจากเซิร์ฟเวอร์",
        }
        return thai_states.get(state, state) if self.language_var.get() == "TH" else state

    def _apply_worker(self, value):
        result = self.controller.set_status(value)
        self.after(0, lambda: self._show_result(result))

    def _apply_status_background(self, value, *, cancelled=None):
        # Rotation executes on its own thread. Read the synced config snapshot
        # here instead of calling Tk variables outside the UI thread.
        styles = dict(self.config_data.get("status", {}).get("styles", {}))
        marquee_enabled = bool(styles.get("marquee", False))
        with self._style_lock:
            if marquee_enabled and styles.get("marquee_single_character", True) and self._marquee_current_text != value:
                self._marquee_offset = 0
                self._marquee_current_text = value
            value, next_offset, _ = apply_styles(
                value,
                random_color_enabled=bool(styles.get("random_color", False)),
                custom_color_enabled=bool(styles.get("custom_color_enabled", False)),
                custom_color=str(styles.get("custom_color", "#00C7BE")),
                marquee_enabled=marquee_enabled,
                marquee_offset=self._marquee_offset,
                marquee_width=int(styles.get("marquee_width", 28)),
                marquee_single_character=bool(styles.get("marquee_single_character", True)),
                color_template=str(styles.get("color_template", "[color={color}]{text}[/color]")),
                palette=styles.get("palette", []),
            )
            if marquee_enabled:
                self._marquee_offset = next_offset
        if cancelled is None:
            result = self.controller.set_status(value)
        else:
            result = self.controller.set_status(value, cancelled=cancelled)
        if not getattr(self, "_exiting", False):
            try:
                self.after(0, lambda: self.state_label.configure(text=result.message if result.ok else f"ERROR: {result.message}"))
            except Exception:
                pass

    def _show_result(self, result):
        self.state_label.configure(text=result.message if result.ok else f"ERROR: {result.message}")
        if not result.ok:
            messagebox.showerror("Camfrog Status", result.message)

    def _start_rotation(self):
        c = self._sync_ui_to_config()
        source = c["status"]["rotation"].get("source", "messages")
        messages = self._rotation_messages(c)
        if not messages:
            warning = (
                "ไม่พบประวัติสถานะ Camfrog ให้อ่าน History ก่อน"
                if source == "camfrog_history" and self.language_var.get() == "TH"
                else "Camfrog Status History is empty; read the history first."
                if source == "camfrog_history"
                else "เพิ่มอย่างน้อย 1 ข้อความ" if self.language_var.get() == "TH"
                else "Add at least one message."
            )
            messagebox.showwarning("Rotation", warning)
            return
        interval = c["status"]["rotation"]["interval_seconds"]
        mode = "random" if source == "camfrog_history" else c["status"]["rotation"]["mode"]
        self.marquee_animation.stop()
        self.rotation.start(
            messages,
            interval,
            mode,
            schedule=c["status"]["rotation"],
            marquee_enabled=bool(c["status"].get("styles", {}).get("marquee", False)),
            marquee_frame_interval_seconds=self._marquee_interval_seconds(c),
            marquee_progressive_delays=bool(c["status"].get("styles", {}).get("marquee_single_character", False)),
            minimum_interval_seconds=int(c.get("advanced", {}).get("minimum_interval_seconds", 5)),
        )
        self.rotation_var.set(True)
        c["status"]["rotation"]["enabled"] = True
        self.store.save(c)
        self.state_label.configure(text=self._tr(
            f"Rotation started: first eligible message now, then 1 message per {self._format_interval(interval)}",
            f"เริ่มหมุนข้อความ: ส่งข้อความแรกทันทีเมื่ออยู่ในช่วงที่กำหนด แล้วส่ง 1 ข้อความทุก {self._format_interval(interval)}",
        ))


    @staticmethod
    def _format_interval(seconds: int) -> str:
        return format_interval(seconds)

    def _interval_unit_changed(self, unit: str):
        # Make unit selection visibly active and immediately persist a valid conversion.
        try:
            c = self._sync_ui_to_config()
            seconds = int(c["status"]["rotation"]["interval_seconds"])
            self.state_label.configure(text=f"Interval set to {self._format_interval(seconds)}")
        except Exception as exc:
            self.state_label.configure(text=f"Interval error: {exc}")

    def _stop_rotation(self):
        self.rotation.stop()
        self.marquee_animation.stop()
        self.rotation_var.set(False)
        self.config_data["status"]["rotation"]["enabled"] = False
        self.store.save(self.config_data)
        self.state_label.configure(text=self._tr("Rotation stopped","หยุดหมุนข้อความแล้ว"))


    def _capture_target(self):
        self._sync_ui_to_config()
        self._capture_countdown = 3
        self._capture_tick()

    def _capture_tick(self):
        if self._capture_countdown > 0:
            self.state_label.configure(
                text=f"Move mouse over Camfrog status field — capturing in {self._capture_countdown}s..."
            )
            self._capture_countdown -= 1
            self.after(1000, self._capture_tick)
            return

        self.state_label.configure(text=self._tr("Capturing target...","กำลังจับตำแหน่ง..."))
        threading.Thread(target=self._capture_target_worker, daemon=True).start()

    def _capture_target_worker(self):
        try:
            if os.name != "nt":
                raise RuntimeError("Target capture is available on Windows only")
            import win32api

            # pywinauto enumeration can be slow for custom-rendered applications;
            # keep it off the Tk UI thread so Windows never marks the app hung.
            win = self.controller.find_window()
            rect = win.rectangle()
            x, y = win32api.GetCursorPos()
            if not (rect.left <= x <= rect.right and rect.top <= y <= rect.bottom):
                raise RuntimeError("Mouse cursor is not over the Camfrog window")
            rx = (x - rect.left) / max(1, rect.width())
            ry = (y - rect.top) / max(1, rect.height())
            self.after(0, lambda: self._capture_target_success(rx, ry))
        except Exception as exc:
            self.after(0, lambda exc=exc: self._capture_target_failed(exc))

    def _capture_target_success(self, rx: float, ry: float):
        self.fallback_x_var.set(f"{rx:.4f}")
        self.fallback_y_var.set(f"{ry:.4f}")
        self._sync_ui_to_config()
        self.store.save(self.config_data)
        self.state_label.configure(text=f"Captured fallback target X={rx:.4f}, Y={ry:.4f}")
        messagebox.showinfo("Target captured", "Fallback target saved. You can now test with Apply now.")

    def _capture_target_failed(self, exc: Exception):
        self.state_label.configure(text=f"ERROR: {exc}")
        messagebox.showerror("Capture failed", str(exc))

    def _inspect(self):
        self._sync_ui_to_config()
        self.state_label.configure(text=self._tr("Inspecting Camfrog controls...","กำลังตรวจ Camfrog controls..."))
        threading.Thread(target=self._inspect_worker, daemon=True).start()

    def _inspect_worker(self):
        try:
            result = self.controller.ensure_running()
            if not result.ok:
                raise RuntimeError(result.message)
            controls = self.controller.inspect_controls()
            interesting = [x for x in controls if x["control_type"] in {"ComboBox", "Edit", "Text"} and (x["title"] or x["automation_id"])]
            payload = json.dumps(interesting[:100], indent=2, ensure_ascii=False)
            path = self.store.dir / "uia-controls.json"
            path.write_text(payload, encoding="utf-8")
            self.after(0, lambda: messagebox.showinfo("Inspect complete", f"Saved {len(interesting)} candidate controls to:\n{path}"))
            self.after(0, lambda: self.state_label.configure(text=self._tr("Inspect complete","ตรวจ Control เสร็จแล้ว")))
        except Exception as exc:
            self.after(0, lambda error=exc: messagebox.showerror("Inspect failed", str(error)))
            self.after(0, lambda error=exc: self.state_label.configure(text=f"ERROR: {error}"))

    def _inspect_auto_respond_controls(self):
        self.auto_respond_state_label.configure(
            text=self._tr("Inspecting visible Camfrog chat controls...", "กำลังตรวจ Control แชต Camfrog ที่มองเห็น...")
        )
        threading.Thread(target=self._inspect_auto_respond_worker, daemon=True).start()

    def _inspect_video_overlay_controls(self):
        self.tov_inspect_state_label.configure(text="Inspecting visible Camfrog Settings controls...")
        threading.Thread(target=self._inspect_video_overlay_controls_worker, daemon=True).start()

    def _inspect_video_overlay_controls_worker(self):
        try:
            windows = self.controller.inspect_video_overlay_controls()
            self.store.dir.mkdir(parents=True, exist_ok=True)
            path = self.store.dir / "tov-uia.json"
            path.write_text(json.dumps(windows, indent=2, ensure_ascii=False), encoding="utf-8")
            count = sum(len(window.get("controls", [])) for window in windows)
            identified_windows = sum(
                window.get("match_reason") == "settings_title" or window.get("has_tov_markers", False)
                for window in windows
            )
            if identified_windows:
                status = f"Saved {count} sanitized control records to {path}"
                title = "Text Over Video controls inspected"
                detail = f"Saved control metadata to:\n{path}\n\nEdit and ComboBox values were omitted. No Camfrog settings were changed."
            else:
                status = f"No Text Over Video labels were exposed by UIA; saved diagnostic metadata to {path}"
                title = "Camfrog diagnostic saved"
                detail = (
                    f"UI Automation did not identify Text Over Video controls. Sanitized window metadata was saved to:\n{path}\n\n"
                    "Edit and ComboBox values were omitted. No Camfrog settings were changed."
                )
            self.after(0, lambda: self.tov_inspect_state_label.configure(
                text=status
            ))
            self.after(0, lambda: messagebox.showinfo(
                title,
                detail,
            ))
        except Exception as exc:
            log.exception("Text Over Video UIA inspection failed")
            self.after(0, lambda exc=exc: self.tov_inspect_state_label.configure(text=f"ERROR: {exc}"))
            self.after(0, lambda exc=exc: messagebox.showerror("Inspect failed", str(exc)))

    def _inspect_auto_respond_worker(self):
        try:
            controls = self.controller.inspect_chat_controls()
            self.store.dir.mkdir(parents=True, exist_ok=True)
            path = self.store.dir / "auto-respond-uia.json"
            path.write_text(json.dumps(controls, indent=2, ensure_ascii=False), encoding="utf-8")
            self.after(0, lambda: self.auto_respond_state_label.configure(
                text=self._tr(f"Saved {len(controls)} window(s) to auto-respond-uia.json", f"บันทึกข้อมูล {len(controls)} หน้าต่างใน auto-respond-uia.json แล้ว")
            ))
            self.after(0, lambda: messagebox.showinfo(
                self._tr("Chat controls inspected", "ตรวจ Control แชตแล้ว"),
                self._tr(
                    f"Saved UIA metadata to:\n{path}\n\nChat message text is not included.",
                    f"บันทึกข้อมูล UIA ที่:\n{path}\n\nไม่มีการบันทึกเนื้อหาข้อความแชต",
                ),
            ))
        except Exception as exc:
            log.exception("Auto respond UIA inspection failed")
            self.after(0, lambda exc=exc: self.auto_respond_state_label.configure(text=f"ERROR: {exc}"))
            self.after(0, lambda exc=exc: messagebox.showerror(self._tr("Inspect failed", "ตรวจไม่สำเร็จ"), str(exc)))

    def _open_config_dir(self):
        self.store.dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(self.store.dir)  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("Config folder", str(self.store.dir))

    def _resume_background_automation(self):
        c = self.config_data
        if c.get("status", {}).get("rotation", {}).get("enabled", False):
            messages = self._rotation_messages(c)
            if messages:
                interval = max(int(c.get("advanced", {}).get("minimum_interval_seconds", 5)), int(c["status"]["rotation"].get("interval_seconds", 600)))
                source = c["status"]["rotation"].get("source", "messages")
                mode = "random" if source == "camfrog_history" else c["status"]["rotation"].get("mode", "sequential")
                styles = c.get("status", {}).get("styles", {})
                self.rotation.start(
                    messages,
                    interval,
                    mode,
                    schedule=c["status"]["rotation"],
                    marquee_enabled=bool(styles.get("marquee", False)),
                    marquee_frame_interval_seconds=self._marquee_interval_seconds(c),
                    marquee_progressive_delays=bool(styles.get("marquee_single_character", False)),
                    minimum_interval_seconds=int(c.get("advanced", {}).get("minimum_interval_seconds", 5)),
                )
                self.state_label.configure(text=self._tr(
                    f"Background rotation: first eligible message now, then 1 message per {self._format_interval(interval)}",
                    f"หมุนข้อความเบื้องหลัง: ส่งข้อความแรกทันทีเมื่ออยู่ในช่วงที่กำหนด แล้วส่ง 1 ข้อความทุก {self._format_interval(interval)}",
                ))
            elif c["status"]["rotation"].get("source") == "camfrog_history":
                self.state_label.configure(
                    text="ไม่พบประวัติสถานะ Camfrog; หยุดการหมุนข้อความ" if self.language_var.get() == "TH"
                    else "Camfrog Status History is empty; rotation was not started."
                )
        if c.get("auto_respond", {}).get("enabled", False):
            self.auto_responder.start()
        if c.get("bad_word_moderation", {}).get("enabled", False):
            self.bad_word_monitor.start()
        else:
            self._bad_word_last_state = "Bad-word monitoring is disabled"
            self._render_bad_word_state()
        if c.get("room_event_notifications", {}).get("enabled", False):
            self.room_event_monitor.start()
        else:
            self._room_event_last_state = "Room event notifications are disabled"
            self._render_room_event_state()
        if c.get("startup", {}).get("start_minimized", False):
            if self._tray_available():
                self.withdraw()
            else:
                log.warning("Start minimized was requested, but the system tray is unavailable; keeping the dashboard visible")

    def _format_auto_respond_state(self, state: str) -> str:
        thai_states = {
            "Auto respond is disabled": "ปิดการตอบกลับอัตโนมัติอยู่",
            "Auto respond requires Windows UI Automation": "การตอบกลับอัตโนมัติต้องใช้ Windows UI Automation",
            "Auto respond needs your Camfrog nickname and a reply text": "กรอกชื่อบัญชี Camfrog และข้อความตอบกลับก่อน",
            "Auto respond needs UIA selectors for private chat and/or room chat": "กำหนด UIA selector ของแชตส่วนตัวหรือแชตห้องก่อน",
            "Auto respond is waiting for Camfrog": "รอ Camfrog เปิดทำงาน",
            "Auto respond is waiting for a visible Camfrog window": "รอหน้าต่าง Camfrog ที่มองเห็นได้",
            "Auto respond is monitoring configured chat controls": "กำลังตรวจแชตตาม Control ที่ตั้งค่าไว้",
            "Auto reply submitted (private chat)": "ส่งคำตอบผ่าน UIA แล้ว (แชตส่วนตัว)",
            "Auto reply submitted (room chat)": "ส่งคำตอบผ่าน UIA แล้ว (แชตห้อง)",
            "Auto respond is waiting for a configured private or room chat window": "รอหน้าต่างแชตที่ตั้งค่าไว้",
            "Saved; waiting for UIA setup": "บันทึกแล้ว; รอตั้งค่า UIA",
            "Disabled": "ปิดอยู่",
        }
        return thai_states.get(state, state) if self.language_var.get() == "TH" else state

    def _render_auto_respond_state(self):
        if hasattr(self, "auto_respond_state_label"):
            self.auto_respond_state_label.configure(
                text=self._format_auto_respond_state(self._auto_respond_last_state)
            )

    def _auto_respond_state_changed(self, state: str):
        if self._exiting:
            return
        self._auto_respond_last_state = state
        try:
            self.after(0, self._render_auto_respond_state)
        except Exception:
            pass

    def _start_tray(self):
        if os.name != "nt" or self._tray_icon is not None:
            return
        try:
            import pystray
            from PIL import Image

            icon_path = resource_path("app.ico")
            with Image.open(icon_path) as icon_file:
                image = icon_file.convert("RGBA")

            menu = pystray.Menu(
                pystray.MenuItem("Open", lambda icon, item: self.after(0, self._show_from_tray)),
                pystray.MenuItem("Pause rotation", lambda icon, item: self.after(0, self._stop_rotation)),
                pystray.MenuItem("Exit", lambda icon, item: self.after(0, self._exit_app)),
            )
            self._tray_icon = pystray.Icon("CamfrogStatusChanger", image, "Camfrog Status Changer", menu)
            self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
            self._tray_thread.start()
        except Exception:
            log.exception("Could not start system tray")

    def _show_from_tray(self):
        self.deiconify()
        self.lift()

    def _tray_available(self) -> bool:
        try:
            return self._tray_icon is not None and self._tray_thread is not None and self._tray_thread.is_alive()
        except Exception:
            return False

    def _monitor_tray(self):
        if self._exiting:
            return
        if self._tray_icon is not None and not self._tray_available():
            try:
                if self.state() == "withdrawn":
                    log.warning("System tray stopped while the dashboard was hidden; restoring the window")
                    self.deiconify()
                    self.lift()
            except Exception:
                log.exception("Could not restore the dashboard after the system tray stopped")
        self.after(1000, self._monitor_tray)

    def _exit_app(self):
        self._exiting = True
        self.rotation.stop()
        self.marquee_animation.stop()
        self.auto_responder.stop()
        self.bad_word_monitor.stop()
        self.room_event_monitor.stop()
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    def _on_close(self):
        # Closing the control panel keeps automation running in the tray.
        if self._exiting:
            self._exit_app()
            return
        if self._tray_available():
            self.withdraw()
        else:
            log.warning("System tray is unavailable; exiting instead of hiding the dashboard")
            self._exit_app()
