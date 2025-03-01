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
    ):
        self.width = width
        self.height = height
        self.spi = spi_handler
        self.gpio = gpio_handler
        self.commands = commands
        self.LCD_RS = self.gpio.rs_pin
        self.LCD_CS = self.gpio.cs_pin
        self.LCD_RST = self.gpio.rst_pin
        self.spi_lock = spi_handler.spi_lock

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
        self.send_data(0x55)  # Use 0x56 for BGR565 instead of 0x55
        self.send_command(ILI9340.CMD_COLMOD)

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

        n_pixels = self.width * self.height
        high_byte = (color >> 8) & 0xFF
        low_byte = color & 0xFF

        # Create a NumPy array with interleaved high and low bytes
        pixel_bytes = np.empty(n_pixels * 2, dtype=np.uint8)
        pixel_bytes[0::2] = high_byte
        pixel_bytes[1::2] = low_byte

        data_list = pixel_bytes.tolist()

        # Send pixel data in chunks (SPI buffer limit)
        chunk_size = 4096
        for i in range(0, len(data_list), chunk_size):
            self.send_data(data_list[i : i + chunk_size])

    def fill_rectangle(self, x0, y0, x1, y1, color):
        self.set_address_window(x0, y0, x1, y1)

        width = x1 - x0 + 1
        height = y1 - y0 + 1
        pixel_data = [color >> 8, color & 0xFF] * (width * height)

        # Send pixel data in chunks (SPI buffer limit)
        chunk_size = 4096
        for i in range(0, len(pixel_data), chunk_size):
            self.send_data(pixel_data[i : i + chunk_size])

    def plot_image(self, x0, y0, x1, y1, image_path):
        print("Plotting image...")
        # Open the image and convert to RGB
        image = Image.open(image_path).convert("RGB")

        # Resize the image to fit the specified window
        image = image.resize((x1 - x0 + 1, y1 - y0 + 1))

        # Rotate the image 180 degrees
        image = image.rotate(180)

        # Convert image to a NumPy array
        pixel_data = np.array(image)

        # Vectorized conversion to RGB565 with swapped red and blue channels:
        # (r, g, b) -> ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)
        r = pixel_data[:, :, 0]
        g = pixel_data[:, :, 1]
        b = pixel_data[:, :, 2]
        rgb565 = (
            (((b & 0xF8).astype(np.uint16)) << 8)
            | (((g & 0xFC).astype(np.uint16)) << 3)
            | ((r >> 3).astype(np.uint16))
        )

        # Split the 16-bit RGB565 value into high and low bytes
        high_bytes = (rgb565 >> 8) & 0xFF
        low_bytes = rgb565 & 0xFF

        # Interleave the high and low bytes
        pixel_bytes = np.empty(rgb565.size * 2, dtype=np.uint8)
        pixel_bytes[0::2] = high_bytes.flatten()
        pixel_bytes[1::2] = low_bytes.flatten()
        data_list = pixel_bytes.tolist()

        self.set_address_window(x0, y0, x1, y1)

        # Send the data in chunks (SPI buffer limit)
        chunk_size = 4096
        for i in range(0, len(data_list), chunk_size):
            self.send_data(data_list[i : i + chunk_size])

        print("Image plotted successfully!")

    def cleanup(self):
        self.spi.close()
        self.gpio.cleanup()
