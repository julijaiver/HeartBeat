import time
import framebuf
from machine import UART, Pin, I2C, Timer, ADC
import heart
from ssd1306 import SSD1306_I2C

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

def image():
    image = framebuf.FrameBuffer(heart.img, 128, 32, framebuf.MONO_VLSB)
    return image