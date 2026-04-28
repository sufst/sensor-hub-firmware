from __future__ import annotations

import math

from cantools.database import Database as _CantoolsDB

from codegen.models import ChannelConfig, SensorConfig
from codegen.models import MAX_ANALOG_PER_MSG, MAX_DIGITAL_PER_MSG
from codegen.packing import (
    analog_pack_lines,
    analog_signal_specs,
    digital_pack_lines,
    digital_signal_specs,
)


def _chunk(lst: list, n: int) -> list[list]:
    return [lst[i: i + n] for i in range(0, len(lst), n)]


def _build_groups(
    ecu_name: str,
    channels: list[ChannelConfig],
    base_id: int,
    per_msg: int,
    kind: str,
    pack_fn,
    spec_fn,
) -> list[dict]:
    groups = _chunk(channels, per_msg)
    use_index = len(groups) > 1
    result = []
    for i, grp in enumerate(groups):
        suffix = f"_{kind}_{i + 1}" if use_index else f"_{kind}"
        name = f"{ecu_name}{suffix}"
        can_id = base_id + i
        dlc = (
            math.ceil(len(grp) * 12 / 8)
            if kind == "ANALOG"
            else math.ceil(len(grp) / 8)
        )
        result.append({
            "name":       name,
            "can_id":     can_id,
            "can_id_hex": f"0x{can_id:03X}",
            "id_define":  f"{name}_ID",
            "dlc":        dlc,
            "dlc_define": f"{name}_DLC",
            "channels":   grp,
            "signals":    spec_fn(grp),
            "pack_lines": pack_fn(grp),
            "is_analog":  kind == "ANALOG",
        })
    return result


def build_message_groups(
    config: SensorConfig, analog_base_id: int, digital_base_id: int
) -> tuple[list[dict], list[dict]]:
    analog = _build_groups(
        config.ecu_name, config.enabled_analog,
        analog_base_id, MAX_ANALOG_PER_MSG,
        "ANALOG", analog_pack_lines, analog_signal_specs,
    )
    digital = _build_groups(
        config.ecu_name, config.enabled_digital,
        digital_base_id, MAX_DIGITAL_PER_MSG,
        "DIGITAL", digital_pack_lines, digital_signal_specs,
    )
    return analog, digital


def build_i2c_groups(config: SensorConfig) -> list[dict]:
    ecu = config.ecu_name
    base = config.i2c_base_id

    def _msg(suffix: str, can_id: int, dlc: int, signals: list[dict]) -> dict:
        name = f"{ecu}_{suffix}"
        return {
            "name":       name,
            "can_id":     can_id,
            "can_id_hex": f"0x{can_id:03X}",
            "id_define":  f"{name}_ID",
            "dlc":        dlc,
            "dlc_define": f"{name}_DLC",
            "channels":   [],
            "pack_lines": [],
            "signals":    signals,
            "is_analog":  False,
        }

    accel = [
        {"signal_name": f"{ecu}_ACCEL_{ax}", "start_bit": i * 16, "length": 16,
         "scale": "0.000122", "offset": "0", "min": "-4", "max": "4",
         "unit": "g", "value_type": "@1-"}
        for i, ax in enumerate(("X", "Y", "Z"))
    ]
    gyro = [
        {"signal_name": f"{ecu}_GYRO_{ax}", "start_bit": i * 16, "length": 16,
         "scale": "0.0175", "offset": "0", "min": "-500", "max": "500",
         "unit": "dps", "value_type": "@1-"}
        for i, ax in enumerate(("X", "Y", "Z"))
    ]
    temp = [
        {"signal_name": f"{ecu}_IMU_TEMP", "start_bit": 0, "length": 16,
         "scale": "0.00390625", "offset": "25", "min": "-40", "max": "85",
         "unit": "degC", "value_type": "@1-"},
        {"signal_name": f"{ecu}_AMBIENT_TEMP", "start_bit": 16, "length": 16,
         "scale": "0.0625", "offset": "0", "min": "-55", "max": "125",
         "unit": "degC", "value_type": "@1-"},
    ]

    return [
        _msg("IMU_ACCEL", base,     6, accel),
        _msg("IMU_GYRO",  base + 1, 6, gyro),
        _msg("TEMP",      base + 2, 4, temp),
    ]


def validate_with_cantools(config: SensorConfig, groups: list[dict]) -> None:
    db = _CantoolsDB()
    for group in groups:
        sig_lines = "\n".join(
            f" SG_ {s['signal_name']} : {s['start_bit']}|{s['length']}{s.get('value_type', '@1+')}"
            f" ({s['scale']},{s['offset']}) [{s['min']}|{s['max']}] \"{s['unit']}\" Vector__XXX"
            for s in group["signals"]
        )
        dbc_fragment = (
            f"VERSION \"\"\nNS_ :\nBS_:\nBU_:\n"
            f"BO_ {group['can_id']} {group['name']}: {group['dlc']} {config.ecu_name}\n"
            f"{sig_lines}\n"
        )
        db.add_dbc_string(dbc_fragment)
