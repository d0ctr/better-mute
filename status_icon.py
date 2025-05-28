from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QColor
import logging

CORNER_POSITIONS = {
    'top-left': (0, 0),
    'top-right': (1, 0),
    'bottom-left': (0, 1),
    'bottom-right': (1, 1),
}

Colors = {
    'GREEN':  QColor(0,   200, 0, 255),
    'RED':    QColor(200,   0, 0, 255),
    'YELLOW': QColor(255, 200, 0, 255)
}

class StatusIcon(QWidget):
    def __init__(self, audio_controller, settings, parent=None):
        super().__init__(parent)
        self.audio_controller = audio_controller
        self.settings = settings
        self.margin = 2
        self.corner = settings.get('status_corner', 'top-right')
        screen = self.screen().geometry()
        min_dim = min(screen.width(), screen.height())
        self.dot_size = max(12, int(min_dim * 0.005))  # Minimum 8px
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.dot_size + self.margin * 2, self.dot_size + self.margin * 2)
        self.update_position()
        self.show()
        logging.info('StatusIcon: Shown at corner %s', self.corner)
        self.update_status(None)

        # Try to make the window click-through (optional, Windows only)
        try:
            import ctypes
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
        except Exception:
            pass

    def update_status(self, muted):
        self.is_muted = muted if muted is not None else self.audio_controller.is_muted()
        self.is_in_use = self.audio_controller.is_in_use()
        logging.info('StatusIcon: update_status() -> muted=%s, in_use=%s', self.is_muted, self.is_in_use)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.is_in_use:
            color = Colors['YELLOW']
        elif self.is_muted:
            color = Colors['RED']
        else:
            color = Colors['GREEN']
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        rect = QRect(self.margin, self.margin, self.dot_size, self.dot_size)
        painter.drawEllipse(rect)

    def set_corner(self, corner):
        self.corner = corner
        logging.info('StatusIcon: set_corner(%s)', corner)
        self.update_position()
        self.update_status(None)

    def update_position(self):
        screen = self.screen().geometry()
        min_dim = min(screen.width(), screen.height())
        self.setFixedSize(self.dot_size + self.margin * 2, self.dot_size + self.margin * 2)
        x_factor, y_factor = CORNER_POSITIONS.get(self.corner, (1, 0))
        x = screen.left() + self.margin if x_factor == 0 else screen.right() - self.width() - self.margin
        y = screen.top() + self.margin if y_factor == 0 else screen.bottom() - self.height() - self.margin
        self.move(x, y)
        logging.info('StatusIcon: Moved to (%d, %d)', x, y)