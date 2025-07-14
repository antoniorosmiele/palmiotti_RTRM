# Policy Runtime simulator

This series of scripts is used to simulate the RTRM framework and the designed policy. It can also be used as a benchmarking script as it allows easy creation of custom configurations, optimal for co-execution benchmarks.

## Structure

- **App.py**: responsible for holding all necessary application information required to enact the Decide step.
- **Config.py**: module for executing a configuration
- **Engine.py**: module for the execution of a single TRT Engine
- **Decide.py**: module for enacting the Decide step given an application workload
- **Refine.py**: module for calculating the refinements to be made to the configuration cluster clock speed
- **Stats.py**: module for the execution of a power-line data collection process, as well as collecting information regarding currently running frequency
- **SysConfig.py**: module for performing unit DVFS

## Usage (Policy simulator)

### 1. Engine information

Before simulating the policy, it is necessary to collect benchmark information about the engine performance. This has to be loaded into the `engine_info/` folder. The necessary files are:
- **csv file**: this file holds information regarding the maximum throughput achievable by the engine on each unit at different GPU frequencies. CPU frequency is assumed to be a baseline low frequency. This csv file can be created through the **legacy benchmark** scripts located in `../benchmark/`.
    - csv shape:
    - Device, Frequency, Throughput, VDD_IN_Avg, VDD_CPU_GPU_CV_Avg, VDD_SOC_Avg, VDD_IN_Sum,VDD_CPU_GPU_CV_Sum, VDD_SOC_Sum
- **json file**: this file holds information regarding the input and output shapes of the engine. It can be generated through the `App.py` module, function `export_app_io`.
- **TRT log file**: from this file (log of TensorRT `trtexec` execution)we extract the number of application DLA subgraphs. This file is generated from the `../benchmark/build.py` script, or alternatively by saving the log from the `trtexec` TRT Engine build
- **TRT Engine**: the engine file is needed to run the application either on GPU or DLA. It can be built using the `../benchmark/build.py` script or the `trtexec` command ran with the appropriate flags
    - for the list of flags, look into `build.py`

Example files can be already found as the resnet50_Opset17/ example. Other files have to follow the same structure as depicted in these examples.
NOTE: TRT Engine has been saved in `../benchmark/engines/` folder, however they can be moved provided the appropriate change to the configuration json file.

### 2. Building the configuration

Use the `engine_info/apps.json` file to list the applications and their target throughput. An example has already been provided for the expected structure.

Creating a configuration file, holding the GPU/CPU running frequency and their device mappings can be done by running
```
python Decide.py
```

It will create a `config.json` file which will be used by Config.py to execute the reported configuration. It will have this shape.

``` 
{
    "frequencies": {
        "cpu":      # CPU Frequency
        "gpu":      # GPU Frequency
        "maxn":     # Boolean if board is running at MAXN (all 8 cores CPU frequency has to be updated)
    },
    "models": [
        {   
            "name":         # Engine name
            "engineinfo":   # Path to the engine_info (holding I/O shapes)
            "enginepath":   # Path to application engine
            "device":       # Running device
            "throughput":   # Target throughput (negative for no limit)
        },
        ...
    ]
}
```

### 3. Executing the configuration

`runConfig.py` provides an example script for the execution of the configuration as read from `config.json` file.
We use two modules, SysConfig.py to handle cluster frequencies and Config.py to handle application and stats-logging execution

We first set the CPU/GPU frequency through `SysConfig.set_frequencies`. Then we use `Config.run` to execute the configuration of applications. The 'run' function will synchronize all processes (1 per application + 1 for logging power+freq stats) and run them in concurrence. It will periodically print a list of heartbeats per each application (printing their throughput) and information regarding power and frequency. An example of heartbeat printing example:

```
[14/07/2025-17:22:43] [Engine.py] [I] 	Heartbeat for resnet50_Opset17: 69.99 img/s (Actual throughput: 110.14 img/s)
[14/07/2025-17:22:43] [Engine.py] [I] 	Heartbeat for efficientnet_b5: 50.01 img/s (Actual throughput: 73.00 img/s)
[14/07/2025-17:22:43] [Engine.py] [I] 	Heartbeat for yolov3-tiny-416-bs1: 40.02 img/s (Actual throughput: 65.20 img/s)
[14/07/2025-17:22:43] [Stats.py] [I] 	Heartbeat from Stats.py
[14/07/2025-17:22:43] [Stats.py] [I] 		Line                Average Power       Average Partial Power
[14/07/2025-17:22:43] [Stats.py] [I] 		VDD_IN              9336.88             9336.88             
[14/07/2025-17:22:43] [Stats.py] [I] 		VDD_CPU_GPU_CV      4097.86             4097.86             
[14/07/2025-17:22:43] [Stats.py] [I] 		VDD_SOC             1902.10             1902.10             
[14/07/2025-17:22:43] [Stats.py] [I] 		GPU Frequency: 	918000000 MHz
[14/07/2025-17:22:43] [Stats.py] [I] 		CPU0 Frequency: 	1984000 MHz
[14/07/2025-17:22:43] [Stats.py] [I] 		CPU4 Frequency: 	1984000 MHz
```

- "Average power": power averaged from the beginning of execution
- "Average partial power": power averaged between two different heartbeats

At the end of execution, it will automatically calculate the refinments to be made regarding CPU/GPU frequencies. As such:

```
[14/07/2025-17:25:18] [Config.py] [I] Refining results:
[14/07/2025-17:25:18] [Config.py] [I]	New CPU frequency: 960000
[14/07/2025-17:25:18] [Config.py] [I]	New GPU frequency: 510000000
```

You will need to manually edit the `config.json` file in order to refine the configuration. After editing the configuration you can simply rerun it (in this case through `runConfig.py`).

At the end of each execution, `runConfig.py` will use `Config.export_heartbeats` to export the collected heartbeats across all processes to a csv log file. For example:

```
engine_name,device,cpu,gpu,target,throughput,actual_throughput,vdd_in,vdd_cpu_gpu_cv,vdd_soc,run_gpu_freq,run_cpu0_freq,run_cpu4_freq
yolov3-tiny-416-bs1,DLA0,960000,714000000,40.00,40.03,66.02,9400.61,4115.26,1915.51,918000000.00,1984000.00,1984000.00
efficientnet_b5,GPU,960000,714000000,50.00,50.00,76.27,9400.61,4115.26,1915.51,918000000.00,1984000.00,1984000.00
resnet50_Opset17,DLA0,960000,714000000,70.00,69.98,112.95,9400.61,4115.26,1915.51,918000000.00,1984000.00,1984000.00
```

## Usage (Benchmark)

You can also utilize this script for benchmarking, however there will be a difference between the output csv and the LEGACY csv provided by `../benchmark/`.

It is possible to simply create a custom configuration file (as long as it has the expected structure) and run it through `runConfig.py`. For example, in order to benchmark resnet50_Opset17 on the GPU at CPU@729600 and GPU@918000000 without any limit on maximum throguhput, create a `config.json` as:

``` 
{
    "frequencies": {
        "cpu": 729600     
        "gpu": 918000000      
        "maxn": True     
    },
    "models": [
        {   
            "name": "resnet50_Opset17"   
            "engineinfo": "PATH/TO/resnet50_Opset17.json"
            "enginepath": "PATH/TO/resnet50_Opset17.engine"
            "device": GPU
            "throughput": -1
        },
    ]
}
```