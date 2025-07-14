from typing import Any


class SysConfig:
    def __init__(self):
        self.parameters = {}

    def SetCPUFreqMin(self, CpuNum:str, freq:int, MinFrequencyPath:str):
        try:
            # Set the min CPU frequency
            with open(MinFrequencyPath, 'w') as f:
                f.write(str(freq))
            print(f"CPU{CpuNum} min frequency set to {freq} kHz")
        except PermissionError:
            print("Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"CPU frequency control files not found for cpu{CpuNum}. This may not be supported on your system.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def SetCPUFreqMax(self, CpuNum:str, freq:int, MaxFrequencyPath:str):
        try:
            # Set the max CPU frequency
            with open(MaxFrequencyPath, 'w') as f:
                f.write(str(freq))
            print(f"CPU{CpuNum} max frequency set to {freq} kHz")
        except PermissionError:
            print("Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"CPU frequency control files not found for cpu{CpuNum}. This may not be supported on your system.")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    def SetGPUFreqMin(self, freq:int, MinFrequencyPath:str):
        try:
            # Set the min GPU frequency
            with open(MinFrequencyPath, 'w') as f:
                f.write(str(freq))
            print(f"GPU min frequency set to {freq} kHz")
        except PermissionError:
            print("Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"GPU frequency control files not found. This may not be supported on your system.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def SetGPUFreqMax(self, freq:int, MaxFrequencyPath:str):
        try:
            # Set the max GPU frequency
            with open(MaxFrequencyPath, 'w') as f:
                f.write(str(freq))
            print(f"GPU max frequency set to {freq} kHz")
        except PermissionError:
            print("Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"GPU frequency control files not found. This may not be supported on your system.")
        except Exception as e:
            print(f"An error occurred: {e}")


    def SetCPUFreq(self, CpuNum:str, freq:int, GovernorPath:str, FrequencyPath:str):
        try:
            # Set governor to 'userspace' to allow manual frequency control
            with open(GovernorPath, 'w') as f:
                f.write("userspace")
            print(f"Governor for cpu{CpuNum} set to 'userspace'")
            
            # Set the CPU frequency
            with open(FrequencyPath, 'w') as f:
                f.write(str(freq))
            print(f"CPU{CpuNum} frequency set to {freq} kHz")
        except PermissionError:
            print("Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"CPU frequency control files not found for cpu{CpuNum}. This may not be supported on your system.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def SetGPUFreq(self, freq:str, GovernorPath:str, FrequencyPath:str):
        try:
            # Set governor to 'userspace' to allow manual frequency control
            with open(GovernorPath, 'w') as f:
                f.write("userspace")
            print(f"Governor for GPU set to 'userspace'")
            
            # Set the CPU frequency
            with open(FrequencyPath, 'w') as f:
                f.write(freq)
            print(f"GPU frequency set to {freq} kHz")
        except PermissionError:
            print("Permission denied: Please run as root.")
        except FileNotFoundError:
            print(f"GPU frequency control files not found. This may not be supported on your system.")
        except Exception as e:
            print(f"An error occurred: {e}")
