import os
import subprocess
import time
from multiprocessing import Process

from util.trimmer import trim_logs
from util.exporter import export
from util.SysConfigClass import SysConfig
import argparse

'''
This script executes the benchmark_gpudla.py and stats.py scripts in concurrence.
In this way we record the power consumption given by a specific TensorRT Engine
'''

MOCK = False # Set to true for testing without actual frequency changes or benchmarks

#cpufreq [115200 192000 268800 345600 422400 499200 576000 652800 729600 806400 883200 960000 1036800 1113600 1190400 1267200 1344000 1420800 1497600 1574400 1651200 1728000 1804800 1881600 1958400 1984000]
#gpufreq [306000000 408000000 510000000 612000000 714000000 816000000 918000000]

cpufreq = []
gpufreq = ["306000000", "408000000", "510000000", "612000000", "714000000", "816000000", "918000000"]

duration = 15
batch_size = 1

CpuFreqMin = "268800"
CpuFreqMax = "1984000"
CpuNum = 0

CpuGovernorPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_governor"
CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_setspeed"
CpuMinFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_min_freq"
CpuMaxFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_max_freq"

GpuGovernorPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/governor"
GpuFrequencyPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/target_freq"
GpuMinFrequencyPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/min_freq"
GpuMaxFrequencyPath = f"/sys/devices/gpu.0/devfreq/17000000.ga10b/max_freq"

sysconfig = SysConfig()

#### Frequency handling #### --------------------------------------------

def init_sysconfig(MAXN=False):

    '''
    Set max and min CPU frequencies to 1984000 and 268800 respectively.
    '''

    if MOCK: 
        print("No worries")
        return
    
    CpuNum = 0
    CpuMinFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_min_freq"
    CpuMaxFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_max_freq"

    print(f"Setting min max CPU frequencies: {CpuFreqMin} -> {CpuFreqMax}")
    sysconfig.SetCPUFreqMin(CpuNum, CpuFreqMin, CpuMinFrequencyPath)
    sysconfig.SetCPUFreqMax(CpuNum, CpuFreqMax, CpuMaxFrequencyPath)
    if MAXN:

        CpuNum = 4
        CpuMinFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_min_freq"
        CpuMaxFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_max_freq"

        sysconfig.SetCPUFreqMin(CpuNum, CpuFreqMin, CpuMinFrequencyPath)
        sysconfig.SetCPUFreqMax(CpuNum, CpuFreqMax, CpuMaxFrequencyPath)

def restore_sysconfig(MAXN=False):

    '''
    Restore CPU and GPU frequencies to low values.
    CPU frequencies are set to 729600, GPU to 408000000.
    '''

    if MOCK:
        print("Done")
        return
    
    CpuNum = 0
    CpuGovernorPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_governor"
    CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_setspeed"

    print(f"Restoring CPU/GPU frequencies")
    sysconfig.SetCPUFreq(CpuNum, "729600", CpuGovernorPath, CpuFrequencyPath)
    if MAXN:

        CpuNum = 4
        CpuGovernorPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_governor"
        CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_setspeed"

        sysconfig.SetCPUFreq(CpuNum, "729600", CpuGovernorPath, CpuFrequencyPath)
    
    # Set GPU frequency to 408000000
    sysconfig.SetGPUFreqMin("408000000", GpuMinFrequencyPath)
    sysconfig.SetGPUFreqMax("408000000", GpuMaxFrequencyPath)


def set_frequencies(CpuFreq, GpuFreq, MAXN=False):

    '''
    Set CPU and GPU frequencies.
    You may only set either CPU or GPU frequency in one call.
    If GPU frequency is set, CPU is set to a baseline value of 1881600.

    NOTE: This function was written for taking GPU benchmarks at a base fixed CPU speed.
          CPU frequency is hardcoded and CPU/GPU cant be set togther to avoid making mistakes regarding CPU frequency.
          Ideally this should be changed to allow both frequencies to be set at once.
    '''


    if CpuFreq is None and GpuFreq is None:
        print("No frequencies to set")
        return
    if CpuFreq is not None and GpuFreq is not None:
        print("Overload, please set only one frequency")
        return
    
    CpuNum = 0
    CpuGovernorPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_governor"
    CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_setspeed"
    
    # CPU freq
    if GpuFreq is None:
        print(f"Setting CPU frequency: {CpuFreq}")
        if MOCK: 
            return
        sysconfig.SetCPUFreq(CpuNum, CpuFreq, CpuGovernorPath, CpuFrequencyPath)
        if MAXN:

            CpuNum = 4
            CpuGovernorPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_governor"
            CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_setspeed"

            sysconfig.SetCPUFreq(CpuNum, CpuFreq, CpuGovernorPath, CpuFrequencyPath)
        return
    
    # GPU freq
    if CpuFreq is None:
        print(f"Setting GPU frequency: {GpuFreq}, CPU to 1881600")
        if MOCK: 
            return
        
        CpuNum = 0
        CpuGovernorPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_governor"
        CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_setspeed"

        sysconfig.SetCPUFreq(CpuNum, "1881600", CpuGovernorPath, CpuFrequencyPath)  
        if MAXN:
            CpuNum = 4
            CpuGovernorPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_governor"
            CpuFrequencyPath = f"/sys/devices/system/cpu/cpu{CpuNum}/cpufreq/scaling_setspeed"

            sysconfig.SetCPUFreq(CpuNum, "1881600", CpuGovernorPath, CpuFrequencyPath)

        sysconfig.SetGPUFreqMin(GpuFreq, GpuMinFrequencyPath)
        sysconfig.SetGPUFreqMax(GpuFreq, GpuMaxFrequencyPath)
        return
    return
    
#### Frequency handling #### --------------------------------------------


#### Subprocess handling #### -------------------------------------------

'''
Simply run two subprocesses, one for the benchmark and one for the stats.
The benchmark script will be run for 15s, while the stats process will continue logging for a longer time (15*15s).
This is to ensure that the stats process is still running when the benchmark process finishes.
At the end, the stats log will be trimmed to the duration of the benchmark.
'''

def run_stats(stats_command):
    subprocess.run(stats_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def run_benchmark_command(benchmark_command, log_file_name, label):
    with subprocess.Popen(benchmark_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
        with open(log_file_name, 'a') as log_file:
            log_file.write(f"{label}\n")
            for line in proc.stdout:
                if "Start timestamp:" in line:
                    log_file.write(line.replace("Start timestamp: ", ""))
                elif "End timestamp:" in line:
                    log_file.write(line.replace("End timestamp: ", ""))
                elif "Throughput:" in line:
                    log_file.write(line.replace("Throughput: ", "").replace(" inferences per second", ""))

def run_benchmark_gpudla(model, device, duration, freq, log_base):

    duration_stats = duration * 15

    model_name = os.path.splitext(os.path.basename(model))[0]
    print(f"Running benchmark for model: {model}, device: {device}")
    
    # Construct commands
    engine_path = f"engines/{model}/{device}.engine"
    if not os.path.exists(engine_path):
        print(f"Engine not found for model: {model}, device: {device}")
        return
    benchmark_command = f"python benchmark_gpudla.py --engine={engine_path} --duration={duration}"

    # This has been hardcoded for the specific models used
    if ('resnet' in model):
        benchmark_command += f" --input_shape='{batch_size},3,224,224' --output_shape='{batch_size},1000'"

    if ('yolo11' in model):
        benchmark_command += f" --input_shape='{batch_size},3,640,640' --output_shape='{batch_size},84,8400'"

    if ('yolov3' in model):
        benchmark_command += f" --input_shape='{batch_size},3,416,416' --output_shape='{batch_size},255,13,13;{batch_size},255,26,26'"
    
    if ('super' in model):
        benchmark_command += f" --input_shape='{batch_size},3,321,481' --output_shape='{batch_size},3,963,1443'"
    
    print("Running " + benchmark_command)
    log_dir = os.path.join(log_base, f"{model_name}/{device}/{freq}")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file_name = os.path.join(log_dir, "throughput.log")
    stats_command = f"python stats.py --interval 250 --log-file {log_file_name} --duration {duration_stats}"

    try:
        # Start the stats process
        stats_process = Process(target=run_stats, args=(stats_command,))
        stats_process.start()

        # Start the benchmark process
        ts_log = os.path.join(log_base, "timestamps.log")
        benchmark_process = Process(target=run_benchmark_command, args=(benchmark_command, ts_log, log_file_name))
        benchmark_process.start()
        benchmark_process.join()  # Wait for the benchmark process to complete

    finally:
        stats_process.join() 

#### Subprocess handling #### -------------------------------------------


#### Main #### -----------------------------------------------------------

MAXN = False

parser = argparse.ArgumentParser()
parser.add_argument('--maxn', action='store_true', help='MAXN mode')
parser.add_argument('--logbase', type=str, default='logs', help='Base log directory')
args = parser.parse_args()

if args.maxn:
    MAXN = True

init_sysconfig(MAXN)

# Read models from MODELS.txt
with open('MODELS.txt', 'r') as file:
    models = [line.strip() for line in file.readlines()]

# Iterate over each GPU frequency and run GPU benchmarks
for freq in gpufreq:
    set_frequencies(CpuFreq=None, GpuFreq=freq, MAXN=MAXN)
    for model in models:
        run_benchmark_gpudla(model, 'gpu', duration, freq, args.logbase)
        time.sleep(5)
    time.sleep(5)

# Iterate over each GPU frequency and run DLA benchmarks
for freq in gpufreq:
    set_frequencies(CpuFreq=None, GpuFreq=freq, MAXN=MAXN)
    for model in models:
        run_benchmark_gpudla(model, 'dla0', duration, freq, args.logbase)
        time.sleep(5)
    time.sleep(5)


trim_logs(f'{args.logbase}/timestamps.log')
export(f'{args.logbase}/')

restore_sysconfig(MAXN)

#### Main #### -----------------------------------------------------------
