# Python
import time
from spi_handler import SPIHandler
from gpio_handler import GPIOHandler
from PIL import Image
import numpy as np
import RPi.GPIO as GPIO
from const import ILI9340


def rgb2RGB565(r, g, b):
    return ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)


class LCDDriver:
    def __init__(
        self,
        gpio_handler: GPIOHandler = None,
        spi_handler: SPIHandler = None,
        commands=None,
        width: int = 240,
        height: int = 320,
        spi_lock=None,
    ):
        self.width = width
        self.height = height
        self.spi = spi_handler
        self.gpio = gpio_handler
        self.commands = commands
        self.spi_lock = spi_lock
        self.LCD_RS = self.gpio.rs_pin
        self.LCD_CS = self.gpio.cs_pin
        self.LCD_RST = self.gpio.rst_pin

    def send_command(self, cmd):
        self.gpio.set_pin(self.LCD_RS, GPIO.LOW)  # Command Mode
        self.gpio.set_pin(self.LCD_CS, GPIO.LOW)
        if self.spi_lock:
            with self.spi_lock.display_lock():
                self.spi.transfer([cmd])
        else:
            self.spi.transfer([cmd])
        self.gpio.set_pin(self.LCD_CS, GPIO.HIGH)

    def send_data(self, data):
        self.gpio.set_pin(self.LCD_RS, GPIO.HIGH)  # Data Mode
        self.gpio.set_pin(self.LCD_CS, GPIO.LOW)
        if self.spi_lock:
            with self.spi_lock.display_lock():
                if isinstance(data, list):
                    self.spi.transfer(data)
                else:
                    self.spi.transfer([data])
        else:
            if isinstance(data, list):
                self.spi.transfer(data)
            else:
                self.spi.transfer([data])
        self.gpio.set_pin(self.LCD_CS, GPIO.HIGH)

    # ... (rest of the file remains unchanged)
