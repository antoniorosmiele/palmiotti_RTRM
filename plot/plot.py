import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import seaborn as sns
import argparse

'''
This script plots
- latency vs power consumption
- throughput vs power consumption
- performance per watt (PPW) vs frequency
- PPW ratio (PPW_DLA / PPW_GPU) vs frequency
- average PPW ratio across all models

It takes as arguments:
- csv_dir: directory containing LEGACY CSV files
- out_dir: directory to save the output plots
- vdd: column name for power consumption (default: 'VDD_IN_Avg')
'''

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Process CSV files and generate plots.")
parser.add_argument("csv_dir", type=str, help="Directory containing the input LEGACY CSV files.")
parser.add_argument("out_dir", type=str, help="Directory to save the output plots.")
parser.add_argument("vdd", type=str, default="VDD_IN_Avg", help="Column name for power consumption (e.g., 'VDD_IN_Avg').")
args = parser.parse_args()

csv_dir = args.csv
output_folder = args.out_dir
line = args.vdd

avg_ppw = {}

for csv_file in os.listdir(csv_dir):
    if csv_file.endswith('.csv'):

        model_name = (os.path.splitext(csv_file)[0])
        data = pd.read_csv(os.path.join(csv_dir, csv_file))

        # Filter out negative values (assosciated with failed execution)
        data = data[(data['Throughput'] >= 0) & (data[line] >= 0) & (data['Frequency'] >= 0)]

        device = data['Device']
        throughput = data['Throughput']
        latency = 1 / throughput * 1000
        power_consumption = data[line] / 1000
        frequency = data['Frequency']  # Assuming there is a Frequency column

        # Normalize frequency for dot size scaling
        min_size, max_size = 20, 200
        norm_frequency = (frequency - frequency.min()) / (frequency.max() - frequency.min())
        dot_sizes = norm_frequency * (max_size - min_size) + min_size

        color_map = {'gpu': 'green', 'dla0': 'red', 'dla1': 'red'}
        colors = device.map(color_map)



        # Plot latency ----------------------
        plt.figure(figsize=(10, 6))
        plt.scatter(latency, power_consumption, c=colors, s=dot_sizes)

        plt.xlabel('Latency (ms)')
        plt.ylabel(f'Power Consumption ({line}) (mW)')
        plt.title(f'Latency vs Power Consumption {line} for {model_name}')
        plt.legend(handles=[plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='GPU'),
                            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='DLA')])
        plt.grid(True)

        plt.savefig(os.path.join(output_folder, f"{model_name}_latency.png"))
        plt.close()



        # Plot throughput ----------------------
        plt.figure(figsize=(10, 6))
        plt.scatter(throughput, power_consumption, c=colors, s=dot_sizes)

        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.xlabel('Throughput (inf/s)', fontsize=14)
        plt.ylabel(f'Power Consumption (W)', fontsize=14)
        plt.legend(handles=[plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='GPU'),
                            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='DLA')])

        plt.grid(True)

        plt.savefig(os.path.join(output_folder, f"{model_name}_throughput.png"))
        plt.close()



        # Plot performance-per-watt ----------------------
        plt.figure(figsize=(10, 6))

        performance_per_watt = throughput / power_consumption

        plot_data = pd.DataFrame({
            'Frequency': frequency / 1e6,
            'Device': device,
            'PerformancePerWatt': performance_per_watt
        })
        pivot_data = plot_data.pivot_table(index='Frequency', columns='Device', values='PerformancePerWatt', aggfunc='mean')

        ax = pivot_data.plot(kind='bar', figsize=(10, 6))

        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.xlabel('Frequency (MHz)', fontsize=14)
        plt.ylabel(f'Performance per Watt (Throughput / Power Consumption)', fontsize=14)
        plt.legend(title='Device')

        # Make the frequency labels horizontal
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        
        plt.savefig(os.path.join(output_folder, f"{model_name}_ppw.png"))
        plt.close()



        # Plot ppw ratio (ppw_gpu / ppw_dla) ----------------------
        plt.figure(figsize=(10, 6))

        ppw_gpu = plot_data[plot_data['Device'] == 'gpu']['PerformancePerWatt'].reset_index(drop=True)
        ppw_dla = plot_data[plot_data['Device'] == 'dla0']['PerformancePerWatt'].reset_index(drop=True)

        min_length = min(len(ppw_gpu), len(ppw_dla))
        ppw_gpu = ppw_gpu[:min_length]
        ppw_dla = ppw_dla[:min_length]

        ppw_ratio = ppw_dla / ppw_gpu

        ratio_data = pd.DataFrame({
            'Frequency': frequency[:min_length] / 1e6,
            'PPW Ratio': ppw_ratio
        })

        avg_ppw_ratio = ppw_ratio.mean()
        avg_ppw[model_name] = avg_ppw_ratio

        ratio_data['Frequency'] = ratio_data['Frequency'].astype(float)
        ratio_data.sort_values(by='Frequency', inplace=True)

        ax = ratio_data.plot(
            x='Frequency',
            y='PPW Ratio',
            kind='bar',
            color='#1f77b4',
            figsize=(10, 6),
            legend=False
        )

        plt.xticks(fontsize=14, rotation=0)
        plt.yticks(fontsize=14)
        plt.xlabel('Frequency (MHz)', fontsize=14)
        plt.ylabel('PPW Ratio (PPW_DLA / PPW_GPU)', fontsize=14)

        # Line at y = 1
        plt.ylim(0, 2)
        plt.axhline(y=1, color='black', linestyle='--', linewidth=1.5)

        plt.savefig(os.path.join(output_folder, f"{model_name}_ppw_ratio.png"))
        plt.close()



# Plot average PPW ratio across all models inside csv folder ------------------
avg_ppw_df = pd.DataFrame(list(avg_ppw.items()), columns=['Model', 'Average PPW Ratio'])
plt.figure(figsize=(8, 8))
avg_ppw_df.sort_values(by='Average PPW Ratio', ascending=False, inplace=True)
avg_ppw_df['Color'] = avg_ppw_df['Average PPW Ratio'].apply(lambda x: '#1f77b4' if x > 1 else '#ff7f0e')

sns.barplot(
    data=avg_ppw_df,
    x='Model',
    y='Average PPW Ratio',
    palette=avg_ppw_df.set_index('Model')['Color'].to_dict()
)

plt.axhline(y=1.0, color='black', linestyle='--', linewidth=1.5)  # Line at y = 1.0
plt.xticks(rotation=45, ha='right', fontsize=12)
plt.yticks(fontsize=12)
plt.xlabel('Model', fontsize=14)
plt.ylabel('Average PPW Ratio (PPW_DLA / PPW_GPU)', fontsize=14)
plt.tight_layout()
plt.savefig(os.path.join(output_folder, "avg_ppw_ratio.png"))