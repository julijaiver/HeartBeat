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
class Sensor:
    def __init__(self, pin):
        self.adc = ADC(Pin(pin))
        self.sensor_fifo = Fifo(100, typecode='i')       
    
    def read_samples(self, var):
        self.sensor_fifo.put(self.adc.read_u16())

sensor = Sensor(26)
timer = Piotimer(period=4, mode=Piotimer.PERIODIC, callback=sensor.read_samples)


frequency = 250
T = 1/frequency


#Use first 2s to find initial min/max
def find_threshold(frequency, data):
    value_list = []
    for i in range(frequency):
        while sensor.sensor_fifo.empty():
            pass
        value = sensor.sensor_fifo.get()
        value_list.append(value)
    minima, maxima = min(value_list), max(value_list)
    #threshold = minima+maxima//2
    return minima, maxima

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)
    
curr_min, curr_max = find_threshold(frequency*2, sensor.sensor_fifo)
init_threshold = (curr_min + curr_max * 3) // 4
#print(curr_min, curr_max, init_threshold)

ppi = []
curr_peak = 0
prev_peak = 0
curr_max = 0
min_interval = 100 #samples
min_heart_rate = 30
max_heart_rate = 240

threshold_update_interval = 250
threshold_counter = 0
sample_counter = 0
min_val = 65536
max_val = 0
peak_max = 0
        

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
            if encoder.fifo.get() == 0 and selected_item == 0:
                if sensor.sensor_fifo.has_data():
                    while sensor.sensor_fifo.has_data():
                        value = sensor.sensor_fifo.get()
                        if value < min_val:
                            min_val = value
                        if value > max_val:
                            max_val = value
                        sample_counter += 1
                        
                        if threshold_counter == threshold_update_interval:
                            #curr_min, curr_max = find_threshold(frequency, data)
                            #print(init_threshold)
                            threshold_counter = 0
                            curr_min = min_val
                            curr_max = max_val
                            max_val =0
                            min_val=65536
                            init_threshold = (curr_min+curr_max * 3) // 4
                            
                        if value > init_threshold:
                            if value > peak_max and sample_counter - prev_peak > min_interval:
                                peak_max = value
                                curr_peak = sample_counter
                        else:
                            if peak_max > 0:
                                peak_diff = sample_counter - prev_peak
                                #ppi.append(peak_diff)
                                prev_peak = sample_counter
                                peak_max = 0
                                #print(peak_diff)
                                ppi_ms = int(peak_diff*T*1000)
                                print(ppi_ms)
                                
                                #print(ppi_ms)
                                avg_heart_rate = int(60 / (ppi_ms / 1000))
                                if min_heart_rate <= avg_heart_rate <= max_heart_rate:
                                    ppi.append(ppi_ms)
                                    oled.fill(0)
                                    oled.text(str(avg_heart_rate), 50, 30, 1)
                                    oled.show()
                                    print(avg_heart_rate)
                        threshold_counter += 1
                
        
        
        

