from DisplayHandler import DisplayHandler
from GpioHandler import GPIOHandler
from SPIHandler import SPIHandler
from touch_handler import XPT2046
from const import ILI9340, Colors
import time
import signal
import sys
import RPi.GPIO as GPIO

# Initialize handlers
gpio = GPIOHandler()
spi = SPIHandler()
display = DisplayHandler(gpio_handler=gpio, spi_handler=spi, commands=ILI9340)


# Define the touch callback function
def on_touch(coordinates):
    x, y = coordinates
    print(f"Touch detected at X={x}, Y={y}")

    # Draw a small dot at the touch location
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            nx, ny = x + dx, y + dy
            if 0 <= nx < display.width and 0 <= ny < display.height:
                display.draw_pixel(nx, ny, Colors.WHITE)


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

    # Initialize touch controller
    touch = XPT2046(
        tp_cs=7,  # Touch controller CS pin
        tp_irq=17,  # Touch controller IRQ pin
        spi_handler=spi,  # Reuse SPI handler
        screen_width=240,
        screen_height=320,
    )

    # Test IRQ pin functionality
    print("Testing IRQ pin functionality...")
    print(f"Current IRQ pin state: {GPIO.input(touch.tp_irq)}")
    print("Touch the screen for IRQ test (5 seconds)...")

    start_time = time.time()
    while time.time() - start_time < 5:
        state = GPIO.input(touch.tp_irq)
        if state == GPIO.LOW:
            print(f"IRQ LOW detected (touch)")
            # Try manual reading
            coords = touch.get_touch()
            if coords:
                print(f"Manual read: {coords}")
        time.sleep(0.1)

    # Register touch callback
    touch.set_callback(on_touch)

    # Start touch handler - try interrupt mode first, fallback to polling
    print("\nStarting touch handler. Touch the screen to see coordinates.")
    print("Press Ctrl+C to exit")

    # Option to calibrate
    do_calibrate = input("Calibrate the touch screen? (y/n): ").lower() == "y"
    if do_calibrate:
        touch.calibrate()

    # First try interrupt mode
    touch_mode = input("Use polling mode instead of interrupts? (y/n): ").lower() == "y"
    touch.start_listening(polling_mode=touch_mode)

    try:
        print("Main loop running...")
        counter = 0
        while True:
            time.sleep(1)
            counter += 1
            if counter % 10 == 0:
                print(f"Main loop alive - IRQ state: {GPIO.input(touch.tp_irq)}")
    except KeyboardInterrupt:
        cleanup()
