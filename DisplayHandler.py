import time
import RPi.GPIO as GPIO


class DisplayHandler:
    def __init__(self, gpio_handler, spi_handler, commands):
        self.gpio = gpio_handler
        self.spi = spi_handler
        self.commands = commands

        # Pin definitions
        self.LCD_RS = self.gpio.rs_pin
        self.LCD_CS = self.gpio.cs_pin
        self.LCD_RST = self.gpio.rst_pin

        # Display dimensions
        self.width = 240
        self.height = 320

        # Lock from SPI handler if present
        self.spi_lock = getattr(self.spi, "spi_lock", None)

    def send_command(self, cmd):
        """Send a command to the display."""
        self.gpio.set_pin(self.LCD_RS, GPIO.LOW)  # Command mode
        self.gpio.set_pin(self.LCD_CS, GPIO.LOW)
        self.spi.write([cmd])
        self.gpio.set_pin(self.LCD_CS, GPIO.HIGH)

    def send_data(self, data):
        """Send data to the display."""
        self.gpio.set_pin(self.LCD_RS, GPIO.HIGH)  # Data mode
        self.gpio.set_pin(self.LCD_CS, GPIO.LOW)

        if isinstance(data, list):
            self.spi.write(data)
        else:
            self.spi.write([data])

        self.gpio.set_pin(self.LCD_CS, GPIO.HIGH)

    def init_display(self):
        """Initialize the display with required settings."""
        # Reset display first
        self.gpio.set_pin(self.LCD_RST, GPIO.LOW)
        time.sleep(0.1)
        self.gpio.set_pin(self.LCD_RST, GPIO.HIGH)
        time.sleep(0.1)

        # Software reset
        self.send_command(self.commands.CMD_SWRESET)
        time.sleep(0.1)

        # Exit sleep mode
        self.send_command(self.commands.CMD_SLPOUT)
        time.sleep(0.1)

        # Set color mode
        self.send_command(self.commands.CMD_COLMOD)

        # Set memory access control
        self.send_command(self.commands.CMD_MADCTL)
        self.send_data(0xC0)  # Match the working configuration

        # Turn on display
        self.send_command(self.commands.CMD_DISPON)
        time.sleep(0.1)

        # Set color mode to 16-bit (565 RGB)
        self.send_command(self.commands.CMD_COLMOD)
        self.send_data(0x55)  # 16-bit color
        time.sleep(0.1)

    def set_address_window(self, x0, y0, x1, y1):
        """Set the address window for drawing."""
        # Column address set
        self.send_command(self.commands.CMD_CASET)
        self.send_data([0x00, x0, 0x00, x1])  # Start and end column

        # Row address set
        self.send_command(self.commands.CMD_RASET)
        self.send_data([0x00, y0, 0x00, y1])  # Start and end row

        # Write to RAM
        self.send_command(self.commands.CMD_RAMWR)

    def fill_screen(self, color):
        """Fill the entire screen with a single color."""
        # Set address window to entire screen
        self.send_command(self.commands.CMD_CASET)
        self.send_data([0x00, 0x00, 0x00, 0xEF])  # Column address set (0-239)

        self.send_command(self.commands.CMD_RASET)
        self.send_data([0x00, 0x00, 0x01, 0x3F])  # Row address set (0-319)

        self.send_command(self.commands.CMD_RAMWR)

        # Create color bytes (high byte, low byte pattern)
        high_byte = (color >> 8) & 0xFF
        low_byte = color & 0xFF

        # Calculate pixel count for entire screen
        pixels = [high_byte, low_byte] * (self.width * self.height)

        # Send in chunks to avoid buffer issues
        chunk_size = 4096
        for i in range(0, len(pixels), chunk_size):
            self.send_data(pixels[i : i + chunk_size])

    def draw_pixel(self, x, y, color):
        """Draw a single pixel at the specified position."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return  # Out of bounds

        # Set address window to the pixel
        self.set_address_window(x, y, x, y)

        # Send color
        high_byte = (color >> 8) & 0xFF
        low_byte = color & 0xFF
        self.send_data([high_byte, low_byte])
