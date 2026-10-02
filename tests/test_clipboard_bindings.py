from pathlib import Path


def test_clipboard_bindings_do_not_use_bind_all_or_virtual_paste():
    source = Path('ui/dashboard.py').read_text(encoding='utf-8')
    block = source[source.index('    def _install_clipboard_shortcuts'):source.index('    def _build', source.index('    def _install_clipboard_shortcuts'))]
    assert 'self.bind_all(' not in block
    assert 'event_generate' not in block
    assert 'bind_class' in block


def test_clipboard_selection_paste_replaces_selected_range_at_its_start():
    source = Path('ui/dashboard.py').read_text(encoding='utf-8')
    block = source[source.index('    def _clipboard_action'):source.index('    def _build')]
    assert 'widget.index("sel.first")' in block
    assert 'widget.index("sel.last")' in block
    assert 'widget.mark_set("insert", first)' in block
    assert 'widget.icursor(first)' in block


def test_style_callback_has_real_preview_method():
    source = Path('ui/dashboard.py').read_text(encoding='utf-8')
    assert 'def _refresh_status_preview' in source
    assert 'self._refresh_status_preview()' in source
