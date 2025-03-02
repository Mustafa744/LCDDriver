import RPi.GPIO as GPIO

# GPIO Pin Definitions
LCD_CS = 8  # Chip Select
LCD_RS = 22  # Command/Data (DC)
LCD_RST = 27  # Reset


class GPIOHandler:
    def __init__(
        self,
        cs_pin=LCD_CS,
        rs_pin=LCD_RS,
        rst_pin=LCD_RST,
    ):
        self.cs_pin = cs_pin
        self.rs_pin = rs_pin
        self.rst_pin = rst_pin

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.cs_pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.rs_pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.rst_pin, GPIO.OUT, initial=GPIO.HIGH)

    def set_pin(self, pin, value):
        GPIO.output(pin, value)

    def cleanup(self):
        GPIO.cleanup()
