import pandas as pd
import matplotlib.pyplot as plt
import json
import seaborn as sns

'''
Each folder is labeled logsA, logsB, logsC, logsD. For each letter we shift by zero or more indices two lists of models
indicating different combinations. For example:
logsA:
    ["efficientnet_b5", "efficientvit_b3", "resnet50_Opset17", "yolo11n", "yolov3-tiny-416-bs1", "super_resolution_bsd500-bs1"]
    ["efficientnet_b5", "efficientvit_b3", "resnet50_Opset17", "yolo11n", "yolov3-tiny-416-bs1", "super_resolution_bsd500-bs1"]
    (logsA contains combinations of the same models (diagonal values))
logsB:
    ["efficientnet_b5", "efficientvit_b3", "resnet50_Opset17", "yolo11n", "yolov3-tiny-416-bs1", "super_resolution_bsd500-bs1"]
    ["efficientvit_b3", "resnet50_Opset17", "yolo11n", "yolov3-tiny-416-bs1", "super_resolution_bsd500-bs1", "efficientnet_b5"]
    (logsB contains combinations of the same models but shifted by one index)

So on and so forth... we stop at D because it is enough to derive all possible combinations. 
For example logsB will first benchmark:
    how much effnet is slowed down by effvit
    how much effvit is slowed down by effnet

There is also a logZ to hold infomration regarding standalone execution
'''
models = ["efficientnet_b5", "efficientvit_b3", "resnet50_Opset17", "yolo11n", "yolov3-tiny-416-bs1", "super_resolution_bsd500-bs1"]
logs = ["A", "B", "C", "D"]

model_rename_dict = {
    'resnet50_Opset17': 'ResNet50',
    'efficientvit_b3': 'EfficientViT-B3',
    'efficientnet_b5': 'EfficientNet-B5',
    'yolov3-tiny-416-bs1': 'YOLOv3-Tiny',
    'yolo11n': 'YOLOv11n',
    'super_resolution_bsd500-bs1': 'Super-Resolution',
}

def generate_incident_matrix(models):
    """Generate an incident matrix initialized with zeros for the given models."""
    return {model: {other_model: 0.0 for other_model in models} for model in models}

def save_incident_matrix(incident_matrix, output_path, frequency=612000000):
    return_matrix = generate_incident_matrix(models)
    for model1, comparisons in incident_matrix.items():
        for model2, values in comparisons.items():
            return_matrix[model1][model2] = values[frequency]

    with open(output_path, "w") as f:
        json.dump(return_matrix, f, indent=4)

def plot_standalone(standalone, output_dir):

    def create_dataframe(standalone):
        data = {}
        for model, values in standalone.items():
            data[model] = values
        return pd.DataFrame(data)
    
    def plot_heatmap(dataframe, output_path):
        plt.figure(figsize=(10, 8))
        sns.heatmap(dataframe.T, annot=True, fmt=".2f", cmap="Greys", vmin=0.0, vmax=0.0, cbar=False, linewidths=0.5, linecolor='black')
        plt.title("Standalone Throughput")
        plt.xlabel("Model")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    df = create_dataframe(standalone)
    output_file = f"{output_dir}standalone_throughput.png"
    plot_heatmap(df, output_file)

def plot_incident_matrices(incident_matrix, output_dir):
    
    def create_dataframe(incident_matrix, frequency):
        data = {}
        for model1, comparisons in incident_matrix.items():
            data[model1] = {model2: values[frequency] for model2, values in comparisons.items()}
        return pd.DataFrame(data)

    def plot_heatmap(dataframe, frequency, output_path):
        plt.figure(figsize=(10, 8))
        sns.heatmap(dataframe.T, annot=True, fmt=".2f", cmap="Greys", vmin=0.0, vmax=0.0, cbar=False, linewidths=0.5, linecolor='black')
        plt.title(f"Incident Matrix for Frequency {frequency}")
        plt.xlabel("Model 2")
        plt.ylabel("Model 1")
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    frequencies = [612000000, 918000000]
    for freq in frequencies:
        df = create_dataframe(incident_matrix, freq)
        output_file = f"{output_dir}cm_{freq}.png"
        plot_heatmap(df, freq, output_file)

def plot_percentage_loss_matrices(incident_matrix, standalone, output_dir):
    
    def create_dataframe(incident_matrix, standalone, frequency):
        data = {}
        for model1, comparisons in incident_matrix.items():
            # skip super-res because the paper didnt include it
            if model1 == "super_resolution_bsd500-bs1":
                continue  # Skip Super-Resolution
            data[model1] = {model2: 100 * (1 - (values[frequency] / standalone[model1][frequency])) 
                            for model2, values in comparisons.items() if model2 != "super_resolution_bsd500-bs1"}
        return pd.DataFrame(data)
    
    def save_dataframe(dataframe, output_path):
        dataframe.T.to_json(output_path, orient='index', indent=4)

    def plot_heatmap_with_stats(dataframe, output_path):
        dataframe.rename(columns=model_rename_dict, inplace=True)
        dataframe.index = [model_rename_dict.get(model, model) for model in dataframe.index]

        row_means = dataframe.T.mean(axis=1)
        row_perr = [14.88, 14.88, 7.11, 14.65, 13.78] # sorry for hardcoded values

        plt.figure(figsize=(8, 5))
        sns.heatmap(dataframe.T, annot=True, fmt=".2f", cmap="coolwarm", vmin=0, vmax=100, cbar=False, linewidths=0.5, linecolor='black',
                    annot_kws={"size":12})

        # statistics table
        plt.text(dataframe.shape[1] + 0.55, -0.5, "Avg", va='center', ha='left', fontsize=14, fontweight='bold')
        plt.text(dataframe.shape[1] + 1.65, -0.5, "Err", va='center', ha='left', fontsize=14, fontweight='bold')
        for idx, (mean, perr) in enumerate(zip(row_means, row_perr)):
            plt.text(dataframe.shape[1] + 0.5, idx + 0.5, f"{mean:.2f}", va='center', ha='left', fontsize=12)
            plt.text(dataframe.shape[1] + 1.5, idx + 0.5, f"{perr:.2f}%", va='center', ha='left', fontsize=12)

        plt.xlabel("", fontsize=14)
        plt.ylabel("", fontsize=14)
        plt.xticks(ticks=[i + 0.5 for i in range(len(dataframe.columns))], labels=dataframe.columns, rotation=45, fontsize=12, ha='right')
        plt.yticks(ticks=[i + 0.5 for i in range(len(dataframe.index))], labels=[str(label) for label in dataframe.index], fontsize=12, va='center')
        plt.tight_layout()

        plt.savefig(output_path)
        plt.close()

    frequencies = [612000000, 918000000]
    for freq in frequencies:
        df = create_dataframe(incident_matrix, standalone, freq)
        save_dataframe(df, f"out/gpu-gpu_{freq}.json")
        output_file = f"{output_dir}percentage_loss_cm_{freq}.pdf"
        plot_heatmap_with_stats(df, output_file)

# ----------


def create_standalone(logs_standalone):
    standalone = {model: 0.0 for model in models}

    for model in models:
        model_path = logs_standalone + model + ".csv"
        model_df = pd.read_csv(model_path)
        model_tps = list(zip(model_df["Frequency"], model_df["Throughput"]))
        model_tps = {freq: throughput for freq, throughput in model_tps}
        standalone[model] = model_tps
    
    return standalone

def create_incident_matrix(logs_base_path):
    incident_matrix = generate_incident_matrix(models)
    for i in range(0, len(logs)):

        logs_config = logs_base_path + f"logs{logs[i]}/"
        logs1_csv = logs_config + "logs1/csv/"
        logs2_csv = logs_config + "logs2/csv/"
        
        models1 = models
        models2 = models[-i:] + models[:-i]

        print(models1)
        print(models2)

        for i in range(len(models1)):
            model1 = models1[i]
            model2 = models2[i]
            
            model1_path = logs1_csv + model1 + ".csv"
            model1_df = pd.read_csv(model1_path)
            model1_tps = list(zip(model1_df["Frequency"], model1_df["Throughput"]))
            model1_tps = {freq: throughput for freq, throughput in model1_tps}

            model2_path = logs2_csv + model2 + ".csv"
            model2_df = pd.read_csv(model2_path)
            model2_tps = list(zip(model2_df["Frequency"], model2_df["Throughput"]))
            model2_tps = {freq: throughput for freq, throughput in model2_tps}

            incident_matrix[model1][model2] = model1_tps
            incident_matrix[model2][model1] = model2_tps
    
    return incident_matrix

def load_incident_matrix(incident_matrix_path):
    with open(incident_matrix_path, "r") as f:
        incident_matrix = json.load(f)
    # Convert frequencies from strings to integers
    for model1, comparisons in incident_matrix.items():
        for model2, values in comparisons.items():
            incident_matrix[model1][model2] = {int(freq): throughput for freq, throughput in values.items()}
    return incident_matrix


logs_standalone = "./data/logs_20250412/logsZ/logs1/csv/"
logs_base_path = "./data/logs_20250412/"

standalone = create_standalone(logs_standalone)
incident_matrix = create_incident_matrix(logs_base_path)

output_dir = "./png/gpu-gpu/"
plot_incident_matrices(incident_matrix, output_dir)
plot_percentage_loss_matrices(incident_matrix, standalone, output_dir)
plot_standalone(standalone, output_dir)