from __future__ import annotations

import math

from codegen.models import ChannelConfig, MAX_ANALOG_PER_MSG, MAX_DIGITAL_PER_MSG


def analog_pack_lines(channels: list[ChannelConfig]) -> list[str]:
    """C statements packing N 12-bit ADC values into data[] (Intel byte order, sequential)."""
    n_bytes = math.ceil(len(channels) * 12 / 8)
    lines = []
    for b in range(n_bytes):
        terms = []
        for i, ch in enumerate(channels):
            sig_start = i * 12
            ov_start = max(sig_start, b * 8)
            ov_end = min(sig_start + 12, b * 8 + 8)
            if ov_start >= ov_end:
                continue
            shift_out = ov_start - sig_start
            shift_in = ov_start - b * 8
            nbits = ov_end - ov_start
            mask = (1 << nbits) - 1
            t = ch.signal_name
            if shift_out:
                t = f"({t} >> {shift_out}U)"
            t = f"({t} & 0x{mask:02X}U)"
            if shift_in:
                t = f"({t} << {shift_in}U)"
            terms.append(t)
        expr = " | ".join(terms) if terms else "0U"
        lines.append(f"    data[{b}] = (uint8_t)({expr});")
    return lines


def digital_pack_lines(channels: list[ChannelConfig]) -> list[str]:
    """C statements packing N 1-bit digital values into data[]."""
    n_bytes = math.ceil(len(channels) / 8)
    lines = []
    for b in range(n_bytes):
        terms = []
        for i in range(b * 8, min((b + 1) * 8, len(channels))):
            shift = i % 8
            t = f"({channels[i].signal_name} & 0x01U)"
            if shift:
                t = f"({t} << {shift}U)"
            terms.append(t)
        expr = " | ".join(terms) if terms else "0U"
        lines.append(f"    data[{b}] = (uint8_t)({expr});")
    return lines


def analog_signal_specs(channels: list[ChannelConfig]) -> list[dict]:
    return [
        {
            "signal_name": ch.signal_name,
            "start_bit":   i * 12,
            "length":      12,
            "scale":       f"{ch.vref / 4096:.10g}",
            "offset":      "0",
            "min":         "0",
            "max":         f"{ch.vref:.6g}",
            "unit":        "V",
        }
        for i, ch in enumerate(channels)
    ]


def digital_signal_specs(channels: list[ChannelConfig]) -> list[dict]:
    return [
        {
            "signal_name": ch.signal_name,
            "start_bit":   i,
            "length":      1,
            "scale":       "1",
            "offset":      "0",
            "min":         "0",
            "max":         "1",
            "unit":        "",
        }
        for i, ch in enumerate(channels)
    ]
