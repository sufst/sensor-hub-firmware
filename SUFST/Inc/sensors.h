#pragma once
#include "stm32f1xx_hal.h"

HAL_StatusTypeDef Sensors_Init(void);
HAL_StatusTypeDef Sensors_Transmit(void);
uint8_t           Sensors_GetStatus(void);
