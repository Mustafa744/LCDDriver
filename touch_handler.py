import time
import RPi.GPIO as GPIO


class XPT2046:
    def __init__(
        self,
        spi_handler,
        cs_pin,
        irq_pin=None,
        cal_x=1.0,
        cal_y=1.0,
        offset_x=0,
        offset_y=0,
    ):
        self.spi = spi_handler
        self.cs_pin = cs_pin
        self.irq_pin = irq_pin
        self.cal_x = cal_x
        self.cal_y = cal_y
        self.offset_x = offset_x
        self.offset_y = offset_y

        # Setup chip-select pin
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.output(self.cs_pin, GPIO.HIGH)
        # Optionally setup IRQ pin for interrupt-driven touch detection
        if self.irq_pin is not None:
            GPIO.setup(self.irq_pin, GPIO.IN)

    def _read_adc(self, command):
        # Send command and read 3 bytes.
        # The ADC returns a 12-bit result left-aligned in the 16-bit data, so shift appropriately.
        response = self.spi.transfer([command, 0x00, 0x00])
        # Combine bytes: response[1] is the high byte, response[2] is the low.
        adc_val = ((response[1] << 8) | response[2]) >> 3  # 12-bit result
        return adc_val

    def get_touch(self):
        # Check IRQ (if provided) to see if the screen is being touched.
        if self.irq_pin is not None and GPIO.input(self.irq_pin):
            return None  # No touch detected

        GPIO.output(self.cs_pin, GPIO.LOW)
        time.sleep(0.001)  # Small delay

        # Read X and Y channels.
        # Command bytes: for X, use 0xD0; for Y, use 0x90.
        x_adc = self._read_adc(0xD0)
        y_adc = self._read_adc(0x90)

        GPIO.output(self.cs_pin, GPIO.HIGH)

        # Apply calibration and offsets if needed.
        x = int(x_adc * self.cal_x) + self.offset_x
        y = int(y_adc * self.cal_y) + self.offset_y

        return (x, y)
