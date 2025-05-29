import logging
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioEndpointVolumeCallback, IMMDeviceEnumerator, EDataFlow, ERole
from comtypes import COMObject, CLSCTX_ALL, CoCreateInstance

from commons import MicStatus


# Define the COM callback interface
class _MuteCallback(COMObject):
    _com_interfaces_ = [IAudioEndpointVolumeCallback]

    def __init__(self, listener):
        super().__init__()
        self.listener = listener

    def OnNotify(self, pNotify):
        notification_data = pNotify.contents
        logging.info('MuteCallback: OnNotify (pNotify.bMuted=%s)', notification_data.bMuted)
        
        try:
            self.listener()
        except Exception as e:
            logging.error(e)

        return 0

class _AudioController:
    def __init__(self):
        self._com_callback = _MuteCallback(self.update)
        self.mic = None
        self.volume = None
        self.reload()
        self._listeners = set()
    
    def update(self):
        status = self.status()
        for listener in self._listeners:
            try:
                listener(status)
            except Exception as e:
                logging.error('Error calling audio controller listener', e)

    def reload(self):
        if self.volume is not None:
            self.volume.UnregisterControlChangeNotify(self._com_callback)

        self.mic = None
        self.volume = None

        try:
            # Get the default input (microphone) device
            self.mic = AudioUtilities.GetMicrophone()
        except Exception as e:
            logging.error(e)
        
        logging.info('AudioController: Initialized (mic found: %s)', bool(self.mic))

        if self.mic is not None:
            interface = self.mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume = interface.QueryInterface(IAudioEndpointVolume)
            self.volume.RegisterControlChangeNotify(self._com_callback)

    def add_listener(self, listener):
        try:
            self._listeners.add(listener)
            listener(self.status())
            logging.info('AudioController: Registered mute change callback')
        except Exception as e:
            logging.warning('AudioController: Failed to register mute change callback: %s', e)

    def remove_listener(self, listener):
        try:
            self._listeners.remove(listener)
            logging.info('AudioController: UnRegistered mute change callback')
        except Exception as e:
            logging.warning('AudioController: Failed to unregister mute change callback: %s', e)

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
            # logging.info('AudioController: is_muted() -> %s', muted)
            return muted
        logging.warning('AudioController: is_muted() -> No microphone')
        return False

    def is_in_use(self):
        # TODO: Implement actual detection of microphone usage
        logging.info('AudioController: is_in_use() called (stub)')
        return False

    def status(self) -> MicStatus:
        if self.mic is None:
            return MicStatus.DISABLED
        if self.is_muted():
            return MicStatus.MUTED
        elif self.is_in_use():
            return MicStatus.INUSE
        else:
            return MicStatus.UNMUTED
    
AudioController = _AudioController()