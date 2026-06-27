from dataclasses import dataclass
from typing import ClassVar, Sequence


@dataclass
class AnalogRead:
    kind: ClassVar[str] = 'analog'
    name: str
    adc_channel: str
    board_id: str
    stm32_pin: str


@dataclass
class DigitalRead:
    kind: ClassVar[str] = 'digital'
    name: str
    gpio_port: str
    gpio_pin: str
    board_id: str
    stm32_pin: str


@dataclass
class ThermistorRead:
    kind: ClassVar[str] = 'ntc-therm'
    name: str
    adc_channel: str
    board_id: str
    stm32_pin: str


ChannelRead = AnalogRead | DigitalRead | ThermistorRead


@dataclass
class DbcSignalView:
    signal_name: str
    start_bit: int
    length: int
    scale: str
    offset: str
    min: str
    max: str
    unit: str
    value_type: str = "@1+"


@dataclass
class MessageView:
    name: str
    can_id: int
    can_id_hex: str
    id_macro: str  # {msg_name}_ID
    dlc: int
    dlc_macro: str  # {msg_name}_DLC
    pack_lines: list[str]
    c_signals: Sequence[ChannelRead]
    dbc_signals: Sequence[DbcSignalView]


@dataclass
class HardwareView:
    prescaler: int
    period: int
    led_port: str
    led_pin: str
