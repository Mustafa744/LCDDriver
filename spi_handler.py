# Python
import spidev

# SPI Configuration
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 10000000  # 10MHz for fast updates


class SPIHandler:
    def __init__(self, bus=SPI_BUS, device=SPI_DEVICE, speed=SPI_SPEED, spi_lock=None):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed
        self.spi_lock = spi_lock

    def transfer(self, data):
        if self.spi_lock:
            with self.spi_lock:
                self.spi.xfer2(data)
        else:
            self.spi.xfer2(data)

    def close(self):
        self.spi.close()
