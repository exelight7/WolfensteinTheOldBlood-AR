"""Read-only Bink 2 decoder using the game's own official bink2w64.dll (RAD decoder).

No external decoder exists that supports Bink 2 video (ffmpeg 7.1 explicitly reports
"Bink 2 video is not implemented"), so we drive the shipping RAD runtime through ctypes.
This only READS .bik files into memory and writes PNG frames; it never re-encodes.

Struct layouts were reverse-engineered from live BinkGetFrameBuffersInfo output:
  BINKFRAMEBUFFERS : { int TotalFrames; u32 YABufferWidth, YABufferHeight,
                       cRcBBufferWidth, cRcBBufferHeight; u32 FrameNum;
                       BINKFRAMEPLANESET Frames[2]; }
  BINKFRAMEPLANESET: { BINKPLANE YPlane, cRPlane, cBPlane, APlane; }
  BINKPLANE        : { void* Buffer; int Allocate; u32 BufferPitch; }   (16 bytes on x64)
"""
import ctypes
import os
import time
from ctypes import (c_int, c_uint32, c_void_p, c_char_p, POINTER, byref, cast,
                    create_string_buffer)

import numpy as np


GAME_DIR = os.environ.get("WTOB_GAME_DIR")
DEFAULT_DLL = os.path.join(GAME_DIR, "bink2w64.dll") if GAME_DIR else None


class BINKPLANE(ctypes.Structure):
    _fields_ = [("Buffer", c_void_p), ("Allocate", c_int), ("BufferPitch", c_uint32)]


class BINKFRAMEPLANESET(ctypes.Structure):
    _fields_ = [("YPlane", BINKPLANE), ("cRPlane", BINKPLANE),
                ("cBPlane", BINKPLANE), ("APlane", BINKPLANE)]


class BINKFRAMEBUFFERS(ctypes.Structure):
    _fields_ = [("TotalFrames", c_int), ("YABufferWidth", c_uint32),
                ("YABufferHeight", c_uint32), ("cRcBBufferWidth", c_uint32),
                ("cRcBBufferHeight", c_uint32), ("FrameNum", c_uint32),
                ("Frames", BINKFRAMEPLANESET * 2)]


class BINK_HDR(ctypes.Structure):
    _fields_ = [("Width", c_uint32), ("Height", c_uint32), ("Frames", c_uint32),
                ("FrameNum", c_uint32), ("LastFrameNum", c_uint32),
                ("FrameRate", c_uint32), ("FrameRateDiv", c_uint32)]


class Bink2Movie(object):
    """Sequential decoder for a single .bik file. Use grab() to reach a frame index."""

    def __init__(self, path, dll_path=DEFAULT_DLL):
        if not dll_path:
            raise ValueError("Set WTOB_GAME_DIR or pass dll_path to locate bink2w64.dll")
        self.dll = ctypes.WinDLL(dll_path)
        d = self.dll
        d.BinkOpen.restype = c_void_p
        d.BinkOpen.argtypes = [c_char_p, c_uint32]
        d.BinkGetFrameBuffersInfo.argtypes = [c_void_p, POINTER(BINKFRAMEBUFFERS)]
        d.BinkRegisterFrameBuffers.argtypes = [c_void_p, POINTER(BINKFRAMEBUFFERS)]
        d.BinkDoFrame.argtypes = [c_void_p]
        d.BinkDoFrame.restype = c_int
        d.BinkWait.argtypes = [c_void_p]
        d.BinkWait.restype = c_int
        d.BinkCopyToBuffer.argtypes = [c_void_p, c_void_p, c_int, c_uint32,
                                       c_uint32, c_uint32, c_uint32]
        d.BinkCopyToBuffer.restype = c_int
        d.BinkNextFrame.argtypes = [c_void_p]
        d.BinkGoto.argtypes = [c_void_p, c_uint32, c_int]
        d.BinkClose.argtypes = [c_void_p]
        d.BinkGetError.restype = c_char_p

        self.handle = d.BinkOpen(path.encode("ascii"), 0)
        if not self.handle:
            raise RuntimeError("BinkOpen failed: %s" % d.BinkGetError())

        hdr = cast(self.handle, POINTER(BINK_HDR)).contents
        self.width = int(hdr.Width)
        self.height = int(hdr.Height)
        self.frames = int(hdr.Frames)
        self.fps = float(hdr.FrameRate) / float(hdr.FrameRateDiv or 1)

        self.fbi = BINKFRAMEBUFFERS()
        d.BinkGetFrameBuffersInfo(self.handle, byref(self.fbi))
        self._plane_keep = []
        for i in range(self.fbi.TotalFrames):
            for nm, (w, hh) in (("YPlane", (self.fbi.YABufferWidth, self.fbi.YABufferHeight)),
                                ("cRPlane", (self.fbi.cRcBBufferWidth, self.fbi.cRcBBufferHeight)),
                                ("cBPlane", (self.fbi.cRcBBufferWidth, self.fbi.cRcBBufferHeight))):
                pl = getattr(self.fbi.Frames[i], nm)
                if not pl.Allocate:
                    continue
                pitch = (int(w) + 15) & ~15
                buf = create_string_buffer(pitch * int(hh))
                pl.BufferPitch = pitch
                pl.Buffer = cast(buf, c_void_p)
                self._plane_keep.append(buf)
        d.BinkRegisterFrameBuffers(self.handle, byref(self.fbi))

        self._out = np.zeros((self.height, self.width * 4), np.uint8)
        self._out_ptr = c_void_p(self._out.ctypes.data)
        self.pos = -1
        self._need_next = False

    def _decode_current(self):
        d = self.dll
        rc = 1
        t0 = time.time()
        while rc != 0 and time.time() - t0 < 10:
            rc = d.BinkDoFrame(self.handle)
            if rc != 0:
                time.sleep(0.001)
        d.BinkCopyToBuffer(self.handle, self._out_ptr, self.width * 4,
                           self.height, 0, 0, 0x00000003)

    def grab_rgba(self, frame_index):
        """Return (H,W,4) RGBA uint8 for frame_index (0-based), containing B,G,R,A.

        Frames must be requested in non-decreasing order for correct dirty-rect
        accumulation; a backward request seeks to a keyframe via BinkGoto.
        """
        d = self.dll
        if frame_index < self.pos:
            d.BinkGoto(self.handle, frame_index, 1)
            self.pos = frame_index - 1
            self._need_next = False
        while self.pos < frame_index:
            if self._need_next:
                d.BinkNextFrame(self.handle)
            self._decode_current()
            self.pos += 1
            self._need_next = True
        return self._out.reshape(self.height, self.width, 4).copy()

    def snapshot(self):
        """Return the currently accumulated frame as (H,W,4) B,G,R,A."""
        return self._out.reshape(self.height, self.width, 4).copy()

    def close(self):
        if self.handle:
            self.dll.BinkClose(self.handle)
            self.handle = None


def bgrx_to_png(bgrx):
    """Convert a B,G,R,A array to an RGB PIL image."""
    from PIL import Image
    rgb = bgrx[:, :, [2, 1, 0]].copy()
    return Image.fromarray(rgb)
