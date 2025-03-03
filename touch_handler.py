import RPi.GPIO as GPIO
import time
import threading
from queue import Queue
import queue


class XPT2046:
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

        # Initialize touch panel CS pin
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
        self.polling_mode = False  # Add polling mode option

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

            # Use debug print only during development
            # print(f"Touch ADC command:{command:02X}, result:{result}")
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
        # Check Z1/Z2 first to verify touch is happening
        z1 = self._read_adc(self.CMD_Z1_POS)
        z2 = self._read_adc(self.CMD_Z2_POS)

        # Calculate touch pressure
        z = z1 - z2

        # If no significant pressure, return None
        if z < 100:
            return None

        # Now read X/Y coordinates
        x = self._read_adc(self.CMD_X_POS)
        y = self._read_adc(self.CMD_Y_POS)

        return x, y

    def get_touch(self):
        """Get calibrated touch coordinates."""
        raw = self._get_touch_raw()
        if raw is None:
            return None

        raw_x, raw_y = raw

        # Debug print raw values
        # print(f"Raw touch: x={raw_x}, y={raw_y}")

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
        if GPIO.input(self.tp_irq) != GPIO.LOW:
            return

        # Basic debouncing
        current_time = time.time() * 1000  # Convert to ms
        if (current_time - self.last_touch_time) < self.debounce_ms:
            return

        self.last_touch_time = current_time

        # Queue the touch event for processing
        self.touch_queue.put(True)
        print("IRQ triggered - touch event queued")

    def _touch_processor(self):
        """Process touch events from the queue."""
        while self.running:
            try:
                if self.polling_mode:
                    # In polling mode, check the IRQ pin directly
                    if GPIO.input(self.tp_irq) == GPIO.LOW:
                        coords = self.get_touch()
                        if coords is not None and self.callback:
                            self.callback(coords)
                    time.sleep(0.05)  # Poll at 20Hz
                else:
                    # In interrupt mode, wait for events from the queue
                    self.touch_queue.get(timeout=0.1)

                    # Process the touch
                    coords = self.get_touch()
                    if coords is not None and self.callback:
                        print(f"Touch detected at {coords}")
                        self.callback(coords)

                    # Wait for release and mark task as done
                    release_timeout = time.time() + 1.0  # 1 second max wait
                    while (
                        GPIO.input(self.tp_irq) == GPIO.LOW and time.sleep(0.01) is None
                    ):
                        if time.time() > release_timeout:
                            print("Touch release timeout")
                            break

                    # Mark task as done
                    self.touch_queue.task_done()

            except queue.Empty:
                # This is normal in interrupt mode, just continue
                pass
            except Exception as e:
                if self.running:
                    print(f"Touch processing error: {e.__class__.__name__}: {e}")
                    import traceback

                    traceback.print_exc()
                    # Try to recover by marking task as done if possible
                    try:
                        self.touch_queue.task_done()
                    except:
                        pass

    def start_listening(self, polling_mode=False):
        """
        Start listening for touch events.

        Args:
            polling_mode: If True, poll the IRQ pin instead of using interrupts
        """
        if self.touch_thread and self.touch_thread.is_alive():
            print("Touch handler is already running")
            return

        self.polling_mode = polling_mode
        self.running = True

        # Start the touch processor thread
        self.touch_thread = threading.Thread(target=self._touch_processor)
        self.touch_thread.daemon = True
        self.touch_thread.start()

        # Only add interrupt handler if not in polling mode
        if not polling_mode:
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
                print("Falling back to polling mode")
                self.polling_mode = True

        if self.polling_mode:
            print("Touch handler started in polling mode")

    def stop_listening(self):
        """Stop listening for touch events."""
        self.running = False

        # Remove interrupt handler if it was set
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

        # Wait for touch
        ul = None
        attempts = 0
        while ul is None and attempts < 30:
            if GPIO.input(self.tp_irq) == GPIO.LOW:
                print("Touch detected - reading coordinates...")
                ul = self._get_touch_raw()
                if ul is None:
                    print("Failed to read upper-left - try again")
            time.sleep(0.1)
            attempts += 1

        if ul is None:
            print("Calibration failed - couldn't detect touch in upper-left")
            return False

        print(f"Upper-left raw value: {ul}")

        # Wait for release
        while GPIO.input(self.tp_irq) == GPIO.LOW:
            time.sleep(0.1)

        print("Now touch the lower-right corner of the screen...")
        time.sleep(1)

        # Wait for touch
        lr = None
        attempts = 0
        while lr is None and attempts < 30:
            if GPIO.input(self.tp_irq) == GPIO.LOW:
                print("Touch detected - reading coordinates...")
                lr = self._get_touch_raw()
                if lr is None:
                    print("Failed to read lower-right - try again")
            time.sleep(0.1)
            attempts += 1

        if lr is None:
            print("Calibration failed - couldn't detect touch in lower-right")
            return False

        print(f"Lower-right raw value: {lr}")

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
