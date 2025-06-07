import keyboard
import logging

from audio_control import AudioController
from settings import Settings

class HotkeyManager:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.hotkey_refs = {}
        self.logger.info('Initialized')
        Settings.add_listener(self.update_settings)

    def update_settings(self, settings):
        self.unregister_hotkeys()

        mute_key   = settings.get('hotkey_mute', 'ctrl+alt+m').lstrip()
        unmute_key = settings.get('hotkey_unmute', 'ctrl+alt+u').lstrip()
        toggle_key = settings.get('hotkey_toggle', 'ctrl+alt+t').lstrip()

        self.logger.info('Registering hotkeys: mute=%s, unmute=%s, toggle=%s', mute_key, unmute_key, toggle_key)
        
        if len(mute_key) > 0:
            self.hotkey_refs['mute'] = keyboard.add_hotkey(mute_key, self._log_and_call('mute', AudioController.mute))
        
        if len(unmute_key) > 0:
            self.hotkey_refs['unmute'] = keyboard.add_hotkey(unmute_key, self._log_and_call('unmute', AudioController.unmute))
        
        if len(toggle_key) > 0:
            self.hotkey_refs['toggle'] = keyboard.add_hotkey(toggle_key, self._log_and_call('toggle', AudioController.toggle))

    def unregister_hotkeys(self):
        for ref in self.hotkey_refs.values():
            try:
                keyboard.remove_hotkey(ref)
            except Exception:
                pass
        if self.hotkey_refs:
            self.logger.info('Unregistered all hotkeys')
        self.hotkey_refs = {}


    def _log_and_call(self, name, cb):
        def wrapper():
            self.logger.info('Hotkey "%s" triggered', name)
            cb()
        return wrapper