# SPDX-License-Identifier: MIT
# Copyright 2026 Trieflow LLC.
# File, PNG and MSIX checks derived from Scriblark's reviewed qualification
# implementation (474e93cec63af125eab0458ef97c889a79ec7be7).
# Retained upstream terms: PIPELINE-MIT.txt and RETICLEQUAY-MIT.txt.
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import unicodedata
import zlib


def _digest(stream):
    hasher = hashlib.sha256()
    size = 0
    while block := stream.read(1024 * 1024):
        hasher.update(block)
        size += len(block)
    return {"bytes": size, "sha256": hasher.hexdigest()}


def _reject_link(path):
    path = Path(path)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError(f"Symlink/reparse point refused: {path}")
    return info


def _regular_stream(path):
    path = Path(path)
    before = _reject_link(path)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Expected regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    stream = os.fdopen(fd, "rb")
    after = os.fstat(fd)
    if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (
        after.st_dev,
        after.st_ino,
    ):
        stream.close()
        raise ValueError(f"File identity changed while opening: {path}")
    return stream


def _checked_path(value):
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or value.startswith("/")
    ):
        raise ValueError(f"Unsafe Windows path: {value!r}")
    parts = value.split("/")
    if any(
        not part
        or part in (".", "..")
        or part.endswith((".", " "))
        or re.search(r'[<>"|?*\x00-\x1f\x7f]', part)
        or re.fullmatch(r"(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I)
        for part in parts
    ):
        raise ValueError(f"Unsafe Windows path: {value!r}")
    return value


def _register_path(value, seen):
    _checked_path(value)
    parts = value.split("/")
    for count in range(1, len(parts) + 1):
        prefix = "/".join(parts[:count])
        key = unicodedata.normalize("NFC", prefix).casefold()
        if ("file", key) in seen:
            raise ValueError(f"File/directory or case/Unicode alias: {value}")
        prior = seen.get(("component", key))
        if prior is not None and prior != prefix:
            raise ValueError(f"Case/Unicode path alias: {value}")
        if count == len(parts) and ("directory", key) in seen:
            raise ValueError(f"File/directory path alias: {value}")
        seen[("component", key)] = prefix
        seen[("file" if count == len(parts) else "directory", key)] = prefix


def inventory_tree(root):
    root = Path(root)
    for parent in root.absolute().parents:
        _reject_link(parent)
    root_info = _reject_link(root)
    if not stat.S_ISDIR(root_info.st_mode):
        raise ValueError(f"Expected directory: {root}")
    result = {}
    seen = {}

    def walk(directory):
        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            info = _reject_link(path)
            relative = path.relative_to(root).as_posix()
            _checked_path(relative)
            if stat.S_ISDIR(info.st_mode):
                walk(path)
            elif stat.S_ISREG(info.st_mode):
                _register_path(relative, seen)
                with _regular_stream(path) as stream:
                    result[relative] = _digest(stream)
            else:
                raise ValueError(f"Special file refused: {relative}")

    walk(root)
    if not result:
        raise ValueError("Empty tree refused")
    return result


def file_record(path):
    with _regular_stream(path) as stream:
        return _digest(stream)


def _png_chunks(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Artwork is not PNG")
    position = 8
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError("Truncated PNG")
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        crc = data[position + 8 + length : position + 12 + length]
        if (
            len(body) != length
            or len(crc) != 4
            or zlib.crc32(kind + body) & 0xFFFFFFFF != struct.unpack(">I", crc)[0]
        ):
            raise ValueError("Invalid PNG chunk")
        position += 12 + length
        yield kind, body
        if kind == b"IEND":
            if position != len(data):
                raise ValueError("Trailing PNG data")
            return
    raise ValueError("PNG is missing IEND")


def png_dimensions(data):
    chunks = list(_png_chunks(data))
    if not chunks or chunks[0][0] != b"IHDR" or len(chunks[0][1]) != 13:
        raise ValueError("PNG is missing IHDR")
    return struct.unpack(">II", chunks[0][1][:8])


def _decode_rgba_png(data):
    chunks = list(_png_chunks(data))
    if chunks[0][0] != b"IHDR":
        raise ValueError("PNG is missing IHDR")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1]
    )
    if not (
        0 < width <= 4096
        and 0 < height <= 4096
        and depth == 8
        and color == 6
        and compression == filtering == interlace == 0
    ):
        raise ValueError("Artwork must be bounded noninterlaced 8-bit RGBA PNG")
    compressed = b"".join(body for kind, body in chunks if kind == b"IDAT")
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as error:
        raise ValueError(f"Invalid compressed PNG: {error}") from error
    stride = width * 4
    if len(raw) != (stride + 1) * height:
        raise ValueError("Unexpected PNG data size")
    rows = []
    prior = bytearray(stride)
    for row_number in range(height):
        start = row_number * (stride + 1)
        filter_type = raw[start]
        encoded = raw[start + 1 : start + stride + 1]
        if filter_type > 4:
            raise ValueError("Unsupported PNG filter")
        row = bytearray(stride)
        for index, value in enumerate(encoded):
            left = row[index - 4] if index >= 4 else 0
            up = prior[index]
            upper_left = prior[index - 4] if index >= 4 else 0
            if filter_type == 0:
                prediction = 0
            elif filter_type == 1:
                prediction = left
            elif filter_type == 2:
                prediction = up
            elif filter_type == 3:
                prediction = (left + up) // 2
            else:
                candidate = left + up - upper_left
                dl, du, dul = (
                    abs(candidate - left),
                    abs(candidate - up),
                    abs(candidate - upper_left),
                )
                prediction = (
                    left if dl <= du and dl <= dul else up if du <= dul else upper_left
                )
            row[index] = (value + prediction) & 0xFF
        rows.append(bytes(row))
        prior = row
    return width, height, rows


def _chunk(kind, body):
    return (
        struct.pack(">I", len(body))
        + kind
        + body
        + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    )


def resize_png(data, target):
    if target not in (44, 50, 150):
        raise ValueError("Unreviewed qualification asset size")
    width, height, rows = _decode_rgba_png(data)
    output = bytearray()
    for y in range(target):
        source_row = rows[min(height - 1, y * height // target)]
        output.append(0)
        for x in range(target):
            start = min(width - 1, x * width // target) * 4
            output.extend(source_row[start : start + 4])
    header = struct.pack(">IIBBBBB", target, target, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(output), 9))
        + _chunk(b"IEND", b"")
    )


def _write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def assert_unsigned_payload(files):
    for name in files:
        if PurePosixPath(name).suffix.casefold() in (
            ".pfx",
            ".p12",
            ".p7x",
            ".pem",
            ".key",
            ".cer",
            ".snk",
        ):
            raise ValueError(
                f"Signing/certificate input is forbidden in unsigned package payload: {name}"
            )
