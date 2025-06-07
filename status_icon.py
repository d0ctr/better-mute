from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QTimer, Slot
from PySide6.QtGui import QPainter
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
DOT_SIZE = 10

class StatusIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger('StatusIcon')
        
        self.status = MicStatus.DISABLED
        self.corner = (1, 0)
        self.level = 0.0
        self.show_level = False

        self.level_timer = QTimer(self)
        self.level_timer.timeout.connect(self.fetch_level)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
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
        self.logger.debug('update_status(%s)', self.status)
        self.update()

    def update_level(self, level: float):
        self.level = level
        # self.logger.debug('update_level() -> level=%.2f', self.level)
        self.update()
    
    @Slot()
    def fetch_level(self):
        self.level = AudioController.level()
        self.update()

    def update_settings(self, settings):
        self.corner = settings.get('status_corner', 'top-right')

        show_level = settings.get('show_level', False)
        
        if show_level and not self.level_timer.isActive():
            self.level_timer.start()
        elif not show_level and self.level_timer.isActive():
            self.level_timer.stop()
            self.level = 0.0
        
        self.logger.debug('update_settings({status_corner: %s, show_level: %s})', self.corner, show_level)
        self.update()

    def paintEvent(self, _):
        with QPainter(self) as painter:
            # Colors
            color = MicStatus.toColor(self.status)
            screen = self.screen().geometry()

            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            
            # Size
            width = max(DOT_SIZE, int(DOT_SIZE * 10 * self.level))
            self.setFixedSize(width + MARGIN * 2, DOT_SIZE + MARGIN * 2)

            # Position
            x_factor, y_factor = CORNER_POSITIONS.get(self.corner, (1, 0))
            x = screen.left() + MARGIN if x_factor == 0 else screen.right() - self.width() - MARGIN
            y = screen.top() + MARGIN if y_factor == 0 else screen.bottom() - self.height() - MARGIN
            self.move(x, y)
            
            # Shape
            rect = QRect(0, 0, width, DOT_SIZE)
            painter.drawRoundedRect(rect, DOT_SIZE  / 2, DOT_SIZE / 2)
