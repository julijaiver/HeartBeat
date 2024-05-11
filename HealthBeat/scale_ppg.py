from machine import Pin, ADC, I2C
from ssd1306 import SSD1306_I2C
import math

width_screen = 128*2/3
height_screen = 32
font = 8


def scale(ppg):
    min_val = int(min(ppg))
    max_val = int(max(ppg))
    scale = (max_val-min_val)/(height_screen-1)
    scaled_ppg = []
    scale_plot = math.ceil(len(ppg)/ width_screen)
    #scale_plot = 4
    count = 0
    
    #calculate the average value of x consecutive data
    while count<= len(ppg)-scale_plot:
        value = 0
        for x in range(count,count+scale_plot):
            value += ppg[x]
            #count +=1
        scaled_average = int(((value/scale_plot)-min_val)/scale)
        scaled_ppg.append(scaled_average)
        count +=scale_plot
    #for i in ppg:
        #scaled_ppg.append(int((i-min_val)/scale))
    return scaled_ppg

