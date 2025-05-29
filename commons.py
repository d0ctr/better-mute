from enum import Enum

from PyQt5.QtGui import QColor


Colors = {
    'GREEN':  QColor(0,   200,   0, 255),
    'RED':    QColor(200,   0,   0, 255),
    'YELLOW': QColor(255, 200,   0, 255),
    'GRAY':   QColor(230, 230, 230, 255),
}


class MicStatus(Enum):
    DISABLED = 0
    UNMUTED  = 1
    INUSE    = 2
    MUTED    = 3

    @staticmethod
    def toColor(status) -> QColor:
        match status:
            case MicStatus.DISABLED:
                return Colors['GRAY']
            case MicStatus.MUTED:
                return Colors['RED']
            case MicStatus.UNMUTED:
                return Colors['GREEN']
            case MicStatus.INUSE:
                return Colors['YELLOW']