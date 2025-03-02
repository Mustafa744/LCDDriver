from DisplayHandler import DisplayHandler
from gpio_handler import GPIOHandler
from spi_handler import SPIHandler
from const import ILI9340, Colors
import time

gpio = GPIOHandler()
spi = SPIHandler()
display = DisplayHandler(gpio_handler=gpio, spi_handler=spi, commands=ILI9340)

if __name__ == "__main__":
    display.init_display()
    time.sleep(0.1)
    display.reset_display()
    time.sleep(0.1)
    display.fill_screen(Colors.RED)
