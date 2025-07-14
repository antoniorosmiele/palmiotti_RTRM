import json
import datetime
import multiprocessing
import traceback

from Engine import Engine
from Stats import Stats
from Refine import Refine
import os
import csv

'''
This module is responsible for reading the configuration file, initializing the engines and stats processes and
executing the workload on the engines while collecting statistics.
It reads the configuration from a JSON file, builds the engines, and runs them in parallel with a stats process.
It runs Refine.refine() to print the next CPU and GPU frequencies to use based on the collected heartbeats.
It export the configuration run statistics
'''

def get_ts():
    return datetime.datetime.now().strftime('%d/%m/%Y-%H:%M:%S')

class Config:
    def __init__(self):
        self.engines = None
        self.stats = None
        self.heartbeats = []
        self.statsheartbeats = None
        self.cpufreq = None
        self.gpufreq = None

    def print_config(self):
        '''
        Prints a recap of the current configuration, including the engines and their properties.
        '''
        print(f"[{get_ts()}] [Config.py] [D] Configuration recap:")
        print("----------------------------------")
        for engine in self.engines:
            engine.print_engine()
            print("----------------------------------")

    def read_config(self, configpath: str):
        '''
        Reads the configuration from a JSON file and initializes the engines and stats.

        configpath: The path to the configuration JSON file.
        '''
        print(f"[{get_ts()}] [Config.py] [D] Reading config from {configpath}")
        with open(configpath, 'r') as f:
            config = json.load(f)
        
        frequencies = config.get("frequencies", {})
        self.cpufreq = frequencies.get("cpu", None)
        self.gpufreq = frequencies.get("gpu", None)

        self.stats = Stats()
        self.engines = []
        for engine_config in config["models"]:
            print(f"[{get_ts()}] [Config.py] [D] Building {engine_config['name']}")
            print(f"[{get_ts()}] [Config.py] [D] \tEngine path: {engine_config['enginepath']}")
            print(f"[{get_ts()}] [Config.py] [D] \tEngine info path: {engine_config['engineinfo']}")
            print(f"[{get_ts()}] [Config.py] [D] \tDevice: {engine_config['device']}")
            print(f"[{get_ts()}] [Config.py] [D] \tThroughput: {engine_config['throughput']}")

            # Creates the engine from the enginepath
            engine = Engine()
            enginepath = engine_config.get("enginepath", "default_engine_path")
            if engine_config["device"] == "DLA0":
                enginepath = enginepath + "dla0.engine"
            elif engine_config["device"] == "DLA1":
                enginepath = enginepath + "dla1.engine"
            else:
                enginepath = enginepath + "gpu.engine"

            engine.throughput = engine_config.get("throughput", -1)

            engine.build_engine(enginepath, engine_config["engineinfo"])

            # and adds it to the list of engines
            self.engines.append(engine)
        
        printts = get_ts()
        print(f"[{printts}] [Config.py] [D] Correctly read config. All engines built")
        self.print_config()

    def run(self, statscsvpath=None, execution_duration=35):
        '''
        Runs the current configuration by executing all engines and the stats process in parallel.
        It collects heartbeats from each engine and the stats process, and then prints refinements results using Refine.refine().

        statscsvpath: If provided, the path to a CSV file where the VDD stats will be logged continuously in time.
        execution_duration: The total duration in seconds for which to run the engines and stats process.
        '''

        print(f"[{get_ts()}] [Config.py] [D] Beginning execution of current configuration")

        num_processes = len(self.engines) + 1  # +1 for the stats process
        start_barrier = multiprocessing.Barrier(num_processes)

        manager = multiprocessing.Manager()
        shared_heartbeats = manager.list()  # Shared list for heartbeats

        def engine_worker(engine, duration, barrier, shared_heartbeats):
            try:
                engine.execute(heartbeat=10, duration=duration, start_barrier=barrier)
                shared_heartbeats.append(engine.get_heartbeats())
            except Exception as e:
                print(f"[{get_ts()}] [Config.py] [E] Engine execution error: {e}")
                traceback.print_exc()

        def stats_worker(stats, duration, barrier, shared_heartbeats, csvpath):
            try:
                print(f"[{get_ts()}] [Config.py] [D] Stats process waiting at the barrier...")
                barrier.wait()  # Wait for all processes to be ready
                stats.execute(heartbeat=10, interval=500, duration=duration, csvpath=csvpath)
                shared_heartbeats.append(stats.get_heartbeats())
            except Exception as e:
                print(f"[{get_ts()}] [Config.py] [E] Stats execution error: {e}")
                traceback.print_exc()

        # Create a process for each engine
        processes = []
        for engine in self.engines:
            p = multiprocessing.Process(target=engine_worker, args=(engine, execution_duration, start_barrier, shared_heartbeats))
            processes.append(p)

        # Create a process for stats
        stats_process = multiprocessing.Process(target=stats_worker, args=(self.stats, execution_duration, start_barrier, shared_heartbeats, statscsvpath))
        processes.append(stats_process)

        # Start all processes
        for process in processes:
            process.start()

        # Wait for all processes to complete
        for process in processes:
            process.join()

        # Update the heartbeats in the main process
        for heartbeat in shared_heartbeats:
            if heartbeat[0] == "stats":
                self.statsheartbeats = heartbeat
            else:
                self.heartbeats.append(heartbeat)

        print(f"[{get_ts()}] [Config.py] [D] Configuration execution completed")
        
        refiner = Refine()
        new_cpuFreq, new_gpuFreq = refiner.refine(self.heartbeats, self.cpufreq, self.gpufreq)
        print(f"[{get_ts()}] [Config.py] [I] Refining results:")
        print(f"[{get_ts()}] [Config.py] [I]\tNew CPU frequency: {new_cpuFreq}")
        print(f"[{get_ts()}] [Config.py] [I]\tNew GPU frequency: {new_gpuFreq}")


    def export_heartbeats(self, output_path: str):
        '''
        Exports the collected heartbeats to a CSV file with the following columns:
            engine_name: The name of the engine
            device: The device on which the engine is running (e.g., GPU, DLA0, DLA1)
            cpu: The CPU frequency used during the execution
            gpu: The GPU frequency used during the execution
            target: The target throughput for the engine
            throughput: The throughput measured by the engine in the last heartbeat
            actual_throughput: The actual throughput measured by the engine in the last heartbeat
            vdd_in: The average VDD_IN value from the stats process        
            vdd_cpu_gpu_cv: The average VDD_CPU_GPU_CV value from the stats process
            vdd_soc: The average VDD_SOC value from the stats process
            run_gpu_freq: The running GPU frequency (in case frequency not set by user)
            run_cpu0_freq: The running CPU0 frequency (in case frequency not set by user)
            run_cpu4_freq: The running CPU4 frequency (in case frequency not set by user)

        output_path: The path to the output CSV file where the heartbeats will be saved.
        '''

        print(f"[{get_ts()}] [Config.py] [D] Exporting heartbeats to CSV at {output_path}")
        with open(output_path, mode='w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            # Write the header
            csv_writer.writerow(["engine_name", "device", "cpu", "gpu", "target", "throughput", "actual_throughput", "vdd_in", "vdd_cpu_gpu_cv", "vdd_soc", "run_gpu_freq", "run_cpu0_freq", "run_cpu4_freq"])

            # self.statsheartbeats is a tuple where:
            # self.statsheartbeats[1] is a list of VDD heartbeats from the stats process (as dictionary on the VDD line) - self.statsheartbeats[1][-1] is the last heartbeat
            # self.statsheartbeats[2] is the running GPU frequency
            # self.statsheartbeats[3] is the running CPU0 frequency
            # self.statsheartbeats[4] is the running CPU4 frequency
            
            # NOTE: these values are the same for all engines
            vdd_in_avg = self.statsheartbeats[1][-1]["VDD_IN"]
            vdd_cpu_gpu_cv_avg = self.statsheartbeats[1][-1]["VDD_CPU_GPU_CV"]
            vdd_soc_avg = self.statsheartbeats[1][-1]["VDD_SOC"]
            run_gpu_freq = self.statsheartbeats[2]
            run_cpu0_freq = self.statsheartbeats[3]
            run_cpu4_freq = self.statsheartbeats[4]
            
            # self.heartbeats contains every engine heartbeats
            # This loop goes through heartbeats collected across all engines running
            for name, device, targettp, hb, hb_actual in self.heartbeats:
                last_throughput = hb[-1]
                last_throughput_actual = hb_actual[-1]
                csv_writer.writerow([
                    name, 
                    device, 
                    self.cpufreq,
                    self.gpufreq,
                    f"{targettp:.2f}", 
                    f"{last_throughput:.2f}",
                    f"{last_throughput_actual:.2f}", 
                    f"{vdd_in_avg:.2f}", 
                    f"{vdd_cpu_gpu_cv_avg:.2f}", 
                    f"{vdd_soc_avg:.2f}",
                    f"{run_gpu_freq:.2f}",
                    f"{run_cpu0_freq:.2f}",
                    f"{run_cpu4_freq:.2f}"
                ])

        print(f"[{get_ts()}] [Config.py] [D] Heartbeats successfully exported to {output_path}")
