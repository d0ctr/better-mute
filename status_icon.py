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

class StatusIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.margin = 2
        
        self.status = MicStatus.DISABLED
        screen = self.screen().geometry()
        min_dim = min(screen.width(), screen.height())
        self.dot_size = max(12, int(min_dim * 0.005))  # Minimum 8px
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.dot_size + self.margin * 2, self.dot_size + self.margin * 2)

        AudioController.add_listener(self.update_status)
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

    def paintEvent(self, event):
        painter = QPainter(self)
        color = MicStatus.toColor(self.status)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        rect = QRect(self.margin, self.margin, self.dot_size, self.dot_size)
        painter.drawEllipse(rect)

    def update_settings(self, settings):
        self.corner = settings.get('status_corner', 'top-right')
        logging.info('StatusIcon: set_corner(%s)', self.corner)
        self.update_position()
        self.update()

    def update_position(self):
        screen = self.screen().geometry()
        self.setFixedSize(self.dot_size + self.margin * 2, self.dot_size + self.margin * 2)
        x_factor, y_factor = CORNER_POSITIONS.get(self.corner, (1, 0))
        x = screen.left() + self.margin if x_factor == 0 else screen.right() - self.width() - self.margin
        y = screen.top() + self.margin if y_factor == 0 else screen.bottom() - self.height() - self.margin
        self.move(x, y)
        logging.info('StatusIcon: Moved to (%d, %d)', x, y)