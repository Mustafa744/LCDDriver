# from DisplayHandler import DisplayHandler
# from gpio_handler import GPIOHandler
# from spi_handler import SPIHandler
# from const import ILI9340, Colors
# import time

# gpio = GPIOHandler()
# spi = SPIHandler()
# display = DisplayHandler(gpio_handler=gpio, spi_handler=spi, commands=ILI9340)

# if __name__ == "__main__":
#     display.init_display()
#     time.sleep(0.1)
#     display.fill_screen(Colors.RED)
from gpio_handler import GPIOHandler
from spi_handler import SPIHandler
from const import ILI9340, Colors
import time
import RPi.GPIO as GPIO

gpio = GPIOHandler()
spi = SPIHandler()

# Reset display
gpio.set_pin(gpio.rst_pin, GPIO.LOW)
time.sleep(0.1)
gpio.set_pin(gpio.rst_pin, GPIO.HIGH)
time.sleep(0.1)


def send_command(cmd):
    gpio.set_pin(gpio.rs_pin, GPIO.LOW)  # Command mode
    gpio.set_pin(gpio.cs_pin, GPIO.LOW)
    spi.write([cmd])
    gpio.set_pin(gpio.cs_pin, GPIO.HIGH)


def send_data(data):
    gpio.set_pin(gpio.rs_pin, GPIO.HIGH)  # Data mode
    gpio.set_pin(gpio.cs_pin, GPIO.LOW)
    if isinstance(data, list):
        spi.write(data)
    else:
        spi.write([data])
    gpio.set_pin(gpio.cs_pin, GPIO.HIGH)


# Initialize display
send_command(ILI9340.CMD_SWRESET)
time.sleep(0.1)
send_command(ILI9340.CMD_SLPOUT)
time.sleep(0.1)
send_command(ILI9340.CMD_COLMOD)
send_command(ILI9340.CMD_MADCTL)
send_data(0xC0)
send_command(ILI9340.CMD_DISPON)
time.sleep(0.1)
send_command(ILI9340.CMD_COLMOD)
send_data(0x55)
time.sleep(0.1)

# Fill screen with red
send_command(ILI9340.CMD_CASET)
send_data([0x00, 0x00, 0x00, 0xEF])  # Column address set
send_command(ILI9340.CMD_RASET)
send_data([0x00, 0x00, 0x01, 0x3F])  # Row address set
send_command(ILI9340.CMD_RAMWR)

# Create red color bytes (high byte, low byte pattern)
high_byte = (Colors.RED >> 8) & 0xFF  # Should be 0xF8 for red
low_byte = Colors.RED & 0xFF  # Should be 0x00 for red
pixels = [high_byte, low_byte] * (240 * 320)  # Fill entire screen

# Send in chunks
chunk_size = 4096
for i in range(0, len(pixels), chunk_size):
    send_data(pixels[i : i + chunk_size])
