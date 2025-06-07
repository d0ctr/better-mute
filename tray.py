from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from settings_window import SettingsWindow
from settings import Settings
import logging

from audio_control import AudioController
from commons import MicStatus


def create_dot_icon(color: QColor):
    pixmap = QPixmap(24, 24)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(color)
    painter.setPen(color)
    painter.drawEllipse(2, 2, 20, 20)
    painter.end()
    return QIcon(pixmap)

class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.menu = QMenu()

        # Fallback icons (must be set before update_status)
        self.icon_muted = create_dot_icon(MicStatus.toColor(MicStatus.MUTED))
        self.icon_unmuted = create_dot_icon(MicStatus.toColor(MicStatus.UNMUTED))
        self.icon_disabled = create_dot_icon(MicStatus.toColor(MicStatus.DISABLED))
        self.icon_in_use = create_dot_icon(MicStatus.toColor(MicStatus.INUSE))

        # Actions
        self.mute_action = QAction('Mute', self)
        self.unmute_action = QAction('Unmute', self)
        self.toggle_action = QAction('Toggle', self)
        self.settings_action = QAction('Settings', self)
        self.exit_action = QAction('Exit', self)

        self.mute_action.triggered.connect(self._on_mute)
        self.unmute_action.triggered.connect(self._on_unmute)
        self.toggle_action.triggered.connect(self._on_toggle)
        self.settings_action.triggered.connect(self.show_settings)
        self.exit_action.triggered.connect(self.exit_app)

        self.menu.addAction(self.mute_action)
        self.menu.addAction(self.unmute_action)
        self.menu.addAction(self.toggle_action)
        self.menu.addSeparator()
        self.menu.addAction(self.settings_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

        self.setContextMenu(self.menu)
        self.setToolTip('Better Mute')

        AudioController.add_status_listener(self.update_status)
        self.show()

    def update_status(self, status: MicStatus):
        # Update tray icon and tooltip based on mute status
        icon = None
        tooltip = None
        
        match status:
            case MicStatus.MUTED:
                icon = self.icon_muted
                tooltip = 'muted'
            case MicStatus.UNMUTED:
                icon = self.icon_unmuted
                tooltip = 'unmuted'
            case MicStatus.INUSE:
                icon = self.icon_in_use
                tooltip = 'in use'
            case _:
                icon = self.icon_disabled
                tooltip = 'disabled'

        self.setIcon(icon)
        self.setToolTip('Microphone is ' + tooltip)

    def _on_mute(self):
        logging.info('TrayIcon: Mute action triggered from tray')
        AudioController.mute()

    def _on_unmute(self):
        logging.info('TrayIcon: Unmute action triggered from tray')
        AudioController.unmute()

    def _on_toggle(self):
        logging.info('TrayIcon: Toggle action triggered from tray')
        AudioController.toggle()

    def show_settings(self):
        logging.info('TrayIcon: Settings window opened')
        
        def on_save(new_settings):
            logging.info('TrayIcon: Settings saved: %s', new_settings)
            Settings.update(new_settings)

        dlg = SettingsWindow(on_save=on_save)
        dlg.exec_()

    def exit_app(self):
        logging.info('TrayIcon: Exit action triggered from tray')
        AudioController.unmute()
        from PyQt5.QtWidgets import QApplication
        QApplication.quit() 