# -*- coding: utf-8 -*-
# Copyright (C) 2010, 2011, 2012, 2013 Sebastian Wiesner <lunaryorn@gmail.com>

# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.

# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
"""
    pyudev._ctypeslib.libudev
    =========================

    Wrapper types for libudev.  Use ``libudev`` attribute to access libudev
    functions.

    .. moduleauthor::  Sebastian Wiesner  <lunaryorn@gmail.com>
"""

# isort: STDLIB
from ctypes import POINTER, Structure, c_char, c_char_p, c_int, c_uint, c_ulonglong

from ._errorcheckers import (
    check_errno_on_nonzero_return,
    check_errno_on_null_pointer_return,
    check_negative_errorcode,
)


class udev(Structure):  # pylint: disable=invalid-name
    """
    Dummy for ``udev`` structure.
    """

    # pylint: disable=too-few-public-methods
    pass


udev_p = POINTER(udev)  # pylint: disable=invalid-name


class udev_enumerate(Structure):  # pylint: disable=invalid-name
    """
    Dummy for ``udev_enumerate`` structure.
    """

    # pylint: disable=too-few-public-methods
    pass


udev_enumerate_p = POINTER(udev_enumerate)  # pylint: disable=invalid-name


class udev_list_entry(Structure):  # pylint: disable=invalid-name
    """
    Dummy for ``udev_list_entry`` structure.
    """

    # pylint: disable=too-few-public-methods
    pass


udev_list_entry_p = POINTER(udev_list_entry)  # pylint: disable=invalid-name


class udev_device(Structure):  # pylint: disable=invalid-name
    """
    Dummy for ``udev_device`` structure.
    """

    # pylint: disable=too-few-public-methods
    pass


udev_device_p = POINTER(udev_device)  # pylint: disable=invalid-name


class udev_monitor(Structure):  # pylint: disable=invalid-name
    """
    Dummy for ``udev_device`` structure.
    """

    # pylint: disable=too-few-public-methods
    pass


udev_monitor_p = POINTER(udev_monitor)  # pylint: disable=invalid-name


class udev_hwdb(Structure):  # pylint: disable=invalid-name
    """
    Dummy for ``udev_hwdb`` structure.
    """

    # pylint: disable=too-few-public-methods
    pass


udev_hwdb_p = POINTER(udev_hwdb)  # pylint: disable=invalid-name

dev_t = c_ulonglong  # pylint: disable=invalid-name

SIGNATURES = dict(
    # context
    udev_new=([], udev_p),
    udev_unref=([udev_p], None),
    udev_ref=([udev_p], udev_p),
    udev_get_sys_path=([udev_p], c_char_p),
    udev_get_dev_path=([udev_p], c_char_p),
    udev_get_run_path=([udev_p], c_char_p),
    udev_get_log_priority=([udev_p], c_int),
    udev_set_log_priority=([udev_p, c_int], None),
    udev_enumerate_new=([udev_p], udev_enumerate_p),
    udev_enumerate_ref=([udev_enumerate_p], udev_enumerate_p),
    udev_enumerate_unref=([udev_enumerate_p], None),
    udev_enumerate_add_match_subsystem=([udev_enumerate_p, c_char_p], c_int),
    udev_enumerate_add_nomatch_subsystem=([udev_enumerate_p, c_char_p], c_int),
    udev_enumerate_add_match_property=([udev_enumerate_p, c_char_p, c_char_p], c_int),
    udev_enumerate_add_match_sysattr=([udev_enumerate_p, c_char_p, c_char_p], c_int),
    udev_enumerate_add_nomatch_sysattr=([udev_enumerate_p, c_char_p, c_char_p], c_int),
    udev_enumerate_add_match_tag=([udev_enumerate_p, c_char_p], c_int),
    udev_enumerate_add_match_sysname=([udev_enumerate_p, c_char_p], c_int),
    udev_enumerate_add_match_parent=([udev_enumerate_p, udev_device_p], c_int),
    udev_enumerate_add_match_is_initialized=([udev_enumerate_p], c_int),
    udev_enumerate_scan_devices=([udev_enumerate_p], c_int),
    udev_enumerate_get_list_entry=([udev_enumerate_p], udev_list_entry_p),
    # list entries
    udev_list_entry_get_next=([udev_list_entry_p], udev_list_entry_p),
    udev_list_entry_get_name=([udev_list_entry_p], c_char_p),
    udev_list_entry_get_value=([udev_list_entry_p], c_char_p),
    # devices
    udev_device_ref=([udev_device_p], udev_device_p),
    udev_device_unref=([udev_device_p], None),
    udev_device_new_from_syspath=([udev_p, c_char_p], udev_device_p),
    udev_device_new_from_subsystem_sysname=(
        [udev_p, c_char_p, c_char_p],
        udev_device_p,
    ),
    udev_device_new_from_devnum=([udev_p, c_char, dev_t], udev_device_p),
    udev_device_new_from_device_id=([udev_p, c_char_p], udev_device_p),
    udev_device_new_from_environment=([udev_p], udev_device_p),
    udev_device_get_parent=([udev_device_p], udev_device_p),
    udev_device_get_parent_with_subsystem_devtype=(
        [udev_device_p, c_char_p, c_char_p],
        udev_device_p,
    ),
    udev_device_get_devpath=([udev_device_p], c_char_p),
    udev_device_get_subsystem=([udev_device_p], c_char_p),
    udev_device_get_syspath=([udev_device_p], c_char_p),
    udev_device_get_sysnum=([udev_device_p], c_char_p),
    udev_device_get_sysname=([udev_device_p], c_char_p),
    udev_device_get_driver=([udev_device_p], c_char_p),
    udev_device_get_devtype=([udev_device_p], c_char_p),
    udev_device_get_devnode=([udev_device_p], c_char_p),
    udev_device_get_property_value=([udev_device_p, c_char_p], c_char_p),
    udev_device_get_sysattr_value=([udev_device_p, c_char_p], c_char_p),
    udev_device_get_devnum=([udev_device_p], dev_t),
    udev_device_get_action=([udev_device_p], c_char_p),
    udev_device_get_seqnum=([udev_device_p], c_ulonglong),
    udev_device_get_is_initialized=([udev_device_p], c_int),
    udev_device_get_usec_since_initialized=([udev_device_p], c_ulonglong),
    udev_device_get_devlinks_list_entry=([udev_device_p], udev_list_entry_p),
    udev_device_get_tags_list_entry=([udev_device_p], udev_list_entry_p),
    udev_device_get_properties_list_entry=([udev_device_p], udev_list_entry_p),
    udev_device_get_sysattr_list_entry=([udev_device_p], udev_list_entry_p),
    udev_device_set_sysattr_value=([udev_device_p, c_char_p, c_char_p], c_int),
    udev_device_has_tag=([udev_device_p, c_char_p], c_int),
    # monitoring
    udev_monitor_ref=([udev_monitor_p], udev_monitor_p),
    udev_monitor_unref=([udev_monitor_p], None),
    udev_monitor_new_from_netlink=([udev_p, c_char_p], udev_monitor_p),
    udev_monitor_enable_receiving=([udev_monitor_p], c_int),
    udev_monitor_set_receive_buffer_size=([udev_monitor_p, c_int], c_int),
    udev_monitor_get_fd=([udev_monitor_p], c_int),
    udev_monitor_receive_device=([udev_monitor_p], udev_device_p),
    udev_monitor_filter_add_match_subsystem_devtype=(
        [udev_monitor_p, c_char_p, c_char_p],
        c_int,
    ),
    udev_monitor_filter_add_match_tag=([udev_monitor_p, c_char_p], c_int),
    udev_monitor_filter_update=([udev_monitor_p], c_int),
    udev_monitor_filter_remove=([udev_monitor_p], c_int),
    # hwdb
    udev_hwdb_ref=([udev_hwdb_p], udev_hwdb_p),
    udev_hwdb_unref=([udev_hwdb_p], None),
    udev_hwdb_new=([udev_p], udev_hwdb_p),
    udev_hwdb_get_properties_list_entry=(
        [udev_hwdb_p, c_char_p, c_uint],
        udev_list_entry_p,
    ),
)

ERROR_CHECKERS = dict(
    udev_device_get_action=None,
    udev_device_get_devlinks_list_entry=None,
    udev_device_get_devnode=None,
    udev_device_get_devnum=None,
    udev_device_get_devpath=None,
    udev_device_get_devtype=None,
    udev_device_get_driver=None,
    udev_device_get_is_initialized=None,
    udev_device_get_parent=None,
    udev_device_get_parent_with_subsystem_devtype=None,
    udev_device_get_properties_list_entry=None,
    udev_device_get_property_value=None,
    udev_device_get_seqnum=None,
    udev_device_get_subsystem=None,
    udev_device_get_sysattr_list_entry=None,
    udev_device_get_sysattr_value=None,
    udev_device_get_sysname=None,
    udev_device_get_sysnum=None,
    udev_device_get_syspath=None,
    udev_device_get_tags_list_entry=None,
    udev_device_get_usec_since_initialized=None,
    udev_device_has_tag=None,
    udev_device_new_from_device_id=None,
    udev_device_new_from_devnum=None,
    udev_device_new_from_environment=None,
    udev_device_new_from_subsystem_sysname=None,
    udev_device_new_from_syspath=None,
    udev_device_ref=None,
    udev_device_unref=None,
    udev_device_set_sysattr_value=check_negative_errorcode,
    udev_enumerate_add_match_parent=check_negative_errorcode,
    udev_enumerate_add_match_subsystem=check_negative_errorcode,
    udev_enumerate_add_nomatch_subsystem=check_negative_errorcode,
    udev_enumerate_add_match_property=check_negative_errorcode,
    udev_enumerate_add_match_sysattr=check_negative_errorcode,
    udev_enumerate_add_nomatch_sysattr=check_negative_errorcode,
    udev_enumerate_add_match_tag=check_negative_errorcode,
    udev_enumerate_add_match_sysname=check_negative_errorcode,
    udev_enumerate_add_match_is_initialized=check_negative_errorcode,
    udev_enumerate_get_list_entry=None,
    udev_enumerate_new=None,
    udev_enumerate_ref=None,
    udev_enumerate_scan_devices=None,
    udev_enumerate_unref=None,
    udev_get_dev_path=None,
    udev_get_log_priority=None,
    udev_get_run_path=None,
    udev_get_sys_path=None,
    udev_hwdb_get_properties_list_entry=None,
    udev_hwdb_new=None,
    udev_hwdb_ref=None,
    udev_hwdb_unref=None,
    udev_list_entry_get_name=None,
    udev_list_entry_get_next=None,
    udev_list_entry_get_value=None,
    udev_monitor_set_receive_buffer_size=check_errno_on_nonzero_return,
    # libudev doc says, enable_receiving returns a negative errno, but tests
    # show that this is not reliable, so query the real error code
    udev_monitor_enable_receiving=check_errno_on_nonzero_return,
    udev_monitor_receive_device=check_errno_on_null_pointer_return,
    udev_monitor_ref=None,
    udev_monitor_filter_add_match_subsystem_devtype=check_negative_errorcode,
    udev_monitor_filter_add_match_tag=check_negative_errorcode,
    udev_monitor_filter_update=check_errno_on_nonzero_return,
    udev_monitor_filter_remove=check_errno_on_nonzero_return,
    udev_monitor_get_fd=None,
    udev_monitor_new_from_netlink=None,
    udev_monitor_unref=None,
    udev_new=None,
    udev_ref=None,
    udev_set_log_priority=None,
    udev_unref=None,
)
