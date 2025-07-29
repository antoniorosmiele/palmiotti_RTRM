import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from matplotlib.patches import Patch

tags = ["policy+refine", "allGPU+schedutil", "allDLA+schedutil", "dumb+schedutil"]
configurations = [f"config{i}" for i in range(1, 11)]
folder = "10config"
pline = 'vdd_in'

tag_display_mapping = {
    "policy+refine": "Policy",
    "policy+schedutil": "Decide + OS Governor",
    "policy+schedutilCPU": "Decide + Refine GPU",
    "allGPU+schedutil": "AllGPU + OS Governor",
    "allDLA+schedutil": "AllDLA + OS Governor",
    "dumb+schedutil": "Naive + OS Governor"
}

all_data = pd.DataFrame()

curr_conf = 1
got_power = False

for tag in tags:
    curr_conf = 1
    config_path = f"./data/{folder}/{tag}/"

    for config in configurations:

        csv_path = os.path.join(config_path, config)
        csv_files = [f for f in os.listdir(csv_path) if f.startswith("step") and f.endswith(".csv")]
        csv_files.sort(key=lambda x: int(x.replace("step", "").replace(".csv", "")))
        
        highest_step_csv = os.path.join(csv_path, csv_files[-1])
        data = pd.read_csv(highest_step_csv)
        
        app1_data = data[data['label'] == 'App 1'][[pline]].copy() / 1000

        not_met = 0
        if data['throughput'].isnull().any():
            not_met += data['throughput'].isnull().sum()
        not_met += (data['target'] - 0.5 > data['throughput']).sum()

        not_met = (not_met / len(data) * 100) if len(data) > 0 else 0

        app1_data['Workload'] = curr_conf
        app1_data['NotMet'] = not_met
        curr_conf += 1
        app1_data['Strategy'] = tag_display_mapping[tag]

        all_data = pd.concat([all_data, app1_data], ignore_index=True)


all_data = all_data[['Workload', "Strategy", "NotMet"]]
custom_palette = {
    tag_display_mapping["policy+refine"]: "#1f77b4",  # Blue
    tag_display_mapping["allGPU+schedutil"]: "#ff7f0e",  # Orange
    tag_display_mapping["allDLA+schedutil"]: "#2ca02c",  # Green
    tag_display_mapping["dumb+schedutil"]: "#d62728"  # Red
}

g = sns.catplot(
    data=all_data,
    x='Strategy',
    y='NotMet',
    kind='bar',
    col='Workload',
    palette=custom_palette,  
    order=[tag_display_mapping["policy+refine"], 
        tag_display_mapping["allGPU+schedutil"], 
        tag_display_mapping["allDLA+schedutil"], 
        tag_display_mapping["dumb+schedutil"]],
    edgecolor='black',
    height=2,
    aspect=0.75,
)

g.set(ylim=(0, 101))

g.fig.subplots_adjust(wspace=0.25)  

legend_elements = [
    Patch(facecolor="#1f77b4", edgecolor='black', label=tag_display_mapping["policy+refine"]),
    Patch(facecolor="#ff7f0e", edgecolor='black', label=tag_display_mapping["allGPU+schedutil"]),
    Patch(facecolor="#2ca02c", edgecolor='black', label=tag_display_mapping["allDLA+schedutil"]),
    Patch(facecolor="#d62728", edgecolor='black', label=tag_display_mapping["dumb+schedutil"]),
]

# g.fig.legend(
#     handles=legend_elements,
#     title="",
#     loc='upper center',
#     bbox_to_anchor=(0.5, 1.35),  # Move the legend further above the plots
#     ncol=4,  # Arrange legend items in a single row
#     fontsize=14
# )

# titles
g.fig.text(
    0.25,  
    1.0,  
    "Three-app Workloads",
    ha='center',
    va='center',
    fontsize=16,
)

g.fig.text(
    0.75,  
    1.0,  
    "Four-app Workloads",
    ha='center',
    va='center',
    fontsize=16,
)

g.fig.subplots_adjust(wspace=0.25, top=0.9, hspace=0.5)  

for ax in g.axes.flat:

    workload = ax.get_title().split(' = ')[-1]
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    if (int(workload) <= 5):
        ax.set_xlabel("Workload " + workload, fontsize=16)
    else:
        ax.set_xlabel("Workload " + str(int(workload) - 5), fontsize=16)
    ax.set_ylabel("Throughput Fail (%)", fontsize=16)
    workload = int(ax.get_title().split(' = ')[-1])
    ax.set_title(f"", fontsize=16)

for i, ax in enumerate(g.axes.flat):
    if i >= 5:  # After the first 5 workloads
        pos = ax.get_position()  # Get the current position of the axis
        ax.set_position([pos.x0 + 0.025, pos.y0, pos.width, pos.height])  

for ax in g.axes.flat:
    ax.set_xticklabels("")

g.savefig(f"./png/tpfail_NL.pdf")
