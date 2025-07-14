import csv
import onnx
import json

'''
This module is responsible for holding all necessary information regarding an application characteristics
In particular it holds information regarding:
- IO shapes
- DLA subgraphs
- PPW Ratio
- Slowdown values
- Max achievable throughputs


It also provides methods to get 
- the minimum running frequency given the running device, target throughput and number of concurrent apps
- the most power efficient device given the average ppw ratio and target throughput
- export the relevant information regarding I/O shapes necessary for the Engine.py script
'''

class App:
    def __init__(self):
        self.name = None
        self.dlaSubgraphs = []
        self.input_shape = None
        self.output_shapes = None

        self.perf_per_watt = None
        self.ppw_ratio = None
        self.throughputs = None # dict with throughput for each device
        self.max_throughput = None # dict with max throughput for each device
        self.slowdown = None # dict with slowdown values for different number of apps

        self.DLA_THRESH = 1.0


    def read_engine_onnx(self, engine_onnx_file):
        '''
        Read ONNX file to extract input shape and output shapes
        '''
        model = onnx.load(engine_onnx_file)
        input_shape = model.graph.input[0].type.tensor_type.shape.dim
        output_shapes = [out.type.tensor_type.shape.dim for out in model.graph.output]
        self.input_shape = ",".join([str(d.dim_value) for d in input_shape])
        self.output_shapes = ";".join([",".join([str(d.dim_value) for d in out]) for out in output_shapes])

    def read_engine_log(self, engine_log_file):
        '''
        Read TRT log file to extract DLA subgraphs and app name
        '''
        with open(engine_log_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if "[DlaLayer]" in line:
                    self.dlaSubgraphs.append(line.strip().split("[DlaLayer]")[1].strip())
                if "--onnx=" in line:
                    self.name = line.split("--onnx=")[1].split(".onnx")[0].replace("onnx/", "").replace("onnx_n/", "") # hardcoded way to extract name
    
    def read_slowdown(self, slowdown_file):
        '''
        Read slowdown JSON to extract slowdown values for different number of apps
        '''
        with open(slowdown_file, 'r') as f:
            slowdown_data = json.load(f)
            if self.name in slowdown_data:
                self.slowdown = slowdown_data[self.name]
                return
            else:
                raise ValueError(f"Slowdown data for {self.name} not found in {slowdown_file}")

    def read_engine_csv(self, engine_csv_file):
        '''
        Read LEGACY CSV file to extract performance per watt, throughput and max throughput for each device
        '''
        self.perf_per_watt = {"gpu": {}, "dla": {}}
        self.max_throughput = {"gpu": 0, "dla": 0}
        self.throughputs = {"gpu": {}, "dla": {}}
        self.ppw_ratio = {}

        with open(engine_csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                device = row["Device"]
                device = "dla" if "dla" in device else device
                frequency = int(row["Frequency"])
                throughput = float(row["Throughput"])
                vdd_cgc_avg = float(row["VDD_CPU_GPU_CV_Avg"])

                # Calculate performance per watt (from vdd_cpu_gpu_cv line)
                perf_per_watt_value = throughput / vdd_cgc_avg
                self.perf_per_watt[device][frequency] = perf_per_watt_value

                # Update throughput
                self.throughputs[device][frequency] = throughput

                # Update maximum throughput
                if throughput > self.max_throughput[device]:
                    self.max_throughput[device] = throughput

        # Calculate the ppw ratio for each frequency
        for freq in self.perf_per_watt["dla"]:
            self.ppw_ratio[freq] = self.perf_per_watt["dla"][freq] / self.perf_per_watt["gpu"][freq]

    # ----------------------------------------

    def get_tp_freq(self, target_throughput, numapps=0):
        '''
        Calculate the minimum frequency for each device to achieve the target throughput

        target_throughput: The target throughput to achieve
        numapps: The number of concurrent applications running
        '''
        slowdown = self.slowdown[str(numapps)] if (numapps > 1) else 0
        factor = (1 - slowdown)
        min_frequencies = {"gpu": None, "dla": None}
        for device in self.throughputs:
            for frequency, throughput in sorted(self.throughputs[device].items()):
                if throughput * factor >= target_throughput:
                    print(f"For app {self.name}")
                    print(f"Device: {device}, Frequency: {frequency}, Throughput: {throughput}")
                    print(f"Actual throughput: {throughput * factor}")
                    min_frequencies[device] = frequency
                    break
        print(f"Max tps for app {self.name}: {self.max_throughput['gpu'] * factor} (gpu), {self.max_throughput['dla'] * factor} (dla)")
        return min_frequencies

    def analyze_app(self, target_throughput, numapps=0):
        '''
        Chooses between DLA and GPU execution:
        - If the average ppw ratio is above a threshold and the max throughput of DLA is above the target throughput, choose DLA
        - If the max throughput of GPU is above the target throughput, choose GPU
        - Otherwise, choose the device with the highest throughput

        target_throughput: The target throughput to achieve
        numapps: The number of concurrent applications running
        Returns the device to use ("gpu" or "dla")
        '''
        avg_ppw_ratio = sum(self.ppw_ratio.values()) / len(self.ppw_ratio)
        slowdown = self.slowdown[str(numapps)] if (numapps > 1) else 0
        factor = (1 - slowdown)
        print(f"Slowdown: {slowdown} ({factor})")
        if avg_ppw_ratio > self.DLA_THRESH and self.max_throughput["dla"] * factor >= target_throughput:
            return "dla"
        elif self.max_throughput["gpu"] * factor >= target_throughput:
            return "gpu"
        else:
            max_device = max(self.max_throughput, key=self.max_throughput.get)
            return max_device        
        
    # ----------------------------------------

    def print_app(self):
        print("-------------------")
        print(f"App name: {self.name}")
        print(f"Input shape: {self.input_shape}")
        print(f"Output shapes: {self.output_shapes}")
        print(f"#DLA subgraphs: {len(self.dlaSubgraphs)}")
        print(f"PPW ratio: {self.ppw_ratio}")
        print(f"Max throughput: {self.max_throughput}")
        print("-------------------")

    def export_app_io(self, path="./"):
        '''
        Exports, after initialization, the application I/O shapes to a JSON file for use in Engine.py
        '''
        app_data = {
            "name": self.name,
            "input_shape": self.input_shape,
            "output_shapes": self.output_shapes,
        }
        with open(f"{path}{self.name}.json", 'w') as f:
            json.dump(app_data, f, indent=4)

    
    def init_app(self, name: str, base_path: str = "engine_info/"):
        self.name = name

        onnx_path = f"{base_path}{name}/{name}.onnx"
        log_path = f"{base_path}{name}/{name}.log"
        csv_path = f"{base_path}{name}/{name}.csv"
        slowdown_path = f"{base_path}slowdowns.json"

        self.read_engine_onnx(onnx_path)
        self.read_engine_log(log_path)
        self.read_engine_csv(csv_path)
        self.read_slowdown(slowdown_path)