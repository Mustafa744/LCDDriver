import spidev
import time
import RPi.GPIO as GPIO

# GPIO Pin Definitions
LCD_CS = 8  # Chip Select
LCD_RS = 22  # Command/Data (DC)
LCD_RST = 27  # Reset

# SPI Configuration
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 10000000  # 10MHz for fast updates

# Corrected Display Parameters (Swapped Width & Height)
LCD_WIDTH = 240  # Your display is rotated
LCD_HEIGHT = 320  # Swapped to match full-screen

# ILI9340 / ILI9341 Commands
CMD_SWRESET = 0x01  # Software Reset
CMD_SLPOUT = 0x11  # Sleep Out
CMD_DISPON = 0x29  # Display On
CMD_CASET = 0x2A  # Column Address Set
CMD_RASET = 0x2B  # Row Address Set
CMD_RAMWR = 0x2C  # Write to Memory
CMD_COLMOD = 0x3A  # Set Pixel Format
CMD_MADCTL = 0x36  # Memory Access Control


# colors
RED = 0x001F
GREEN = 0x07E0
BLUE = 0xF800
WHITE = 0xFFFF
BLACK = 0x0000
# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LCD_CS, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(LCD_RS, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(LCD_RST, GPIO.OUT, initial=GPIO.HIGH)

# SPI Initialization
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = SPI_SPEED


# Send Command
def send_command(cmd):
    GPIO.output(LCD_RS, GPIO.LOW)  # Command Mode
    GPIO.output(LCD_CS, GPIO.LOW)
    spi.xfer2([cmd])
    GPIO.output(LCD_CS, GPIO.HIGH)


# Send Data
def send_data(data):
    GPIO.output(LCD_RS, GPIO.HIGH)  # Data Mode
    GPIO.output(LCD_CS, GPIO.LOW)
    if isinstance(data, list):
        spi.xfer2(data)
    else:
        spi.xfer2([data])
    GPIO.output(LCD_CS, GPIO.HIGH)


# Reset the Display
def reset_display():
    GPIO.output(LCD_RST, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(LCD_RST, GPIO.HIGH)
    time.sleep(0.1)


# Initialize Display
def init_display():
    reset_display()

    send_command(CMD_SWRESET)  # Software Reset
    time.sleep(0.1)

    send_command(CMD_SLPOUT)  # Sleep Out
    time.sleep(0.1)

    send_command(CMD_COLMOD)  # Set Pixel Format to 16-bit (BGR565)
    send_data(0x56)  # Use 0x56 for BGR565 instead of 0x55

    send_command(CMD_MADCTL)  # Memory Access Control (Rotation Fix)
    send_data(0xC0)  # Corrected orientation

    send_command(CMD_DISPON)  # Display On
    time.sleep(0.1)


# Set Address Window
def set_address_window(x0, y0, x1, y1):
    send_command(CMD_CASET)  # Column Address Set
    send_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])

    send_command(CMD_RASET)  # Row Address Set
    send_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])

    send_command(CMD_RAMWR)  # Prepare for pixel data


# Fill Screen with a Color
def fill_screen(color):
    set_address_window(0, 0, LCD_WIDTH - 1, LCD_HEIGHT - 1)

    pixel_data = [color >> 8, color & 0xFF] * (LCD_WIDTH * LCD_HEIGHT)

    # Send pixel data in chunks (SPI buffer limit)
    chunk_size = 4096
    for i in range(0, len(pixel_data), chunk_size):
        send_data(pixel_data[i : i + chunk_size])


def fill_rectangle(x0, y0, x1, y1, color):
    set_address_window(x0, y0, x1, y1)

    width = x1 - x0 + 1
    height = y1 - y0 + 1
    pixel_data = [color >> 8, color & 0xFF] * (width * height)

    # Send pixel data in chunks (SPI buffer limit)
    chunk_size = 4096
    for i in range(0, len(pixel_data), chunk_size):
        send_data(pixel_data[i : i + chunk_size])


# Main
if __name__ == "__main__":
    init_display()

    # TRY DIFFERENT PIXEL FORMATS
    send_command(CMD_COLMOD)
    send_data(0x55)  # Try 0x56 if 0x55 does not work

    # TRY DIFFERENT ROTATION VALUES
    send_command(CMD_MADCTL)
    send_data(0x00)  # Try other values like 0x08, 0xC8, 0x48

    fill_screen(GREEN)  # Test with a different red format
    time.sleep(1)
    fill_rectangle(70, 110, 190, 230, RED)  # Fill a rectangle with red
