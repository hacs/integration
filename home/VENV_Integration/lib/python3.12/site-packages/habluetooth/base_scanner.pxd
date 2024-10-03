
import cython

from .models cimport BluetoothServiceInfoBleak
from .manager cimport BluetoothManager

cdef object NO_RSSI_VALUE
cdef object BluetoothServiceInfoBleak
cdef object AdvertisementData
cdef object BLEDevice
cdef bint TYPE_CHECKING

cdef class BaseHaScanner:

    cdef public str adapter
    cdef public bint connectable
    cdef public str source
    cdef public object connector
    cdef public unsigned int _connecting
    cdef public str name
    cdef public bint scanning
    cdef public double _last_detection
    cdef public object _start_time
    cdef public object _cancel_watchdog
    cdef public object _loop
    cdef BluetoothManager _manager

    cpdef tuple get_discovered_device_advertisement_data(self, str address)


cdef class BaseHaRemoteScanner(BaseHaScanner):

    cdef public dict _details
    cdef public float _expire_seconds
    cdef public object _cancel_track
    cdef public dict _previous_service_info

    @cython.locals(
        prev_service_uuids=list,
        prev_service_data=dict,
        prev_manufacturer_data=dict,
        prev_name=str,
        prev_discovery=tuple,
        has_manufacturer_data=bint,
        has_service_data=bint,
        has_service_uuids=bint,
        prev_details=dict,
        service_info=BluetoothServiceInfoBleak,
        prev_service_info=BluetoothServiceInfoBleak
    )
    cpdef void _async_on_advertisement(
        self,
        str address,
        int rssi,
        str local_name,
        list service_uuids,
        dict service_data,
        dict manufacturer_data,
        object tx_power,
        dict details,
        double advertisement_monotonic_time
    )

    @cython.locals(now=float, timestamp=float, service_info=BluetoothServiceInfoBleak)
    cpdef void _async_expire_devices(self)

    cpdef void _schedule_expire_devices(self)

    @cython.locals(info=BluetoothServiceInfoBleak)
    cpdef tuple get_discovered_device_advertisement_data(self, str address)
