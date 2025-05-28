from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from settings_window import SettingsWindow
from settings import save_settings
import startup
import logging

def create_dot_icon(color):
    pixmap = QPixmap(24, 24)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(QColor(color))
    painter.drawEllipse(2, 2, 20, 20)
    painter.end()
    return QIcon(pixmap)

class TrayIcon(QSystemTrayIcon):
    def __init__(self, audio_controller, settings, hotkeys=None, status_icon=None, parent=None):
        super().__init__(parent)
        self.audio_controller = audio_controller
        self.settings = settings
        self.hotkeys = hotkeys
        self.status_icon = status_icon
        self.menu = QMenu()

        # Fallback icons (must be set before update_status)
        self.icon_muted = QIcon.fromTheme('audio-input-microphone-muted')
        if self.icon_muted.isNull():
            self.icon_muted = create_dot_icon('#d32f2f')
        self.icon_unmuted = QIcon.fromTheme('audio-input-microphone')
        if self.icon_unmuted.isNull():
            self.icon_unmuted = create_dot_icon('#388e3c')

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
        self.update_status(None)

    def update_status(self, muted):
        # Update tray icon and tooltip based on mute status
        muted = self.audio_controller.is_muted() if muted is None else muted
        if muted:
            self.setIcon(self.icon_muted)
            self.setToolTip('Microphone is muted')
        else:
            self.setIcon(self.icon_unmuted)
            self.setToolTip('Microphone is unmuted')

    def _on_mute(self):
        logging.info('TrayIcon: Mute action triggered from tray')
        self.audio_controller.mute()

    def _on_unmute(self):
        logging.info('TrayIcon: Unmute action triggered from tray')
        self.audio_controller.unmute()

    def _on_toggle(self):
        logging.info('TrayIcon: Toggle action triggered from tray')
        self.audio_controller.toggle()

    def show_settings(self):
        logging.info('TrayIcon: Settings window opened')
        def on_save(new_settings):
            logging.info('TrayIcon: Settings saved: %s', new_settings)
            self.settings.update(new_settings)
            save_settings(self.settings)
            if self.hotkeys:
                self.hotkeys.update_hotkeys(
                    self.settings,
                    self.audio_controller.mute,
                    self.audio_controller.unmute,
                    self.audio_controller.toggle
                )
            if self.status_icon:
                self.status_icon.set_corner(self.settings.get('status_corner', 'top-right'))
            if self.settings.get('start_on_startup', False):
                startup.add_to_startup()
            else:
                startup.remove_from_startup()
            self.update_status(None)
        dlg = SettingsWindow(self.settings, on_save=on_save, parent=None)
        dlg.exec_()

    def exit_app(self):
        logging.info('TrayIcon: Exit action triggered from tray')
        from PyQt5.QtWidgets import QApplication
        QApplication.quit() 