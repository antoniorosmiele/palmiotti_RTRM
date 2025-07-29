import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

# Load the base directory containing configurations
tags = ["policy+refine", "allGPU+schedutil", "dumb+schedutil", "allDLA+schedutil"]

# Create a mapping for tag display names
tag_display_mapping = {
    "policy+refine": "Policy",
    "policy+schedutil": "Decide + OS Governor",
    "policy+schedutilCPU": "Decide + Refine GPU",
    "allGPU+schedutil": "AllGPU + OS Governor",
    "allDLA+schedutil": "AllDLA + OS Governor",
    "dumb+schedutil": "Naive + OS Governor"
}

configurations = [f"config{i}" for i in range(1, 11)]

folder = "10config"
curr_conf = 1

# Initialize a dictionary to store the percentage of workloads not meeting targets for each tag
tag_failure_percentages = {}

for tag in tags:
    config_path = f"./data/{folder}/{tag}/"
    curr_conf = 1
   
    all_data = pd.DataFrame()

    for config in configurations:
        csv_path = os.path.join(config_path, config)
        csv_files = [f for f in os.listdir(csv_path) if f.startswith("step") and f.endswith(".csv")]
        csv_files.sort(key=lambda x: int(x.replace("step", "").replace(".csv", "")))
        
        # get the CSV file with the highest step index (aka take the last step of the iteration, usually 0)
        highest_step_csv = os.path.join(csv_path, csv_files[-1])
        data = pd.read_csv(highest_step_csv)
        
        data['Normalized Throughput'] = data['throughput'] / data['target']
        data['Workload'] = curr_conf
        curr_conf += 1

        all_data = pd.concat([all_data, data], ignore_index=True)

    num_failures = (all_data['Normalized Throughput'] < 0.99).sum()
    num_failures += pd.isna(all_data['Normalized Throughput']).sum()
    print(f"Tag: {tag}")
    print(all_data['Normalized Throughput'])
    print(f"Failures for tag {tag}: {num_failures}") 
    total_workloads = len(all_data)
    failure_percentage = (num_failures / total_workloads) * 100 if total_workloads > 0 else 0
    tag_failure_percentages[tag_display_mapping[tag]] = failure_percentage

    all_data.rename(columns={'label': 'Application'}, inplace=True)
    all_data.rename(columns={'device': 'Device'}, inplace=True)

    g = sns.catplot(
        data=all_data,
        x='Application',
        y='Normalized Throughput',
        hue='Device',
        palette={'GPU': '#90ee90', 'DLA0': '#ff9999', 'DLA1': '#d16262'},
        kind='bar',
        col='Workload',
        order=['App 1', 'App 2', 'App 3'],
        edgecolor='black',
        height=4,
        aspect=0.6,
    )

    g.set_axis_labels("", "Normalized Throughput", fontsize=14)
    g.set_xticklabels(fontsize=14)
    g.set_yticklabels(fontsize=14)
    g.legend.set_title("Device")
    for text in g.legend.texts:
        text.set_fontsize(12)

    # Draw a horizontal line at y = 1.0
    for ax in g.axes.flat:
        ax.axhline(y=1.0, color='black', linestyle='--', linewidth=2)

    g.savefig(f"./png/{folder}__{tag}.png")

# failure percentages
failure_data = pd.DataFrame({
    'Strategy': list(tag_failure_percentages.keys()),
    'Failure Percentage': list(tag_failure_percentages.values())
})

plt.figure(figsize=(4, 5))
sns.barplot(data=failure_data, x='Strategy', y='Failure Percentage', palette='viridis')
plt.ylabel('Failure Percentage (%)', fontsize=14)
plt.title('Three concurrent applications', fontsize=14)
plt.xticks(rotation=45, ha='right', fontsize=12)
plt.ylim(0, 100)
plt.tight_layout()

# Save the plot
output_path = f"./png/perc_tp.png"
plt.savefig(output_path)
plt.show()
