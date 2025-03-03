import RPi.GPIO as GPIO
import time
import threading
from queue import Queue
import queue


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
        # Set up GPIO mode right at the beginning
        if GPIO.getmode() != GPIO.BCM:
            GPIO.setmode(GPIO.BCM)

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

        # Initialize touch panel CS pin - should be HIGH when idle
        GPIO.setup(self.tp_cs, GPIO.OUT, initial=GPIO.HIGH)

        # Initialize touch panel IRQ pin as input with pull-up
        GPIO.setup(self.tp_irq, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Read current IRQ state to verify setup
        irq_state = GPIO.input(self.tp_irq)
        print(f"Touch IRQ initial state: {irq_state} (HIGH=not touched, LOW=touched)")

        # For touch detection
        self.callback = None
        self.running = False
        self.touch_thread = None
        self.touch_queue = Queue()

        # For debouncing
        self.last_touch_time = 0
        self.debounce_ms = 50  # 50ms debounce time

        print(f"Touch controller initialized. CS pin: {tp_cs}, IRQ pin: {tp_irq}")

        # Test SPI communication
        self._test_spi()

    def _test_spi(self):
        """Test SPI communication with the touch controller"""
        print("Testing SPI communication with touch controller...")
        try:
            # Read Z-position to check if controller responds
            z1 = self._read_adc(self.CMD_Z1_POS)
            z2 = self._read_adc(self.CMD_Z2_POS)
            print(f"SPI test read: Z1={z1}, Z2={z2}")

            # Try reading X/Y positions
            x = self._read_adc(self.CMD_X_POS)
            y = self._read_adc(self.CMD_Y_POS)
            print(f"SPI test read: X={x}, Y={y}")

            if x == 0 and y == 0 and z1 == 0 and z2 == 0:
                print(
                    "WARNING: All readings are zero. Touch controller may not be responding."
                )
            else:
                print("SPI communication test successful!")
        except Exception as e:
            print(f"SPI test failed: {e}")

    def _read_adc(self, command):
        """Read ADC value from touch controller."""
        # Pull CS low to start transmission
        GPIO.output(self.tp_cs, GPIO.LOW)
        time.sleep(0.001)  # Small delay for stability

        # Buffer for the response
        result = [0, 0]

        try:
            # Direct SPI access for better control
            if hasattr(self.spi_handler, "spi") and hasattr(
                self.spi_handler.spi, "xfer2"
            ):
                # Direct spidev access
                tx_data = [command, 0x00, 0x00]
                rx_data = self.spi_handler.spi.xfer2(tx_data)
                if len(rx_data) >= 3:
                    result[0] = rx_data[1]
                    result[1] = rx_data[2]
            else:
                # Use SPI handler methods
                if self.spi_lock:
                    with self.spi_lock:
                        self.spi_handler.write([command])
                        result = self.spi_handler.read([0x00, 0x00])
                else:
                    self.spi_handler.write([command])
                    result = self.spi_handler.read([0x00, 0x00])
        except Exception as e:
            print(f"SPI error in _read_adc: {e}")
        finally:
            # Always return CS to high when done
            GPIO.output(self.tp_cs, GPIO.HIGH)

        if result and len(result) >= 2:
            # Combine the two bytes into a 12-bit ADC value (discard the lower 3 bits)
            adc_val = ((result[0] << 8) | result[1]) >> 3
            return adc_val
        return 0

    def _get_touch_raw(self):
        """Get raw touch coordinates."""
        # First check if we can detect pressure
        z1 = self._read_adc(self.CMD_Z1_POS)
        z2 = self._read_adc(self.CMD_Z2_POS)

        # Calculate touch pressure
        z = z1 - z2

        # Only proceed if there's significant pressure
        if z < 100:
            return None

        # Now take multiple samples for X/Y for stability
        samples = 3
        x_samples = []
        y_samples = []

        for _ in range(samples):
            x = self._read_adc(self.CMD_X_POS)
            y = self._read_adc(self.CMD_Y_POS)

            # Add to samples list
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

        print(f"Raw touch values: X={median_x}, Y={median_y}, Z={z}")
        return median_x, median_y

    def get_touch(self):
        """Get calibrated touch coordinates."""
        raw = self._get_touch_raw()
        if raw is None:
            return None

        raw_x, raw_y = raw

        # Apply calibration and convert to screen coordinates
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
        # Double-check that we're responding to LOW state
        current_state = GPIO.input(self.tp_irq)
        if current_state != GPIO.LOW:
            print(f"IRQ handler triggered but pin is {current_state} not LOW")
            return

        # Basic debouncing
        current_time = time.time() * 1000  # Convert to ms
        if (current_time - self.last_touch_time) < self.debounce_ms:
            return

        self.last_touch_time = current_time

        # Queue the touch event for processing
        try:
            # Read directly to confirm touch
            coords = self.get_touch()
            if coords:
                self.touch_queue.put(True)
                print(f"IRQ triggered - touch event queued. Direct read: {coords}")
        except Exception as e:
            print(f"Error during IRQ handling: {e}")

    def _touch_processor(self):
        """Process touch events from the queue."""
        while self.running:
            try:
                # Wait for events from the queue
                # Use non-blocking get with timeout to be more responsive
                got_event = self.touch_queue.get(timeout=0.05)
                print(f"Touch event dequeued")

                # Sleep briefly to let touch stabilize
                time.sleep(0.01)

                # Process the touch
                coords = self.get_touch()
                print(f"Touch coordinates read: {coords}")

                # Execute callback if coordinates were obtained
                if coords is not None and self.callback:
                    print(f"Executing callback with coords {coords}")
                    try:
                        self.callback(coords)
                        print("Callback completed successfully")
                    except Exception as e:
                        print(f"Exception in callback: {e}")
                        import traceback

                        traceback.print_exc()
                else:
                    if coords is None:
                        print("No valid coordinates read")
                    if self.callback is None:
                        print("No callback function registered")

                # Wait for release
                wait_start = time.time()
                irq_released = False
                while time.time() - wait_start < 0.5:  # Max 500ms wait for release
                    if GPIO.input(self.tp_irq) == GPIO.HIGH:
                        print("Touch released (IRQ HIGH)")
                        irq_released = True
                        break
                    time.sleep(0.01)

                if not irq_released:
                    print("Touch release timeout - forcing continue")

                # Mark task as done
                self.touch_queue.task_done()
                print("Touch task marked as done")

            except queue.Empty:
                # This is normal, just continue
                pass
            except Exception as e:
                if self.running:
                    print(f"Touch processing error: {e.__class__.__name__}: {e}")
                    import traceback

                    traceback.print_exc()
                    # Try to recover by marking task as done if possible
                    try:
                        self.touch_queue.task_done()
                    except Exception as e2:
                        print(f"Could not mark task as done: {e2}")

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

        try:
            # Remove any existing event detection first
            GPIO.remove_event_detect(self.tp_irq)
            # Add the new event detection
            GPIO.add_event_detect(
                self.tp_irq, GPIO.FALLING, callback=self._irq_handler, bouncetime=50
            )
            print("Touch handler started with interrupt detection")
        except Exception as e:
            print(f"Failed to set up interrupt: {e}")
            self.running = False
            raise

    def stop_listening(self):
        """Stop listening for touch events."""
        self.running = False

        # Remove interrupt handler
        try:
            GPIO.remove_event_detect(self.tp_irq)
        except:
            pass

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
