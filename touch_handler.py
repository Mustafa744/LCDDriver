# Python
import time
import RPi.GPIO as GPIO
import spidev


class XPT2046:
    def __init__(
        self,
        tp_cs=26,
        spi=None,
        screen_width=240,
        screen_height=320,
        x_min=300,
        x_max=3800,
        y_min=300,
        y_max=3800,
    ):
        self.spi = spi.spi
        self.spi_lock = self.spi_lock
        self.tp_cs = tp_cs
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.tp_cs, GPIO.OUT)
        GPIO.output(self.tp_cs, GPIO.HIGH)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

    def _read_adc(self, command):
        GPIO.output(self.tp_cs, GPIO.LOW)
        time.sleep(0.01)
        if self.spi_lock:
            with self.spi_lock.touch_lock():
                self.spi.xfer2([command])
                raw = self.spi.xfer2([0x00, 0x00])
        else:
            self.spi.xfer2([command])
            raw = self.spi.xfer2([0x00, 0x00])
        GPIO.output(self.tp_cs, GPIO.HIGH)
        adc_val = ((raw[0] << 8) | raw[1]) >> 3
        return adc_val

    def read_touch(self):
        x_adc = self._read_adc(0xD0)
        y_adc = self._read_adc(0x90)
        return x_adc, y_adc

    def map_value(self, value, from_min, from_max, to_min, to_max):
        return to_min + (to_max - to_min) * (value - from_min) / (from_max - from_min)

    def get_touch_coordinates(self):
        x, y = self.read_touch()
        if self.x_min < x < self.x_max and self.y_min < y < self.y_max:
            screen_x = int(
                self.map_value(x, self.x_min, self.x_max, self.screen_width, 0)
            )
            screen_y = int(
                self.map_value(y, self.y_min, self.y_max, 0, self.screen_height)
            )
            return screen_x, screen_y
        return None
