import json
import datetime

from App import App

'''
This module is responsible for enacting the Decide step of the policy
It reads the apps from a JSON file and using App.py creates the App objects with the relevant information (PPW Ratio, DLA subgraphs etc...)
"decide" function enacts the decision making and returns the configuration as a JSON
'''

def get_ts():
    return datetime.datetime.now().strftime('%d/%m/%Y-%H:%M:%S')

MAX_FREQUENCY_GPU = 918000000
BASE_FREQUENCY_CPU = 729600

class Decide:

    def __init__(self):
        self.apps = []  # list of tuples (app, target_throughput)
        self.config = {}

    def read_apps(self, apps_json_path):
        print(f"[{get_ts()}] [Decide.py] [D] Reading apps from {apps_json_path}")
        with open(apps_json_path, 'r') as f:
            apps_json = json.load(f)
            for app in apps_json["apps"]:
                print(f"[{get_ts()}] [Decide.py] [D] Initializing app {app['name']} with target throughput {app['tp']}")
                a = App()
                a.init_app(app["name"])
                self.apps.append((a, app["tp"]))
        print(f"[{get_ts()}] [Decide.py] [D] Successfully read {len(self.apps)} apps")

    def print_config(self, config_json, cpu_freq, gpu_freq, output_path="config.json"):
        printing = {"frequencies": {"cpu": str(cpu_freq), "gpu": str(gpu_freq), "maxn": "True"}, "models": []}
        for app in config_json["apps"]:
            name = app["name"]
            enginepath = f"../benchmark/engines/{name}/"
            engineinfo = f"engine_info/{name}/{name}.json"
            device = app["device"]
            throughput = app["tp"]
            printing["models"].append({"name": name, "engineinfo": engineinfo, "enginepath": enginepath, "device": device, "throughput": throughput})

        print(json.dumps(printing, indent=4))
        with open(output_path, "w") as f:
            json.dump(printing, f, indent=4)

    # --------------------------------------------------------

    def decide(self):
        '''
        Decide step algorithm.
        1. Read the apps from the JSON file
        2. Sort the apps by their average ppw ratio
        3. For each app, analyze it to determine the most power efficient device capable of achieving the target throughput
        4. Allocate the app to the device, considering the DLA capacities
        5. Determine the minimum running frequency for the device based on the target throughput
        6. Prints and saves the configuration in the required format by Config.py
        '''

        print(f"[{get_ts()}] [Decide.py] [D] Building configuration")

        dla0_capacity = 16
        dla1_capacity = 16
        output_config = {"apps": []}

        # Sort apps by the average ppw ratio
        self.apps.sort(key=lambda app_tuple: sum(app_tuple[0].ppw_ratio.values()) / len(app_tuple[0].ppw_ratio))

        min_running_freq = 0

        for app, target_throughput in self.apps:
            
            # NOTE: analyze_app is returning the device with the highest achievable throughput if the target throughput is not achievable
            device = app.analyze_app(target_throughput, numapps=len(self.apps))
            print(f"[{get_ts()}] [Decide.py] [D] Analyzed app {app.name} with target throughput {target_throughput}")
            print(f"[{get_ts()}] [Decide.py] [D] Device: {device}")
            device_label = None
            if device == "dla":
                num_dla_subgraphs = len(app.dlaSubgraphs)
                if num_dla_subgraphs <= dla0_capacity:
                    device_label = "DLA0"
                    dla0_capacity -= num_dla_subgraphs
                    print(f"[{get_ts()}] [Decide.py] [D] Allocated app {app.name} to DLA0 (remaining capacity: {dla0_capacity})")
                elif num_dla_subgraphs <= dla1_capacity:
                    device_label = "DLA1"
                    dla1_capacity -= num_dla_subgraphs
                    print(f"[{get_ts()}] [Decide.py] [D] Allocated app {app.name} to DLA1 (remaining capacity: {dla1_capacity})")
                else:
                    device_label = "GPU"
                    print(f"[{get_ts()}] [Decide.py] [D] Allocated app {app.name} to GPU (No capacity on DLAs)")
            else:
                device_label = "GPU"
                print(f"[{get_ts()}] [Decide.py] [D] Allocated app {app.name} to GPU")

            # Get minimum running frequency at decided device
            min_frequency = app.get_tp_freq(target_throughput, numapps=len(self.apps))[device]
            if min_frequency is None:
                min_frequency = MAX_FREQUENCY_GPU
                print(f"[{get_ts()}] [Decide.py] [W] App {app.name} is unachievable (target throughput: {target_throughput})")
            min_running_freq = max(min_running_freq, min_frequency)

            output_config["apps"].append({
                "name": app.name,
                "tp": target_throughput,
                "device": device_label,
            })
        
        self.print_config(output_config, BASE_FREQUENCY_CPU=729600, gpu_freq=min_running_freq)