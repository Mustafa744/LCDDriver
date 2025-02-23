from PIL import Image
import numpy as np

img = Image.open("shakal.jpg")


def rgb2RGB565(r, g, b):
    # Swap the red and blue channels for the conversion.
    return ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)

# convert the image to array
img = np.array(img)

# apply the conversion to all pixels
img = np.array([[rgb2RGB565(*pixel) for pixel in row] for row in img])


x = (255, 0, 0)
assert rgb2RGB565(*x) == 0x001F
