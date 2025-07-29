import pandas as pd
import matplotlib.pyplot as plt
import json
import seaborn as sns

# Global font size variable
FONT_SIZE = 14

models = ["resnet50_Opset17", "yolov3-tiny-416-bs1", "super_resolution_bsd500-bs1"]
logs = ["A", "B", "C"]


model_rename_dict = {
    'resnet50_Opset17': 'ResNet50',
    'yolov3-tiny-416-bs1': 'YOLOv3-Tiny',
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
        plt.figure(figsize=(8, 8))
        sns.heatmap(dataframe.T, annot=True, fmt=".2f", cmap="Greys", vmin=0.0, vmax=0.0, cbar=False, linewidths=0.5, linecolor='black')
        plt.xlabel("Model", fontsize=FONT_SIZE)
        plt.ylabel("Frequency", fontsize=FONT_SIZE)
        plt.xticks(fontsize=FONT_SIZE)
        plt.yticks(fontsize=FONT_SIZE)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    df = create_dataframe(standalone)
    output_file = f"{output_dir}standalone_throughput.png"
    plot_heatmap(df, output_file)

def plot_incident_matrices(incident_matrix, output_dir):
    
    print(json.dumps(incident_matrix, indent=4))
    def create_dataframe(incident_matrix, frequency):
        data = {}
        for model1, comparisons in incident_matrix.items():
            data[model1] = {model2: values[frequency] for model2, values in comparisons.items()}
        return pd.DataFrame(data)

    def plot_heatmap(dataframe, frequency, output_path):
        plt.figure(figsize=(8, 8))
        sns.heatmap(dataframe.T, annot=True, fmt=".2f", cmap="Greys", vmin=0.0, vmax=0.0, cbar=False, linewidths=0.5, linecolor='black')
        plt.xlabel("Model 2", fontsize=FONT_SIZE)
        plt.ylabel("Model 1", fontsize=FONT_SIZE)
        plt.xticks(fontsize=FONT_SIZE)
        plt.yticks(fontsize=FONT_SIZE)
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
            data[model1] = {model2: 100 * (1 - (values[frequency] / standalone[model1][frequency])) for model2, values in comparisons.items()}
        return pd.DataFrame(data)
    
    def save_dataframe(dataframe, output_path):
        # Transpose the dataframe before saving
        dataframe.T.to_json(output_path, orient='index', indent=4)

    def plot_heatmap(dataframe, frequency, output_path):
        dataframe.rename(columns=model_rename_dict, inplace=True)
        dataframe.index = [model_rename_dict.get(model, model) for model in dataframe.index]
        plt.figure(figsize=(6, 5))
        sns.heatmap(dataframe.T, annot=True, fmt=".2f", cmap="coolwarm", vmin=0, vmax=100, cbar=True, linewidths=0.5, linecolor='black',
                annot_kws={"size": 12})  # Increase annotation font size
        plt.xlabel("Model 2 (DLA)", fontsize=14)  # Increase x-axis label font size
        plt.ylabel("Model 1 (DLA)", fontsize=14)  # Increase y-axis label font size
        plt.xticks(fontsize=12)  # Increase x-axis tick font size
        plt.yticks(fontsize=12)  # Increase y-axis tick font size
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    frequencies = [612000000, 918000000]
    for freq in frequencies:
        df = create_dataframe(incident_matrix, standalone, freq)
        save_dataframe(df, f"out/dla-dla_{freq}.json")
        output_file = f"{output_dir}percentage_loss_cm_{freq}.png"
        plot_heatmap(df, freq, output_file)

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

logs_standalone = "./data/logs_20250414/logsZ/logs1/csv/"
logs_base_path = "./data/logs_20250418/"

standalone = create_standalone(logs_standalone)
incident_matrix = create_incident_matrix(logs_base_path)

output_dir = "./png/dla-dla/"
plot_incident_matrices(incident_matrix, output_dir)
plot_percentage_loss_matrices(incident_matrix, standalone, output_dir)
plot_standalone(standalone, output_dir)
