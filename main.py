from DisplayHandler import DisplayHandler
from GpioHandler import GPIOHandler
from SPIHandler import SPIHandler
from touch_handler import XPT2046
from const import ILI9340, Colors
import time
import signal
import sys

# Initialize handlers
gpio = GPIOHandler()
spi = SPIHandler()
display = DisplayHandler(gpio_handler=gpio, spi_handler=spi, commands=ILI9340)


# Define the touch callback function
def on_touch(coordinates):
    x, y = coordinates
    print(f"Touch detected at X={x}, Y={y}")

    # Draw a small white dot at the touch location
    original_color = None
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            nx, ny = x + dx, y + dy
            if 0 <= nx < display.width and 0 <= ny < display.height:
                display.draw_pixel(nx, ny, Colors.BLUE)


# Initialize touch controller
touch = XPT2046(
    tp_cs=18,  # Touch controller CS pin
    tp_irq=17,  # Touch controller IRQ pin
    spi_handler=spi,  # Reuse the same SPI handler
    screen_width=240,  # Display width
    screen_height=320,  # Display height
    # You may need to calibrate these values for your specific screen
    x_min=150,
    x_max=3900,
    y_min=150,
    y_max=3900,
)


# Set up clean exit
def cleanup(signum=None, frame=None):
    print("Cleaning up...")
    touch.stop_listening()
    gpio.cleanup()
    spi.close()
    print("Done.")
    sys.exit(0)


# Register signal handlers for clean exit
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

if __name__ == "__main__":
    # Initialize display
    display.init_display()
    time.sleep(0.1)

    # Fill screen with a color
    display.fill_screen(Colors.GREEN)
    time.sleep(0.5)

    # Register touch callback
    touch.set_callback(on_touch)

    # Start touch handler
    print("Starting touch handler. Touch the screen to see coordinates.")
    print("Press Ctrl+C to exit")

    # Option to calibrate first (uncomment if needed)
    # touch.calibrate()

    # Start the touch handler
    touch.start_listening()

    try:
        # Keep program running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()
