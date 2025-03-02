# Python
import time
from test_spi import SPIHandler
from ..gpio_handler import GPIOHandler
from ..const import ILI9340

# Create handlers
spi = SPIHandler()
gpio = GPIOHandler()

# Reset display
gpio.set_pin(gpio.rst_pin, 0)
time.sleep(0.1)
gpio.set_pin(gpio.rst_pin, 1)
time.sleep(0.1)


# Helper to send a command or data
def send_command(cmd):
    gpio.set_pin(gpio.rs_pin, 0)  # Command mode
    gpio.set_pin(gpio.cs_pin, 0)
    spi.write([cmd])
    gpio.set_pin(gpio.cs_pin, 1)


def send_data(data):
    gpio.set_pin(gpio.rs_pin, 1)  # Data mode
    gpio.set_pin(gpio.cs_pin, 0)
    if isinstance(data, list):
        spi.write(data)
    else:
        spi.write([data])
    gpio.set_pin(gpio.cs_pin, 1)


# Send Software Reset
send_command(ILI9340.CMD_SWRESET)
time.sleep(0.1)

# Sleep Out
send_command(ILI9340.CMD_SLPOUT)
time.sleep(0.1)

# Set Pixel Format
send_command(ILI9340.CMD_COLMOD)

# Memory Access Control
send_command(ILI9340.CMD_MADCTL)
send_data(0xC0)

# Display ON
send_command(ILI9340.CMD_DISPON)
time.sleep(0.1)

# (Optional) Send another Pixel Format command with data
send_command(ILI9340.CMD_COLMOD)
send_data(0x55)
time.sleep(0.1)
