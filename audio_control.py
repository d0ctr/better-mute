from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioEndpointVolumeCallback

from comtypes import COMObject, CLSCTX_ALL
import logging

# Define the COM callback interface
class MuteCallback(COMObject):
    _com_interfaces_ = [IAudioEndpointVolumeCallback]

    def __init__(self, on_mute_change):
        super().__init__()
        self.on_mute_change = on_mute_change

    def OnNotify(self, pNotify):
        notification_data = pNotify.contents
        logging.info('MuteCallback: OnNotify (pNotify.bMuted=%s)', notification_data.bMuted)
        if self.on_mute_change:
            self.on_mute_change(bool(notification_data.bMuted))
        return 0  # S_OK

class AudioController:
    def __init__(self, settings=None):
        # Get the default input (microphone) device
        self.mic = None
        self.volume = None

        try:
            self.mic = AudioUtilities.GetMicrophone()
        except Exception:
            pass

        if self.mic is not None:
            interface = self.mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume = interface.QueryInterface(IAudioEndpointVolume)

        self._mute_change_callback = None
        self._com_callback = None
        logging.info('AudioController: Initialized (mic found: %s)', bool(self.mic))

    def register_mute_change_callback(self, callback):
        if self.volume:
            self._mute_change_callback = callback
            self._com_callback = MuteCallback(callback)
            try:
                self.volume.RegisterControlChangeNotify(self._com_callback)
                logging.info('AudioController: Registered mute change callback')
                return True
            except Exception as e:
                logging.warning('AudioController: Failed to register mute change callback: %s', e)
                return False
        return False

    def mute(self):
        logging.info('AudioController: mute() called')
        if self.volume:
            self.volume.SetMute(1, None)
            logging.info('AudioController: Microphone muted')
        else:
            logging.warning('AudioController: No microphone to mute')

    def unmute(self):
        logging.info('AudioController: unmute() called')
        if self.volume:
            self.volume.SetMute(0, None)
            logging.info('AudioController: Microphone unmuted')
        else:
            logging.warning('AudioController: No microphone to unmute')

    def toggle(self):
        logging.info('AudioController: toggle() called')
        if self.volume:
            current = self.volume.GetMute()
            self.volume.SetMute(0 if current else 1, None)
            logging.info('AudioController: Microphone toggled to %s', 'unmuted' if current else 'muted')
        else:
            logging.warning('AudioController: No microphone to toggle')

    def is_muted(self):
        if self.volume:
            muted = bool(self.volume.GetMute())
            logging.info('AudioController: is_muted() -> %s', muted)
            return muted
        logging.warning('AudioController: is_muted() -> No microphone')
        return False

    def is_in_use(self):
        # TODO: Implement actual detection of microphone usage
        logging.info('AudioController: is_in_use() called (stub)')
        return False 