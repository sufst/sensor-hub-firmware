MAX_ANALOG_PER_MSG = 5        # floor(64 bits / 12 bits)
MAX_DIGITAL_PER_MSG = 64      # 64 * 1-bit
MAX_TEMPERATURE_PER_MSG = 4   # 4 * 16 bits = 64 bits

NTC_BETA     = 3950.0   # K
NTC_R0       = 10000.0  # Ω — nominal resistance at T0
NTC_T0_K     = 298.15   # K — 25 °C
NTC_R_PULLUP = 10000.0  # Ω

PIN_TO_ADC = {
    "PA0": "ADC_CHANNEL_0",  "PA1": "ADC_CHANNEL_1",
    "PA2": "ADC_CHANNEL_2",  "PA3": "ADC_CHANNEL_3",
    "PA4": "ADC_CHANNEL_4",  "PA5": "ADC_CHANNEL_5",
    "PA6": "ADC_CHANNEL_6",  "PA7": "ADC_CHANNEL_7",
    "PB0": "ADC_CHANNEL_8",  "PB1": "ADC_CHANNEL_9",
    "PC0": "ADC_CHANNEL_10", "PC1": "ADC_CHANNEL_11",
    "PC2": "ADC_CHANNEL_12", "PC3": "ADC_CHANNEL_13",
    "PC4": "ADC_CHANNEL_14", "PC5": "ADC_CHANNEL_15",
}
