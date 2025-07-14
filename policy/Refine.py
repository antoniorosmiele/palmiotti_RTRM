'''
This module implements the Refine algorithm for adjusting CPU and GPU frequencies based on application throughput / target delta.
"refine" outputs the new CPU and GPU frequencies based on the current frequencies and the application throughputs.
'''

class Refine:

    def __init__(self):
        # Available CPU/GPU frequencies
        self.CpuFreqArray = ["576000", "652800", "729600", "806400", "883200", "960000", "1036800", "1113600", "1190400", "1267200", "1344000", "1420800", "1497600", "1574400", "1651200", "1728000", "1804800", "1881600"]
        self.GpuFreqArray = ["306000000", "408000000", "510000000", "612000000", "714000000", "816000000", "918000000"]

    def refine(self, in_heartbeats, cpuFreq, gpuFreq):
        '''
        Refines the CPU and GPU frequencies based on the throughput of applications.

        in_heartbeats : list of tuples (name, device, target_throughput, heartbeats, heartbeats_actual) [As taken from Engine.get_heartbeats()]
        '''
        # appsList : list of (app_name, target_throughput, last_actual_throughput)
        # It is looking at the last actual throughput (throughput without autosleep) and calculating the delta based on this last value
        appsList = []
        for name, _, target_tp, _, heartbeats_actual in in_heartbeats:
            appsList.append((name, target_tp, heartbeats_actual[-1]))

        cpuFreq = int(cpuFreq)
        gpuFreq = int(gpuFreq)

        delta = 0
        cpu_factor = 1.71
        gpu_factor = 1.0

        for (_, target_throughput, actual_throughput) in appsList:
            ratio = target_throughput / actual_throughput
            delta = max(delta, ratio)

        new_gpuFreq = gpuFreq
        new_cpuFreq = cpuFreq
        if delta > 1.0:
            # Accelerate
            if gpuFreq != 918000000:
                new_gpuFreq = gpuFreq * (delta ** gpu_factor)
                new_gpuFreq = min((freq for freq in self.GpuFreqArray if int(freq) > new_gpuFreq), default=self.GpuFreqArray[-1])
            else:
                if cpuFreq == 1881600:
                    # Already at max CPU freq
                    new_cpuFreq = cpuFreq
                    return new_cpuFreq, new_gpuFreq
                new_cpuFreq = cpuFreq * (delta ** cpu_factor)
                new_cpuFreq = min((freq for freq in self.CpuFreqArray if int(freq) > new_cpuFreq), default=self.CpuFreqArray[-1])
                new_gpuFreq = gpuFreq
        else:
            # Decelerate
            if gpuFreq != 306000000:
                new_gpuFreq = gpuFreq * (delta ** gpu_factor)
                new_gpuFreq = min((freq for freq in self.GpuFreqArray if int(freq) > new_gpuFreq), default=self.GpuFreqArray[0])
            else:
                if cpuFreq == 576000:
                    # Already at min CPU freq
                    new_cpuFreq = cpuFreq
                    return new_cpuFreq, new_gpuFreq
                new_cpuFreq = cpuFreq * (delta ** cpu_factor)
                new_cpuFreq = min((freq for freq in self.CpuFreqArray if int(freq) > new_cpuFreq), default=self.CpuFreqArray[0])
                new_gpuFreq = gpuFreq

        return new_cpuFreq, new_gpuFreq
