import network
from time import sleep
from umqtt.simple import MQTTClient
from machine import Timer

# Replace these values with your own
SSID = "KMD652_Group_4"
PASSWORD = "HWgroup4"
BROKER_IP = "192.168.4.253"

# Function to connect to WLAN
def connect_wlan():
    # Connecting to the group WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    
    timer = Timer(-1)
    timeout = 7
    elapsed_time = 0

    # Attempt to connect once per second
    while elapsed_time < timeout:
        if wlan.isconnected():
            print("Connection successful. Pico IP:", wlan.ifconfig()[0])
            return True
        else:
            print("Connecting... ")
            elapsed_time += 1
            sleep(1)
    
    print("Connection failed")
    return False
    
    
def connect_mqtt(topic, message):
    mqtt_client=MQTTClient("", BROKER_IP)
    mqtt_client.connect(clean_session=True)
    try:
        
        # Sending a message every 5 seconds.
        topic = topic
        message = message
        mqtt_client.publish(topic, message)
        print(f"Sending to MQTT: {topic} -> {message}")
        #sleep(5)
            
    except Exception as e:
        print(f"Failed to send MQTT message: {e}")
