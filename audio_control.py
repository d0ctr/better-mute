import logging
import threading
from time import time
from typing import Callable, Dict, List, Tuple, Type
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioEndpointVolumeCallback, IMMNotificationClient, EDataFlow, ERole, IMMDevice, AUDIO_VOLUME_NOTIFICATION_DATA, IAudioMeterInformation
from comtypes import COMObject, CLSCTX_ALL, CoInitializeEx, CoUninitialize, COINIT_MULTITHREADED, GUID

from commons import MicStatus


AUDIO_CONTROLLER_EVENT_GUID = GUID("{E005B3BF-A746-4300-9939-E1BBCC94C6C1}")
EMPTY_DEVICE_ID = '{0.0.0.00000000}.{c424cab4-9985-4b21-b259-ffffffffffff}'

def strip_guid(input: str) -> str:
    # Split by the last dot and take the second part
    guid = str(input).strip('{}').split('.')[-1].split('-')[-1]
    # Remove any curly braces if present
    guid = guid.strip('{}')
    guid = guid.split('-')[-1]
    return guid

class _VolumeCallback(COMObject):
    _com_interfaces_ = [IAudioEndpointVolumeCallback]

    def __init__(self, callback: Callable[[bool], None], dev_id: str):
        super().__init__()
        self.callback = callback
        self.dev_id = dev_id
        self.logger = logging.getLogger(str(self))

    def OnNotify(self, pNotify):
        notification_data: Type[AUDIO_VOLUME_NOTIFICATION_DATA] = pNotify.contents
        
        bMuted           = notification_data.bMuted
        guidEventContext = notification_data.guidEventContext
        
        if guidEventContext != AUDIO_CONTROLLER_EVENT_GUID:
            return
        
        self.logger.debug('OnNotify (pNotify.bMuted=%s)', bMuted)

        try:
            self.callback()
        except Exception as e:
            self.logger.error('OnNotify:', exc_info=e)
    
    def destroy(self):
        self.callback = None
    
    def update(self, callback: Callable[[bool], None]):
        self.callback = callback
    
    def __repr__(self) -> str:
        return '<VolumeCallback dev_id=%s>' % (strip_guid(self.dev_id),)

class _DeviceCallback(COMObject):
    _com_interfaces_ = [IMMNotificationClient]

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.logger = logging.getLogger('DeviceCallback')
    
    def OnDefaultDeviceChanged(self, flow, role, pwstrDefaultDeviceId):
        if flow != EDataFlow.eCapture.value:
            return
        
        self.logger.debug('OnDefaultDeviceChanged (flow=%s, role=%s, id=%s)', EDataFlow(flow), ERole(role), pwstrDefaultDeviceId)

        try:
            self.callback(ERole(role), pwstrDefaultDeviceId)
        except Exception as e:
            self.logger.error('OnDefaultDeviceChanged', exc_info=e)

    def OnDeviceAdded(self, pwstrDeviceId):
        # self.logger.debug('OnDeviceAdded: %s', pwstrDeviceId)
        pass
        
    def OnDeviceRemoved(self, pwstrDeviceId):
        # self.logger.debug('OnDeviceRemoved: %s', pwstrDeviceId)
        pass

    def OnDeviceStateChanged(self, pwstrDeviceId, dwNewState):
        # self.logger.debug('OnDeviceStateChanged: %s, state -> %s', pwstrDeviceId, dwNewState)
        pass        

    def OnPropertyValueChanged(self, pwstrDeviceId, key):
        # self.logger.debug('OnPropertyValueChanged: %s, key=%s', pwstrDeviceId, key)
        pass
    
    def update(self, callback: Callable[[bool], None]):
        self.callback = callback

    def destroy(self):
        self.callback = None

DEVICE_CALLBACK = _DeviceCallback(None)

class Device:
    def __init__(self, dev: IMMDevice | None):
        self._id = EMPTY_DEVICE_ID
        self._destroyed = True
        self._volume_callback: Type[_VolumeCallback] = None

        if dev is not None:
            self._dev: Type[IMMDevice] = dev
            self._id = dev.GetId()
            self._control: Type[IAudioEndpointVolume] = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)
            self._meter: Type[IAudioMeterInformation] = dev.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None).QueryInterface(IAudioMeterInformation)
            self._destroyed = False
        
        self.logger = logging.getLogger(str(self))
    
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, _):
        pass
    
    def mute(self):
        self.logger.debug('mute()')
        self._control.SetMute(1, AUDIO_CONTROLLER_EVENT_GUID)

    def unmute(self):
        self.logger.debug('unmute()')
        self._control.SetMute(0, AUDIO_CONTROLLER_EVENT_GUID)
    
    def toggle(self):
        self.logger.debug('toggle()')
        if self._dev.GetMute():
            self.unmute()
        else:
            self.mute()
    
    def is_muted(self) -> bool:
        return self._control.GetMute()
    
    def set_volume_callback(self, callback: Callable[[bool], None]):
        self.logger.debug('Register volume callback')
        if self._volume_callback is not None:
            self._volume_callback.update(callback)
            self.logger.info('Updated volume callback')
        else:
            self._volume_callback = _VolumeCallback(callback, self._id)
            self._control.RegisterControlChangeNotify(self._volume_callback)
            self.logger.info('Registered volume callback')
    
    def has_volume_callback(self):
        return False if self._volume_callback is None else True

    def get_level(self) -> float:
        return 0.0 if self.is_muted() else self._meter.GetPeakValue()

    def destroy(self):
        self.logger.debug('Destroying device')
        if self._volume_callback is not None:
            try:
                self._control.UnregisterControlChangeNotify(self._volume_callback)
            except Exception as e:
                self.logger.error('Error unregistering callback', exc_info=e)
            
            self._volume_callback = None
        
        self._control = None
        self._dev = None
        self._meter = None
        self._destroyed = True
        self.logger.info('Destroyed device')

    def destroyed(self):
        return self._destroyed
    
    def __repr__(self) -> str:
        return '<Device id=%s%s>' % (strip_guid(self._id), ' destroyed' if self._destroyed else '')

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Device) and value.id == self.id
    
    @classmethod
    def from_default(cls, role=ERole.eMultimedia, flow=EDataFlow.eCapture) -> Type['Device']:
        try:
            dev = AudioUtilities.GetDeviceEnumerator().GetDefaultAudioEndpoint(flow.value, role.value)
            return cls(dev) if dev is not None else EMPTY_DEVICE
        except Exception as e:
            logging.warning('Device.from_default(role=%s,flow=%s) failed', role, flow, exc_info=e)
        return EMPTY_DEVICE

    @staticmethod
    def get_default_id(role=ERole.eMultimedia, flow=EDataFlow.eCapture) -> str:
        try:
            dev = AudioUtilities.GetDeviceEnumerator().GetDefaultAudioEndpoint(flow.value, role.value)
            return dev.GetId() if dev else None
        except Exception as e:
            logging.warning('Device.get_default_id(role=%s,flow=%s) failed', role, flow, exc_info=e)
        return None

EMPTY_DEVICE = Device(None)
    
class _AudioController:
    def __init__(self):
        self.logger = logging.getLogger('AudioController')
        self._started = False
        self.devs: Dict[ERole, Device]  = {
            ERole.eCommunications: EMPTY_DEVICE,
            ERole.eMultimedia    : EMPTY_DEVICE,
            ERole.eConsole       : EMPTY_DEVICE
        }
        self._devs_lock = threading.Lock()
        # self._threads = []
        self._level_listeners = set()
        self._status_listeners = set()

        self.reload(ERole.eCommunications)
        self.reload(ERole.eMultimedia)
        self.reload(ERole.eConsole)

        self._level_start = False
        self._level_notifier_thread = threading.Thread(target=self.level_notifier, daemon=True)
    
    def start(self):
        if self._started:
            return
        
        self._started = True
        
        self.logger.debug('Registering device change listener')
        DEVICE_CALLBACK.update(self._update_device)
        AudioUtilities.GetDeviceEnumerator().RegisterEndpointNotificationCallback(DEVICE_CALLBACK)

        self.logger.debug('Registering volume change listeners')
        for role, dev in self.devs.items():
            callback = self._update_status(role)
            dev.set_volume_callback(callback)
            callback()

    
    def _update_status(self, role: ERole) -> Callable[[bool], None]:
        def update(*_: bool):
            status = self.status(role=role)
            for listener in self._status_listeners:
                try:
                    listener(status)
                except Exception as e:
                    self.logger.error('Error calling status listener for %s update', role, exc_info=e)
        
        return update
    
    def _update_device(self, role: Type[ERole], id: str):
        dev = self.devs.get(role)
        if not dev.destroyed() and dev.id == id:
            self.logger.debug('Default %s device did not change, skipping', role)
            return
        
        self.logger.info('Updating active %s microphone -> (%s)', role, id)

        reload_thread = threading.Thread(target=self.reload_runner, args=(role,), daemon=True)
        reload_thread.start()

    def reload(self, role: ERole):
        old_status = self.status(role=role)
        if self.devs.get(role) is not None:
            old_dev = self.devs.get(role)
            if not old_dev.destroyed():
                try:
                    old_dev.unmute()
                except Exception as e:
                    self.logger.warning('Error unmuting old %s device (%s)', role, old_dev.id, exc_info=e)

                try:
                    old_dev.destroy()
                except Exception as e:
                    self.logger.error('Error releasing old %s device (%s)', role, old_dev.id, exc_info=e)

                self.logger.info('Released old %s device', role)

        try:
            # Get new default id before creating device
            new_dev_id = Device.get_default_id(role=role)
            for d in self.devs.values():
                if d.id == new_dev_id:
                    self.logger.info('Reusing device (%s) as %s', new_dev_id, role)
                    dev = d
                    break
            else:
                dev = Device.from_default(role=role)
                self.logger.info('Initialized %s device (mic found: %s)', role, dev.id if bool(dev) else False)

            self.devs[role] = dev

            match old_status:
                case MicStatus.MUTED:
                    dev.mute()
                case MicStatus.UNMUTED:
                    dev.unmute()
                case _:
                    pass
            
            if self._started:
                self.logger.debug('Registering volume change listener')
                callback = self._update_status(role)
                dev.set_volume_callback(callback)
                callback()

        except Exception as e:
            self.logger.error('Failed to initialize %s device', role, exc_info=e)
    
    def reload_runner(self, role: ERole):
        self._devs_lock.acquire()
        CoInitializeEx(COINIT_MULTITHREADED)
        
        self.logger.debug('reload_runner received notification, proceeding to reload.')
        try:
            self.reload(role)
        except Exception as e:
            self.logger.error('Exception during self.reload() in reload_runner for %s', role, exc_info=e)

        self.logger.info("reload_runner thread exiting, uninitializing COM.")
        CoUninitialize()
        self._devs_lock.release()

    def level_notifier(self):
        CoInitializeEx(COINIT_MULTITHREADED)
        last_log = 0
        while self._level_start:
            try:
                if time() - last_log > 5:
                    # log once in 5secs
                    self.logger.debug('level_notifier getting new level value (this is logged once every 5s instead of every time)')
                    last_log = time()

                level = self.level()
                for listener in self._level_listeners:
                    try:
                        listener(level)
                        pass
                    except Exception as e:
                        self.logger.error('Error calling level listener', exc_info=e)
            except Exception as e:
                self.logger.error('Error getting level', exc_info=e)
            threading.Event().wait(0.1)  # Poll every 100ms
        self.logger.debug('level_notifier is stopped')
        CoUninitialize()

    def add_status_listener(self, listener: Callable[[MicStatus], None]):
        try:
            self._status_listeners.add(listener)
            listener(self.status())
            self.logger.info('Registered status change callback')
        except Exception as e:
            self.logger.warning('Failed to register status change callback', exc_info=e)

    def remove_status_listener(self, listener: Callable[[MicStatus], None]):
        self._status_listeners.remove(listener)
        self.logger.info('Unregistered status change callback')

    def add_level_listener(self, listener: Callable[[float], None]):
        try:
            self._level_listeners.add(listener)
            if not self._level_start:
                self._level_start = True
                self._level_notifier_thread.start()

            listener(self.level())
            self.logger.info('Registered level change callback')
        except Exception as e:
            self.logger.warning('Failed to register level change callback', exc_info=e)

    def remove_level_listener(self, listener: Callable[[float], None]):
        self._level_listeners.remove(listener)
        if not len(self._level_listeners):
            self._level_stop = True
            self._level_notifier_thread.join()

        self.logger.info('Unregistered level change callback')

    def mute(self, role: ERole | None=None):
        self.logger.info('mute() called')
        muted_devs = set()
        for role, dev in self.get_devs(role):
            if dev.destroyed():
                self.logger.warning('No %s device to mute', role)
            elif dev.id in muted_devs:
                pass
            else:
                dev.mute()
                muted_devs.add(dev.id)
                self.logger.debug('%s microphone muted', role)

    def unmute(self, role: ERole | None=None):
        self.logger.info('unmute() called')
        unmuted_devs = set()

        for role, dev in self.get_devs(role):
            if dev.destroyed():
                self.logger.warning('No %s device to unmute', role)
            elif dev.id in unmuted_devs:
                pass
            else:
                dev.unmute()
                unmuted_devs.add(dev.id)
                self.logger.debug('%s microphone unmuted', role)

    def toggle(self, role: ERole | None=None):
        self.logger.info('toggle() called')

        main_dev = self.find_main_dev()
        if main_dev.destroyed():
            self.logger.debug('No main device found, skipping toggle')
            return

        muted = main_dev.is_muted()
        toggled_devs = set()
        for role, dev in self.devs.items():
            if dev.destroyed():
                self.logger.warning('No %s device to toggle', role)
            elif dev.id in toggled_devs:
                pass
            else:
                if muted:
                    dev.unmute()
                else:
                    dev.mute()
                toggled_devs.add(dev.id)
                self.logger.debug('%s microphone %s', role, 'unmuted' if muted else 'muted')

    def is_muted(self, role: ERole | None=None):
        dev = self.get_dev(role=role)
        if not dev.destroyed():
            return dev.is_muted()
        self.logger.warning('is_muted(%s) -> No microphone', 'main' if role is None else role)
        return False

    def is_in_use(self, role: ERole | None=None):
        # TODO: Implement actual detection of microphone usage
        self.logger.info('is_in_use() called (stub)')
        return False

    def status(self, role: ERole | None=None) -> MicStatus:
        dev = self.get_dev(role=role)
        if dev.destroyed():
            return MicStatus.DISABLED
        if dev.is_muted():
            return MicStatus.MUTED
        # if self.is_in_use():
        #     return MicStatus.INUSE
        return MicStatus.UNMUTED
    
    def level(self, role: ERole | None=None) -> float:
        dev = self.get_dev(role=role)
        if not dev.destroyed():
            return dev.get_level()
        self.logger.warning('get_level(%s) -> No microphone', 'main' if role is None else role)
        return 0.0
    
    def find_main_dev(self) -> Type[Device]:
        # The list is ordered based on priority, first one that exists is the "main" device
        for role in [ERole.eCommunications, ERole.eMultimedia, ERole.eConsole]:
            dev = self.devs.get(role)
            if not dev.destroyed():
                return dev
        
        return EMPTY_DEVICE
    
    def get_dev(self, role: ERole | None=None) -> Type[Device]:
        return self.find_main_dev() if role is None else self.devs.get(role)

    def get_devs(self, role: ERole | None=None) -> List[Tuple[ERole, Device]]:
        return self.devs.items() if role is None else [(role, self.devs.get(role))]

    
AudioController = _AudioController()