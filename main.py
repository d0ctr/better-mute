import sys
import logging
import multiprocessing

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(threadName)-10s | %(name)-12s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from PyQt5.QtWidgets import QApplication
from tray import TrayIcon
from status_icon import StatusIcon
from hotkeys import HotkeyManager


def main():
    # Start event loop
    logging.info('Application started')
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Register global hotkeys
    HotkeyManager()

    # Create always-on-top status icon
    StatusIcon()

    # Create tray icon
    TrayIcon()

    # TODO: get notification when device(s) change
    # # Listen for device changes
    # def on_device_change():
    #     logging.info('DeviceChangeListener: Audio device change detected, re-initializing AudioController')
    #     AudioController.reload()      
    sys.exit(app.exec_())

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()