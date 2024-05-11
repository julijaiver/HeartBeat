from machine import Pin, ADC, I2C
from piotimer import Piotimer
from fifo import Fifo
from ssd1306 import SSD1306_I2C
from HR_measure import hr_measure
from HRV import hrv_analysis
from kubios import kubios
from mqtt import connect_wlan, connect_mqtt
import text_display
import time
import micropython
import json

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

def display_text(text, position):
    #oled.fill(0)
    if position == "center":
        text,width,height = text_display.center(text)
    elif position == "bottom":
        text,width,height = text_display.bottom(text, 2)
    oled.text(text, width, height, 1)
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
        oled.text(f"{item}", xval, yval, 1)
        oled.text(f"{results[item]}", int(oled_width/2), yval, 1)
        yval += text_height
    oled.text("PRESS TO EXIT", 10, 55, 1)
    oled.show()
    
def display_kubios_results(results, result_list):
    global yval, text_height
    for i in range(selected_item, selected_item+4):
        oled.text(f"{result_list[i]}", xval, yval, 1)
        oled.text(f"{results[result_list[i]]:.2f}", int(oled_width/2), yval, 1)
        yval += text_height
    oled.text("SCROLL DATA", 10, 48, 1)
    oled.text("PRESS TO EXIT", 10, 56, 1)
    oled.show()

def save_history(new_data):
    with open("data.json", "r+") as file:
        file_data = json.load(file)
        file_data["history"].append(new_data)
        file.seek(0)
        json.dump(file_data, file)
        print("data saved")

def get_history():
    history_list = None
    with open("data.json", "r+") as file:
        file_data = json.load(file)
        history_list = file_data["history"]
        history_list.append({"Time": "Exit"})
    if len(history_list) <= 7:
        return history_list
    else:
        return history_list[-7:]

def display_history_menu(history_list):
    oled.fill(0)
    oled.text("Data History", 0, 0, 1)
    oled.fill_rect(xval, (selected_item+1)*text_height, oled_width, text_height, 1)
    for i, item in enumerate(history_list):
        text_color = 0 if i == selected_item else 1
        oled.text(item['Time'], xval+text_height, (i+1)*text_height, text_color)
    oled.show()
    
display_menu()
history_on = False
    
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
                    oled.fill(0)
                    display_text("Place finger", "center")
                    time.sleep(3)
                    oled.fill(0)
                    hr_measure(encoder, oled, display_menu, display=True)
                    check_for_button()
                    
                elif selected_item == 1:
                    oled.fill(0)
                    display_text("Place finger", "center")
                    time.sleep(3)
                    ppi_list = hr_measure(encoder, oled, display_menu, display=False)
                    oled.fill(0)
                    
                    if connect_wlan():
                        oled.fill(0)
                        display_text("Connected", "center")
                        display_text("Please wait", "bottom")
                        results = hrv_analysis(ppi_list, timezone=True)
                        save_history(results)
                        if connect_mqtt("measurements", json.dumps(results)):
                            oled.fill(0)
                            display_text("MQTT Sent", "center")
                            time.sleep(3)
                    else:
                        display_text("No connection", "center")
                        results = hrv_analysis(ppi_list, timezone=False)
                        save_history(results)
                        time.sleep(3)
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
                    oled.fill(0)
                    display_text("Place finger", "center")
                    time.sleep(3)
                    ppi_list = hr_measure(encoder, oled, display_menu, display=False)
                    oled.fill(0)
                    if connect_wlan():
                        display_text("Connected", "center")
                        display_text("Please wait", "bottom")
                        kubios_data = kubios(ppi_list)
                        
                        if kubios_data:
                            save_history(kubios_data)
                            if connect_mqtt("measurements", json.dumps(kubios_data)):
                                oled.fill(0)
                                display_text("MQTT Sent", "center")
                                time.sleep(3)
                            print(kubios_data)
                            kubios_data_display = True
                            selected_item = 0
                            while kubios_data_display:
                                oled.fill(0)
                                yval = 0
                                oled.text(f"{kubios_data['Time']}", xval, yval, 1)
                                yval += text_height*2
                                result_list = ['RMSSD', 'SDNN', 'HR','SD1','SD2', 'PNS', 'SNS', 'STRESS']
                                display_kubios_results(kubios_data, result_list)
                                while encoder.fifo.has_data():
                                    value = encoder.fifo.get()
                                    if value != 0:
                                        selected_item += value
                                        if selected_item >= len(result_list)-4:
                                            selected_item = len(result_list)-4
                                        elif selected_item <= 0:  
                                            selected_item = 0
                                    else:
                                        kubios_data_display = value
                                        selected_item = 0
                    #check_for_button()
                        else:
                            oled.fill(0)
                            display_text("Kubios Error", "center")
                            time.sleep(3)
                            #display_menu()
                    else:
                        display_text("No connection", "center")
                        time.sleep(3)
                        #display_menu()
                    
                
                elif selected_item == 3:
                    history_on = True
                    history = get_history()
                    while history_on:
                        display_history_menu(history)
                        while encoder.fifo.has_data():
                            value = encoder.fifo.get()
                            if value != 0:
                                selected_item += value
                                if selected_item >= len(history)-1:
                                    selected_item = len(history)-1
                                elif selected_item <= 0:  
                                    selected_item = 0
                            else:
                                if selected_item != len(history) - 1:
                                    selected_history = history[selected_item]
                                    history_result_display = True
                                    selected_item = 0
                                    while history_result_display:
                                        if len(selected_history) == 5:
                                            result_items = ['Avg HR', 'Avg PPI', 'RMSSD', 'SDNN']
                                            oled.fill(0)
                                            yval = 0
                                            oled.text(f"{selected_history['Time']}", xval, yval, 1)
                                            yval += text_height*2
                                            display_results(selected_history, result_items)
                                            if encoder.fifo.has_data():
                                                history_result_display = encoder.fifo.get()
                                        else:
                                            result_items = ['RMSSD', 'SDNN', 'HR','SD1','SD2','PNS', 'SNS', 'STRESS']
                                            oled.fill(0)
                                            yval = 0
                                            oled.text(f"{selected_history['Time']}", xval, yval, 1)
                                            yval += text_height*2
                                            display_kubios_results(selected_history, result_items)
                                            while encoder.fifo.has_data():
                                                value = encoder.fifo.get()
                                                if value != 0:
                                                    selected_item += value
                                                    if selected_item >= len(result_items)-4:
                                                        selected_item = len(result_items)-4
                                                    elif selected_item <= 0:  
                                                        selected_item = 0
                                                else:
                                                    history_result_display = value
                                else:
                                   history_on = False
                                   selected_item = 0
                                                        
    display_menu()
    

