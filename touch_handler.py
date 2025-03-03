import RPi.GPIO as GPIO
import time
import threading
from queue import Queue
import queue  # Add this import


class XPT2046:
    """
    Class for handling touch inputs from XPT2046 touch controller using interrupts.
    This controller uses SPI to communicate and has an IRQ pin for touch detection.
    """

    # Command constants for XPT2046
    CMD_X_POS = 0xD0  # X position command (12-bit mode)
    CMD_Y_POS = 0x90  # Y position command (12-bit mode)
    CMD_Z1_POS = 0xB0  # Z1 position command (12-bit mode)
    CMD_Z2_POS = 0xC0  # Z2 position command (12-bit mode)

    def __init__(
        self,
        tp_cs=7,
        tp_irq=17,
        spi_handler=None,
        screen_width=240,
        screen_height=320,
        x_min=150,
        x_max=3900,
        y_min=150,
        y_max=3900,
        rotate=False,
    ):
        """
        Initialize the touch controller.

        Args:
            tp_cs: Touch panel chip select pin
            tp_irq: Touch panel interrupt pin
            spi_handler: SPI handler instance
            screen_width: Width of the display in pixels
            screen_height: Height of the display in pixels
            x_min: Minimum raw X value
            x_max: Maximum raw X value
            y_min: Minimum raw Y value
            y_max: Maximum raw Y value
            rotate: Whether to rotate coordinates (swap X and Y)
        """
        self.tp_cs = tp_cs
        self.tp_irq = tp_irq
        self.spi_handler = spi_handler
        self.spi_lock = getattr(self.spi_handler, "spi_lock", None)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.rotate = rotate

        # Calibration parameters
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

        # Initialize touch panel CS pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.tp_cs, GPIO.OUT, initial=GPIO.HIGH)

        # Initialize touch panel IRQ pin as input with pull-up
        GPIO.setup(self.tp_irq, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # For touch detection
        self.callback = None
        self.running = False
        self.touch_thread = None
        self.touch_queue = Queue()

        # For debouncing
        self.last_touch_time = 0
        self.debounce_ms = 50  # 50ms debounce time

        print(f"Touch controller initialized. CS pin: {tp_cs}, IRQ pin: {tp_irq}")

    def _read_adc(self, command):
        """Read ADC value from touch controller."""
        GPIO.output(self.tp_cs, GPIO.LOW)
        time.sleep(0.001)  # Small delay for stability

        # Send command and read result
        result = None
        try:
            if self.spi_lock:
                with self.spi_lock:
                    self.spi_handler.write([command])
                    result = self.spi_handler.read([0x00, 0x00])
            else:
                self.spi_handler.write([command])
                result = self.spi_handler.read([0x00, 0x00])

            print(f"Touch ADC command:{command:02X}, result:{result}")
        except Exception as e:
            print(f"SPI error in _read_adc: {e}")
        finally:
            GPIO.output(self.tp_cs, GPIO.HIGH)

        if result and len(result) >= 2:
            # Combine the two bytes into a 12-bit ADC value
            adc_val = ((result[0] << 8) | result[1]) >> 3
            return adc_val
        return 0

    def _get_touch_raw(self):
        """Get raw touch coordinates."""
        # Take multiple samples for stability
        samples = 3
        x_samples = []
        y_samples = []

        for _ in range(samples):
            x = self._read_adc(self.CMD_X_POS)
            y = self._read_adc(self.CMD_Y_POS)
            z1 = self._read_adc(self.CMD_Z1_POS)
            z2 = self._read_adc(self.CMD_Z2_POS)

            # Calculate touch pressure
            z = z1 - z2

            # Skip if no touch detected
            if z < 100:
                continue

            x_samples.append(x)
            y_samples.append(y)

        # Return None if not enough samples
        if len(x_samples) < samples / 2:
            return None

        # Filter out outliers (simple median filter)
        x_samples.sort()
        y_samples.sort()
        median_x = x_samples[len(x_samples) // 2]
        median_y = y_samples[len(y_samples) // 2]

        return median_x, median_y

    def get_touch(self):
        """Get calibrated touch coordinates."""
        raw = self._get_touch_raw()
        if raw is None:
            return None

        raw_x, raw_y = raw

        # Apply calibration and convert to screen coordinates
        # Note: Some displays have inverted coordinates
        x = int((raw_x - self.x_min) * self.screen_width / (self.x_max - self.x_min))
        y = int((raw_y - self.y_min) * self.screen_height / (self.y_max - self.y_min))

        # Option to swap X/Y if needed for orientation
        if self.rotate:
            x, y = y, x

        # Ensure coordinates are within screen bounds
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))

        return x, y

    def set_callback(self, callback_func):
        """Set callback function to be called when touch is detected."""
        self.callback = callback_func

    def _irq_handler(self, channel):
        """Handle IRQ pin interrupt."""
        # Basic debouncing
        current_time = time.time() * 1000  # Convert to ms
        if (current_time - self.last_touch_time) < self.debounce_ms:
            return

        self.last_touch_time = current_time

        # If IRQ pin is LOW, touch is detected
        if GPIO.input(self.tp_irq) == GPIO.LOW:
            # Queue the touch event for processing
            self.touch_queue.put(True)

    def _touch_processor(self):
        """Process touch events from the queue."""
        while self.running:
            # Wait for a touch event or timeout
            try:
                # Non-blocking to allow clean shutdown
                self.touch_queue.get(timeout=0.1)

                try:
                    # Get the touch coordinates
                    coords = self.get_touch()
                    if coords is not None and self.callback:
                        # Call the user's callback function with coordinates
                        self.callback(coords)

                    # Wait for IRQ to go high again (touch release)
                    while GPIO.input(self.tp_irq) == GPIO.LOW and self.running:
                        time.sleep(0.01)

                    # Small delay to avoid rapid retriggering
                    time.sleep(0.05)

                except Exception as e:
                    print(f"Touch processing detail error: {e.__class__.__name__}: {e}")
                    import traceback

                    traceback.print_exc()
                finally:
                    # Always mark the task as done
                    self.touch_queue.task_done()

            except queue.Empty:
                # This is normal, just continue the loop
                pass
            except Exception as e:
                if self.running:  # Only log errors if still running
                    print(f"Touch queue error: {e.__class__.__name__}: {e}")
                    import traceback

                    traceback.print_exc()

    def start_listening(self):
        """Start listening for touch interrupts."""
        if self.touch_thread and self.touch_thread.is_alive():
            print("Touch handler is already running")
            return

        self.running = True

        # Start the touch processor thread
        self.touch_thread = threading.Thread(target=self._touch_processor)
        self.touch_thread.daemon = True
        self.touch_thread.start()

        # Add the interrupt handler
        GPIO.add_event_detect(
            self.tp_irq, GPIO.FALLING, callback=self._irq_handler, bouncetime=50
        )

        print("Touch handler started - waiting for touch events")

    def stop_listening(self):
        """Stop listening for touch events."""
        self.running = False

        # Remove the interrupt handler
        GPIO.remove_event_detect(self.tp_irq)

        # Wait for thread to finish
        if self.touch_thread:
            self.touch_thread.join(timeout=1.0)

        print("Touch handler stopped")

    def calibrate(self):
        """Interactive calibration routine."""
        print("\n=== Touch Calibration ===")
        print("Touch the upper-left corner of the screen...")
        time.sleep(2)

        # Wait for touch
        while GPIO.input(self.tp_irq) == GPIO.HIGH:
            time.sleep(0.1)

        ul = self._get_touch_raw()
        print(f"Upper-left raw value: {ul}")
        time.sleep(1)

        # Wait for release
        while GPIO.input(self.tp_irq) == GPIO.LOW:
            time.sleep(0.1)
        time.sleep(0.5)  # Debounce delay

        print("Now touch the lower-right corner of the screen...")
        time.sleep(2)

        # Wait for touch
        while GPIO.input(self.tp_irq) == GPIO.HIGH:
            time.sleep(0.1)

        lr = self._get_touch_raw()
        print(f"Lower-right raw value: {lr}")

        # Wait for release
        while GPIO.input(self.tp_irq) == GPIO.LOW:
            time.sleep(0.1)

        if ul and lr:
            # Update calibration values
            self.x_min = min(ul[0], lr[0])
            self.x_max = max(ul[0], lr[0])
            self.y_min = min(ul[1], lr[1])
            self.y_max = max(ul[1], lr[1])

            print("\nCalibration values updated:")
            print(f"X range: {self.x_min} - {self.x_max}")
            print(f"Y range: {self.y_min} - {self.y_max}")
            print("\nUse these values in your initialization:")
            print(
                f"x_min={self.x_min}, x_max={self.x_max}, y_min={self.y_min}, y_max={self.y_max}"
            )
            return True
        else:
            print("Calibration failed. Using default values.")
            return False
