from machine import Pin, ADC, I2C
from piotimer import Piotimer
from fifo import Fifo
from ssd1306 import SSD1306_I2C
from HR_measure import hr_measure
from HRV import hrv_analysis
from kubios import kubios
from mqtt import connect_wlan
import time
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
    global selected_item
    oled.fill(0)
    oled.fill_rect(xval, selected_item*text_height, oled_width, text_height, 1)
    for i, item in enumerate(menu_items):
        text_color = 0 if i == selected_item else 1
        oled.text(item, xval+text_height, i*text_height, text_color)
    oled.show()
                            
display_menu()

def display_text(text):
    oled.fill(0)
    oled.text(text, text_height*2, int(oled_height/2), 1)
    oled.show()
    
def check_for_button():
    value = 1
    while value != 0:
        while encoder.fifo.empty():
            pass
        value = encoder.fifo.get()

def display_results(results, result_list):
    global yval, text_height
    for item in result_list:
        oled.text(f"{item}: {results[item]}", xval, yval, 1)
        yval += text_height
    oled.text("PRESS TO EXIT", 10, 50, 1)
    oled.show()

    
display_menu()
    
while True:   
    if encoder.fifo.has_data():
        while encoder.fifo.has_data():
            value = encoder.fifo.get()
            if value != 0:
                selected_item += value
                if selected_item >= len(menu_items)-1:
                    selected_item = len(menu_items)-1
                elif selected_item <= 0:  
                    selected_item = 0
            else:
                if selected_item == 0:
                    display_text("Place finger")
                    time.sleep(3)
                    hr_measure(encoder, oled, display_menu, display=True)
                    check_for_button()
                    
                elif selected_item == 1:
                    display_text("Place finger")
                    time.sleep(3)
                    ppi_list = hr_measure(encoder, oled, display_menu, display=False)
                    results = hrv_analysis(ppi_list)
                    
                    oled.fill(0)
                    yval = 0
                    oled.text(f"{results['Time']}", xval, yval, 1)
                    yval += text_height*2
                    
                    result_items = ['Avg HR', 'Avg PPI', 'RMSSD', 'SDNN']
                    display_results(results, result_items)
            
                    #current_timestamp = time.time()
                    #formatted_time = time.localtime(current_timestamp)
            
                    #print(f"Current time:, {formatted_time[0]}-{formatted_time[1]}-{formatted_time[2]} {formatted_time[3]}:{formatted_time[4]}")
                    print(results)
                    check_for_button()
                    
                elif selected_item == 2:
                    display_text("Place finger")
                    time.sleep(3)
                    ppi_list = hr_measure(encoder, oled, display_menu, display=False)
                    
                    connect_wlan()
                    kubios_data = kubios(ppi_list)
                    print(kubios_data)
                    
                    oled.fill(0)
                    yval = 0
                    oled.text(f"{kubios_data['Time']}", xval, yval, 1)
                    yval += text_height*2
                    
                    result_list = ['HR', 'RMSSD', 'SDNN', 'PNS', 'SNS', 'STRESS']
                    display_results(kubios_data, result_list)
                    
                    check_for_button()
                    
                                            
    display_menu()
    
                
                    
