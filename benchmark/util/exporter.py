import os
import re
import pandas as pd

# Regular expression to match the log entries
log_entry_pattern = re.compile(
    r"\[.*?\] VDD_IN: (\d+\.\d+) mW, VDD_CPU_GPU_CV: (\d+\.\d+) mW, VDD_SOC: (\d+\.\d+) mW"
)

def process_log_file(log_file):
    vdd_in_sum = 0
    vdd_cpu_gpu_cv_sum = 0
    vdd_soc_sum = 0
    entry_count = 0
    throughput = None

    with open(log_file, 'r') as file:
        lines = file.readlines()

        if not lines:
            return [-1, -1, -1, -1, -1, -1, -1]

        if lines:
            throughput_line = lines[0].strip()
            throughput_match = re.match(r'Throughput: (.+)', throughput_line)
            if throughput_match:
                throughput = throughput_match.group(1)
        
        for line in lines[1:]:
            match = log_entry_pattern.search(line)
            if match:
                vdd_in_sum += float(match.group(1))
                vdd_cpu_gpu_cv_sum += float(match.group(2))
                vdd_soc_sum += float(match.group(3))
                entry_count += 1

    if entry_count > 0:
        vdd_in_avg = vdd_in_sum / entry_count
        vdd_cpu_gpu_cv_avg = vdd_cpu_gpu_cv_sum / entry_count
        vdd_soc_avg = vdd_soc_sum / entry_count
        return [round(vdd_in_avg, 3), 
                round(vdd_cpu_gpu_cv_avg, 3), 
                round(vdd_soc_avg, 3), 
                round(vdd_in_sum, 3), 
                round(vdd_cpu_gpu_cv_sum, 3), 
                round(vdd_soc_sum, 3), 
                throughput]
    else:
        return [None, None, None, None, None, None, throughput]

def process_model_logs(model_name, base_dir='logs/csv', logs_base_dir='logs/'):
    model_dir = os.path.join(logs_base_dir, model_name)
    csv_dir = base_dir
    os.makedirs(csv_dir, exist_ok=True)
    data = []

    for device in os.listdir(model_dir):
        device_dir = os.path.join(model_dir, device)
        for freq in os.listdir(device_dir):
            freq_dir = os.path.join(device_dir, freq)
            for throughput_file in os.listdir(freq_dir):
                log_file = os.path.join(freq_dir, throughput_file)
                vdd_in_avg, vdd_cpu_gpu_cv_avg, vdd_soc_avg, vdd_in_sum, vdd_cpu_gpu_cv_sum, vdd_soc_sum, throughput = process_log_file(log_file)
                if vdd_in_avg is not None and throughput is not None:
                    data.append({
                        'Model': model_name,
                        'Device': device,
                        'Frequency': freq,
                        'Throughput': throughput,
                        'VDD_IN_Avg': vdd_in_avg,
                        'VDD_CPU_GPU_CV_Avg': vdd_cpu_gpu_cv_avg,
                        'VDD_SOC_Avg': vdd_soc_avg,
                        'VDD_IN_Sum': vdd_in_sum,
                        'VDD_CPU_GPU_CV_Sum': vdd_cpu_gpu_cv_sum,
                        'VDD_SOC_Sum': vdd_soc_sum
                    })

    df = pd.DataFrame(data)
    df.set_index(['Device', 'Frequency', 'Throughput'], inplace=True)
    csv_file = os.path.join(csv_dir, f'{model_name}.csv')
    df.to_csv(csv_file)

def export(logs_base_dir='logs/'):
    models = [d for d in os.listdir(logs_base_dir) if os.path.isdir(os.path.join(logs_base_dir, d))]
    for model in models:
        process_model_logs(model, base_dir=logs_base_dir+"/csv", logs_base_dir=logs_base_dir)

if __name__ == "__main__":
    export('/home/davide/Desktop/logs/logs_20250412/logsA/logs2')