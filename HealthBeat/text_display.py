oled_width = 128
oled_height = 64
font = 8

def center(text):
    length= len(text)
    width = int((oled_width-length*font)/2)
    height = int((oled_height-font)/2)

    return text, width, height

def bottom(text,line): #line indicating how many lines from bottom to show the display
    length = len(text)
    width = int((oled_width-length*font)/2)
    height = int(oled_height-line*font)
    
    return text, width, height
