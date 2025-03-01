import threading
import time
from lcd_driver import LCDDriver
from const import ILI9340, Colors
from gpio_handler import GPIOHandler
from spi_handler import SPIHandler
from touch_handler import XPT2046

# Create a global lock for SPI operations
spi_lock = threading.Lock()


def update_display(lcd):
    while True:
        with spi_lock:
            lcd.fill_screen(Colors.RED)
        time.sleep(0.5)
        with spi_lock:
            lcd.fill_screen(Colors.BLUE)
        time.sleep(0.5)


def read_touch(touch):
    while True:
        with spi_lock:
            pos = touch.get_touch_coordinates()
        if pos:
            print(f"Touch detected at: {pos}")
        time.sleep(0.01)


if __name__ == "__main__":
    gpio = GPIOHandler()
    spi = SPIHandler(speed=32000000)
    lcd = LCDDriver(
        gpio_handler=gpio,
        spi_handler=spi,
        commands=ILI9340,
        width=240,
        height=320,
        # Passing the SPI lock if needed within the driver
        spi_lock=spi_lock,
    )
    touch = XPT2046(tp_cs=26, spi=spi, spi_lock=spi_lock)
    lcd.init_display()

    # Create threads for display update and touch reading
    display_thread = threading.Thread(target=update_display, args=(lcd,), daemon=True)
    touch_thread = threading.Thread(target=read_touch, args=(touch,), daemon=True)

    display_thread.start()
    touch_thread.start()

    # Keep the main thread alive.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
