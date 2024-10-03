import cython

from .advertisement_tracker cimport AdvertisementTracker
from .base_scanner cimport BaseHaScanner
from .models cimport BluetoothServiceInfoBleak

cdef int NO_RSSI_VALUE
cdef int RSSI_SWITCH_THRESHOLD
cdef double TRACKER_BUFFERING_WOBBLE_SECONDS
cdef double FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS
cdef object FILTER_UUIDS
cdef object AdvertisementData
cdef object BLEDevice
cdef bint TYPE_CHECKING
cdef set APPLE_START_BYTES_WANTED

cdef object APPLE_MFR_ID

@cython.locals(uuids=set)
cdef _dispatch_bleak_callback(
    BleakCallback bleak_callback,
    object device,
    object advertisement_data
)

cdef class BleakCallback:

    cdef public object callback
    cdef public dict filters

cdef class BluetoothManager:

    cdef public object _cancel_unavailable_tracking
    cdef public AdvertisementTracker _advertisement_tracker
    cdef public dict _fallback_intervals
    cdef public dict _intervals
    cdef public dict _unavailable_callbacks
    cdef public dict _connectable_unavailable_callbacks
    cdef public set _bleak_callbacks
    cdef public dict _all_history
    cdef public dict _connectable_history
    cdef public set _non_connectable_scanners
    cdef public set _connectable_scanners
    cdef public dict _adapters
    cdef public dict _sources
    cdef public object _bluetooth_adapters
    cdef public object slot_manager
    cdef public bint _debug
    cdef public bint shutdown
    cdef public object _loop
    cdef public object _adapter_refresh_future
    cdef public object _recovery_lock

    @cython.locals(stale_seconds=float)
    cdef bint _prefer_previous_adv_from_different_source(
        self,
        object address,
        BluetoothServiceInfoBleak old,
        BluetoothServiceInfoBleak new
    )

    @cython.locals(
        old_service_info=BluetoothServiceInfoBleak,
        old_connectable_service_info=BluetoothServiceInfoBleak,
        source=str,
        connectable=bint,
        scanner=BaseHaScanner,
        connectable_scanner=BaseHaScanner,
        apple_data=bytes,
        bleak_callback=BleakCallback
    )
    cpdef void scanner_adv_received(self, BluetoothServiceInfoBleak service_info)

    cpdef _async_describe_source(self, BluetoothServiceInfoBleak service_info)
