import time
from machine import ADC, Pin
from piotimer import Piotimer
from fifo import Fifo
import heart
import heart_graph
import text_display
import scale_ppg

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
        
def hr_measure(encoder, oled, display_menu, display):
    frequency = 250
    T = 1/frequency
    sensor = Sensor(26)
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
    print(curr_min, curr_max, init_threshold)

    ppi = []
    curr_peak = 0
    prev_peak = 0
    #curr_max = 0
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
    measurement_duration = 30
    remaining_time = None
    ppg_counter = 0
    ppg_avg = 0
    scaled_ppg = 0
    scaled_ppg_counter = 0
    previous_x = 0
    current_x = 0
    previous_y = 0
    current_y = 0
    oled_width = 128

    while True:
        if sensor.fifo.has_data():
            while sensor.fifo.has_data():
                value = sensor.fifo.get()
                if display:
                    if ppg_counter < 8:
                        ppg_avg += value
                        ppg_counter += 1
                    else:
                        ppg_counter = 0
                        ppg_avg = ppg_avg//8
                        scaled_ppg = int((curr_max-ppg_avg)*(31/(curr_max-curr_min)))
                        ppg_avg = 0
                        if scaled_ppg_counter < 127:
                            scaled_ppg_counter += 1
                            previous_x = current_x
                            previous_y = current_y
                            current_x = scaled_ppg_counter
                            current_y = scaled_ppg
                            oled.line(previous_x,previous_y,current_x,current_y,1)
                        else:
                            scaled_ppg_counter = 0
                            previous_x = 0
                            current_x = 0
                            oled.fill_rect(0,0,128,32,0)
                        oled.show()
                        
                if value < min_val:
                    min_val = value
                if value > max_val:
                    max_val = value
                sample_counter += 1
                
                if threshold_counter == threshold_update_interval:
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
                                oled.fill_rect(0,32,128,64,0)
                                text,width,height = text_display.bottom(f"{str(avg_heart_rate)} BPM",3)
                                oled.text(text,width,height,1)
                                text,width,height = text_display.bottom("PRESS TO STOP",1)
                                oled.text(text,width,height,1)
                                oled.show()
                            elif not display and remaining_time != 0:
                                oled.fill_rect(0,0,128,32,0)
                                oled.show()
                                oled.fill_rect(0,0,128,32,0)
                                oled.blit(heart_graph.image(),20,0)
                                oled.show()
                threshold_counter += 1
                if encoder.switch.value() == 0:
                    sensor.stop_reading()
                    return
                
        if display == False:
            if time.time() - start_time >= measurement_duration:
                break
            remaining_time = measurement_duration - (time.time() - start_time) - 1
            oled.fill(0)
            text,width,height = text_display.bottom("MEASURING...",3)
            oled.text(text,width,height,1)
            text,width,height = text_display.bottom(f"Hold for {remaining_time}s",1)
            oled.text(text,width,height,1)
            if remaining_time == 0:
                oled.fill(0)
                text,width,height = text_display.center("CALCULATING...")
                oled.text(text,width,height,1)
            oled.show()
    sensor.stop_reading()
    return ppi
                
                
                
               
