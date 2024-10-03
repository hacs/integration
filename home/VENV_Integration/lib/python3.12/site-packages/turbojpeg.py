# -*- coding: UTF-8 -*-
#
# PyTurboJPEG - A Python wrapper of libjpeg-turbo for decoding and encoding JPEG image.
#
# Copyright (c) 2018-2024, Lilo Huang. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__author__ = 'Lilo Huang <kuso.cc@gmail.com>'
__version__ = '1.7.5'

from ctypes import *
from ctypes.util import find_library
import platform
import numpy as np
import math
import warnings
import os
from struct import unpack, calcsize

# default libTurboJPEG library path
DEFAULT_LIB_PATHS = {
    'Darwin': [
        '/usr/local/opt/jpeg-turbo/lib/libturbojpeg.dylib',
        '/opt/libjpeg-turbo/lib64/libturbojpeg.dylib',
        '/opt/homebrew/opt/jpeg-turbo/lib/libturbojpeg.dylib'
    ],
    'Linux': [
        '/usr/lib/x86_64-linux-gnu/libturbojpeg.so.0',
        '/usr/lib/libturbojpeg.so.0'
        '/usr/lib64/libturbojpeg.so.0',
        '/opt/libjpeg-turbo/lib64/libturbojpeg.so'
    ],
    'FreeBSD': [
        '/usr/local/lib/libturbojpeg.so.0',
        '/usr/local/lib/libturbojpeg.so'
    ],
    'NetBSD': [
        '/usr/pkg/lib/libturbojpeg.so.0',
        '/usr/pkg/lib/libturbojpeg.so'
    ],
    'Windows': ['C:/libjpeg-turbo64/bin/turbojpeg.dll']
}

# error codes
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJERR_WARNING = 0
TJERR_FATAL = 1

# color spaces
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJCS_RGB = 0
TJCS_YCbCr = 1
TJCS_GRAY = 2
TJCS_CMYK = 3
TJCS_YCCK = 4

# pixel formats
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJPF_RGB = 0
TJPF_BGR = 1
TJPF_RGBX = 2
TJPF_BGRX = 3
TJPF_XBGR = 4
TJPF_XRGB = 5
TJPF_GRAY = 6
TJPF_RGBA = 7
TJPF_BGRA = 8
TJPF_ABGR = 9
TJPF_ARGB = 10
TJPF_CMYK = 11

# chrominance subsampling options
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJSAMP_444 = 0
TJSAMP_422 = 1
TJSAMP_420 = 2
TJSAMP_GRAY = 3
TJSAMP_440 = 4
TJSAMP_411 = 5
TJSAMP_441 = 6

# transform operations
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJXOP_NONE = 0
TJXOP_HFLIP = 1
TJXOP_VFLIP = 2
TJXOP_TRANSPOSE = 3
TJXOP_TRANSVERSE = 4
TJXOP_ROT90 = 5
TJXOP_ROT180 = 6
TJXOP_ROT270 = 7

# transform options
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJXOPT_PERFECT = 1
TJXOPT_TRIM = 2
TJXOPT_CROP = 4
TJXOPT_GRAY = 8
TJXOPT_NOOUTPUT = 16
TJXOPT_PROGRESSIVE = 32
TJXOPT_COPYNONE = 64

# pixel size
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
tjPixelSize = [3, 3, 4, 4, 4, 4, 1, 4, 4, 4, 4, 4]

# MCU block width (in pixels) for a given level of chrominance subsampling.
# MCU block sizes:
#  - 8x8 for no subsampling or grayscale
#  - 16x8 for 4:2:2
#  - 8x16 for 4:4:0
#  - 16x16 for 4:2:0
#  - 32x8 for 4:1:1
tjMCUWidth = [8, 16, 16, 8, 8, 32]

# MCU block height (in pixels) for a given level of chrominance subsampling.
# MCU block sizes:
#  - 8x8 for no subsampling or grayscale
#  - 16x8 for 4:2:2
#  - 8x16 for 4:4:0
#  - 16x16 for 4:2:0
#  - 32x8 for 4:1:1
tjMCUHeight = [8, 8, 16, 8, 16, 8]

# miscellaneous flags
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
# note: TJFLAG_NOREALLOC cannot be supported due to reallocation is needed by PyTurboJPEG.
TJFLAG_BOTTOMUP = 2
TJFLAG_FASTUPSAMPLE = 256
TJFLAG_FASTDCT = 2048
TJFLAG_ACCURATEDCT = 4096
TJFLAG_STOPONWARNING = 8192
TJFLAG_PROGRESSIVE = 16384
TJFLAG_LIMITSCANS = 32768

class CroppingRegion(Structure):
    _fields_ = [("x", c_int), ("y", c_int), ("w", c_int), ("h", c_int)]

class ScalingFactor(Structure):
    _fields_ = ('num', c_int), ('denom', c_int)

CUSTOMFILTER = CFUNCTYPE(
    c_int,
    POINTER(c_short),
    CroppingRegion,
    CroppingRegion,
    c_int,
    c_int,
    c_void_p
)

class BackgroundStruct(Structure):
    """Struct to send data to fill_background callback function.

    Parameters
    ----------
    w: c_int
        Width of the input image.
    h: c_int
        Height of the input image.
    lum: c_int
        Luminance value to use as background when extending the image.
    """
    _fields_ = [
        ("w", c_int),
        ("h", c_int),
        ("lum", c_int)
    ]

class TransformStruct(Structure):
    _fields_ = [
        ("r", CroppingRegion),
        ("op", c_int),
        ("options", c_int),
        ("data", POINTER(BackgroundStruct)),
        ("customFilter", CUSTOMFILTER)
    ]

# MCU for luminance is always 8
MCU_WIDTH = 8
MCU_HEIGHT = 8
MCU_SIZE = 64

def fill_background(coeffs_ptr, arrayRegion, planeRegion, componentID, transformID, transform_ptr):
    """Callback function for filling extended crop images with background
    color. The callback can be called multiple times for each component, each
    call providing a region (defined by arrayRegion) of the image.

    Parameters
    ----------
    coeffs_ptr: POINTER(c_short)
        Pointer to the coefficient array for the callback.
    arrayRegion: CroppingRegion
        The width and height coefficient array and its offset relative to
        the component plane.
    planeRegion: CroppingRegion
        The width and height of the component plane of the coefficient array.
    componentID: c_int
        The component number (i.e. 0, 1, or 2)
    transformID: c_int
        The index of the transformation in the array of transformation given to
        the transform function.
    transform_ptr: c_voipd_p
        Pointer to the transform structure used for the transformation.

    Returns
    ----------
    c_int
        CFUNCTYPE function must return an int.
    """

    # Only modify luminance data, so we dont need to worry about subsampling
    if componentID == 0:
        coeff_array_size = arrayRegion.w * arrayRegion.h
        # Read the coefficients in the pointer as a np array (no copy)
        ArrayType = c_short*coeff_array_size
        array_pointer = cast(coeffs_ptr, POINTER(ArrayType))
        coeffs = np.frombuffer(array_pointer.contents, dtype=np.int16)
        coeffs.shape = (
            arrayRegion.h//MCU_WIDTH,
            arrayRegion.w//MCU_HEIGHT,
            MCU_SIZE
        )

        # Cast the content of the transform pointer into a transform structure
        transform = cast(transform_ptr, POINTER(TransformStruct)).contents
        # Cast the content of the callback data pointer in the transform
        # structure to a background structure
        background_data = cast(
            transform.data, POINTER(BackgroundStruct)
        ).contents

        # The coeff array is typically just one MCU heigh, but it is up to the
        # libjpeg implementation how to do it. The part of the coeff array that
        # is 'left' of 'non-background' data should thus be handled separately
        # from the part 'under'. (Most of the time, the coeff array will be
        # either 'left' or 'under', but both could happen). Note that start
        # and end rows defined below can be outside the arrayRegion, but that
        # the range they then define is of 0 length.

        # fill mcus left of image
        left_start_row = min(arrayRegion.y, background_data.h) - arrayRegion.y
        left_end_row = (
            min(arrayRegion.y+arrayRegion.h, background_data.h)
            - arrayRegion.y
        )
        for x in range(background_data.w//MCU_WIDTH, planeRegion.w//MCU_WIDTH):
            for y in range(
                left_start_row//MCU_HEIGHT,
                left_end_row//MCU_HEIGHT
            ):
                coeffs[y][x][0] = background_data.lum

        # fill mcus under image
        bottom_start_row = (
            max(arrayRegion.y, background_data.h) - arrayRegion.y
        )
        bottom_end_row = (
            max(arrayRegion.y+arrayRegion.h, background_data.h)
            - arrayRegion.y
        )
        for x in range(0, planeRegion.w//MCU_WIDTH):
            for y in range(
                bottom_start_row//MCU_HEIGHT,
                bottom_end_row//MCU_HEIGHT
            ):
                coeffs[y][x][0] = background_data.lum

    return 1


def split_byte_into_nibbles(value):
    """Split byte int into 2 nibbles (4 bits)."""
    first = value >> 4
    second = value & 0x0F
    return first, second


class TurboJPEG(object):
    """A Python wrapper of libjpeg-turbo for decoding and encoding JPEG image."""
    def __init__(self, lib_path=None):
        turbo_jpeg = cdll.LoadLibrary(
            self.__find_turbojpeg() if lib_path is None else lib_path)
        self.__init_decompress = turbo_jpeg.tjInitDecompress
        self.__init_decompress.restype = c_void_p
        self.__buffer_size = turbo_jpeg.tjBufSize
        self.__buffer_size.argtypes = [c_int, c_int, c_int]
        self.__buffer_size.restype = c_ulong
        self.__init_compress = turbo_jpeg.tjInitCompress
        self.__init_compress.restype = c_void_p
        self.__buffer_size_YUV2 = turbo_jpeg.tjBufSizeYUV2
        self.__buffer_size_YUV2.argtypes = [c_int, c_int, c_int, c_int]
        self.__buffer_size_YUV2.restype = c_ulong
        self.__plane_width = turbo_jpeg.tjPlaneWidth
        self.__plane_width.argtypes = [c_int, c_int, c_int]
        self.__plane_width.restype = c_int
        self.__plane_height = turbo_jpeg.tjPlaneHeight
        self.__plane_height.argtypes = [c_int, c_int, c_int]
        self.__plane_height.restype = c_int
        self.__destroy = turbo_jpeg.tjDestroy
        self.__destroy.argtypes = [c_void_p]
        self.__destroy.restype = c_int
        self.__decompress_header = turbo_jpeg.tjDecompressHeader3
        self.__decompress_header.argtypes = [
            c_void_p, POINTER(c_ubyte), c_ulong, POINTER(c_int),
            POINTER(c_int), POINTER(c_int), POINTER(c_int)]
        self.__decompress_header.restype = c_int
        self.__decompress = turbo_jpeg.tjDecompress2
        self.__decompress.argtypes = [
            c_void_p, POINTER(c_ubyte), c_ulong, POINTER(c_ubyte),
            c_int, c_int, c_int, c_int, c_int]
        self.__decompress.restype = c_int
        self.__decompressToYUV2 = turbo_jpeg.tjDecompressToYUV2
        self.__decompressToYUV2.argtypes = [
            c_void_p, POINTER(c_ubyte), c_ulong, POINTER(c_ubyte),
            c_int, c_int, c_int, c_int]
        self.__decompressToYUV2.restype = c_int
        self.__decompressToYUVPlanes = turbo_jpeg.tjDecompressToYUVPlanes
        self.__decompressToYUVPlanes.argtypes = [
            c_void_p, POINTER(c_ubyte), c_ulong, POINTER(POINTER(c_ubyte)),
            c_int, POINTER(c_int), c_int, c_int]
        self.__decompressToYUVPlanes.restype = c_int
        self.__compress = turbo_jpeg.tjCompress2
        self.__compress.argtypes = [
            c_void_p, POINTER(c_ubyte), c_int, c_int, c_int, c_int,
            POINTER(c_void_p), POINTER(c_ulong), c_int, c_int, c_int]
        self.__compress.restype = c_int
        self.__compressFromYUV = turbo_jpeg.tjCompressFromYUV
        self.__compressFromYUV.argtypes = [
            c_void_p, POINTER(c_ubyte), c_int, c_int, c_int, c_int,
            POINTER(c_void_p), POINTER(c_ulong), c_int, c_int]
        self.__compressFromYUV.restype = c_int
        self.__init_transform = turbo_jpeg.tjInitTransform
        self.__init_transform.restype = c_void_p
        self.__transform = turbo_jpeg.tjTransform
        self.__transform.argtypes = [
            c_void_p, POINTER(c_ubyte), c_ulong, c_int, POINTER(c_void_p),
            POINTER(c_ulong), POINTER(TransformStruct), c_int]
        self.__transform.restype = c_int
        self.__transform3 = getattr(turbo_jpeg, 'tj3Transform', None)
        if self.__transform3 is not None:
            self.__transform3.argtypes = [
                c_void_p, POINTER(c_ubyte), c_size_t, c_int, POINTER(c_void_p),
                POINTER(c_size_t), POINTER(TransformStruct)]
            self.__transform3.restype = c_int
        self.__free = turbo_jpeg.tjFree
        self.__free.argtypes = [c_void_p]
        self.__free.restype = None
        self.__get_error_str = turbo_jpeg.tjGetErrorStr
        self.__get_error_str.restype = c_char_p
        # tjGetErrorStr2 is only available in newer libjpeg-turbo
        self.__get_error_str2 = getattr(turbo_jpeg, 'tjGetErrorStr2', None)
        if self.__get_error_str2 is not None:
            self.__get_error_str2.argtypes = [c_void_p]
            self.__get_error_str2.restype = c_char_p
        # tjGetErrorCode is only available in newer libjpeg-turbo
        self.__get_error_code = getattr(turbo_jpeg, 'tjGetErrorCode', None)
        if self.__get_error_code is not None:
            self.__get_error_code.argtypes = [c_void_p]
            self.__get_error_code.restype = c_int

        get_scaling_factors = turbo_jpeg.tjGetScalingFactors
        get_scaling_factors.argtypes = [POINTER(c_int)]
        get_scaling_factors.restype = POINTER(ScalingFactor)
        num_scaling_factors = c_int()
        scaling_factors = get_scaling_factors(byref(num_scaling_factors))
        self.__scaling_factors = frozenset(
            (scaling_factors[i].num, scaling_factors[i].denom)
            for i in range(num_scaling_factors.value)
        )

    def decode_header(self, jpeg_buf):
        """decodes JPEG header and returns image properties as a tuple.
           e.g. (width, height, jpeg_subsample, jpeg_colorspace)
        """
        handle = self.__init_decompress()
        try:
            width = c_int()
            height = c_int()
            jpeg_subsample = c_int()
            jpeg_colorspace = c_int()
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            status = self.__decompress_header(
                handle, src_addr, jpeg_array.size, byref(width), byref(height),
                byref(jpeg_subsample), byref(jpeg_colorspace))
            if status != 0:
                self.__report_error(handle)
            return (width.value, height.value, jpeg_subsample.value, jpeg_colorspace.value)
        finally:
            self.__destroy(handle)

    def decode(self, jpeg_buf, pixel_format=TJPF_BGR, scaling_factor=None, flags=0):
        """decodes JPEG memory buffer to numpy array."""
        handle = self.__init_decompress()
        try:
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            scaled_width, scaled_height, _, _ = \
                self.__get_header_and_dimensions(handle, jpeg_array.size, src_addr, scaling_factor)
            img_array = np.empty(
                [scaled_height, scaled_width, tjPixelSize[pixel_format]],
                dtype=np.uint8)
            dest_addr = self.__getaddr(img_array)
            status = self.__decompress(
                handle, src_addr, jpeg_array.size, dest_addr, scaled_width,
                0, scaled_height, pixel_format, flags)
            if status != 0:
                self.__report_error(handle)
            return img_array
        finally:
            self.__destroy(handle)

    def decode_to_yuv(self, jpeg_buf, scaling_factor=None, pad=4, flags=0):
        """decodes JPEG memory buffer to yuv array."""
        handle = self.__init_decompress()
        try:
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            scaled_width, scaled_height, jpeg_subsample, _ = \
                self.__get_header_and_dimensions(handle, jpeg_array.size, src_addr, scaling_factor)
            buffer_size = self.__buffer_size_YUV2(scaled_width, pad, scaled_height, jpeg_subsample)
            buffer_array = np.empty(buffer_size, dtype=np.uint8)
            dest_addr = self.__getaddr(buffer_array)
            status = self.__decompressToYUV2(
                handle, src_addr, jpeg_array.size, dest_addr, scaled_width,
                pad, scaled_height, flags)
            if status != 0:
                self.__report_error(handle)
            plane_sizes = list()
            plane_sizes.append((scaled_height, scaled_width))
            if jpeg_subsample != TJSAMP_GRAY:
                for i in range(1, 3):
                    plane_sizes.append((
                        self.__plane_height(i, scaled_height, jpeg_subsample),
                        self.__plane_width(i, scaled_width, jpeg_subsample)))
            return buffer_array, plane_sizes
        finally:
            self.__destroy(handle)

    def decode_to_yuv_planes(self, jpeg_buf, scaling_factor=None, strides=(0, 0, 0), flags=0):
        """decodes JPEG memory buffer to yuv planes."""
        handle = self.__init_decompress()
        try:
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            scaled_width, scaled_height, jpeg_subsample, _ = \
                self.__get_header_and_dimensions(handle, jpeg_array.size, src_addr, scaling_factor)
            num_planes = 3
            if jpeg_subsample == TJSAMP_GRAY:
                num_planes = 1
            strides_addr = (c_int * num_planes)()
            dest_addr = (POINTER(c_ubyte) * num_planes)()
            planes = list()
            for i in range(num_planes):
                if strides[i] == 0:
                    strides_addr[i] = self.__plane_width(i, scaled_width, jpeg_subsample)
                else:
                    strides_addr[i] = strides[i]
                planes.append(np.empty(
                    (self.__plane_height(i, scaled_height, jpeg_subsample), strides_addr[i]), dtype=np.uint8))
                dest_addr[i] = self.__getaddr(planes[i])
            status = self.__decompressToYUVPlanes(
                handle, src_addr, jpeg_array.size, dest_addr, scaled_width, strides_addr, scaled_height, flags)
            if status != 0:
                self.__report_error(handle)
            return planes
        finally:
            self.__destroy(handle)

    def encode(self, img_array, quality=85, pixel_format=TJPF_BGR, jpeg_subsample=TJSAMP_422, flags=0):
        """encodes numpy array to JPEG memory buffer."""
        handle = self.__init_compress()
        try:
            jpeg_buf = c_void_p()
            jpeg_size = c_ulong()
            img_array = np.ascontiguousarray(img_array)
            height, width = img_array.shape[:2]
            channel = tjPixelSize[pixel_format]
            if channel > 1 and (len(img_array.shape) < 3 or img_array.shape[2] != channel):
                raise ValueError('Invalid shape for image data')
            src_addr = self.__getaddr(img_array)
            status = self.__compress(
                handle, src_addr, width, img_array.strides[0], height, pixel_format,
                byref(jpeg_buf), byref(jpeg_size), jpeg_subsample, quality, flags)
            if status != 0:
                self.__report_error(handle)
            dest_buf = create_string_buffer(jpeg_size.value)
            memmove(dest_buf, jpeg_buf.value, jpeg_size.value)
            self.__free(jpeg_buf)
            return dest_buf.raw
        finally:
            self.__destroy(handle)

    def encode_from_yuv(self, img_array, height, width, quality=85, jpeg_subsample=TJSAMP_420, flags=0):
        """encodes numpy array to JPEG memory buffer."""
        handle = self.__init_compress()
        try:
            jpeg_buf = c_void_p()
            jpeg_size = c_ulong()
            img_array = np.ascontiguousarray(img_array)
            src_addr = self.__getaddr(img_array)
            status = self.__compressFromYUV(
                handle, src_addr, width, 4, height, jpeg_subsample,
                byref(jpeg_buf), byref(jpeg_size), quality, flags)
            if status != 0:
                self.__report_error(handle)
            dest_buf = create_string_buffer(jpeg_size.value)
            memmove(dest_buf, jpeg_buf.value, jpeg_size.value)
            self.__free(jpeg_buf)
            return dest_buf.raw
        finally:
            self.__destroy(handle)

    def scale_with_quality(self, jpeg_buf, scaling_factor=None, quality=85, flags=0):
        """decompresstoYUV with scale factor, recompresstoYUV with quality factor"""
        handle = self.__init_decompress()
        try:
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            scaled_width, scaled_height, jpeg_subsample, _ = self.__get_header_and_dimensions(
                handle, jpeg_array.size, src_addr, scaling_factor)
            buffer_YUV_size = self.__buffer_size_YUV2(
                scaled_height, 4, scaled_width, jpeg_subsample)
            img_array = np.empty([buffer_YUV_size])
            dest_addr = self.__getaddr(img_array)
            status = self.__decompressToYUV2(
                handle, src_addr, jpeg_array.size, dest_addr, scaled_width, 4, scaled_height, flags)
            if status != 0:
                self.__report_error(handle)
            self.__destroy(handle)
            handle = self.__init_compress()
            jpeg_buf = c_void_p()
            jpeg_size = c_ulong()
            status = self.__compressFromYUV(
                handle, dest_addr, scaled_width, 4, scaled_height, jpeg_subsample, byref(jpeg_buf),
                byref(jpeg_size), quality, flags)
            if status != 0:
                self.__report_error(handle)
            dest_buf = create_string_buffer(jpeg_size.value)
            memmove(dest_buf, jpeg_buf.value, jpeg_size.value)
            self.__free(jpeg_buf)
            return dest_buf.raw
        finally:
            self.__destroy(handle)

    def crop(self, jpeg_buf, x, y, w, h, preserve=False, gray=False, copynone=False):
        """losslessly crop a jpeg image with optional grayscale"""
        handle = self.__init_transform()
        try:
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            width = c_int()
            height = c_int()
            jpeg_colorspace = c_int()
            jpeg_subsample = c_int()
            status = self.__decompress_header(
                handle, src_addr, jpeg_array.size, byref(width), byref(height),
                byref(jpeg_subsample), byref(jpeg_colorspace))
            if status != 0:
                self.__report_error(handle)
            x, w = self.__axis_to_image_boundaries(
                x, w, width.value, preserve, tjMCUWidth[jpeg_subsample.value])
            y, h = self.__axis_to_image_boundaries(
                y, h, height.value, preserve, tjMCUHeight[jpeg_subsample.value])
            region = CroppingRegion(x, y, w, h)
            crop_transform = TransformStruct(region, TJXOP_NONE,
                TJXOPT_CROP | (gray and TJXOPT_GRAY) | (copynone and TJXOPT_COPYNONE))
            return self.__do_transform(handle, src_addr, jpeg_array.size, 1, byref(crop_transform))[0]

        finally:
            self.__destroy(handle)

    def crop_multiple(self, jpeg_buf, crop_parameters, background_luminance=1.0, gray=False, copynone=False):
        """Lossless crop and/or extension operations on jpeg image.
        Crop origin(s) needs be divisable by the MCU block size and inside
        the input image, or OSError: Invalid crop request is raised.

        Parameters
        ----------
        jpeg_buf: bytes
            Input jpeg image.
        crop_parameters: List[Tuple[int, int, int, int]]
            List of crop parameters defining start x and y origin and width
            and height of each crop operation.
        background_luminance: float
            Luminance level (0 -1 ) to fill background when extending image.
            Default to 1, resulting in white background.
        gray: bool
            Produce greyscale output
        copynone: bool
            True = do not copy EXIF data (False by default)

        Returns
        ----------
        List[bytes]
            Cropped and/or extended jpeg images.
        """
        handle = self.__init_transform()
        try:
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            image_width = c_int()
            image_height = c_int()
            jpeg_subsample = c_int()
            jpeg_colorspace = c_int()

            # Decompress header to get input image size and subsample value
            decompress_header_status = self.__decompress_header(
                handle,
                src_addr,
                jpeg_array.size,
                byref(image_width),
                byref(image_height),
                byref(jpeg_subsample),
                byref(jpeg_colorspace)
            )

            if decompress_header_status != 0:
                self.__report_error(handle)

            # Define cropping regions from input parameters and image size
            crop_regions = self.__define_cropping_regions(crop_parameters)
            number_of_operations = len(crop_regions)

            # Define crop transforms from cropping_regions
            crop_transforms = (TransformStruct * number_of_operations)()
            for i, crop_region in enumerate(crop_regions):
                # The fill_background callback is slow, only use it if needed
                if self.__need_fill_background(
                    crop_region,
                    (image_width.value, image_height.value),
                    background_luminance
                ):
                    # Use callback to fill in background post-transform
                    callback_data = BackgroundStruct(
                        image_width,
                        image_height,
                        self.__map_luminance_to_dc_dct_coefficient(
                            bytearray(jpeg_buf),
                            background_luminance
                        )
                    )
                    callback = CUSTOMFILTER(fill_background)
                    crop_transforms[i] = TransformStruct(
                        crop_region,
                        TJXOP_NONE,
                        TJXOPT_PERFECT | TJXOPT_CROP | (gray and TJXOPT_GRAY) | (copynone and TJXOPT_COPYNONE),
                        pointer(callback_data),
                        callback
                    )
                else:
                    crop_transforms[i] = TransformStruct(
                        crop_region,
                        TJXOP_NONE,
                        TJXOPT_PERFECT | TJXOPT_CROP | (gray and TJXOPT_GRAY) | (copynone and TJXOPT_COPYNONE)
                    )
            results = self.__do_transform(handle, src_addr, jpeg_array.size, number_of_operations, crop_transforms)

            return results

        finally:
            self.__destroy(handle)

    def __do_transform(self, handle, src_buf, src_size, number_of_transforms, transforms):
        """Do transform.

        Parameters
        ----------
        handle: int
            Initiated transform handle.
        src_buf: LP_c_ubyte
            Pointer to source buffer for transform
        src_size: int
            Size of source buffer.
        number_of_transforms: int
            Number of transforms to perform.
        transforms: CArgObject
            C-array of transforms to perform.

        Returns
        ----------
        List[bytes]
            Cropped and/or extended jpeg images.
        """
        # Pointers to output image buffers
        dest_array = (c_void_p * number_of_transforms)()
        try:
            if self.__transform3 is not None:
                dest_size = (c_size_t * number_of_transforms)()
                transform_status = self.__transform3(
                handle,
                src_buf,
                src_size,
                number_of_transforms,
                dest_array,
                dest_size,
                transforms,
            )
            else:
                dest_size = (c_ulong * number_of_transforms)()
                transform_status = self.__transform(
                handle,
                src_buf,
                src_size,
                number_of_transforms,
                dest_array,
                dest_size,
                transforms,
                0
            )

            if transform_status != 0:
                self.__report_error(handle)
             # Copy the transform results into python bytes
            return [
                self.__copy_from_buffer(dest_array[i], dest_size[i])
                for i in range(number_of_transforms)
            ]
        finally:
            # Free the output image buffers
            for dest in dest_array:
                self.__free(dest)

    @staticmethod
    def __copy_from_buffer(buffer, size):
        """Copy bytes from buffer to python bytes."""
        dest_buf = create_string_buffer(size)
        memmove(dest_buf, buffer, size)
        return dest_buf.raw

    def __get_header_and_dimensions(self, handle, jpeg_array_size, src_addr, scaling_factor):
        """returns scaled image dimensions and header data"""
        if scaling_factor is not None and \
            scaling_factor not in self.__scaling_factors:
            raise ValueError('supported scaling factors are ' +
                str(self.__scaling_factors))
        width = c_int()
        height = c_int()
        jpeg_colorspace = c_int()
        jpeg_subsample = c_int()
        status = self.__decompress_header(
            handle, src_addr, jpeg_array_size, byref(width), byref(height),
            byref(jpeg_subsample), byref(jpeg_colorspace))
        if status != 0:
            self.__report_error(handle)
        scaled_width = width.value
        scaled_height = height.value
        if scaling_factor is not None:
            def get_scaled_value(dim, num, denom):
                return (dim * num + denom - 1) // denom
            scaled_width = get_scaled_value(
                scaled_width, scaling_factor[0], scaling_factor[1])
            scaled_height = get_scaled_value(
                scaled_height, scaling_factor[0], scaling_factor[1])
        return scaled_width, scaled_height, jpeg_subsample, jpeg_colorspace

    def __axis_to_image_boundaries(self, a, b, img_boundary, preserve, mcuBlock):
        img_b = img_boundary - (img_boundary % mcuBlock)
        delta_a = a % mcuBlock
        if a > img_b:
            a = img_b
        else:
            a = a - delta_a
        if not preserve:
            b = b + delta_a
        if (a + b) > img_b:
            b = img_b - a
        return a, b

    @staticmethod
    def __define_cropping_regions(crop_parameters):
        """Return list of crop regions from crop parameters

        Parameters
        ----------
        crop_parameters: List[Tuple[int, int, int, int]]
            List of crop parameters defining start x and y origin and width
            and height of each crop operation.

        Returns
        ----------
        List[CroppingRegion]
            List of crop operations, size is equal to the product of number of
            crop operations to perform in x and y direction.
        """
        return [
            CroppingRegion(x=crop[0], y=crop[1], w=crop[2], h=crop[3])
            for crop in crop_parameters
        ]

    @staticmethod
    def __need_fill_background(crop_region, image_size, background_luminance):
        """Return true if crop operation require background fill operation.

        Parameters
        ----------
        crop_region: CroppingRegion
            The crop region to check.
        image_size: [int, int]
            Size of input image.
        background_luminance: float
            Requested background luminance.

        Returns
        ----------
        bool
            True if crop operation require background fill operation.
        """
        return (
            (
                (crop_region.x + crop_region.w > image_size[0])
                or
                (crop_region.y + crop_region.h > image_size[1])
            )
            and (background_luminance != 0.5)
        )

    @staticmethod
    def __find_dqt(jpeg_data, dqt_index):
        """Return byte offset to quantification table with index dqt_index in
        jpeg_data.

        Parameters
        ----------
        jpeg_data: bytes
            Jpeg data.
        dqt_index: int
            Index of quantificatin table to find (0 - luminance).

        Returns
        ----------
        Optional[int]
            Byte offset to quantification table, or None if not found.
        """
        offset = 0
        while offset < len(jpeg_data):
            dct_table_offset = jpeg_data[offset:].find(b'\xFF\xDB')
            if dct_table_offset == -1:
                break
            dct_table_offset += offset
            dct_table_length = unpack(
                '>H',
                jpeg_data[dct_table_offset+2:dct_table_offset+4]
            )[0]
            dct_table_id_offset = dct_table_offset + 4
            table_index, _ = split_byte_into_nibbles(
                jpeg_data[dct_table_id_offset]
            )
            if table_index == dqt_index:
                return dct_table_offset
            offset += dct_table_offset+dct_table_length
        return None

    @classmethod
    def __get_dc_dqt_element(cls, jpeg_data, dqt_index):
        """Return dc quantification element from jpeg_data for quantification
        table dqt_index.

        Parameters
        ----------
        jpeg_data: bytes
            Jpeg data containing quantification table(s).
        dqt_index: int
            Index of quantificatin table to get (0 - luminance).

        Returns
        ----------
        int
            Dc quantification element.
        """
        dqt_offset = cls.__find_dqt(jpeg_data, dqt_index)
        if dqt_offset is None:
            raise ValueError(
                "Quantisation table {dqt_index} not found in header".format(
                    dqt_index=dqt_index)
            )
        precision_offset = dqt_offset+4
        precision = split_byte_into_nibbles(jpeg_data[precision_offset])[0]
        if precision == 0:
            unpack_type = '>b'
        elif precision == 1:
            unpack_type = '>h'
        else:
            raise ValueError('Not valid precision definition in dqt')
        dc_offset = dqt_offset + 5
        dc_length = calcsize(unpack_type)
        dc_value = unpack(
            unpack_type,
            jpeg_data[dc_offset:dc_offset+dc_length]
        )[0]
        return dc_value

    @classmethod
    def __map_luminance_to_dc_dct_coefficient(cls, jpeg_data, luminance):
        """Map a luminance level (0 - 1) to quantified dc dct coefficient.
        Before quantification dct coefficient have a range -1024 - 1023. This
        is reduced upon quantification by the quantification factor. This
        function maps the input luminance level range to the quantified dc dct
        coefficient range.

        Parameters
        ----------
        jpeg_data: bytes
            Jpeg data containing quantification table(s).
        luminance: float
            Luminance level (0 - black, 1 - white).

        Returns
        ----------
        int
            Quantified luminance dc dct coefficent.
        """
        luminance = min(max(luminance, 0), 1)
        dc_dqt_coefficient = cls.__get_dc_dqt_element(jpeg_data, 0)
        return int(round((luminance * 2047 - 1024) / dc_dqt_coefficient))

    def __report_error(self, handle):
        """reports error while error occurred"""
        if self.__get_error_code is not None:
            # using new error handling logic if possible
            if self.__get_error_code(handle) == TJERR_WARNING:
                warnings.warn(self.__get_error_string(handle))
                return
        # fatal error occurred
        raise IOError(self.__get_error_string(handle))

    def __get_error_string(self, handle):
        """returns error string"""
        if self.__get_error_str2 is not None:
            # using new interface if possible
            return self.__get_error_str2(handle).decode()
        # fallback to old interface
        return self.__get_error_str().decode()

    def __find_turbojpeg(self):
        """returns default turbojpeg library path if possible"""
        lib_path = find_library('turbojpeg')
        if lib_path is not None:
            return lib_path
        for lib_path in DEFAULT_LIB_PATHS[platform.system()]:
            if os.path.exists(lib_path):
                return lib_path
        if platform.system() == 'Linux' and 'LD_LIBRARY_PATH' in os.environ:
            ld_library_path = os.environ['LD_LIBRARY_PATH']
            for path in ld_library_path.split(':'):
                lib_path = os.path.join(path, 'libturbojpeg.so.0')
                if os.path.exists(lib_path):
                    return lib_path
        raise RuntimeError(
            'Unable to locate turbojpeg library automatically. '
            'You may specify the turbojpeg library path manually.\n'
            'e.g. jpeg = TurboJPEG(lib_path)')

    def __getaddr(self, nda):
        """returns the memory address for a given ndarray"""
        return cast(nda.__array_interface__['data'][0], POINTER(c_ubyte))

    @property
    def scaling_factors(self):
        return self.__scaling_factors

if __name__ == '__main__':
    jpeg = TurboJPEG()
    in_file = open('input.jpg', 'rb')
    img_array = jpeg.decode(in_file.read())
    in_file.close()
    out_file = open('output.jpg', 'wb')
    out_file.write(jpeg.encode(img_array))
    out_file.close()
    import cv2
    cv2.imshow('image', img_array)
    cv2.waitKey(0)
