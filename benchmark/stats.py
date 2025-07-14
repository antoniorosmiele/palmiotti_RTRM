import time
import argparse
import subprocess
from datetime import datetime
import random

'''
This script periodaclly reads the power lines and logs the power consumption of various components.
'''

# Paths to the files
VDD_IN_CURR_PATH = "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/curr1_input"
VDD_IN_VOLT_PATH = "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/in1_input"
VDD_CPU_GPU_CV_CURR_PATH = "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/curr2_input"
VDD_CPU_GPU_CV_VOLT_PATH = "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/in2_input"
VDD_SOC_CURR_PATH = "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/curr3_input"
VDD_SOC_VOLT_PATH = "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/in3_input"

MOCK = False

# List of current and voltage path pairs
path_pairs = [
    (VDD_IN_CURR_PATH, VDD_IN_VOLT_PATH, "VDD_IN"),
    (VDD_CPU_GPU_CV_CURR_PATH, VDD_CPU_GPU_CV_VOLT_PATH, "VDD_CPU_GPU_CV"),
    (VDD_SOC_CURR_PATH, VDD_SOC_VOLT_PATH, "VDD_SOC")
]

def read_sensor_data(path):
    if MOCK:
        return random.randint(0, 1000)
    try:
        result = subprocess.run(['sudo', 'cat', path], capture_output=True, text=True)
        return int(result.stdout.strip())
    except Exception as e:
        return f"Error: {e}"

def main(interval, log_file=None, duration=None):
    '''
    interval: Interval between readings in milliseconds.
    log_file: The output will be logged to this file.
    duration: The script will run for this many seconds.
    '''
    start_time = time.time()
    while True:
        if duration and (time.time() - start_time) >= duration:
            break
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] "
        for curr_path, volt_path, label in path_pairs:
            curr_value = read_sensor_data(curr_path)
            volt_value = read_sensor_data(volt_path)
            if isinstance(curr_value, int) and isinstance(volt_value, int):
                power = curr_value * (volt_value / 1000.0)  # Convert to Amps and Volts
                log_entry += f"{label}: {power:.3f} mW, "
            else:
                log_entry += f"Error reading sensor data for paths ({curr_path}, {volt_path})\n"
        print(log_entry.strip())
        if log_file:
            with open(log_file, 'a') as f:
                f.write(log_entry.strip() + '\n')
        time.sleep(interval / 1000.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Read sensor data and log power consumption.')
    parser.add_argument('--interval', type=int, help='Interval between readings in milliseconds')
    parser.add_argument('--log-file', type=str, help='File to log the data')
    parser.add_argument('--duration', type=int, help='Duration to run the script in seconds')
    args = parser.parse_args()
    
    main(args.interval, args.log_file, args.duration)