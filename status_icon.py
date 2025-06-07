from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter
import logging

from audio_control import AudioController, MicStatus
from settings import Settings


CORNER_POSITIONS = {
    'top-left': (0, 0),
    'top-right': (1, 0),
    'bottom-left': (0, 1),
    'bottom-right': (1, 1),
}

MARGIN = 2

class StatusIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.status = MicStatus.DISABLED
        self.corner = 'top-right'
        self.level = 0.0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        AudioController.add_status_listener(self.update_status)
        Settings.add_listener(self.update_settings)
        
        self.show()

        # Try to make the window click-through (optional, Windows only)
        try:
            import ctypes
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
        except Exception:
            pass

    def update_status(self, status: MicStatus):
        self.status = status
        logging.info('StatusIcon: update_status() -> status=%s', self.status)
        self.update()

    def update_level(self, level: float):
        self.level = level
        # logging.debug('StatusIcon: update_level() -> level=%.2f', self.level)
        self.update()

    def paintEvent(self, event):
        # Colors
        painter = QPainter(self)
        color = MicStatus.toColor(self.status)
        screen = self.screen().geometry()

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        
        # Size
        min_dim = min(screen.width(), screen.height())
        dot_size = max(12, int(min_dim * 0.005))  # Minimum 12px
        width = max(dot_size, int(dot_size * 10 * self.level))
        self.setFixedSize(width + MARGIN * 2, dot_size + MARGIN * 2)

        # Position
        x_factor, y_factor = CORNER_POSITIONS.get(self.corner, (1, 0))
        x = screen.left() + MARGIN if x_factor == 0 else screen.right() - self.width() - MARGIN
        y = screen.top() + MARGIN if y_factor == 0 else screen.bottom() - self.height() - MARGIN
        self.move(x, y)
        
        # Shape
        rect = QRect(MARGIN, MARGIN, width, dot_size)
        painter.drawRoundedRect(rect, dot_size / 2, dot_size / 2)

    def update_settings(self, settings):
        self.corner = settings.get('status_corner', 'top-right')
        logging.info('StatusIcon: set_corner(%s)', self.corner)
        if settings.get('show_level', False):
            AudioController.add_level_listener(self.update_level)

        self.update()