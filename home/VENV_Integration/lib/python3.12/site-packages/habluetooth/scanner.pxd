import cython


from .base_scanner cimport BaseHaScanner
from .models cimport BluetoothServiceInfoBleak

cdef object NO_RSSI_VALUE
cdef object AdvertisementData
cdef object BLEDevice

cdef bint TYPE_CHECKING

cdef object _NEW_SERVICE_INFO

cdef class HaScanner(BaseHaScanner):

    cdef public object mac_address
    cdef public object requested_mode
    cdef public object _start_stop_lock
    cdef public object _background_tasks
    cdef public object scanner
    cdef public object _start_future
    cdef public object current_mode

    @cython.locals(service_info=BluetoothServiceInfoBleak)
    cpdef void _async_detection_callback(
        self,
        object device,
        object advertisement_data
    )
