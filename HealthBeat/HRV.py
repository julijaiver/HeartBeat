import ntptime
import time

def hrv_analysis(ppi_ms_list, timezone):
    current_timestamp = time.time()
    formatted_time = time.localtime(current_timestamp)
    if timezone:
        ntptime.settime()
        formatted_time = time.localtime()
                    
    print(f"Current time:, {formatted_time[0]}-{formatted_time[1]}-{formatted_time[2]} {formatted_time[3]}:{formatted_time[4]}")
    results = {
        "Time": f"{formatted_time[0]}-{formatted_time[1]}-{formatted_time[2]} {formatted_time[3]}:{formatted_time[4]}",
        "Avg PPI" : 0,
        "Avg HR" : 0,
        "RMSSD" : 0,
        "SDNN" : 0
        }
    
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
    return results
    
    
    
    
    
    
