import sys
import logging
import multiprocessing
import argparse
import os
import psutil
import time
from tempfile import gettempdir
from pathlib import Path
from getpass import getuser
from contextlib import contextmanager

def is_running_as_exe():
    return getattr(sys, 'frozen', False)

# Setup logging
LOG_FORMAT = '%(asctime)s | %(threadName)-10s | %(name)-12s | %(levelname)-8s | %(message)s'
HANDLERS = []

def get_temp_log_path():
    username = getuser()
    temp_dir = gettempdir()
    return Path(temp_dir) / f'better-mute-{username}.log'

if is_running_as_exe():
    # When running as exe, add file handler in temp directory
    file_handler = logging.FileHandler(get_temp_log_path())
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    HANDLERS.append(file_handler)
else:
    HANDLERS.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    handlers=HANDLERS
)

def parse_args():
    parser = argparse.ArgumentParser(description='Better Mute - Audio Control Application')
    parser.add_argument('-l', '--logs', action='store_true', help='Print path to current log file and exit')
    parser.add_argument('--toggle', action='store_true', help='Toggle microphone mute state and exit')
    parser.add_argument('--mute', action='store_true', help='Mute microphone and exit')
    parser.add_argument('--unmute', action='store_true', help='Unmute microphone and exit')
    parser.add_argument('--stop', action='store_true', help='Stop all running better-mute processes')
    return parser.parse_args()

def get_pid_file():
    username = getuser()
    temp_dir = gettempdir()
    return Path(temp_dir) / f'better-mute-{username}.pid'

def is_process_running(pid):
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.name().lower().startswith(('python', 'better-mute'))
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False

def find_and_stop_existing():
    pid_file = get_pid_file()
    
    if pid_file.exists():
        try:
            # Read the PID from the file
            with open(pid_file, 'r') as f:
                try:
                    old_pid = int(f.read().strip())
                    # Check if the process is still running
                    if is_process_running(old_pid):
                        logging.info('Found previous instance (%s), terminating', old_pid)
                        try:
                            process = psutil.Process(old_pid)
                            process.terminate()
                            # Wait for the process to terminate (up to 5 seconds)
                            process.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            logging.warning('Previous instance did not terminate in time, forcing')
                            process.kill()
                        except Exception as e:
                            logging.error('Error terminating previous instance', exc_info=e)
                            raise e
                    else:
                        logging.info('Found previous instance (%s), but process does not exist', old_pid)
                except ValueError as e:
                    logging.warning('Invalid PID in file', exc_info=e)
        except Exception as e:
            logging.error('Error reading PID file', exc_info=e)
            raise e


@contextmanager
def pid_file_manager():
    pid_file = get_pid_file()
    pid = os.getpid()

    try:
        find_and_stop_existing()
    except Exception as e:
        logging.error('Could not clean-up existing process', exc_info=e)
        raise

    # Write our PID to the file
    try:
        logging.debug('Writing new pid file (%s)', pid)
        with open(pid_file, 'w') as f:
            f.write(str(pid))
        yield
    except Exception as e:
        logging.error('Application error', exc_info=e)
    finally:
        try:
            if pid_file.exists():
                # Verify the PID in the file is our own before deleting
                with open(pid_file, 'r') as f:
                    stored_pid = int(f.read().strip())
                try:
                    if stored_pid == pid:
                        pid_file.unlink()
                        logging.debug('Cleaned up PID file')
                except (ValueError, OSError):
                    # If we can't read the PID or it's not a number, delete the file anyway
                    pid_file.unlink()
                    logging.debug('Cleaned up invalid PID file')
        except Exception as e:
            logging.error('Error cleaning up PID file', exc_info=e)

def main():
    args = parse_args()
    
    # Handle --logs argument
    if args.logs:
        print(f'Log file: {get_temp_log_path()}')
        return

    if args.stop:
        find_and_stop_existing()
        return
    
    from audio_control import AudioController # just to initilize

    # Handle audio control arguments
    if args.toggle:
        AudioController.toggle()
        return
    if args.mute:
        AudioController.mute()
        return
    if args.unmute:
        AudioController.unmute()
        return

    # Handle previous instance and manage PID file
    with pid_file_manager():
        from PySide6.QtWidgets import QApplication
        from tray import TrayIcon
        from status_icon import StatusIcon
        from hotkeys import HotkeyManager
        from startup import StartupManager

        # Start event loop
        logging.info('Application started')
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # Register global hotkeys
        HotkeyManager()

        # Create always-on-top status icon
        StatusIcon()

        # Create tray icon
        TrayIcon()

        # Create startup manager
        StartupManager()

        # start listening for device changes
        AudioController.start()

        # TODO: get notification when device(s) change
        # # Listen for device changes
        # def on_device_change():
        #     logging.info('DeviceChangeListener: Audio device change detected, re-initializing AudioController')
        #     AudioController.reload()      
        sys.exit(app.exec())

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()