#include "sensors.h"
#include "sensor_hub.h"
#include "i2c.h"
#include "can.h"

/* ISM330DHCX — 7-bit address 0x6A (SA0 pin low) */
#define ISM330_ADDR     (0x6A << 1)
#define ISM330_CTRL1_XL 0x10U  /* accelerometer control */
#define ISM330_CTRL2_G  0x11U  /* gyroscope control */
#define ISM330_OUT_TEMP 0x20U  /* temperature output (2 bytes) */
#define ISM330_OUT_G    0x22U  /* gyroscope output (6 bytes, X/Y/Z) */
#define ISM330_OUT_A    0x28U  /* accelerometer output (6 bytes, X/Y/Z) */

/* MCP9800 — 7-bit address 0x48 (all address pins low) */
#define MCP9800_ADDR    (0x48 << 1)
#define MCP9800_REG_T   0x00U  /* temperature register */
#define MCP9800_REG_CFG 0x01U  /* configuration register */
#define MCP9800_CFG_12B 0x60U  /* 12-bit resolution, continuous */

static void i2c_write(uint8_t dev, uint8_t reg, uint8_t val)
{
    HAL_I2C_Mem_Write(&hi2c1, dev, reg, I2C_MEMADD_SIZE_8BIT, &val, 1, HAL_MAX_DELAY);
}

static void i2c_read(uint8_t dev, uint8_t reg, uint8_t *buf, uint16_t len)
{
    HAL_I2C_Mem_Read(&hi2c1, dev, reg, I2C_MEMADD_SIZE_8BIT, buf, len, HAL_MAX_DELAY);
}

void Sensors_Init(void)
{
    /* ISM330DHCX: 104 Hz ODR, ±4 g accel, ±500 dps gyro */
    i2c_write(ISM330_ADDR, ISM330_CTRL1_XL, 0x48U);  /* ODR=104Hz FS=±4g  */
    i2c_write(ISM330_ADDR, ISM330_CTRL2_G,  0x44U);  /* ODR=104Hz FS=±500dps */

    /* MCP9800: 12-bit resolution, continuous conversion */
    i2c_write(MCP9800_ADDR, MCP9800_REG_CFG, MCP9800_CFG_12B);
}

void Sensors_Transmit(void)
{
    uint8_t buf[6];
    CAN_TxHeaderTypeDef hdr = {0};
    uint32_t mailbox;
    uint8_t  data[8] = {0};

    hdr.RTR                = CAN_RTR_DATA;
    hdr.IDE                = CAN_ID_STD;
    hdr.TransmitGlobalTime = DISABLE;

    /* --- IMU accelerometer (6 bytes, little-endian X/Y/Z) --- */
    i2c_read(ISM330_ADDR, ISM330_OUT_A, buf, 6);
    data[0] = buf[0]; data[1] = buf[1];  /* ACCEL_X */
    data[2] = buf[2]; data[3] = buf[3];  /* ACCEL_Y */
    data[4] = buf[4]; data[5] = buf[5];  /* ACCEL_Z */
    hdr.StdId = SENSOR_HUB_IMU_ACCEL_ID;
    hdr.DLC   = SENSOR_HUB_IMU_ACCEL_DLC;
    HAL_CAN_AddTxMessage(&hcan1, &hdr, data, &mailbox);

    /* --- IMU gyroscope (6 bytes, little-endian X/Y/Z) --- */
    i2c_read(ISM330_ADDR, ISM330_OUT_G, buf, 6);
    data[0] = buf[0]; data[1] = buf[1];  /* GYRO_X */
    data[2] = buf[2]; data[3] = buf[3];  /* GYRO_Y */
    data[4] = buf[4]; data[5] = buf[5];  /* GYRO_Z */
    hdr.StdId = SENSOR_HUB_IMU_GYRO_ID;
    hdr.DLC   = SENSOR_HUB_IMU_GYRO_DLC;
    HAL_CAN_AddTxMessage(&hcan1, &hdr, data, &mailbox);

    /* --- Combined temperature (IMU chip temp + ambient) --- */
    /* ISM330DHCX: 16-bit signed, 1°C = 256 LSB, 0 = 25°C */
    i2c_read(ISM330_ADDR, ISM330_OUT_TEMP, buf, 2);
    data[0] = buf[0];
    data[1] = buf[1];

    /* MCP9800: 12-bit in upper bits of 16-bit register — right-shift to get signed 12-bit */
    i2c_read(MCP9800_ADDR, MCP9800_REG_T, buf, 2);
    int16_t ambient = (int16_t)((uint16_t)buf[0] << 8 | buf[1]) >> 4;
    data[2] = (uint8_t)(ambient & 0xFF);
    data[3] = (uint8_t)((ambient >> 8) & 0xFF);

    hdr.StdId = SENSOR_HUB_TEMP_ID;
    hdr.DLC   = SENSOR_HUB_TEMP_DLC;
    HAL_CAN_AddTxMessage(&hcan1, &hdr, data, &mailbox);
}
