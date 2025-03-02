# Python
import threading
import time
from lcd_driver import LCDDriver
from const import ILI9340, Colors
from gpio_handler import GPIOHandler
from spi_handler import SPIHandler, PrioritySPILock
from touch_handler import XPT2046

# Create a single shared priority lock
spi_lock = PrioritySPILock()


def update_display(lcd):
    while True:
        lcd.fill_screen(Colors.RED)
        time.sleep(1)
        lcd.fill_screen(Colors.BLUE)
        time.sleep(1)


def touch_callback(coords):
    print(f"Touch detected at: {coords}")


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
    touch = XPT2046(tp_cs=26, spi_handler=spi)
    lcd.init_display()

    # Set callback and start listening for touch events in callback style.
    touch.set_callback(touch_callback)
    touch.start_listening(interval=0.05)

    display_thread = threading.Thread(target=update_display, args=(lcd,), daemon=True)
    display_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
