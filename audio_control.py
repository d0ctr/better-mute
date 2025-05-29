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
        logging.info('AudioController: is_in_use() called')
        if not self.mic or not self.volume:
            logging.warning('AudioController: No microphone to check usage')
            return False

        try:
            # Get the device enumerator
            device_enumerator = CoCreateInstance(IMMDeviceEnumerator._iid_,
                                                 IMMDeviceEnumerator,
                                                 CLSCTX_ALL)

            # Get the default microphone device ID
            default_mic_device = device_enumerator.GetDefaultAudioEndpoint(EDataFlow.eCapture.value, ERole.eCommunications.value)
            if not default_mic_device:
                logging.warning("Could not get default microphone device.")
                return False
            default_mic_id_str = default_mic_device.GetId()

            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.State == 1:  # State == 1 means active
                    try:
                        # Get the session's control interface to access device information
                        session_control = session.QueryInterface(AudioUtilities.IAudioSessionControl2)
                        if not session_control:
                            continue

                        # Get the audio meter information to check for activity
                        audio_meter = session_control.QueryInterface(AudioUtilities.IAudioMeterInformation)
                        if audio_meter and audio_meter.GetPeakValue() > 0.0:
                            # Get the audio session's device
                            session_device = session_control.GetSessionIdentifier()
                            if session_device:
                                # The session_device is a string, format is {guid}#{device_id}
                                # We need to parse the actual device ID part
                                # However, a simpler check is to see if the session is associated with a capture device.
                                # A more direct way to check if the session is using *our* specific microphone
                                # is to get the device for the session and compare its ID.

                                # Get the device for the current session
                                # This part is tricky as IAudioSessionControl2 doesn't directly give IMMDevice
                                # We might need to iterate devices and match properties, or find a more direct way.

                                # For now, let's assume if a session has activity and is not system sounds,
                                # and it's on a capture device, it's using a mic.
                                # A truly robust check involves matching the session's device ID to our mic's ID.
                                
                                # Attempt to get the device for the session
                                # This is still a simplification, as getting the exact device for a session is not straightforward
                                # with just IAudioSessionControl2. The session identifier might not directly map to IMMDevice.

                                if not session.IsSystemSoundsSession:
                                    # Crude check: if it's active and not system sounds, assume it's using the mic.
                                    # This needs to be improved to check the actual device ID against the default mic.
                                    pid = session.ProcessId
                                    process_name = AudioUtilities.GetProcessName(pid) if pid else "Unknown Process"
                                    logging.info(f"Microphone might be in use by: {process_name} (PID: {pid}) - active audio session detected.")
                                    return True

                    except Exception as e:
                        # Log specific session check errors but continue checking other sessions
                        if hasattr(session, 'ProcessId'):
                            pid = session.ProcessId
                            process_name = AudioUtilities.GetProcessName(pid) if pid else "Unknown Process"
                            logging.error(f"Error checking session for process {process_name} (PID: {pid}): {e}")
                        else:
                            logging.error(f"Error checking session (no PID): {e}")
        except Exception as e:
            logging.error(f"Error in is_in_use: {e}")

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