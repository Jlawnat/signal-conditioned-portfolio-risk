"""Render generated SVGs to PNG via installed librsvg, using stdlib PNG encoding."""

import ctypes
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "paper/figures"
rsvg = ctypes.CDLL("librsvg-2.so.2")
pix = ctypes.CDLL("libgdk_pixbuf-2.0.so.0")
obj = ctypes.CDLL("libgobject-2.0.so.0")
rsvg.rsvg_handle_new_from_file.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
rsvg.rsvg_handle_new_from_file.restype = ctypes.c_void_p
rsvg.rsvg_handle_get_pixbuf.argtypes = [ctypes.c_void_p]
rsvg.rsvg_handle_get_pixbuf.restype = ctypes.c_void_p
for name in ("gdk_pixbuf_get_width", "gdk_pixbuf_get_height", "gdk_pixbuf_get_rowstride", "gdk_pixbuf_get_n_channels"):
    method = getattr(pix, name)
    method.argtypes = [ctypes.c_void_p]
    method.restype = ctypes.c_int
pix.gdk_pixbuf_get_pixels.argtypes = [ctypes.c_void_p]
pix.gdk_pixbuf_get_pixels.restype = ctypes.c_void_p
obj.g_object_unref.argtypes = [ctypes.c_void_p]


def chunk(name, data):
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))


def convert(path):
    handle = rsvg.rsvg_handle_new_from_file(str(path).encode(), None)
    if not handle:
        raise RuntimeError(f"SVG_LOAD_FAILED:{path}")
    bitmap = rsvg.rsvg_handle_get_pixbuf(handle)
    if not bitmap:
        obj.g_object_unref(handle)
        raise RuntimeError(f"SVG_RENDER_FAILED:{path}")
    width = pix.gdk_pixbuf_get_width(bitmap)
    height = pix.gdk_pixbuf_get_height(bitmap)
    stride = pix.gdk_pixbuf_get_rowstride(bitmap)
    channels = pix.gdk_pixbuf_get_n_channels(bitmap)
    if channels != 4:
        raise RuntimeError("EXPECTED_RGBA_PIXBUF")
    pixels = pix.gdk_pixbuf_get_pixels(bitmap)
    scanlines = b"".join(
        b"\x00" + ctypes.string_at(pixels + y * stride, width * channels)
        for y in range(height)
    )
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b"")
    path.with_suffix(".png").write_bytes(png)
    obj.g_object_unref(bitmap)
    obj.g_object_unref(handle)


if __name__ == "__main__":
    for source in sorted(FIG.glob("fig*.svg")):
        convert(source)
    print(f"Rendered {len(list(FIG.glob('fig*.png')))} PNG previews")
