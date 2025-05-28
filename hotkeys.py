import keyboard
import logging

class HotkeyManager:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.hotkey_refs = {}
        logging.info('HotkeyManager: Initialized')

    def register_hotkeys(self, mute_cb, unmute_cb, toggle_cb):
        self.unregister_hotkeys()
        mute_key = self.settings.get('hotkey_mute', 'ctrl+alt+m')
        unmute_key = self.settings.get('hotkey_unmute', 'ctrl+alt+u')
        toggle_key = self.settings.get('hotkey_toggle', 'ctrl+alt+t')
        logging.info('HotkeyManager: Registering hotkeys: mute=%s, unmute=%s, toggle=%s', mute_key, unmute_key, toggle_key)
        
        if len(mute_key) > 0:
            self.hotkey_refs['mute'] = keyboard.add_hotkey(mute_key, self._log_and_call('mute', mute_cb))
        
        if len(unmute_key) > 0:
            self.hotkey_refs['unmute'] = keyboard.add_hotkey(unmute_key, self._log_and_call('unmute', unmute_cb))
        
        if len(toggle_key) > 0:
            self.hotkey_refs['toggle'] = keyboard.add_hotkey(toggle_key, self._log_and_call('toggle', toggle_cb))

    def unregister_hotkeys(self):
        for ref in self.hotkey_refs.values():
            try:
                keyboard.remove_hotkey(ref)
            except Exception:
                pass
        if self.hotkey_refs:
            logging.info('HotkeyManager: Unregistered all hotkeys')
        self.hotkey_refs = {}

    def update_hotkeys(self, settings, mute_cb, unmute_cb, toggle_cb):
        self.settings = settings
        logging.info('HotkeyManager: Updating hotkeys')
        self.register_hotkeys(mute_cb, unmute_cb, toggle_cb)

    def _log_and_call(self, name, cb):
        def wrapper():
            logging.info('HotkeyManager: Hotkey "%s" triggered', name)
            cb()
        return wrapper 