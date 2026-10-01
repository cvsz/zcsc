from __future__ import annotations
import logging, threading, tkinter as tk, ntpath, os
from tkinter import filedialog, messagebox
import customtkinter as ctk
from automation.rotation import RotationWorker
from automation.intervals import interval_to_seconds, seconds_to_interval
from camfrog.controller import CamfrogController
from camfrog.detector import discover_executable
from camfrog.registry_status import read_camfrog_custom_statuses, merge_presets
from status_styles import apply_styles
from system.startup import set_start_with_windows

log=logging.getLogger(__name__)
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")

def windows_path(value: str) -> str:
    value=str(value or "").strip()
    if not value:
        return ""
    return ntpath.normpath(value.replace("/", "\\"))

class AppUI(ctk.CTk):
    def __setattr__(self, name, value):
        # Tk/CustomTkinter relies on the inherited title() method internally.
        # Redirect accidental legacy widget assignment instead of shadowing it.
        if name == "title" and not callable(value):
            object.__setattr__(self, "title_label", value)
            logging.getLogger(__name__).warning(
                "Redirected non-callable AppUI.title assignment to title_label: %s",
                type(value).__name__,
            )
            return
        super().__setattr__(name, value)

    def __init__(self,store):
        super().__init__()
        self.store=store; self.config_data=store.load(); self.controller=CamfrogController(self.config_data)
        self.rotation=RotationWorker(self._rotation_apply); self._marquee_offsets={}
        self.geometry("780x700"); self.minsize(720,600)
        self.language_var=tk.StringVar(value=self.config_data.get("ui",{}).get("language","EN"))
        self._install_clipboard_shortcuts()
        self._build()
        self._restore_tk_title_method()
        self._load()

    def _restore_tk_title_method(self):
        """Recover if an older/local UI build shadowed Tk.title with a widget."""
        instance_title = self.__dict__.get("title")
        if instance_title is not None and not callable(instance_title):
            log.warning(
                "Removing non-callable AppUI.title instance attribute: %s",
                type(instance_title).__name__,
            )
            del self.__dict__["title"]

    def _tr(self,en,th): return th if self.language_var.get()=="TH" else en

    def _install_clipboard_shortcuts(self):
        """Install one class-level clipboard handler without duplicate virtual events."""
        def select_all(event):
            widget = event.widget
            try:
                if isinstance(widget, tk.Text):
                    widget.tag_add("sel", "1.0", "end-1c")
                    widget.mark_set("insert", "1.0")
                else:
                    widget.selection_range(0, "end")
                    widget.icursor("end")
            except Exception:
                return None
            return "break"

        def copy(event):
            widget = event.widget
            try:
                text = widget.selection_get()
                self.clipboard_clear()
                self.clipboard_append(text)
            except Exception:
                pass
            return "break"

        def cut(event):
            widget = event.widget
            try:
                text = widget.selection_get()
                self.clipboard_clear()
                self.clipboard_append(text)
                if isinstance(widget, tk.Text):
                    widget.delete("sel.first", "sel.last")
                else:
                    widget.delete("sel.first", "sel.last")
            except Exception:
                pass
            return "break"

        def paste(event):
            widget = event.widget
            try:
                text = self.clipboard_get()
                if isinstance(widget, tk.Text):
                    try:
                        widget.delete("sel.first", "sel.last")
                    except Exception:
                        pass
                    widget.insert("insert", text)
                else:
                    try:
                        widget.delete("sel.first", "sel.last")
                    except Exception:
                        pass
                    widget.insert("insert", text)
            except Exception:
                pass
            return "break"

        classes = ("Entry", "TEntry", "Text")
        for cls in classes:
            self.bind_class(cls, "<Control-a>", select_all)
            self.bind_class(cls, "<Control-A>", select_all)
            self.bind_class(cls, "<Control-c>", copy)
            self.bind_class(cls, "<Control-C>", copy)
            self.bind_class(cls, "<Control-x>", cut)
            self.bind_class(cls, "<Control-X>", cut)
            self.bind_class(cls, "<Control-v>", paste)
            self.bind_class(cls, "<Control-V>", paste)

    def _build(self):
        root=ctk.CTkScrollableFrame(self); root.pack(fill="both",expand=True,padx=12,pady=12)
        self.header=ctk.CTkLabel(root,text="Camfrog Status Changer",font=ctk.CTkFont(size=24,weight="bold")); self.header.pack(anchor="w")
        self.state=ctk.CTkLabel(root,text="Ready"); self.state.pack(anchor="w",pady=(2,10))
        top=ctk.CTkFrame(root); top.pack(fill="x",pady=5)
        self.exe=tk.StringVar(); ctk.CTkEntry(top,textvariable=self.exe).pack(side="left",fill="x",expand=True,padx=8,pady=8)
        ctk.CTkButton(top,text="Browse",width=80,command=self._browse).pack(side="left",padx=4)
        ctk.CTkButton(top,text="Detect",width=80,command=self._detect).pack(side="left",padx=4)
        ctk.CTkButton(top,text="Native profile",width=110,command=self._profile).pack(side="left",padx=4)
        lang=ctk.CTkFrame(root); lang.pack(fill="x",pady=5)
        ctk.CTkLabel(lang,text="Language / ภาษา").pack(side="left",padx=8)
        ctk.CTkOptionMenu(lang,values=["EN","TH"],variable=self.language_var,command=lambda _ : self._language_changed()).pack(side="left",padx=4)

        msgf=ctk.CTkFrame(root); msgf.pack(fill="x",pady=5)
        self.msg_vars=[tk.StringVar() for _ in range(4)]
        self.msg_labels=[]; self.apply_buttons=[]
        for i,v in enumerate(self.msg_vars):
            lbl=ctk.CTkLabel(msgf,text=f"Message {i+1}",width=90); lbl.grid(row=i,column=0,padx=8,pady=4,sticky="w")
            ctk.CTkEntry(msgf,textvariable=v).grid(row=i,column=1,padx=4,pady=4,sticky="ew")
            btn=ctk.CTkButton(msgf,text="Apply",width=80,command=lambda n=i:self._apply(n)); btn.grid(row=i,column=2,padx=8,pady=4)
            self.msg_labels.append(lbl); self.apply_buttons.append(btn)
        msgf.grid_columnconfigure(1,weight=1)

        sf=ctk.CTkFrame(root); sf.pack(fill="x",pady=5)
        self.color=tk.BooleanVar(); self.marquee=tk.BooleanVar()
        ctk.CTkCheckBox(sf,text="Random Color Marker",variable=self.color,command=self._style_changed).pack(side="left",padx=8,pady=8)
        ctk.CTkCheckBox(sf,text="Marquee",variable=self.marquee,command=self._style_changed).pack(side="left",padx=8,pady=8)
        self.status_preview=ctk.CTkLabel(sf,text=""); self.status_preview.pack(side="left",padx=8,pady=8)

        rf=ctk.CTkFrame(root); rf.pack(fill="x",pady=5)
        self.interval=tk.StringVar(value="10"); self.unit=tk.StringVar(value="minutes"); self.mode=tk.StringVar(value="sequential")
        ctk.CTkEntry(rf,textvariable=self.interval,width=80).pack(side="left",padx=8,pady=8)
        ctk.CTkOptionMenu(rf,values=["seconds","minutes","hours"],variable=self.unit).pack(side="left",padx=4)
        ctk.CTkOptionMenu(rf,values=["sequential","random"],variable=self.mode).pack(side="left",padx=4)
        self.start_btn=ctk.CTkButton(rf,text="Start rotation",command=self._start); self.start_btn.pack(side="left",padx=4)
        self.stop_btn=ctk.CTkButton(rf,text="Stop",command=self._stop); self.stop_btn.pack(side="left",padx=4)

        hf=ctk.CTkFrame(root); hf.pack(fill="x",pady=5)
        ctk.CTkButton(hf,text="Read Camfrog History",command=self._history).pack(side="left",padx=8,pady=8)
        ctk.CTkButton(hf,text="Open config folder",command=self._open_config).pack(side="left",padx=8,pady=8)

        of=ctk.CTkFrame(root); of.pack(fill="x",pady=5)
        self.bg=tk.BooleanVar(value=True); self.fg=tk.BooleanVar(value=False); self.startup=tk.BooleanVar(value=False)
        ctk.CTkCheckBox(of,text="Background only",variable=self.bg,command=self._bg_toggle).pack(side="left",padx=8,pady=8)
        ctk.CTkCheckBox(of,text="Allow foreground fallback",variable=self.fg,command=self._fg_toggle).pack(side="left",padx=8,pady=8)
        ctk.CTkCheckBox(of,text="Start with Windows",variable=self.startup,command=self._startup_toggle).pack(side="left",padx=8,pady=8)

    def _load(self):
        c=self.config_data
        self.exe.set(windows_path(c.get("camfrog",{}).get("executable","")))
        for v,x in zip(self.msg_vars,c.get("status",{}).get("editor_messages",[])): v.set(x)
        s=c.get("status",{}).get("styles",{}); self.color.set(bool(s.get("random_color"))); self.marquee.set(bool(s.get("marquee")))
        sec=int(c.get("status",{}).get("rotation",{}).get("interval_seconds",600)); amt,u=seconds_to_interval(sec); self.interval.set(str(amt)); self.unit.set(u); self.mode.set(c["status"]["rotation"].get("mode","sequential"))
        a=c.get("advanced",{}); self.bg.set(bool(a.get("background_only",True))); self.fg.set(bool(a.get("fallback_enabled",False))); self.startup.set(bool(c.get("startup",{}).get("windows_startup",False)))
        if not self.exe.get(): self.after(250,self._detect)
        self._language_changed(save=False)

    def _sync(self):
        c=self.config_data
        c["camfrog"]["executable"]=windows_path(self.exe.get())
        self.exe.set(c["camfrog"]["executable"])
        c["status"]["editor_messages"]=[v.get().strip() for v in self.msg_vars]
        c["status"]["styles"]["random_color"]=bool(self.color.get()); c["status"]["styles"]["marquee"]=bool(self.marquee.get())
        c["status"]["rotation"]["interval_seconds"]=interval_to_seconds(self.interval.get(),self.unit.get()); c["status"]["rotation"]["mode"]=self.mode.get()
        c["ui"]["language"]=self.language_var.get(); c["advanced"]["background_only"]=bool(self.bg.get()); c["advanced"]["fallback_enabled"]=bool(self.fg.get()) and not bool(self.bg.get())
        c["startup"]["windows_startup"]=bool(self.startup.get()); self.store.save(c); self.config_data=self.store.load(); self.controller.config=self.config_data; return self.config_data

    def _save(self): self._sync()

    def _style_changed(self):
        self._sync()
        self._refresh_status_preview()

    def _refresh_status_preview(self):
        if not hasattr(self, "status_preview"):
            return
        raw = next((v.get().strip() for v in self.msg_vars if v.get().strip()), "")
        if not raw:
            self.status_preview.configure(text="")
            return
        preview = self._styled(raw, "preview")
        self.status_preview.configure(text=preview)

    def _language_changed(self,save=True):
        if save: self._sync()
        th=self.language_var.get()=="TH"; self.wm_title(("ตัวเปลี่ยนสถานะ Camfrog" if th else "Camfrog Status Changer"))
        self.header.configure(text=("ตัวเปลี่ยนสถานะ Camfrog" if th else "Camfrog Status Changer"))
        for i,l in enumerate(self.msg_labels): l.configure(text=(f"ข้อความ {i+1}" if th else f"Message {i+1}"))
        for b in self.apply_buttons: b.configure(text=("ใช้" if th else "Apply"))
        self.start_btn.configure(text=("เริ่มหมุน" if th else "Start rotation")); self.stop_btn.configure(text=("หยุด" if th else "Stop"))

    def _browse(self):
        p=filedialog.askopenfilename(filetypes=[("Executable","*.exe"),("All files","*.*")])
        if p:
            self.exe.set(windows_path(p)); self._save()

    def _detect(self):
        p=windows_path(discover_executable())
        if p:
            self.exe.set(p); self._save(); self.state.configure(text=f"Detected: {p}")
        else:
            messagebox.showwarning(self._tr("Detect","ตรวจหา"),self._tr("Camfrog executable was not found.","ไม่พบไฟล์ Camfrog"))

    def _profile(self):
        self._sync(); i=self.controller.native_profile_info()
        msg=self._tr("Known profile matched.","ตรงกับโปรไฟล์ที่รู้จัก") if i.get("matched") else self._tr("Unknown Camfrog binary; generic safe integration only.","ไม่รู้จัก Camfrog เวอร์ชันนี้ จะใช้โหมดทั่วไปแบบปลอดภัย")
        messagebox.showinfo(self._tr("Native profile","โปรไฟล์ Native"),msg)

    def _styled(self,value,key):
        st=self.config_data.get("status",{}).get("styles",{}); off=self._marquee_offsets.get(key,0)
        out,nxt,_=apply_styles(value,random_color_enabled=bool(st.get("random_color")),marquee_enabled=bool(st.get("marquee")),marquee_offset=off,marquee_width=int(st.get("marquee_width",28)),palette=st.get("palette"))
        self._marquee_offsets[key]=nxt; return out

    def _apply(self,index):
        c=self._sync(); raw=c["status"]["editor_messages"][index]
        if not raw: return
        value=self._styled(raw,f"msg-{index}")
        threading.Thread(target=self._apply_worker,args=(value,),daemon=True).start()

    def _apply_worker(self,value):
        r=self.controller.set_status(value); self.after(0,lambda:self._result(r))

    def _result(self,r):
        detail=f"[{r.stage or 'unknown'}] {r.message}"
        self.state.configure(text=detail if not r.ok else r.message)
        if not r.ok:
            en=f"Status was not changed.\n\nStage: {r.stage or 'unknown'}\nReason: {r.message}\n\nSee app.log for technical details."
            th=f"ยังไม่สามารถเปลี่ยนสถานะได้\n\nขั้นตอน: {r.stage or 'unknown'}\nสาเหตุ: {r.message}\n\nดูรายละเอียดทางเทคนิคได้ใน app.log"
            messagebox.showerror(self._tr("Camfrog Status","สถานะ Camfrog"),self._tr(en,th))

    def _rotation_apply(self,value):
        styled=self._styled(value,value); r=self.controller.set_status(styled); self.after(0,lambda:self.state.configure(text=r.message if r.ok else f"[{r.stage}] {r.message}"))

    def _start(self):
        c=self._sync(); msgs=[x for x in c["status"]["editor_messages"] if x]
        if not msgs: return
        self.rotation.start(msgs,c["status"]["rotation"]["interval_seconds"],c["status"]["rotation"]["mode"]); c["status"]["rotation"]["enabled"]=True; self.store.save(c)
        self.state.configure(text=self._tr("Rotation started: one message per interval.","เริ่มหมุน: หนึ่งข้อความต่อหนึ่งช่วงเวลา"))

    def _stop(self):
        self.rotation.stop(); self.config_data["status"]["rotation"]["enabled"]=False; self.store.save(self.config_data); self.state.configure(text=self._tr("Rotation stopped","หยุดหมุนแล้ว"))

    def _history(self):
        result=read_camfrog_custom_statuses()
        history=list(result.history or [])
        if not result.statuses:
            return messagebox.showinfo(self._tr("Camfrog History","ประวัติ Camfrog"),self._tr("No custom-status history was found.","ไม่พบประวัติสถานะ"))
        text="\n".join(f"{i+1}. {value}" for i,value in enumerate(result.statuses[:30]))
        if messagebox.askyesno(self._tr("Camfrog History","ประวัติ Camfrog"),self._tr("Found status history:\n\n","พบประวัติสถานะ:\n\n")+text+"\n\n"+self._tr("Import all into presets?","นำเข้าทั้งหมดเป็น Presets หรือไม่?")):
            self.config_data["status"]["presets"]=merge_presets(self.config_data["status"].get("presets",[]),result.statuses); self.store.save(self.config_data)
        log.info("History sources: %s",[(v.text,v.source,v.value_name) for v in history])

    def _bg_toggle(self):
        if self.bg.get(): self.fg.set(False)
        self._save()

    def _fg_toggle(self):
        if self.fg.get(): self.bg.set(False)
        self._save()

    def _startup_toggle(self):
        self._sync(); set_start_with_windows(bool(self.startup.get()))

    def _open_config(self):
        self.store.dir.mkdir(parents=True,exist_ok=True)
        if os.name=="nt": os.startfile(self.store.dir)
