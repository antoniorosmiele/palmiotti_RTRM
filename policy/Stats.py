import time
import subprocess
import datetime
import random

'''
This module is responsible for collecting power and frequency stats from the system.
It reads the final GPU and CPU frequencies, as well as the power consumption of various voltage domains.

Ideal use requires the definition of the Stats object and calling "execute" with appropriate parameters
'''

def get_ts():
    return datetime.datetime.now().strftime('%d/%m/%Y-%H:%M:%S')

class Stats:
    def __init__(self):

        self.gpupath = "/sys/devices/gpu.0/devfreq/17000000.ga10b/target_freq"
        self.cpu0path = "/sys/devices/system/cpu/cpu3/cpufreq/scaling_cur_freq"
        self.cpu4path = "/sys/devices/system/cpu/cpu7/cpufreq/scaling_cur_freq"

        self.vddpaths = {
            "VDD_IN": {
                "curr_path": "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/curr1_input",
                "volt_path": "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/in1_input"
            },
            "VDD_CPU_GPU_CV": {
                "curr_path": "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/curr2_input",
                "volt_path": "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/in2_input"
            },
            "VDD_SOC": {
                "curr_path": "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/curr3_input",
                "volt_path": "/sys/bus/i2c/drivers/ina3221/1-0040/hwmon/hwmon4/in3_input"
            }
        }

        self.gpufreq = 0
        self.measurments = 0
        self.partmeasurments = 0
        self.vddpart = {                # The partial VDD sum between two different heartbeats
            "VDD_IN": 0,
            "VDD_CPU_GPU_CV": 0,
            "VDD_SOC": 0
        }
        self.vddsum = {                 # The total VDD sum since the start of the stats collection 
            "VDD_IN": 0,
            "VDD_CPU_GPU_CV": 0,
            "VDD_SOC": 0
        }
        self.heartbeats = []
        self.MOCK = False

    def read_sensor_data(self, path):
        '''
        Reads the sensor data from the specified path.
        If MOCK is enabled, it returns a random value between 0 and 1000.
        
        path: The path to the sensor data file.
        '''
        if self.MOCK:
            return random.randint(0, 1000)
        try:
            result = subprocess.run(['sudo', 'cat', path], capture_output=True, text=True)
            return int(result.stdout.strip())
        except Exception as e:
            print(f"[{get_ts()}] [Stats.py] [E] An error occured: {e}")

    def get_heartbeats(self):
        '''
        Returns the heartbeats collected so far, including the average VDD values and frequencies.
        
        heartbeats: A list of dictionaries containing the average VDD values at every heartbeat for every line
        gpufreq: The final GPU frequency
        cpu0freq: The final CPU0 frequency
        cpu4freq: The final CPU4 frequency
        '''
        return ("stats", self.heartbeats, self.gpufreq, self.cpu0freq, self.cpu4freq)

    def execute(self, heartbeat, interval, duration=None, csvpath=None):
        '''
        Executes the stats collection process.

        heartbeat: The interval in seconds at which to print the stats.
        interval: The interval in milliseconds at which to read the sensor data.
        duration: The total duration in seconds for which to run the stats collection. If None, runs indefinitely.
        csvpath: If provided, the path to a CSV file where the VDD stats will be logged continuously in time
        '''
        if csvpath is not None:
            # create a csv with timestamp, vdd_in, vdd_cpu_gpu_cv, vdd_soc
            with open(csvpath, 'w') as f:
                f.write("timestamp,VDD_IN,VDD_CPU_GPU_CV,VDD_SOC\n")
        
        start_time = time.time()
        hb_time = start_time
        if duration is None:
            duration = float('inf')

        while time.time() - start_time < duration:
            current_time = time.time()  

            # Heartbeat handling
            if (current_time - hb_time) >= heartbeat:
                print(f"[{get_ts()}] [Stats.py] [I] \tHeartbeat from Stats.py")
                self.print_stats()
                hb_time = current_time

            # Read the sensor data for each VDD path (curr and volt) and calculate power (/1000 = power in mW)            
            vdds = {"VDD_IN": 0, "VDD_CPU_GPU_CV": 0, "VDD_SOC": 0}
            for label, paths in self.vddpaths.items():
                curr_value = self.read_sensor_data(paths["curr_path"])
                volt_value = self.read_sensor_data(paths["volt_path"])
                if isinstance(curr_value, int) and isinstance(volt_value, int):
                    power = curr_value * (volt_value / 1000.0)
                    vdds[label] = power
                    self.vddsum[label] += power
                    self.vddpart[label] += power
                else:
                    print(f"[{get_ts()}] [Stats.py] [E] Error reading sensor data for paths ({paths['curr_path']}, {paths['volt_path']})")

            # If a CSV path is provided, append the current timestamp and VDD values
            if csvpath is not None:
                with open(csvpath, 'a') as f:
                    f.write(f"{get_ts()},{vdds['VDD_IN']},{vdds['VDD_CPU_GPU_CV']},{vdds['VDD_SOC']}\n")
            
            self.measurments += 1
            self.partmeasurments += 1
            time.sleep(interval / 1000.0)
        print(f"[{get_ts()}] [Stats.py] [D] Finished running Stats (Duration expired)")

    def print_stats(self):
        '''
        Pretty prints the average power and frequency stats collected so far.
        Resets the partial power measurements after printing.
        '''
        print(f"[{get_ts()}] [Stats.py] [I] \t\t{'Line':<20}{'Average Power':<20}{'Average Partial Power':<20}")
        for label in self.vddsum.keys():
            avg_power = self.vddsum[label] / self.measurments
            avg_partial_power = self.vddpart[label] / self.partmeasurments
            print(f"[{get_ts()}] [Stats.py] [I] \t\t{label:<20}{avg_power:<20.2f}{avg_partial_power:<20.2f}")
            self.vddpart[label] = 0

        # Only considers the GPU and CPU frequencies captured at every heartbeat
        self.gpufreq = self.read_sensor_data(self.gpupath)
        self.cpu0freq = self.read_sensor_data(self.cpu0path)
        self.cpu4freq = self.read_sensor_data(self.cpu4path)
        print(f"[{get_ts()}] [Stats.py] [I] \t\tGPU Frequency: \t{self.gpufreq} MHz")
        print(f"[{get_ts()}] [Stats.py] [I] \t\tCPU0 Frequency: \t{self.cpu0freq} MHz")
        print(f"[{get_ts()}] [Stats.py] [I] \t\tCPU4 Frequency: \t{self.cpu4freq} MHz")
        self.partmeasurments = 0
        vddavg = {label: (self.vddsum[label] / self.measurments) for label in self.vddsum.keys()}   # Only appends average overall VDD to returnable heartbeats
        self.heartbeats.append(vddavg)