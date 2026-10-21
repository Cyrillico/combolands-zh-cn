"""改写 Assembly-CSharp.dll 里的 .NET 用户字符串（#US 堆），等长替换。

教程、提示这类文本不在资源里，而是编译进程序的字符串堆。字符串堆的每个条目是：
[压缩长度前缀][UTF-16LE 字符][结束字节]，运行时按元数据里的偏移读取。

替换策略：新文本比原文短时，保持前缀字节宽度不变，写入新长度、新字符、结束字节，
剩余字节补零。这样后续字符串的偏移不会移动，文件大小也不变。
"""

import struct


def _decode_prefix(buf, pos):
    b = buf[pos]
    if b & 0x80 == 0:
        return b, 1
    if b & 0xC0 == 0x80:
        return ((b & 0x3F) << 8) | buf[pos + 1], 2
    return (((b & 0x1F) << 24) | (buf[pos + 1] << 16)
            | (buf[pos + 2] << 8) | buf[pos + 3]), 4


def _encode_prefix(value, width):
    if width == 1:
        assert value < 0x80
        return bytes([value])
    if width == 2:
        assert value < 0x4000
        return bytes([0x80 | (value >> 8), value & 0xFF])
    return bytes([0xC0 | (value >> 24), (value >> 16) & 0xFF,
                  (value >> 8) & 0xFF, value & 0xFF])


def patch_bytes(data, entries):
    """data: 原始 DLL 字节；entries: [{'source': 原文, 'translation': 译文}]。

    返回 (新字节, 报告列表)。无法安全替换的条目会跳过并记录原因。
    """
    data = bytearray(data)
    original = bytes(data)
    report = []

    for entry in entries:
        source, translation = entry["source"], entry["translation"]
        needle = source.encode("utf-16-le")
        idx = original.find(needle)
        if idx < 0:
            report.append({"source": source[:40], "status": "skip", "reason": "未找到原文"})
            continue

        # 定位长度前缀，并确认它描述的正是这段字符串
        width = None
        for w in (1, 2, 4):
            start = idx - w
            if start < 0:
                continue
            try:
                value, real_width = _decode_prefix(original, start)
            except IndexError:
                continue
            if real_width == w and value == len(needle) + 1 and start + w == idx:
                width = w
                break
        if width is None:
            report.append({"source": source[:40], "status": "skip", "reason": "长度前缀不匹配"})
            continue

        slot_start = idx - width
        slot_end = idx + len(needle) + 1          # 含结束字节
        new_bytes = translation.encode("utf-16-le")
        need = len(new_bytes) + 1
        min_width = 1 if need < 0x80 else (2 if need < 0x4000 else 4)
        if min_width > width:
            report.append({"source": source[:40], "status": "skip", "reason": "新文本太长"})
            continue

        payload = _encode_prefix(need, width) + new_bytes + b"\x00"
        slot_len = slot_end - slot_start
        payload += b"\x00" * (slot_len - len(payload))
        data[slot_start:slot_end] = payload
        report.append({"source": source[:40], "status": "ok", "slot": slot_len})

    if len(data) != len(original):
        raise AssertionError("文件大小发生变化，拒绝写出")
    return bytes(data), report
