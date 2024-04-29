from machine import Pin, ADC, I2C
from piotimer import Piotimer
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import micropython

micropython.alloc_emergency_exception_buf(200)

class Encoder:
    def __init__(self, rot_a, rot_b, button):
        self.a = Pin(rot_a, mode = Pin.IN, pull = Pin.PULL_UP)
        self.b = Pin(rot_b, mode = Pin.IN, pull = Pin.PULL_UP)
        self.switch = Pin(button, mode = Pin.IN, pull = Pin.PULL_UP)
        self.fifo = Fifo(300, typecode = 'i')
        self.last_button_state = self.switch.value()
        self.last_press_time = 0
        self.a.irq(handler = self.rot_handler, trigger = Pin.IRQ_RISING, hard = True)
        self.switch.irq(handler = self.sw_handler, trigger = Pin.IRQ_FALLING, hard = True)
    
    def rot_handler(self, pin):
        if self.b():
            self.fifo.put(-1)
        else:
            self.fifo.put(1)
    
    def sw_handler(self, pin):        
        current_time = time.ticks_ms()        
        if time.ticks_diff(current_time, self.last_press_time) > 200:
            self.fifo.put(0)
        self.last_press_time = current_time


i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

encoder = Encoder(10, 11, 12)

menu_items = ["HR measurement","HRV analysis","Kubios","History"]
selected_item = 0
yval = 0
xval = 0
text_height = 8

def display_menu():
    oled.fill_rect(xval, selected_item*text_height, oled_width, text_height, 1)
    for i, item in enumerate(menu_items):
        text_color = 0 if i == selected_item else 1
        oled.text(item, xval+text_height, i*text_height, text_color)
    oled.show()

display_menu()

while True:
    if encoder.fifo.has_data():
        while encoder.fifo.has_data():
            oled.fill(0)
            value = encoder.fifo.get()
            selected_item += value
            if 0<=selected_item<len(menu_items):
                display_menu()
