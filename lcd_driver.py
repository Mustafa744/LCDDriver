import time
from spi_handler import SPIHandler
from gpio_handler import GPIOHandler
import RPi.GPIO as GPIO


class LCDDriver:
    def __init__(
        self,
        gpio_handler: GPIOHandler = None,
        spi_handler: SPIHandler = None,
        commands=None,
        width: int = 240,
        height: int = 320,
    ):
        self.width = width
        self.height = height

        self.spi = spi_handler
        self.gpio = gpio_handler
        self.commands = commands
        # get gpio pins
        self.LCD_RS = self.gpio.rs_pin
        self.LCD_CS = self.gpio.cs_pin
        self.LCD_RST = self.gpio.rst_pin

    def send_command(self, cmd):
        self.gpio.set_pin(self.LCD_RS, GPIO.LOW)
        self.gpio.set_pin(self.LCD_RS, GPIO.LOW)  # Command Mode
        self.gpio.set_pin(self.LCD_CS, GPIO.LOW)
        self.spi.transfer([cmd])
        self.gpio.set_pin(self.LCD_CS, GPIO.HIGH)

    def send_data(self, data):
        self.gpio.set_pin(self.LCD_RS, GPIO.HIGH)  # Data Mode
        self.gpio.set_pin(self.LCD_CS, GPIO.LOW)
        if isinstance(data, list):
            self.spi.transfer(data)
        else:
            self.spi.transfer([data])
        self.gpio.set_pin(self.LCD_CS, GPIO.HIGH)

    def reset_display(self):
        self.gpio.set_pin(self.LCD_RST, GPIO.LOW)
        time.sleep(0.1)
        self.gpio.set_pin(self.LCD_RST, GPIO.HIGH)
        time.sleep(0.1)

    def init_display(self):
        self.reset_display()

        self.send_command(self.commands.CMD_SWRESET)  # Software Reset
        time.sleep(0.1)

        self.send_command(self.commands.CMD_SLPOUT)  # Sleep Out
        time.sleep(0.1)

        self.send_command(
            self.commands.CMD_COLMOD
        )  # Set Pixel Format to 16-bit (BGR565)
        self.send_data(0x56)  # Use 0x56 for BGR565 instead of 0x55

        self.send_command(
            self.commands.CMD_MADCTL
        )  # Memory Access Control (Rotation Fix)
        self.send_data(0xC0)  # Corrected orientation

        self.send_command(self.commands.CMD_DISPON)  # Display On
        time.sleep(0.1)

    def set_address_window(self, x0, y0, x1, y1):
        self.send_command(self.commands.CMD_CASET)  # Column Address Set
        self.send_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])

        self.send_command(self.commands.CMD_RASET)  # Row Address Set
        self.send_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])

        self.send_command(self.commands.CMD_RAMWR)  # Prepare for pixel data

    def fill_screen(self, color):
        self.set_address_window(0, 0, self.width - 1, self.height - 1)

        pixel_data = [color >> 8, color & 0xFF] * (self.width * self.height)

        # Send pixel data in chunks (SPI buffer limit)
        chunk_size = 4096
        for i in range(0, len(pixel_data), chunk_size):
            self.send_data(pixel_data[i : i + chunk_size])

    def fill_rectangle(self, x0, y0, x1, y1, color):
        self.set_address_window(x0, y0, x1, y1)

        width = x1 - x0 + 1
        height = y1 - y0 + 1
        pixel_data = [color >> 8, color & 0xFF] * (width * height)

        # Send pixel data in chunks (SPI buffer limit)
        chunk_size = 4096
        for i in range(0, len(pixel_data), chunk_size):
            self.send_data(pixel_data[i : i + chunk_size])

    def cleanup(self):
        self.spi.close()
        self.gpio.cleanup()
