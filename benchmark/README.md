# Legacy benchmark script

These scripts can be used for benchmarking TRT Engines in terms of throughput (and maximum throughput achievable) and power consumption.

These scripts have been developed for standalone execution of models, as its idea is to run the same engine at different GPU frequencies and gain information regarding:
- Throughput vs Power consumption
- Maximum throughput achievable
- Performance Per Watt

These scripts have to be used to create the necessary csv which holds information regarding engine characteristics reported above.

## Structure

For all scripts, make sure to use -h to get an understanding of the available flags.

- **benchmark_gpudla.py**: main benchmark script for a single execution of the model
- **build.py**: script for building the necessary TRT Engines with the appropriate flags
- **main.py**: main script for running the whole standalone benchmark and autogenerating the necessary csvs
- **stats.py**: script for logging the power consumption from the Jetson power lines.

## Usage

### Step 1: Build engines

Before executing benchmark the necessary TRT Engines have to be built. Begin by inserting the ONNX models to be built into the `onnx/` folder. Do note that there is no script reported for building the ONNX files.

After the appropriate ONNX files are loaded into the `onnx/` folder, you can use the `build.py` script to build the TRT Engines using `trtexec`. It will build the engines using the appropriate expected flags.

```
python build.py
```

Engines will be saved into the `engines/` folder. TRT build logs are also saved, as they are **necessary for the policy scripts to work**

### Step 2: Run benchmarks

Once the engines have been built, you can use

```
python benchmark_gpudla.py --engine=ENGINE
```

to execute a benchmark run. By default, it will print the maximum throughput achievable by the engine.

In order to instead run multiple benchmarks *and* log information regarding power consumption, use `main.py` as such.

```
sudo python main.py
```

Do note that all the scripts have multiple flags that may be useful to activate. As a critical example, the ```--maxn``` flag of `main.py` is used to indicate that the board is running at MAXN and CPU Frequencies 4-7 have to be changed.

**NOTE**: before executing main, ensure:
- The proper model list (list of engine names) is written in MODELS.txt (written as MODEL1\nMODEL2\n... where \n is newline)
- The `logs/` folder is empty, except for a single **EMPTY** file named `timestamps.log`

At the end of main, in the `logs/` folder you will have:
- `csv/` which contain the benchmark csvs
    - Device, Frequency, Throughput, VDD_IN_Avg, VDD_CPU_GPU_CV_Avg, VDD_SOC_Avg, VDD_IN_Sum, VDD_CPU_GPU_CV_Sum, VDD_SOC_Sum
    - We have the average and cumulative sum of the power lines
- `<MODEL>/` which contain the power logs of all the benchmark run at different frequencies and different devices
