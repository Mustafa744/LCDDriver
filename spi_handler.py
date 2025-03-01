# Python
import threading
import spidev
from contextlib import contextmanager

SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 10000000  # 10MHz for fast updates


class PrioritySPILock:
    def __init__(self):
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._in_use = False
        self._display_waiting = False

    def acquire_display(self):
        with self._cond:
            self._display_waiting = True
            while self._in_use:
                self._cond.wait()
            self._in_use = True
            self._display_waiting = False

    def acquire_touch(self):
        with self._cond:
            while self._in_use or self._display_waiting:
                self._cond.wait()
            self._in_use = True

    def release(self):
        with self._cond:
            self._in_use = False
            self._cond.notify_all()

    @contextmanager
    def display_lock(self):
        self.acquire_display()
        try:
            yield
        finally:
            self.release()

    @contextmanager
    def touch_lock(self):
        self.acquire_touch()
        try:
            yield
        finally:
            self.release()


class SPIHandler:
    def __init__(self, bus=SPI_BUS, device=SPI_DEVICE, speed=SPI_SPEED, spi_lock=None):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed
        self.spi_lock = spi_lock

    def transfer(self, data):
        self.spi.xfer2(data)

    def close(self):
        self.spi.close()
