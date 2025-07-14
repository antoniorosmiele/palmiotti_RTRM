# this code is very ugly
import datetime
import json

def get_ts():
    return datetime.datetime.now().strftime('%d/%m/%Y-%H:%M:%S')

class SysConfig:
    def __init__(self):
        self.CpuFreqArray = ["115200", "192000", "268800", "345600", "422400", "499200", "576000", "652800", "729600", "806400", "883200", "960000", "1036800", "1113600", "1190400", "1267200", "1344000", "1420800", "1497600", "1574400", "1651200", "1728000", "1804800", "1881600", "1958400", "1984000"]
        self.GpuFreqArray = ["306000000", "408000000", "510000000", "612000000", "714000000", "816000000", "918000000"]

        self.CpuFreqMin = "268800"
        self.CpuFreqMax = "1984000"
        
        self.CpuNum = 0
        self.CpuGovernorPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_governor"
        self.CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_setspeed"
        self.CpuMinFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_min_freq"
        self.CpuMaxFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_max_freq"

        self.GpuGovernorPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/governor"
        self.GpuFrequencyPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/target_freq"
        self.GpuMinFrequencyPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/min_freq"
        self.GpuMaxFrequencyPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/max_freq"

    def read_sysconfig(self, configpath:str):
        print(f"[{get_ts()}] [SysConfig.py] [D] Reading config from {configpath}")
        with open(configpath, 'r') as f:
            config = json.load(f)

        cpufreq = config["frequencies"]["cpu"]
        gpufreq = config["frequencies"]["gpu"]
        maxn = False if config["frequencies"]["maxn"] == "False" else True

        return cpufreq, gpufreq, maxn

    def init_sysconfig(self, MAXN=False):
        self.CpuNum = 0
        print(f"[{get_ts()}] [SysConfig.py] [D] Setting min max CPU frequencies: {self.CpuFreqMin} -> {self.CpuFreqMax}")
        self.CpuMinFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_min_freq"
        self.CpuMaxFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_max_freq"
        self.__SetCPUFreqMin(self.CpuNum, self.CpuFreqMin, self.CpuMinFrequencyPath)
        self.__SetCPUFreqMax(self.CpuNum, self.CpuFreqMax, self.CpuMaxFrequencyPath)
        if MAXN:
            self.CpuNum = 4
            self.CpuMinFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_min_freq"
            self.CpuMaxFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_max_freq"
            self.__SetCPUFreqMin(self.CpuNum, self.CpuFreqMin, self.CpuMinFrequencyPath)
            self.__SetCPUFreqMax(self.CpuNum, self.CpuFreqMax, self.CpuMaxFrequencyPath)
            self.CpuNum = 0

    def restore_sysconfig(self, MAXN=False):
        self.CpuNum = 0
        print(f"[{get_ts()}] [SysConfig.py] [D] Restoring CPU/GPU frequencies")
        self.CpuGovernorPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_governor"
        self.CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_setspeed"
        self.__SetCPUFreq(self.CpuNum, "729600", self.CpuGovernorPath, self.CpuFrequencyPath)
        if MAXN:
            self.CpuNum = 4
            self.CpuGovernorPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_governor"
            self.CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_setspeed"
            self.__SetCPUFreq(self.CpuNum, "729600", self.CpuGovernorPath, self.CpuFrequencyPath)
            self.CpuNum = 0
        self.__SetGPUFreqMin("408000000", self.GpuMinFrequencyPath)
        self.__SetGPUFreqMax("408000000", self.GpuMaxFrequencyPath)

    def set_frequencies(self, CpuFreq, GpuFreq, MAXN=False):
        if CpuFreq is None and GpuFreq is None:
            print(f"[{get_ts()}] [SysConfig.py] [E] Bad use of set_frequency. No frequencies to set")
            return
        
        if CpuFreq is not None and CpuFreq not in self.CpuFreqArray:
            print(f"[{get_ts()}] [SysConfig.py] [E] CPU frequency {CpuFreq} is not an available frequency")
            return
        
        if GpuFreq is not None and GpuFreq not in self.GpuFreqArray:
            print(f"[{get_ts()}] [SysConfig.py] [E] GPU frequency {GpuFreq} is not an available frequency")
            return

        if CpuFreq is not None:
            print(f"[{get_ts()}] [SysConfig.py] [D] Setting CPU frequency: {CpuFreq}")
            self.CpuGovernorPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_governor"
            self.CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_setspeed"
            self.__SetCPUFreq(self.CpuNum, CpuFreq, self.CpuGovernorPath, self.CpuFrequencyPath)
            if MAXN:
                self.CpuNum = 4
                self.CpuGovernorPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_governor"
                self.CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{self.CpuNum}/cpufreq/scaling_setspeed"
                self.__SetCPUFreq(self.CpuNum, CpuFreq, self.CpuGovernorPath, self.CpuFrequencyPath)
                self.CpuNum = 0

        if GpuFreq is not None:
            print(f"[{get_ts()}] [SysConfig.py] [D] Setting GPU frequency: {GpuFreq}")
            self.__SetGPUFreqMin(GpuFreq, self.GpuMinFrequencyPath)
            self.__SetGPUFreqMax(GpuFreq, self.GpuMaxFrequencyPath)
        


    def __SetCPUFreqMin(self, CpuNum:str, freq:int, MinFrequencyPath:str):
        try:
            # Set the min CPU frequency
            with open(MinFrequencyPath, 'w') as f:
                f.write(str(freq))
        except PermissionError:
            print(f"[{get_ts()}] [SysConfig.py] [E] Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"[{get_ts()}] [SysConfig.py] [E] CPU frequency control files not found for cpu{CpuNum}. This may not be supported on your system.")
        except Exception as e:
            print(f"[{get_ts()}] [SysConfig.py] [E] An error occurred: {e}")

    def __SetCPUFreqMax(self, CpuNum:str, freq:int, MaxFrequencyPath:str):
        try:
            # Set the max CPU frequency
            with open(MaxFrequencyPath, 'w') as f:
                f.write(str(freq))
        except PermissionError:
            print(f"[{get_ts()}] [SysConfig.py] [E] Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"[{get_ts()}] [SysConfig.py] [E] CPU frequency control files not found for cpu{CpuNum}. This may not be supported on your system.")
        except Exception as e:
            print(f"[{get_ts()}] [SysConfig.py] [E] An error occurred: {e}")
    
    def __SetGPUFreqMin(self, freq:int, MinFrequencyPath:str):
        try:
            # Set the min GPU frequency
            with open(MinFrequencyPath, 'w') as f:
                f.write(str(freq))
        except PermissionError:
            print(f"[{get_ts()}] [SysConfig.py] [E] Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"[{get_ts()}] [SysConfig.py] [E] GPU frequency control files not found. This may not be supported on your system.")
        except Exception as e:
            print(f"[{get_ts()}] [SysConfig.py] [E] An error occurred: {e}")

    def __SetGPUFreqMax(self, freq:int, MaxFrequencyPath:str):
        try:
            # Set the max GPU frequency
            with open(MaxFrequencyPath, 'w') as f:
                f.write(str(freq))
        except PermissionError:
            print(f"[{get_ts()}] [SysConfig.py] [E] Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"[{get_ts()}] [SysConfig.py] [E] GPU frequency control files not found. This may not be supported on your system.")
        except Exception as e:
            print(f"[{get_ts()}] [SysConfig.py] [E] An error occurred: {e}")


    def __SetCPUFreq(self, CpuNum:str, freq:int, GovernorPath:str, FrequencyPath:str):
        print(f"[{get_ts()}] [SysConfig.py] [D] Setting CPU {CpuNum} frequency: {freq}")
        try:
            # Set governor to 'userspace' to allow manual frequency control
            with open(GovernorPath, 'w') as f:
                f.write("userspace")
            # Set the CPU frequency
            with open(FrequencyPath, 'w') as f:
                f.write(str(freq))
        except PermissionError:
            print(f"[{get_ts()}] [SysConfig.py] [E] Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"[{get_ts()}] [SysConfig.py] [E] CPU frequency control files not found for cpu{CpuNum}. This may not be supported on your system.")
        except Exception as e:
            print(f"[{get_ts()}] [SysConfig.py] [E] An error occurred: {e}")
