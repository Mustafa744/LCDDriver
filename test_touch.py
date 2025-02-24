import spidev
import RPi.GPIO as GPIO
import time

# SPI configuration
SPI_BUS = 0  # Default SPI bus
SPI_DEVICE = 0  # Default SPI device
TP_CS = 26  # Chip Select for Touch Panel

# Touchscreen resolution
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 320

# Raw ADC min/max values (calibrate these)
X_MIN, X_MAX = 300, 3800
Y_MIN, Y_MAX = 300, 3800

# Initialize SPI
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = 3000000

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TP_CS, GPIO.OUT)
GPIO.output(TP_CS, GPIO.HIGH)


def read_touch():
    """Reads raw X, Y touch values from XPT2046."""
    GPIO.output(TP_CS, GPIO.LOW)
    time.sleep(0.01)

    # Read X Coordinate
    spi.xfer2([0xD0])  # Start bit + A2-A0 (X position)
    raw_x = spi.xfer2([0x00, 0x00])
    x = ((raw_x[0] << 8) | raw_x[1]) >> 3

    # Read Y Coordinate
    spi.xfer2([0x90])  # Start bit + A2-A0 (Y position)
    raw_y = spi.xfer2([0x00, 0x00])
    y = ((raw_y[0] << 8) | raw_y[1]) >> 3

    GPIO.output(TP_CS, GPIO.HIGH)
    return x, y


def map_value(value, from_min, from_max, to_min, to_max):
    """Maps a value from one range to another."""
    return to_min + (to_max - to_min) * (value - from_min) / (from_max - from_min)


def get_touch_coordinates():
    """Reads touch input and maps it to screen coordinates."""
    x, y = read_touch()
    if X_MIN < x < X_MAX and Y_MIN < y < Y_MAX:
        screen_x = int(map_value(x, X_MIN, X_MAX, SCREEN_WIDTH, 0))  # Reversed X-axis
        screen_y = int(map_value(y, Y_MIN, Y_MAX, 0, SCREEN_HEIGHT))
        return screen_x, screen_y
    return None


try:
    while True:
        touch_pos = get_touch_coordinates()
        if touch_pos:
            print(f"Touch detected at: {touch_pos}")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Exiting...")
    GPIO.cleanup()
    spi.close()
