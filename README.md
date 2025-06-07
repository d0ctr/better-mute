> [!CAUTION]
> Vibe coded asf

# Better Mute

A modern Windows utility for managing your microphone mute state with global shortcuts, system tray integration, and an always-on-top status indicator.

## Features

- 🎤 **System-wide Microphone Control**
  - Mute/Unmute/Toggle functionality
  - Works with all Windows audio devices
  - Supports multiple audio roles (Communications, Multimedia, Console)
  - Real-time microphone level monitoring
  - Automatic device change detection
  - Status monitoring (Muted, Unmuted, In Use, Disabled)

- ⌨️ **Global Hotkeys**
  - Configurable keyboard shortcuts
  - Default: `Ctrl+Alt+M` for toggle
  - Customizable for mute/unmute actions
  - Multiple hotkey support

- 🖥️ **Visual Indicators**
  - System tray icon with status
  - Always-on-top mini status indicator
  - Click-through window support
  - Color-coded status display:
    - 🟢 Green: Unmuted
    - 🔴 Red: Muted
    - 🟡 Yellow: In Use
    - ⚪ Gray: Disabled
  - Real-time microphone level visualization
  - Configurable corner positions (top-left, top-right, bottom-left, bottom-right)

- ⚙️ **Customization**
  - Dark mode settings window
  - Configurable status icon position
  - Microphone level visualization toggle
  - Windows startup integration
  - Automatic startup management
  - Hotkey configuration
  - Status icon position settings

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/better-mute.git
   cd better-mute
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

### From Executable

1. Download the latest release from the [Releases](https://github.com/yourusername/better-mute/releases) page
2. Run the `better-mute.exe` file

## Usage

### Basic Controls

- **System Tray Icon**: Right-click to access menu options
- **Status Icon**: Shows current microphone state
- **Global Hotkeys**: Use configured shortcuts for quick control

### Command Line Interface

The application can be controlled via command line:

```bash
# Toggle microphone state
better-mute --toggle

# Mute microphone
better-mute --mute

# Unmute microphone
better-mute --unmute

# Stop all running instances
better-mute --stop

# Print path to log file
better-mute --logs
```

### Configuration

1. Right-click the system tray icon
2. Select "Settings"
3. Configure:
   - Global hotkeys
   - Status icon position
   - Startup options
   - Microphone level display

## Development

### Building from Source

To create a standalone executable:
```bash
pyinstaller --onefile --windowed main.py
```

### Requirements

- Python 3.8 or higher
- Windows 10/11
- Required Python packages (see `requirements.txt`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with [PySide6](https://www.qt.io/qt-for-python)
- Audio control powered by [pycaw](https://github.com/AndreMiras/pycaw) 