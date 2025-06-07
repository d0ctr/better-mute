from PySide6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QLayout,
    QPushButton, QComboBox, QCheckBox, QGroupBox, QSpacerItem, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPalette, QColor, QFont, QGuiApplication
from settings import Settings

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.settings = Settings.load_settings().copy()

        # Use Fusion style for a modern look
        QApplication.setStyle('Fusion')
        # Set a dark palette for Fusion style
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QGuiApplication.setPalette(palette)

        # Set a larger, system-like font
        font = QFont()
        font.setPointSize(11)
        self.setFont(font)

        # Set dark title bar for Windows 10/11
        try:
            import ctypes
            hwnd = int(self.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception as e:
            pass

        main_layout = QVBoxLayout()
        form_group = QGroupBox("Shortcuts")
        form_layout = QFormLayout()

        self.mute_edit = QLineEdit(self.settings.get('hotkey_mute', 'ctrl+alt+m'))
        self.mute_edit.setMinimumWidth(200)
        self.mute_edit.setToolTip("Set the global mute hotkey")
        form_layout.addRow(QLabel('Mute Hotkey:'), self.mute_edit)

        self.unmute_edit = QLineEdit(self.settings.get('hotkey_unmute', 'ctrl+alt+u'))
        self.unmute_edit.setMinimumWidth(200)
        self.unmute_edit.setToolTip("Set the global unmute hotkey")
        form_layout.addRow(QLabel('Unmute Hotkey:'), self.unmute_edit)

        self.toggle_edit = QLineEdit(self.settings.get('hotkey_toggle', 'ctrl+alt+t'))
        self.toggle_edit.setMinimumWidth(200)
        self.toggle_edit.setToolTip("Set the global toggle hotkey")
        form_layout.addRow(QLabel('Toggle Hotkey:'), self.toggle_edit)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # Status icon section
        icon_group = QGroupBox("Status Icon")
        icon_layout = QFormLayout()
        self.corner_combo = QComboBox()
        self.corner_combo.addItems(['top-left', 'top-right', 'bottom-left', 'bottom-right'])
        self.corner_combo.setCurrentText(self.settings.get('status_corner', 'top-right'))
        self.corner_combo.setToolTip("Choose the screen corner for the status icon")
        icon_layout.addRow(QLabel('Status Icon Corner:'), self.corner_combo)
        icon_group.setLayout(icon_layout)
        main_layout.addWidget(icon_group)

        # Startup option
        self.startup_checkbox = QCheckBox('Start on Windows Startup')
        self.startup_checkbox.setChecked(self.settings.get('start_on_startup', False))
        self.startup_checkbox.setToolTip("Enable to start the app automatically with Windows")
        main_layout.addWidget(self.startup_checkbox)
        
        # Show level option
        self.level_checkbox = QCheckBox('Show microphone level')
        self.level_checkbox.setChecked(self.settings.get('show_level', False))
        self.level_checkbox.setToolTip("Enable to show microphone level")
        main_layout.addWidget(self.level_checkbox)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.save_btn = QPushButton('Save')
        self.cancel_btn = QPushButton('Cancel')
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.save_btn.clicked.connect(self.save)
        self.cancel_btn.clicked.connect(self.reject)

        # Set a minimum, scalable size and allow resizing
        base_width, base_height = 400, 320
        # scale = QGuiApplication.devicePixelRatio(QGuiApplication.instance())
        # min_width = int(base_width * scale)
        # min_height = int(base_height * scale)
        self.setMinimumSize(base_width, base_height)
        # self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, False)
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    @Slot()
    def save(self):
        self.settings['hotkey_mute'] = self.mute_edit.text()
        self.settings['hotkey_unmute'] = self.unmute_edit.text()
        self.settings['hotkey_toggle'] = self.toggle_edit.text()
        self.settings['status_corner'] = self.corner_combo.currentText()
        self.settings['start_on_startup'] = self.startup_checkbox.isChecked()
        self.settings['show_level'] = self.level_checkbox.isChecked()
        
        Settings.update(self.settings)
        self.accept() 