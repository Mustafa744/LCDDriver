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

# Track the last touch position to avoid duplicates
last_touch_pos = None
touch_colors = [Colors.RED, Colors.GREEN, Colors.BLUE, Colors.WHITE]
current_color_index = 0


# Define the touch callback function
def on_touch(coordinates):
    global last_touch_pos, current_color_index

    x, y = coordinates
    print(f"Touch detected at X={x}, Y={y}")

    # Change drawing color on each touch
    current_color = touch_colors[current_color_index]
    current_color_index = (current_color_index + 1) % len(touch_colors)

    # Draw a small dot at the touch location
    radius = 3  # Adjust size as needed
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            # Create a circle pattern
            if dx * dx + dy * dy <= radius * radius:
                nx, ny = x + dx, y + dy
                if 0 <= nx < display.width and 0 <= ny < display.height:
                    display.draw_pixel(nx, ny, current_color)

    # Save last position to enable drawing lines between points
    last_touch_pos = (x, y)


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
    display.fill_screen(Colors.BLACK)
    time.sleep(0.5)

    print("Touch Screen Drawing Application")
    print("-" * 30)

    # Initialize touch controller with the working IRQ setup
    touch = XPT2046(
        tp_cs=7,  # Touch controller CS pin
        tp_irq=17,  # Touch controller IRQ pin (verified working)
        spi_handler=spi,  # Reuse SPI handler
        screen_width=240,
        screen_height=320,
    )

    # Short IRQ test
    print("Testing IRQ pin...")
    irq_state = GPIO.input(touch.tp_irq)
    print(
        f"Current IRQ state: {'LOW (touched)' if irq_state == GPIO.LOW else 'HIGH (not touched)'}"
    )

    # Register touch callback
    touch.set_callback(on_touch)

    # Ask if calibration is needed
    calibrate = (
        input("Would you like to calibrate the touch screen? (y/n): ").lower() == "y"
    )
    if calibrate:
        success = touch.calibrate()
        if success:
            print("Calibration successful!")
        else:
            print("Calibration failed - using default values.")

    # Start touch handler - use interrupt mode since IRQ is working
    polling_mode = (
        input("Use polling mode instead of interrupts? (y/n): ").lower() == "y"
    )

    print("\nStarting touch handler...")
    touch.start_listening(polling_mode=polling_mode)

    print("\n=== Touch Screen Drawing Ready ===")
    print("- Touch screen to draw")
    print("- Each touch uses a different color")
    print("- Press Ctrl+C to exit")

    try:
        # Create a basic drawing loop
        running = True
        counter = 0
        while running:
            time.sleep(0.5)  # Less frequent polling in main loop
            counter += 1

            # Periodic status check
            if counter % 20 == 0:  # Every 10 seconds
                irq_state = GPIO.input(touch.tp_irq)
                print(
                    f"Status: Touch controller is {'active' if touch.running else 'inactive'}, "
                    f"IRQ: {'LOW (touched)' if irq_state == GPIO.LOW else 'HIGH (not touched)'}"
                )

    except KeyboardInterrupt:
        print("\nDrawing session ended.")
        cleanup()
