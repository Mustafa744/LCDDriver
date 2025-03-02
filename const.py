class ILI9340:
    """
    A class containing command constants for the ILI9340 TFT display driver.

    Attributes:
        CMD_SWRESET (int): Software Reset command (0x01).
        CMD_SLPOUT (int): Sleep Out command (0x11).
        CMD_DISPON (int): Display On command (0x29).
        CMD_CASET (int): Column Address Set command (0x2A).
        CMD_RASET (int): Row Address Set command (0x2B).
        CMD_RAMWR (int): Write to Memory command (0x2C).
        CMD_COLMOD (int): Set Pixel Format command (0x3A).
        CMD_MADCTL (int): Memory Access Control command (0x36).
    """

    CMD_SWRESET = 0x01  # Software Reset
    CMD_SLPOUT = 0x11  # Sleep Out
    CMD_DISPON = 0x29  # Display On
    CMD_CASET = 0x2A  # Column Address Set
    CMD_RASET = 0x2B  # Row Address Set
    CMD_RAMWR = 0x2C  # Write to Memory
    CMD_COLMOD = 0x3A  # Set Pixel Format
    CMD_MADCTL = 0x36  # Memory Access Control


class Colors:
    BLUE = 0xF800
    GREEN = 0x07E0
    RED = 0x001F
    WHITE = 0xFFFF
    BLACK = 0x0000
