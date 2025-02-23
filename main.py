from lcd_driver import LCDDriver
from const import ILI9340, Colors
from gpio_handler import GPIOHandler
from spi_handler import SPIHandler
from touch_handler import XPT2046
import time

# Main
if __name__ == "__main__":
    # Initialize GPIO and SPI

    gpio = GPIOHandler()
    spi = SPIHandler(speed=32000000)
    lcd = LCDDriver(
        gpio_handler=gpio, spi_handler=spi, commands=ILI9340, width=240, height=320
    )
    touch = XPT2046(spi, cs_pin=7, irq_pin=17)
    lcd.init_display()

    # TRY DIFFERENT PIXEL FORMATS
    lcd.send_command(ILI9340.CMD_COLMOD)
    lcd.send_data(0x55)  # Try 0x56 if 0x55 does not work

    # TRY DIFFERENT ROTATION VALUES
    lcd.send_command(ILI9340.CMD_MADCTL)
    lcd.send_data(0x00)  # Try other values like 0x08, 0xC8, 0x48

    # # draw france flag
    # lcd.fill_screen(Colors.WHITE)  # Test with a different red format
    # time.sleep(0.2)
    # lcd.fill_rectangle(0, 0, 240, 106, Colors.BLUE)  # Fill a rectangle with blue
    # time.sleep(0.2)
    # lcd.fill_rectangle(0, 212, 240, 320, Colors.RED)  # Fill a rectangle with blue
    # time.sleep(0.5)

    # plot the image
    lcd.fill_screen(Colors.WHITE)
    lcd.plot_image(0, 0, 239, 320, "shakal.jpg")
    # while True:
    #     touch_val = touch.get_touch()
    #     if touch_val is not None:
    #         print(touch_val)
    # lcd.cleanup()
