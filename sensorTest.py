from machine import Pin, ADC, I2C
from piotimer import Piotimer
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import micropython

micropython.alloc_emergency_exception_buf(200)

class Sensor:
    def __init__(self, pin):
        self.adc = ADC(Pin(pin))
        self.fifo = Fifo(100, typecode='i')       
    
    def read_samples(self, var):
        self.fifo.put(self.adc.read_u16())

sensor = Sensor(26)
timer = Piotimer(period=4, mode=Piotimer.PERIODIC, callback=sensor.read_samples)

frequency = 250
T = 1/frequency


#Use first 2s to find initial min/max
def find_threshold(frequency, data):
    value_list = []
    for i in range(frequency):
        while sensor.fifo.empty():
            pass
        value = sensor.fifo.get()
        value_list.append(value)
    minima, maxima = min(value_list), max(value_list)
    #threshold = minima+maxima//2
    return minima, maxima

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)
    
curr_min, curr_max = find_threshold(frequency*2, sensor.fifo)
init_threshold = (curr_min + curr_max * 3) // 4
print(curr_min, curr_max, init_threshold)

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

while True:
    if sensor.fifo.has_data():
        while sensor.fifo.has_data():
            value = sensor.fifo.get()
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
            

        
print(ppi)

avg_heart_rate = int(60 / (sum(ppi)/len(ppi) / 1000))     
print(avg_heart_rate) 