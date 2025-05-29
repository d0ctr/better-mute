import json
import os
import logging

SETTINGS_FILE = 'settings.json'

class _Settings:

    def __init__(self) -> None:
        self._settings = None
        self._listeners = set()
        self.load_settings()

    def load_settings(self):
        if self._settings is not None:
            return self._settings
        
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                self._settings = json.load(f)
                logging.info('Settings loaded: %s', self._settings)
        else:
            self._settings = {}
        
        self._notify()

        return self._settings

    def save_settings(self, settings):
        self._settings = settings
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._settings, f, indent=4)
        
        self._notify()
    
    def update(self, settings):
        if self._settings is None:
            self.load_settings()
        
        self._settings.update(settings)
        
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._settings, f, indent=4)
        
        self._notify()
    
    def _notify(self):
        for listener in self._listeners:
            try:
                listener(self._settings)
            except Exception as e:
                logging.error(e)
    
    def add_listener(self, listener):
        self._listeners.add(listener)
        listener(self._settings)

    def remove_listener(self, listener):
        self._listeners.remove(listener)
        

        


Settings = _Settings()