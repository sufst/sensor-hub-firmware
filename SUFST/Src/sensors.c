#include "sensors.h"
#include "sensor_hub.h"
#include "i2c.h"
#include "can.h"
#include <string.h>

#define I2C_TIMEOUT_MS 10U

/* ISM330DHCX */
#define ISM330_ADDR     (0x6B << 1)
#define ISM330_CTRL1_XL 0x10U  /* accelerometer control */
#define ISM330_CTRL2_G  0x11U  /* gyroscope control */
#define ISM330_OUT_TEMP 0x20U  /* temperature output (2 bytes) */
#define ISM330_OUT_G    0x22U  /* gyroscope output (6 bytes, X/Y/Z) */
#define ISM330_OUT_A    0x28U  /* accelerometer output (6 bytes, X/Y/Z) */

/* MCP9800 */
#define MCP9800_ADDR    (0x4D << 1)
#define MCP9800_REG_T   0x00U  /* temperature register */
#define MCP9800_REG_CFG 0x01U  /* configuration register */
#define MCP9800_CFG_12B 0x60U  /* 12-bit resolution, continuous */

static HAL_StatusTypeDef i2c_write(uint8_t dev, uint8_t reg, uint8_t val)
{
    return HAL_I2C_Mem_Write(&hi2c1, dev, reg, I2C_MEMADD_SIZE_8BIT, &val, 1, I2C_TIMEOUT_MS);
}

static HAL_StatusTypeDef i2c_read(uint8_t dev, uint8_t reg, uint8_t *buf, uint16_t len)
{
    return HAL_I2C_Mem_Read(&hi2c1, dev, reg, I2C_MEMADD_SIZE_8BIT, buf, len, I2C_TIMEOUT_MS);
}

static uint8_t s_ism330_ok = 0U;
static uint8_t s_mcp9800_ok = 0U;

HAL_StatusTypeDef Sensors_Init(void)
{
    uint8_t err = 0U;
    /* ISM330DHCX: 104 Hz ODR, ±4 g accel, ±500 dps gyro */
    if (i2c_write(ISM330_ADDR, ISM330_CTRL1_XL, 0x48U) != HAL_OK) err = 1U;  /* ODR=104Hz FS=±4g  */
    if (i2c_write(ISM330_ADDR, ISM330_CTRL2_G,  0x44U) != HAL_OK) err = 1U;  /* ODR=104Hz FS=±500dps */
    /* MCP9800: 12-bit resolution, continuous conversion */
    if (i2c_write(MCP9800_ADDR, MCP9800_REG_CFG, MCP9800_CFG_12B) != HAL_OK) err = 1U;
    return err ? HAL_ERROR : HAL_OK;
}

HAL_StatusTypeDef Sensors_Transmit(void)
{
    uint8_t buf[6];
    CAN_TxHeaderTypeDef hdr = {0};
    uint32_t mailbox;
    uint8_t  data[8] = {0};
    uint8_t  can_err = 0U;

    hdr.RTR                = CAN_RTR_DATA;
    hdr.IDE                = CAN_ID_STD;
    hdr.TransmitGlobalTime = DISABLE;

    s_ism330_ok  = 0U;
    s_mcp9800_ok = 0U;

    /* --- IMU accelerometer (6 bytes, little-endian X/Y/Z) --- */
    if (i2c_read(ISM330_ADDR, ISM330_OUT_A, buf, 6) == HAL_OK) {
        memcpy(data, buf, 6);
        hdr.StdId = SENSOR_HUB_IMU_ACCEL_ID;
        hdr.DLC   = SENSOR_HUB_IMU_ACCEL_DLC;
        if (HAL_CAN_AddTxMessage(&hcan1, &hdr, data, &mailbox) != HAL_OK) { can_err = 1U; }
    }

    /* --- IMU gyroscope (6 bytes, little-endian X/Y/Z) --- */
    if (i2c_read(ISM330_ADDR, ISM330_OUT_G, buf, 6) == HAL_OK) {
        memcpy(data, buf, 6);
        hdr.StdId = SENSOR_HUB_IMU_GYRO_ID;
        hdr.DLC   = SENSOR_HUB_IMU_GYRO_DLC;
        if (HAL_CAN_AddTxMessage(&hcan1, &hdr, data, &mailbox) != HAL_OK) { can_err = 1U; }
    }

    /* --- IMU chip temperature --- */
    /* ISM330DHCX: 16-bit signed, 1°C = 256 LSB, 0 = 25°C */
    if (i2c_read(ISM330_ADDR, ISM330_OUT_TEMP, buf, 2) == HAL_OK) {
        s_ism330_ok = 1U;
        data[0] = buf[0];
        data[1] = buf[1];
    } else {
        data[0] = 0U;
        data[1] = 0U;
    }

    /* --- Ambient temperature (MCP9800) --- */
    /* MCP9800: 12-bit in upper bits of 16-bit register — right-shift to get signed 12-bit */
    if (i2c_read(MCP9800_ADDR, MCP9800_REG_T, buf, 2) == HAL_OK) {
        s_mcp9800_ok = 1U;
        int16_t ambient = (int16_t)((uint16_t)buf[0] << 8 | buf[1]) >> 4;
        data[2] = (uint8_t)(ambient & 0xFF);
        data[3] = (uint8_t)((ambient >> 8) & 0xFF);
    } else {
        data[2] = 0U;
        data[3] = 0U;
    }

    /* Send temp message if at least one temperature sensor responded */
    if (s_ism330_ok || s_mcp9800_ok) {
        hdr.StdId = SENSOR_HUB_TEMP_ID;
        hdr.DLC   = SENSOR_HUB_TEMP_DLC;
        if (HAL_CAN_AddTxMessage(&hcan1, &hdr, data, &mailbox) != HAL_OK) { can_err = 1U; }
    }

    return can_err ? HAL_ERROR : HAL_OK;
}

uint8_t Sensors_GetStatus(void)
{
    return (uint8_t)(s_ism330_ok | (s_mcp9800_ok << 1));
}
