import logging
import threading
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioEndpointVolumeCallback, IMMNotificationClient, EDataFlow, ERole
from comtypes import COMObject, CLSCTX_ALL, CoInitializeEx, CoUninitialize, COINIT_MULTITHREADED

from commons import MicStatus


# Define the COM callback interface
class _MuteCallback(COMObject):
    _com_interfaces_ = [IAudioEndpointVolumeCallback]

    def __init__(self, listener):
        super().__init__()
        self.listener = listener

    def OnNotify(self, pNotify):
        notification_data = pNotify.contents
        logging.debug('MuteCallback: OnNotify (pNotify.bMuted=%s)', notification_data.bMuted)
        
        try:
            self.listener()
        except Exception as e:
            logging.error('MuteCallback.OnNotify:', exc_info=e)

class _DeviceCallback(COMObject):
    _com_interfaces_ = [IMMNotificationClient]

    def __init__(self, listener):
        super().__init__()
        self.listener = listener
    
    def OnDefaultDeviceChanged(self, flow, role, pwstrDefaultDeviceId):
        if flow != EDataFlow.eCapture.value:
            return
        if role != ERole.eMultimedia.value:
            return
        
        logging.debug('DeviceCallback: OnDefaultDeviceChanged (flow=%s, role=%s, id=%s)', flow, role, pwstrDefaultDeviceId)

        try:
            self.listener(pwstrDefaultDeviceId)
        except Exception as e:
            logging.error('MuteCallback.OnDefaultDeviceChanged', exc_info=e)

    def OnDeviceAdded(self, pwstrDeviceId):
        logging.debug('MuteCallback.OnDeviceAdded: %s', pwstrDeviceId)
        
    def OnDeviceRemoved(self, pwstrDeviceId):
        logging.debug('MuteCallback.OnDeviceRemoved: %s', pwstrDeviceId)

    def OnDeviceStateChanged(self, pwstrDeviceId, dwNewState):
        logging.debug('MuteCallback.OnDeviceStateChanged: %s, state -> %s', pwstrDeviceId, dwNewState)
        
    def OnPropertyValueChanged(self, pwstrDeviceId, key):
        logging.debug('MuteCallback.OnPropertyValueChanged: %s, key=%s', pwstrDeviceId, key)

class _AudioController:
    def __init__(self):
        self.mic = None
        self.volume = None
        self._listeners = set()
        self._reload_condition = threading.Condition()
        self.reload()
        self._register_device_callback()
        self._reload_thread = threading.Thread(target=self.reload_runner, daemon=True)
        self._reload_thread.start()
    
    def _update_state(self):
        status = self.status()
        for listener in self._listeners:
            try:
                listener(status)
            except Exception as e:
                logging.error('AudioController: Error calling audio controller listener', exc_info=e)
    
    def _update_device(self, id):
        if self.mic is not None and self.mic.GetId() == id:
            logging.debug('AudioController: Default device did not change, skipping')
            return
        
        logging.info('AudioController: Updating active microphone -> (%s)', id)
        with self._reload_condition:
            self._reload_condition.notify()
        

    def reload(self):
        if self.mic is not None:
            logging.debug('AudioController: Unregister listener for old device (%s)', self.mic.GetId())
            try:
                self.volume.UnregisterControlChangeNotify(self._mute_callback)
            except Exception as e:
                logging.warning('AudioController: Error unregistering listener for old device', exc_info=e)

            logging.debug('AudioController: Unmute old device (%s)', self.mic.GetId())
            try:
                self.unmute()
            except Exception as e:
                logging.warning('AudioController: Error unmuting old device', exc_info=e)

            self.volume = None
            self.mic = None

            logging.info('AudioController: Released old device')

        try:
            self.mic = AudioUtilities.GetMicrophone()
            logging.info('AudioController: Initialized (mic found: %s)', self.mic.GetId() if bool(self.mic) else False)
        except Exception as e:
            logging.error('AudioController.reload', exc_info=e)
            return
        
        self._register_mute_callback()
    
    def reload_runner(self):
        CoInitializeEx(COINIT_MULTITHREADED)
        try:
            while True:
                with self._reload_condition:
                    logging.debug('AudioController: reload_runner waiting for reload condition.')
                    self._reload_condition.wait()
                    logging.debug('AudioController: reload_runner received notification, proceeding to reload.')
                    try:
                        self.reload()
                    except Exception as e:
                        # Log exceptions specifically from the self.reload() call
                        logging.error('AudioController: Exception during self.reload() in reload_runner', exc_info=e)
        except Exception as e:
            # Log other exceptions from the loop itself (e.g., if wait() is interrupted unexpectedly)
            logging.error("AudioController: Exception in reload_runner's main loop", exc_info=e)
        finally:
            # Uninitialize COM for this thread before it exits.
            logging.info("AudioController: reload_runner thread exiting, uninitializing COM.")
            CoUninitialize()
    
    def _register_mute_callback(self):
        if self.mic is None:
            return
        logging.debug('AudioController: Registering volume change listener')
        self._mute_callback = _MuteCallback(self._update_state)
        self.volume = self.get_volume()
        self.volume.RegisterControlChangeNotify(self._mute_callback)
        self._update_state()

    def _register_device_callback(self):
        if self.mic is None:
            return
        logging.debug('AudioController: Registering device change listener')
        self._device_callback = _DeviceCallback(self._update_device)
        AudioUtilities.GetDeviceEnumerator().RegisterEndpointNotificationCallback(self._device_callback)


    def get_volume(self):
        if not self.mic:
            return None
        if self.volume:
            return self.volume
        
        self.volume = self.mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)
        return self.volume

    def add_listener(self, listener):
        try:
            self._listeners.add(listener)
            listener(self.status())
            logging.info('AudioController: Registered status change callback')
        except Exception as e:
            logging.warning('AudioController: Failed to register status change callback', exc_info=e)

    def remove_listener(self, listener):
        self._listeners.remove(listener)
        logging.info('AudioController: UnRegistered status change callback')

    def mute(self):
        logging.info('AudioController: mute() called')
        volume = self.get_volume()
        if volume:
            volume.SetMute(1, None)
            logging.debug('AudioController: Microphone muted')
        else:
            logging.warning('AudioController: No microphone to mute')

    def unmute(self):
        logging.info('AudioController: unmute() called')
        volume = self.get_volume()
        if volume:
            volume.SetMute(0, None)
            logging.debug('AudioController: Microphone unmuted')
        else:
            logging.warning('AudioController: No microphone to unmute')

    def toggle(self):
        logging.info('AudioController: toggle() called')
        volume = self.get_volume()
        if volume:
            current = volume.GetMute()
            volume.SetMute(0 if current else 1, None)
            logging.debug('AudioController: Microphone toggled to %s', 'unmuted' if current else 'muted')
        else:
            logging.warning('AudioController: No microphone to toggle')

    def is_muted(self):
        volume = self.get_volume()
        if volume:
            muted = bool(volume.GetMute())
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
        # elif self.is_in_use():
        #     return MicStatus.INUSE
        else:
            return MicStatus.UNMUTED
    
AudioController = _AudioController()