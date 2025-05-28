> [!CAUTION]
> Vibe coded asf

# Better Mute

A Windows utility to manage your microphone mute state with global shortcuts, tray icon, and always-on-top status indicator.

## Features
- System-wide microphone mute/unmute/toggle
- Configurable global shortcuts
- Tray icon with status and context menu
- Always-on-top mini status icon (color-coded)
- Settings window for configuration
- Start on Windows startup option
- Detects when microphone is in use

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   python main.py
   ```

## Packaging
To build a standalone executable:
```bash
pyinstaller --onefile --windowed main.py
``` 