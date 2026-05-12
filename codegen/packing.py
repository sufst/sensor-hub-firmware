import math

from codegen.models.config import SensorConfig, ChannelConfig
from codegen.models.view import AnalogRead, DigitalRead, MessageView, DbcSignalView
from codegen.constants import MAX_ANALOG_PER_MSG, MAX_DIGITAL_PER_MSG, PIN_TO_ADC


def generate_pack_lines(channels: list[ChannelConfig], bit_length: int) -> list[str]:
    n_bytes = math.ceil(len(channels) * bit_length / 8)
    lines = []

    for b in range(n_bytes):
        terms = []
        for i, ch in enumerate(channels):
            sig_start = i * bit_length
            ov_start = max(sig_start, b * 8)
            ov_end = min(sig_start + bit_length, b * 8 + 8)

            if ov_start >= ov_end:
                continue

            shift_out = ov_start - sig_start
            shift_in = ov_start - (b * 8)
            nbits = ov_end - ov_start
            mask = (1 << nbits) - 1

            t = ch.name
            if shift_out:
                t = f"({t} >> {shift_out}U)"
            t = f"({t} & 0x{mask:02X}U)"
            if shift_in:
                t = f"({t} << {shift_in}U)"

            terms.append(t)

        expr = " | ".join(terms) if terms else "0U"
        lines.append(f"    data[{b}] = (uint8_t)({expr});")

    return lines


def chunk(lst: list, n: int) -> list[list]:
    return [lst[i: i + n] for i in range(0, len(lst), n)]


def build_messages(config: SensorConfig) -> list[MessageView]:
    messages = []

    # --- Analog Messages ---
    analog_groups = chunk(config.enabled_analog, MAX_ANALOG_PER_MSG)
    for i, group in enumerate(analog_groups):
        suffix = f"_ANALOG_{i+1}" if len(analog_groups) > 1 else "_ANALOG"
        msg_name = f"{config.ecu_name}{suffix}"
        can_id = config.can_base_ids.analog + i

        dbc_signals = []
        for ch_idx, ch in enumerate(group):
            # 12-bit ADC to Voltage mapping
            scale_val = ch.vref / 4095.0

            dbc_signals.append(DbcSignalView(
                signal_name=ch.name,
                start_bit=ch_idx * 12,
                length=12,
                scale=repr(scale_val),
                offset="0",
                min="0",
                max=f"{ch.vref:.3g}",
                unit="V"
            ))

        messages.append(MessageView(
            name=msg_name,
            id_macro=f"{msg_name}_ID",
            can_id=can_id,
            can_id_hex=f"0x{can_id:X}",
            dlc=math.ceil(len(group) * 12 / 8),
            dlc_macro=f"{msg_name}_DLC",
            c_signals=[AnalogRead(
                name=ch.name, adc_channel=PIN_TO_ADC[ch.pin.raw],
                board_id=ch.id, stm32_pin=ch.pin.raw) for ch in group],
            dbc_signals=dbc_signals,
            pack_lines=generate_pack_lines(group, bit_length=12)
        ))

    # --- Digital Messages ---
    digital_groups = chunk(config.enabled_digital, MAX_DIGITAL_PER_MSG)
    for i, group in enumerate(digital_groups):
        suffix = f"_DIGITAL_{i+1}" if len(digital_groups) > 1 else "_DIGITAL"
        msg_name = f"{config.ecu_name}{suffix}"
        can_id = config.can_base_ids.digital + i

        dbc_signals = []
        for ch_idx, ch in enumerate(group):
            dbc_signals.append(DbcSignalView(
                signal_name=ch.name,
                start_bit=ch_idx,
                length=1,
                scale="1",
                offset="0",
                min="0",
                max="1",
                unit="bool"
            ))

        messages.append(MessageView(
            name=msg_name,
            id_macro=f"{msg_name}_ID",
            can_id=can_id,
            can_id_hex=f"0x{can_id:X}",
            dlc=math.ceil(len(group) / 8),
            dlc_macro=f"{msg_name}_DLC",
            c_signals=[DigitalRead(
                name=ch.name, gpio_port=ch.pin.port, gpio_pin=ch.pin.pin_macro,
                board_id=ch.id, stm32_pin=ch.pin.raw) for ch in group],
            dbc_signals=dbc_signals,
            pack_lines=generate_pack_lines(group, bit_length=1)
        ))

    # --- I2C Messages ---
    # The C code handles the actual reading/packing, so c_signals and pack_lines are empty.
    # We only need the macros generated in the header and the DBC definitions (later used in SUFST/Src/sensors.c).
    #
    # id_macro is intentionally NOT prefixed with {ecu_name} (unlike analog/digital above):
    # SUFST/Src/sensors.c is shared across boards and references these fixed macro names.
    # Renaming them to e.g. PEDAL_BOX_IMU_ACCEL_ID would break that shared code.

    i2c_base = config.can_base_ids.i2c

    messages.append(MessageView(
        name=f"{config.ecu_name}_IMU_ACCEL",
        id_macro="SENSOR_HUB_IMU_ACCEL_ID",
        can_id=i2c_base,
        can_id_hex=f"0x{i2c_base:X}",
        dlc=6,
        dlc_macro="SENSOR_HUB_IMU_ACCEL_DLC",
        c_signals=[],
        pack_lines=[],
        dbc_signals=[
            DbcSignalView(f"{config.ecu_name}_ACCEL_{ax}", i *
                          16, 16, "0.000122", "0", "-4", "4", "g", "@1-")
            for i, ax in enumerate(("X", "Y", "Z"))
        ]
    ))

    messages.append(MessageView(
        name=f"{config.ecu_name}_IMU_GYRO",
        id_macro="SENSOR_HUB_IMU_GYRO_ID",
        can_id=i2c_base + 1,
        can_id_hex=f"0x{i2c_base + 1:X}",
        dlc=6,
        dlc_macro="SENSOR_HUB_IMU_GYRO_DLC",
        c_signals=[],
        pack_lines=[],
        dbc_signals=[
            DbcSignalView(f"{config.ecu_name}_GYRO_{ax}", i *
                          16, 16, "0.0175", "0", "-500", "500", "dps", "@1-")
            for i, ax in enumerate(("X", "Y", "Z"))
        ]
    ))

    messages.append(MessageView(
        name=f"{config.ecu_name}_TEMP",
        id_macro="SENSOR_HUB_TEMP_ID",
        can_id=i2c_base + 2,
        can_id_hex=f"0x{i2c_base + 2:X}",
        dlc=4,
        dlc_macro="SENSOR_HUB_TEMP_DLC",
        c_signals=[],
        pack_lines=[],
        dbc_signals=[
            DbcSignalView(f"{config.ecu_name}_IMU_TEMP", 0, 16,
                          "0.00390625", "25", "-40", "85", "degC", "@1-"),
            DbcSignalView(f"{config.ecu_name}_AMBIENT_TEMP", 16,
                          16, "0.0625", "0", "-55", "125", "degC", "@1-")
        ]
    ))

    return messages
