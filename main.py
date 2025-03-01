# Python
import threading
import time
from lcd_driver import LCDDriver
from const import ILI9340, Colors
from gpio_handler import GPIOHandler
from spi_handler import SPIHandler, PrioritySPILock
from touch_handler import XPT2046

# Use the custom priority lock
spi_lock = PrioritySPILock()


def update_display(lcd):
    while True:
        with spi_lock.display_lock():
            lcd.fill_screen(Colors.RED)
        time.sleep(0.5)
        with spi_lock.display_lock():
            lcd.fill_screen(Colors.BLUE)
        time.sleep(0.5)


def read_touch(touch):
    while True:
        with spi_lock.touch_lock():
            pos = touch.get_touch_coordinates()
        if pos:
            print(f"Touch detected at: {pos}")
        time.sleep(0.01)


if __name__ == "__main__":
    gpio = GPIOHandler()
    spi = SPIHandler(speed=32000000, spi_lock=spi_lock)
    lcd = LCDDriver(
        gpio_handler=gpio,
        spi_handler=spi,
        commands=ILI9340,
        width=240,
        height=320,
    )
    touch = XPT2046(tp_cs=26, spi=spi)
    lcd.init_display()

    display_thread = threading.Thread(target=update_display, args=(lcd,), daemon=True)
    touch_thread = threading.Thread(target=read_touch, args=(touch,), daemon=True)

    display_thread.start()
    touch_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
