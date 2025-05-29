import os
import sys
import win32com.client
import logging

from settings import Settings

APP_NAME = 'BetterMute'

def get_startup_folder():
    # Get the path to the user's Startup folder
    return os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')

class StartupManager:
    def __init__(self) -> None:
        Settings.add_listener(self.update_settings)

    def update_settings(self, settings):
        add = settings.get('start_on_startup', False)
        if add:
            self.add_to_startup()
        else:
            self.remove_from_startup()

    def add_to_startup(self):
        startup_folder = get_startup_folder()
        shortcut_path = os.path.join(startup_folder, f'{APP_NAME}.lnk')
        target = sys.executable
        script = os.path.abspath(sys.argv[0])
        # If running as a script, use pythonw.exe to avoid console window
        if target.lower().endswith('python.exe'):
            target = target.replace('python.exe', 'pythonw.exe')
        working_dir = os.path.dirname(script)
        icon = script
        shell = win32com.client.Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.Arguments = f'"{script}"'
        shortcut.WorkingDirectory = working_dir
        shortcut.IconLocation = icon
        shortcut.save()
        logging.info('StartupManager: Added app to Windows startup: %s', shortcut_path)


    def remove_from_startup(self):
        startup_folder = get_startup_folder()
        shortcut_path = os.path.join(startup_folder, f'{APP_NAME}.lnk')
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            logging.info('StartupManager: Removed app from Windows startup: %s', shortcut_path)
        else:
            logging.info('StartupManager: No startup shortcut to remove: %s', shortcut_path) 