# Python
import time
import RPi.GPIO as GPIO
import threading


class XPT2046:
    def __init__(
        self,
        tp_cs=26,
        spi_handler=None,
        screen_width=240,
        screen_height=320,
        x_min=300,
        x_max=3800,
        y_min=300,
        y_max=3800,
    ):
        self.spi = spi_handler.spi
        self.spi_handler = spi_handler
        self.spi_lock = spi_handler.spi_lock
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
        self.callback = None
        self.running = False

    def _read_adc(self, command):
        GPIO.output(self.tp_cs, GPIO.LOW)
        time.sleep(0.01)  # Increase delay as in the working example
        if self.spi_lock:
            with self.spi_lock.touch_lock():
                # Send command first, then read two bytes
                self.spi_handler.transfer([command])
                raw = self.spi_handler.transfer([0x00, 0x00])
        else:
            self.spi_handler.transfer([command])
            raw = self.spi_handler.transfer([0x00, 0x00])
        GPIO.output(self.tp_cs, GPIO.HIGH)
        # Combine the two bytes received into a 12-bit ADC value
        adc_val = ((raw[0] << 8) | raw[1]) >> 3
        print(f"ADC Value: {adc_val}")
        return adc_val

    def get_touch_coordinates(self):
        x = self._read_adc(0xD0)
        y = self._read_adc(0x90)
        if self.x_min < x < self.x_max and self.y_min < y < self.y_max:
            screen_x = int(
                self.map_value(x, self.x_min, self.x_max, self.screen_width, 0)
            )
            screen_y = int(
                self.map_value(y, self.y_min, self.y_max, 0, self.screen_height)
            )
            return screen_x, screen_y
        return None

    def map_value(self, value, from_min, from_max, to_min, to_max):
        return to_min + (to_max - to_min) * (value - from_min) / (from_max - from_min)

    def set_callback(self, callback):
        self.callback = callback

    def start_listening(self, interval=0.05):
        self.running = True
        threading.Thread(
            target=self._listen_loop, args=(interval,), daemon=True
        ).start()

    def stop_listening(self):
        self.running = False

    def _listen_loop(self, interval):
        while self.running:
            coords = self.get_touch_coordinates()
            if coords and self.callback:
                self.callback(coords)
            time.sleep(interval)
