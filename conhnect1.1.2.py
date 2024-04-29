from machine import Pin, ADC, I2C
from piotimer import Piotimer
from fifo import Fifo
from ssd1306 import SSD1306_I2C
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

class Sensor:
    def __init__(self, pin):
        self.adc = ADC(Pin(pin))
        self.fifo = Fifo(100, typecode='i')
        self.timer = None
    
    def start_reading(self, period=4):
        self.timer = Piotimer(period=period, mode=Piotimer.PERIODIC, callback=self.read_samples)
    
    def stop_reading(self):
        if self.timer:
            self.timer.deinit()
            
    def read_samples(self, var):
        self.fifo.put(self.adc.read_u16())
        
        
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

encoder = Encoder(10, 11, 12)
sensor = Sensor(26)
#timer = Piotimer(period=4, mode=Piotimer.PERIODIC, callback=sensor.read_samples)


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

def hr_measure(display):
    frequency = 250
    T = 1/frequency

    sensor.start_reading()
    
    #Use first 2s to find initial min/max
    def find_threshold(frequency, sensor):
        value_list = []
        for i in range(frequency):
            while sensor.fifo.empty():
                pass
            value = sensor.fifo.get()
            value_list.append(value)
        minima, maxima = min(value_list), max(value_list)
        #threshold = minima+maxima//2
        return minima, maxima

    curr_min, curr_max = find_threshold(frequency*2, sensor)
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
    
    start_time = time.time()
    measurement_duration = 35

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
                        #print(ppi_ms)
                        
                        #print(ppi_ms)
                        avg_heart_rate = int(60 / (ppi_ms / 1000))
                        if min_heart_rate <= avg_heart_rate <= max_heart_rate:
                            ppi.append(ppi_ms)
                            if display == True:
                                oled.fill(0)
                                oled.text(f"{str(avg_heart_rate)} BPM", 35, 30, 1)
                                oled.text("PRESS TO STOP", 10, 50, 1)
                                oled.show()
                            print(avg_heart_rate)
                threshold_counter += 1
                if encoder.switch.value() == 0:
                    sensor.stop_reading()
                    display_menu()
                    return
        if display == False:
            if time.time() - start_time >= measurement_duration:
                break
    sensor.stop_reading()
    return ppi

def hrv_analysis(ppi_ms_list):
    results = {}
    avg_ppi = int(sum(ppi_ms_list)/len(ppi_ms_list))
    results["Avg PPI"] = avg_ppi
    avg_hr = int(60/(avg_ppi/1000))
    results["Avg HR"] = avg_hr
    
    square_sum = 0
    for i in range(len(ppi_ms_list)-1):
        succ_square = (ppi_ms_list[i+1] - ppi_ms_list[i]) ** 2
        square_sum += succ_square
    
    rmssd = int((square_sum/(len(ppi_ms_list)-1)) ** 0.5)
    results["RMSSD"] = rmssd
    
    squared_diff_sum = sum((value - avg_ppi) ** 2 for value in ppi_ms_list)
    variance = squared_diff_sum/(len(ppi_ms_list) - 1)
    sdnn = int(variance ** 0.5)
    results["SDNN"] = sdnn
    
    sorted_results = dict(sorted(results.items()))
    return sorted_results


def display_text(text):
    oled.fill(0)
    oled.text(text, text_height*2, int(oled_height/2), 1)
    oled.show()
    
display_menu()
    
while True:
    place_finger_displayed = False
    if encoder.fifo.has_data():
        while encoder.fifo.has_data():
            value = encoder.fifo.get()
            if value != 0:
                selected_item += value
                if selected_item >= len(menu_items)-1:
                    selected_item = len(menu_items)-1
                elif selected_item <= 0:
                    selected_item = 0
                # The following line of code jumps from last to first when rotating
                #selected_item = (selected_item + value) % len(menu_items)
            else:
                if selected_item == 0 and not place_finger_displayed:
                    display_text("Place finger")
                    place_finger_displayed = True
                    time.sleep(3)
                    
                    if not sensor.timer:
                        sensor.start_reading()
                        time.sleep(1)
                        hr_measure(display=True)
                        if encoder.switch.value() == 0:
                            sensor.stop_reading()
                            time.sleep(1)
                            display_menu()
                elif selected_item == 1 and not place_finger_displayed:
                    display_text("Place finger")
                    time.sleep(3)
                    display_text("Hold for 30s")
                    sensor.start_reading()
                    time.sleep(3)
                    ppi_list = hr_measure(display=False)
                    results = hrv_analysis(ppi_list)
                    oled.fill(0)
                    for i, (measurement, value) in enumerate(results.items()):
                        text = f"{measurement}: {value}"
                        oled.text(text, xval, i*text_height, 1)
                    oled.show()
                    print(results)
                    while encoder.switch.value() != 0:
                        pass
                    display_menu()             
        
    display_menu()
    
                