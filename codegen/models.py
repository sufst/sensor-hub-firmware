from __future__ import annotations

import csv
import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, field_validator, model_validator

MAX_ANALOG_PER_MSG = 5   # floor(64 bits / 12 bits per signal)
MAX_DIGITAL_PER_MSG = 64  # 64 × 1-bit signals

PIN_TO_ADC_CHANNEL: dict[str, str] = {
    "PA0": "ADC_CHANNEL_0",   "PA1": "ADC_CHANNEL_1",
    "PA2": "ADC_CHANNEL_2",   "PA3": "ADC_CHANNEL_3",
    "PA4": "ADC_CHANNEL_4",   "PA5": "ADC_CHANNEL_5",
    "PA6": "ADC_CHANNEL_6",   "PA7": "ADC_CHANNEL_7",
    "PB0": "ADC_CHANNEL_8",   "PB1": "ADC_CHANNEL_9",
    "PC0": "ADC_CHANNEL_10",  "PC1": "ADC_CHANNEL_11",
    "PC2": "ADC_CHANNEL_12",  "PC3": "ADC_CHANNEL_13",
    "PC4": "ADC_CHANNEL_14",  "PC5": "ADC_CHANNEL_15",
}

_DBC_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ChannelConfig(BaseModel):
    number: int
    connector_pin: str
    ic_pin: str
    vref: float
    signal_name: str
    enabled: bool
    is_analog: bool

    @field_validator("signal_name")
    @classmethod
    def valid_signal_name(cls, v: str) -> str:
        v = v.strip()
        if not _DBC_IDENT.match(v):
            raise ValueError(
                f"'{v}' is not a valid DBC identifier (must match [A-Za-z_][A-Za-z0-9_]*)"
            )
        if len(v) > 128:
            raise ValueError(f"Signal name exceeds 128 characters: '{v}'")
        return v

    @field_validator("vref")
    @classmethod
    def valid_vref(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"VREF must be a positive voltage, got {v}")
        return v

    @field_validator("ic_pin")
    @classmethod
    def valid_ic_pin(cls, v: str) -> str:
        v = v.strip()
        if v not in PIN_TO_ADC_CHANNEL:
            raise ValueError(
                f"Unknown IC pin '{v}'. Supported pins: {sorted(PIN_TO_ADC_CHANNEL)}"
            )
        return v

    @property
    def adc_channel(self) -> str:
        return PIN_TO_ADC_CHANNEL[self.ic_pin]


class SensorConfig(BaseModel):
    ecu_name: str
    analog_base_id: int
    digital_base_id: int
    i2c_base_id: int
    channels: list[ChannelConfig]

    @field_validator("ecu_name")
    @classmethod
    def valid_ecu_name(cls, v: str) -> str:
        v = v.strip()
        if not _DBC_IDENT.match(v):
            raise ValueError(f"ECU name '{v}' is not a valid DBC identifier")
        return v

    @field_validator("analog_base_id", "digital_base_id", "i2c_base_id")
    @classmethod
    def valid_can_id(cls, v: int) -> int:
        if not (0 <= v <= 0x7FF):
            raise ValueError(
                f"CAN ID 0x{v:X} is out of range for an 11-bit standard ID (0x000–0x7FF)")
        return v

    @model_validator(mode="after")
    def no_duplicate_signal_names(self) -> "SensorConfig":
        names = [c.signal_name for c in self.channels if c.enabled]
        dupes = [n for n, count in Counter(names).items() if count > 1]
        if dupes:
            raise ValueError(
                f"Duplicate signal names among enabled channels: {dupes}")
        return self

    @model_validator(mode="after")
    def no_overlapping_can_ids(self) -> "SensorConfig":
        n_analog = math.ceil(len(self.enabled_analog) /
                             MAX_ANALOG_PER_MSG) if self.enabled_analog else 0
        n_digital = math.ceil(len(self.enabled_digital) /
                              MAX_DIGITAL_PER_MSG) if self.enabled_digital else 0
        ranges = []
        if n_analog > 0:
            ranges.append(("Analog",  self.analog_base_id,
                          self.analog_base_id + n_analog))
        if n_digital > 0:
            ranges.append(("Digital", self.digital_base_id,
                          self.digital_base_id + n_digital))
        ranges.append(("I2C", self.i2c_base_id, self.i2c_base_id + 3))
        for i, (name_a, start_a, end_a) in enumerate(ranges):
            for name_b, start_b, end_b in ranges[i + 1:]:
                if start_a < end_b and start_b < end_a:
                    raise ValueError(
                        f"{name_a} CAN ID range 0x{start_a:03X}–0x{end_a - 1:03X} "
                        f"overlaps {name_b} range 0x{start_b:03X}–0x{end_b - 1:03X}"
                    )
        return self

    @property
    def enabled_analog(self) -> list[ChannelConfig]:
        return [c for c in self.channels if c.enabled and c.is_analog]

    @property
    def enabled_digital(self) -> list[ChannelConfig]:
        return [c for c in self.channels if c.enabled and not c.is_analog]


def parse_csv(path: Path) -> SensorConfig:
    # Row 0: instruction text  Row 1: ECU Name      Row 2: Analog Base ID
    # Row 3: Digital Base ID   Row 4: I2C Base ID   Row 5: column headers  Rows 6+: channel data
    with path.open(newline="") as fh:
        rows = list(csv.reader(fh))

    ecu_name = rows[1][1].strip()
    analog_base_id = int(rows[2][1].strip(), 0)
    digital_base_id = int(rows[3][1].strip(), 0)
    i2c_base_id = int(rows[4][1].strip(), 0)

    df = pd.DataFrame(rows[6:], columns=rows[5])
    channels = [
        ChannelConfig(
            number=int(row["#"]),
            connector_pin=str(row["Connector Pin"]),
            ic_pin=str(row["IC Pin"]),
            vref=float(row["VREF / V"]),
            signal_name=str(row["CAN signal Name"]),
            enabled=bool(int(row["Enabled?"])),
            is_analog=bool(int(row["Analog? (0=digital)"])),
        )
        for _, row in df.iterrows()
    ]
    
    return SensorConfig(
        ecu_name=ecu_name,
        analog_base_id=analog_base_id,
        digital_base_id=digital_base_id,
        i2c_base_id=i2c_base_id,
        channels=channels,
    )
