import urequests as requests
import ujson
import network
import time
import ntptime

def kubios(intervals):
    
    current_timestamp = time.time()
    formatted_time = time.localtime(current_timestamp)
    print(f"time before: {formatted_time}")
    ntptime.settime()
    formatted_time = time.localtime()
    print(f"time after: {formatted_time}")
    
    APIKEY = "pbZRUi49X48I56oL1Lq8y8NDjq6rPfzX3AQeNo3a"
    CLIENT_ID = "3pjgjdmamlj759te85icf0lucv"
    CLIENT_SECRET = "111fqsli1eo7mejcrlffbklvftcnfl4keoadrdv1o45vt9pndlef"

    LOGIN_URL = "https://kubioscloud.auth.eu-west-1.amazoncognito.com/login"
    TOKEN_URL = "https://kubioscloud.auth.eu-west-1.amazoncognito.com/oauth2/token"
    REDIRECT_URI = "https://analysis.kubioscloud.com/v1/portal/login"

    response = requests.post(
        url = TOKEN_URL,
        data = 'grant_type=client_credentials&client_id={}'.format(CLIENT_ID),
        headers = {'Content-Type':'application/x-www-form-urlencoded'},
        auth = (CLIENT_ID, CLIENT_SECRET))

    response = response.json() #Parse JSON response into a python dictionary
    access_token = response["access_token"] #Parse access token

    #Interval data to be sent to Kubios Cloud. Replace with your own data:

    #Create the dataset dictionary HERE
    dataset = {
        "type": "RRI",
        "data": intervals,
        "analysis": {"type": "readiness"}
        }
    try:
        # Make the readiness analysis with the given data
        response = requests.post(
            url = "https://analysis.kubioscloud.com/v2/analytics/analyze",
            headers = { "Authorization": "Bearer {}".format(access_token), #use access token toaccess your Kubios Cloud analysis session
                        "X-Api-Key": APIKEY},
            json = dataset) #dataset will be automatically converted to JSON by the urequests

        r = response.json()
        
        if "analysis" not in r:
            return False
        
        cleaned = {
            'Time': None,
            'RMSSD': 0,
            'SDNN': 0,
            'HR': 0,
            'SD1': 0,
            'SD2': 0,
            'PNS': 0,
            'SNS': 0,
            'STRESS': 0
            }
        
        cleaned['Time'] = f"{formatted_time[0]}-{formatted_time[1]}-{formatted_time[2]} {formatted_time[3]}:{formatted_time[4]}"
        cleaned['RMSSD'] = r['analysis']['rmssd_ms']
        cleaned['PNS'] = r['analysis']['pns_index']
        cleaned['HR'] = r['analysis']['mean_hr_bpm']
        cleaned['SD1'] = r['analysis']['sd1_ms']
        cleaned['SD2'] = r['analysis']['sd2_ms']
        cleaned['SNS'] = r['analysis']['sns_index']
        cleaned['SDNN'] = r['analysis']['sdnn_ms']
        cleaned['STRESS'] = r['analysis']['stress_index']
        
        return cleaned
    
    except Exception as e:
        print("Error: ", e)
        return False


