import logging
import threading
from typing import Callable, Dict, List, Tuple, Type
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioEndpointVolumeCallback, IMMNotificationClient, EDataFlow, ERole, IMMDevice, AUDIO_VOLUME_NOTIFICATION_DATA
from comtypes import COMObject, CLSCTX_ALL, CoInitializeEx, CoUninitialize, COINIT_MULTITHREADED, GUID

from commons import MicStatus


AUDIO_CONTROLLER_EVENT_GUID = GUID("{E005B3BF-A746-4300-9939-E1BBCC94C6C1}")

class _MuteCallback(COMObject):
    _com_interfaces_ = [IAudioEndpointVolumeCallback]

    def __init__(self, callback: Callable[[bool], None]):
        super().__init__()
        self.callback = callback

    def OnNotify(self, pNotify):
        notification_data: Type[AUDIO_VOLUME_NOTIFICATION_DATA] = pNotify.contents
        
        bMuted           = notification_data.bMuted
        guidEventContext = notification_data.guidEventContext
        
        if guidEventContext != AUDIO_CONTROLLER_EVENT_GUID:
            return
        
        logging.debug('MuteCallback: OnNotify (pNotify.bMuted=%s)', bMuted)

        try:
            self.callback()
        except Exception as e:
            logging.error('MuteCallback.OnNotify:', exc_info=e)
    
    def destroy(self):
        self.callback = None
    
    def update(self, callback: Callable[[bool], None]):
        self.callback = callback


class _DeviceCallback(COMObject):
    _com_interfaces_ = [IMMNotificationClient]

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def OnDefaultDeviceChanged(self, flow, role, pwstrDefaultDeviceId):
        if flow != EDataFlow.eCapture.value:
            return
        
        logging.debug('DeviceCallback: OnDefaultDeviceChanged (flow=%s, role=%s, id=%s)', EDataFlow(flow), ERole(role), pwstrDefaultDeviceId)

        try:
            self.callback(ERole(role), pwstrDefaultDeviceId)
        except Exception as e:
            logging.error('MuteCallback.OnDefaultDeviceChanged', exc_info=e)

    def OnDeviceAdded(self, pwstrDeviceId):
        # logging.debug('MuteCallback.OnDeviceAdded: %s', pwstrDeviceId)
        pass
        
    def OnDeviceRemoved(self, pwstrDeviceId):
        # logging.debug('MuteCallback.OnDeviceRemoved: %s', pwstrDeviceId)
        pass

    def OnDeviceStateChanged(self, pwstrDeviceId, dwNewState):
        # logging.debug('MuteCallback.OnDeviceStateChanged: %s, state -> %s', pwstrDeviceId, dwNewState)
        pass        

    def OnPropertyValueChanged(self, pwstrDeviceId, key):
        # logging.debug('MuteCallback.OnPropertyValueChanged: %s, key=%s', pwstrDeviceId, key)
        pass

    def destroy(self):
        self.callback = None

class Device:
    def __init__(self, dev: IMMDevice | None):
        if dev is not None:
            self._dev: Type[IMMDevice] = dev
            self._id: str = dev.GetId()
            self._control: Type[IAudioEndpointVolume] = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)
            self._callback: Type[IAudioEndpointVolumeCallback] = None
            self._destroyed = False
            self.logger = logging.getLogger(str(self))
        else:
            self._destroyed = True
    
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, _):
        pass
    
    def mute(self):
        self.logger.debug('Device mute()')
        self._control.SetMute(1, AUDIO_CONTROLLER_EVENT_GUID)

    def unmute(self):
        self.logger.debug('Device unmute()')
        self._control.SetMute(0, AUDIO_CONTROLLER_EVENT_GUID)
    
    def toggle(self):
        self.logger.debug('Device toggle()')
        if self._dev.GetMute():
            self.unmute()
        else:
            self.mute()
    
    def muted(self):
        return self._control.GetMute()
    
    def set_callback(self, callback: Callable[[bool], None]):
        self.logger.debug('Register volume callback')
        if self._callback is not None:
            self._callback.update(callback)
            self.logger.info('Updated volume callback')
        else:
            self._callback = _MuteCallback(callback)
            self._control.RegisterControlChangeNotify(self._callback)
            self.logger.info('Registered volume callback')

    def destroy(self):
        self.logger.debug('Destroying device')
        if self._callback is not None:
            try:
                self._control.UnregisterControlChangeNotify(self._callback)
            except Exception as e:
                self.logger.error('Error unregistering callback', exc_info=e)
            
            self._callback = None
        
        self._control = None
        self._dev = None
        self._destroyed = True
        self.logger.info('Destroyed device')

    def destroyed(self):
        return self._destroyed
    
    def __repr__(self) -> str:
        return '<Device id=%s destroyed=%s>' % (self._id, self._destroyed)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Device) and value.id == self.id
    
    @classmethod
    def from_default(cls, role=ERole.eMultimedia, flow=EDataFlow.eCapture) -> Type['Device']:
        dev = AudioUtilities.GetDeviceEnumerator().GetDefaultAudioEndpoint(flow.value, role.value)
        return cls(dev) if dev is not None else EMPTY_DEVICE

    @staticmethod
    def get_default_id(role=ERole.eMultimedia, flow=EDataFlow.eCapture) -> str:
        dev = AudioUtilities.GetDeviceEnumerator().GetDefaultAudioEndpoint(flow.value, role.value)
        return dev.GetId() if dev else None

EMPTY_DEVICE = Device(None)
    
class _AudioController:
    def __init__(self):
        self.devs: Dict[ERole, Device]  = {
            ERole.eCommunications: EMPTY_DEVICE,
            ERole.eMultimedia    : EMPTY_DEVICE,
            ERole.eConsole       : EMPTY_DEVICE
        }
        self._devs_lock = threading.Lock()
        self._threads = []

        self._listeners = set()

        self.reload(ERole.eCommunications)
        self.reload(ERole.eMultimedia)
        self.reload(ERole.eConsole)

        self._register_device_callback()
    
    def _update_state(self, role: ERole) -> Callable[[bool], None]:
        def update(*_: bool):
            status = self.status(role=role)
            for listener in self._listeners:
                try:
                    listener(status)
                except Exception as e:
                    logging.error('AudioController: Error calling audio controller listener for %s update', role, exc_info=e)
        
        return update
    
    def _update_device(self, role: Type[ERole], id: str):
        dev = self.devs.get(role)
        if not dev.destroyed() and dev.id == id:
            logging.debug('AudioController: Default %s device did not change, skipping', role)
            return
        
        logging.info('AudioController: Updating active %s microphone -> (%s)', role, id)

        reload_thread = threading.Thread(target=self.reload_runner, args=(role,), daemon=True)
        reload_thread.start()
        self._threads.append(reload_thread)

    def reload(self, role: ERole):
        old_state = self.status(role=role)
        if self.devs.get(role) is not None:
            old_dev = self.devs.get(role)
            if not old_dev.destroyed():
                try:
                    old_dev.unmute()
                except Exception as e:
                    logging.warning('Error unmuting old %s device (%s)', role, old_dev.id, exc_info=e)

                try:
                    old_dev.destroy()
                except Exception as e:
                    logging.error('Error releasing old %s device (%s)', role, old_dev.id, exc_info=e)

                logging.info('AudioController: Released old %s device', role)

        try:
            # Get new default id before creating device
            new_dev_id = Device.get_default_id(role=role)
            for d in self.devs.values():
                if not d.destroyed() and d.id == new_dev_id:
                    logging.info('AudioController: Reusing device (%s) as %s', new_dev_id, role)
                    dev = d
                    break
            else:
                dev = Device.from_default(role=role)
                logging.info('AudioController: Initialized %s device (mic found: %s)', role, dev.id if bool(dev) else False)

            self.devs[role] = dev

            logging.debug('AudioController: Registering volume change listener')
            callback = self._update_state(role)
            dev.set_callback(callback)
            match old_state:
                case MicStatus.MUTED:
                    dev.mute()
                case MicStatus.UNMUTED:
                    dev.unmute()
                case _:
                    callback()
                    pass

        except Exception as e:
            logging.error('AudioController: Failed to initialize %s device', role, exc_info=e)
    
    def reload_runner(self, role: ERole):
        self._devs_lock.acquire()
        CoInitializeEx(COINIT_MULTITHREADED)
        
        logging.debug('AudioController: reload_runner received notification, proceeding to reload.')
        try:
            self.reload(role)
        except Exception as e:
            logging.error('AudioController: Exception during self.reload() in reload_runner for %s', role, exc_info=e)
        finally:
            logging.info("AudioController: reload_runner thread exiting, uninitializing COM.")
            CoUninitialize()
            self._devs_lock.release()

    def _register_device_callback(self):
        logging.debug('AudioController: Registering device change listener')
        self._device_callback = _DeviceCallback(self._update_device)
        AudioUtilities.GetDeviceEnumerator().RegisterEndpointNotificationCallback(self._device_callback)

    def add_listener(self, listener):
        try:
            self._listeners.add(listener)
            listener(self.status())
            logging.info('AudioController: Registered status change callback')
        except Exception as e:
            logging.warning('AudioController: Failed to register status change callback', exc_info=e)

    def remove_listener(self, listener):
        self._listeners.remove(listener)
        logging.info('AudioController: Unregistered status change callback')

    def mute(self, role: ERole | None=None):
        logging.info('AudioController: mute() called')
        muted_devs = set()
        for role, dev in self.get_devs(role):
            if dev.destroyed():
                logging.warning('AudioController: No %s device to mute', role)
            elif dev.id in muted_devs:
                pass
            else:
                dev.mute()
                muted_devs.add(dev.id)
                logging.debug('AudioController: %s microphone muted', role)

    def unmute(self, role: ERole | None=None):
        logging.info('AudioController: unmute() called')
        unmuted_devs = set()

        for role, dev in self.get_devs(role):
            if dev.destroyed():
                logging.warning('AudioController: No %s device to unmute', role)
            elif dev.id in unmuted_devs:
                pass
            else:
                dev.mute()
                unmuted_devs.add(dev.id)
                logging.debug('AudioController: %s microphone unmuted', role)

    def toggle(self, role: ERole | None=None):
        logging.info('AudioController: toggle() called')

        main_dev = self.find_main_dev()
        if main_dev.destroyed():
            logging.debug('AudioController: No main device found, skipping toggle')
            return

        muted = main_dev.muted()
        toggled_devs = set()
        for role, dev in self.devs.items():
            if dev.destroyed():
                logging.warning('AudioController: No %s device to toggle', role)
            elif dev.id in toggled_devs:
                pass
            else:
                if muted:
                    dev.unmute()
                else:
                    dev.mute()
                toggled_devs.add(dev.id)
                logging.debug('AudioController: %s microphone %s', role, 'unmuted' if muted else 'muted')

    def is_muted(self, role: ERole | None=None):
        dev = self.get_dev(role=role)
        if dev:
            muted = dev.muted()
            return muted
        logging.warning('AudioController: is_muted() -> No microphone')
        return False

    def is_in_use(self, role: ERole | None=None):
        # TODO: Implement actual detection of microphone usage
        logging.info('AudioController: is_in_use() called (stub)')
        return False

    def status(self, role: ERole | None=None) -> MicStatus:
        dev = self.get_dev(role=role)
        if dev.destroyed():
            return MicStatus.DISABLED
        if dev.muted():
            return MicStatus.MUTED
        # elif self.is_in_use():
        #     return MicStatus.INUSE
        else:
            return MicStatus.UNMUTED
    
    def find_main_dev(self) -> Type[Device]:
        # The list is ordered based on priority, first one that exists is the "main" device
        for role in [ERole.eCommunications, ERole.eMultimedia, ERole.eMultimedia]:
            dev = self.devs.get(role)
            if not dev.destroyed():
                return dev
        
        return EMPTY_DEVICE
    
    def get_dev(self, role: ERole | None=None):
        return self.find_main_dev() if role is None else self.devs.get(role)

    def get_devs(self, role: ERole | None=None) -> List[Tuple[ERole, Device | None]]:
        return self.devs.items() if role is None else [(role, self.devs.get(role))]


    
AudioController = _AudioController()