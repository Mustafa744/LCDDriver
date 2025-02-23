import spidev

# SPI Configuration
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 10000000  # 10MHz for fast updates


class SPIHandler:
    def __init__(self, bus=SPI_BUS, device=SPI_DEVICE, speed=SPI_SPEED):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed

    def transfer(self, data):
        self.spi.xfer2(data)

    def close(self):
        self.spi.close()
