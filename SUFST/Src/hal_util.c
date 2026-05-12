#include "hal_util.h"
#include "adc.h"

// Used in sensors.c and the generated sensor_board sources (codegen/templates/sensor_hub.c.j2)
// We always use the max 239 ADC samples which only allows for ~55k conversions/s
// but this is plenty given we broadcast over CAN at 2 Hz (every 500ms)
uint16_t read_adc(uint32_t channel)
{
    ADC_ChannelConfTypeDef cfg = {0};
    cfg.Channel      = channel;
    cfg.Rank         = ADC_REGULAR_RANK_1;
    cfg.SamplingTime = ADC_SAMPLETIME_239CYCLES_5;
    
    HAL_ADC_ConfigChannel(&hadc1, &cfg);
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    uint16_t val = (uint16_t)HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    
    return val;
}
