import pandas as pd
import matplotlib.pyplot as plt
import glob
import numpy as np

'''
This is used to print the "Motivating example" figures, seperately. It takes as input the data from a benchmark (non-legacy) as s1, s2, s3, and s4. (scenario 1, 2, 3, and 4).
'''

csv_files = glob.glob("data/s*.csv")

engine_name_mapping = {
    'resnet50_Opset17': 'ResNet50',
    'efficientnet_b5': 'EfficientNet-B5',
    'yolov3-tiny-416-bs1': 'YOLOv3-Tiny'
}

device_map = {
    "GPU": "GPU",
    "DLA0": "DLA0",
    "DLA1": "DLA1"
}

for file in csv_files:
    df = pd.read_csv(file)
    desired_order = ['resnet50_Opset17', 'efficientnet_b5', 'yolov3-tiny-416-bs1']

    engine_names = df['engine_name'].unique()
    vdd_in = df['vdd_in'].iloc[0] / 1000 

    fig, ax1 = plt.subplots(figsize=(6, 4))  

    relative_throughputs = []
    for engine_name in desired_order:
        if engine_name in engine_names:
            engine_data = df[df['engine_name'] == engine_name]
            relative_throughput = (engine_data['actual_throughput'] / engine_data['target']).mean()
        else:
            relative_throughput = 0 
        relative_throughputs.append(relative_throughput)

    bar_height = 0.8
    y_positions = np.arange(len(desired_order))  

    throughput_colors = ['green' if rt > 1 else 'red' for rt in relative_throughputs]

    ax1.barh(y_positions, relative_throughputs, color=throughput_colors, edgecolor='black', height=bar_height, label='Relative Throughput')
    ax1.set_xlabel('Normalized Throughput', fontsize=16)
    ax1.set_xlim(0, 2)
    ax1.xaxis.set_ticks(np.arange(0, 3, 0.5))
    ax1.tick_params(axis='x', labelsize=14)
    ax1.set_ylabel('Engine Name')

    ax1.axvline(x=1, ymin=0, ymax=0.8, color='black', linestyle='--', linewidth=1, label='Ratio = 1')

    #vdd_in
    ax2 = ax1.twiny()
    vdd_bar = ax2.barh([len(desired_order)], [vdd_in], color='gold', edgecolor='black', height=bar_height)
    ax2.set_xlabel('Power Consumption (W)', fontsize=16)
    ax2.set_xlim(0, 13)
    ax2.tick_params(axis='x', labelsize=14)

    for bar in vdd_bar:
        width = bar.get_width()
        ax2.text(width + 0.1, bar.get_y() + bar.get_height() / 2, f'{width:.2f}', va='center', ha='left', fontsize=16)

    y_labels = [f"{engine_name_mapping.get(name, name)} ({device_map[df[df['engine_name'] == name]['device'].iloc[0]]})" if name in engine_names else name for name in desired_order] + [f"GPU @ {gpu_frequency / 1e6} MHz"]
    ax1.set_yticks(np.append(y_positions, len(desired_order)))
    ax1.set_yticklabels(y_labels, fontsize=14, va='center')

    plt.tight_layout(pad=2.0) 

    output_filename = f"{file.split('.')[0]}_plot.png"
    plt.savefig(output_filename, bbox_inches='tight')
    plt.close()

    print(f"Plot saved as {output_filename}")