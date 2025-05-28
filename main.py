import sys
import logging
from PyQt5.QtWidgets import QApplication
from audio_control import AudioController
from tray import TrayIcon
from status_icon import StatusIcon
from settings import load_settings
from hotkeys import HotkeyManager
from PyQt5.QtCore import QCoreApplication

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logging.info('Application started')
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Load settings
    settings = load_settings()
    logging.info('Settings loaded: %s', settings)

    state = {}
    def setup_audio():
        audio_controller = AudioController(settings)
        state['audio_controller'] = audio_controller
        if 'tray' in state:
            state['tray'].audio_controller = audio_controller
        if 'status_icon' in state:
            state['status_icon'].audio_controller = audio_controller
        if 'hotkeys' in state:
            state['hotkeys'].register_hotkeys(audio_controller.mute, audio_controller.unmute, audio_controller.toggle)
        def on_mute_change():
            state['tray'].update_status(None)
            state['status_icon'].update_status(None)
        audio_controller.register_mute_change_callback(on_mute_change)
        logging.info('AudioController re-initialized')

    # Initial AudioController
    audio_controller = AudioController(settings)
    state['audio_controller'] = audio_controller

    # Create always-on-top status icon
    status_icon = StatusIcon(audio_controller, settings)
    status_icon.show()
    state['status_icon'] = status_icon

    # Create tray icon
    tray = TrayIcon(audio_controller, settings, status_icon=status_icon, parent=None)
    tray.show()
    state['tray'] = tray

    # Register global hotkeys
    hotkeys = HotkeyManager(settings)
    hotkeys.register_hotkeys(audio_controller.mute, audio_controller.unmute, audio_controller.toggle)
    state['hotkeys'] = hotkeys

    # Register event-based mute change callback, fallback to timer polling if not supported
    def on_mute_change(muted):
        tray.update_status(muted)
        status_icon.update_status(muted)

    logging.info('TrayIcon and StatusIcon shown')
    audio_controller.register_mute_change_callback(on_mute_change)

    # Listen for device changes
    def on_device_change():
        logging.info('DeviceChangeListener: Audio device change detected, re-initializing AudioController')
        setup_audio()

    # TODO: get notification when device(s) change

    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 