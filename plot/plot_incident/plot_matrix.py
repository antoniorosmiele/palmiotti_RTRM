import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import numpy as np
from matplotlib.colors import ListedColormap

model_rename_dict = {
    'resnet50_Opset17': 'ResNet50',
    'efficientvit_b3': 'EfficientViT-B3',
    'efficientnet_b5': 'EfficientNet-B5',
    'yolov3-tiny-416-bs1': 'YOLOv3-Tiny',
    'yolo11n': 'YOLOv11n',
    'super_resolution_bsd500-bs1': 'Super-Resolution',
}

def load_matrix_from_file(file_path):
    """
    Loads the matrix from a JSON file.
    """
    with open(file_path, "r") as f:
        matrix = json.load(f)
    return matrix

def calculate_average_matrices(matrices):

    # aggregate all matrices into a single DataFrame
    combined_df = pd.DataFrame()
    for _, df in matrices:
        combined_df = combined_df.add(df, fill_value=0)
    combined_df = combined_df.sum(axis=1).to_frame(name="Aggregated Value")

    # count the number of non-NaN entries for each cell
    count_df = pd.DataFrame()
    for _, df in matrices:
        count_df = count_df.add(~df.isna(), fill_value=0) 
    count_df = count_df.sum(axis=1).to_frame(name="Count")

    # calculate the average for each row
    combined_df["Average"] = combined_df["Aggregated Value"] / count_df["Count"]
    combined_df = combined_df.drop(columns=["Aggregated Value"])

    return combined_df
        

def calculate_percentage_error_matrices(matrices, avg):

    percentage_error_matrices = []

    for _, matrix in matrices:
        # for each value in the matrix[model1][model2], take the average from the matrix corresponding to avg[model1] 
        # and percerror[model1][model2] = (matrix[model1][model2] - avg[model1]) / avg[model1] * 100
        perc_error_df = matrix.copy()
        for model1 in perc_error_df.index:
            for model2 in perc_error_df.columns:
                if pd.notna(avg.loc[model1, "Average"]):
                    perc_error_df.loc[model1, model2] = abs(
                        (perc_error_df.loc[model1, model2] - avg.loc[model1, "Average"]) / avg.loc[model1, "Average"]
                    ) * 100
                else:
                    perc_error_df.loc[model1, model2] = np.nan
        percentage_error_matrices.append((_, perc_error_df))

    return percentage_error_matrices

def normalize_matrices(matrices):
    """
    Normalizes all matrices to the same size by filling missing values with NaN.
    Removes empty rows and columns (entirely NaN) from each matrix.
    Renames models using the model_rename_dict.
    """
    all_models = set()
    for _, df in matrices:
        # drop rows and columns that are entirely NaN
        all_models.update(df.index)
        all_models.update(df.columns)

    all_models = sorted(all_models)

    normalized_matrices = []
    for file_name, df in matrices:
        df = df.reindex(index=all_models, columns=all_models, fill_value=np.nan)
        df.rename(index=model_rename_dict, columns=model_rename_dict, inplace=True)
        normalized_matrices.append((file_name, df))

    return normalized_matrices

def plot_matrices_side_by_side(folder_path, output_path):
    """
    Loads all matrices from a folder, normalizes them, inverts their order, and plots them side by side.
    Adds device information (e.g., GPU, DLA) to the x and y labels based on the file name.
    """

    matrix_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    matrices = []

    for file in matrix_files:
        file_path = os.path.join(folder_path, file)
        matrix = load_matrix_from_file(file_path)
        df = pd.DataFrame(matrix).T  # transpose for correct orientation
        matrices.append((file, df))

    avg = calculate_average_matrices(matrices)
    perc = calculate_percentage_error_matrices(matrices, avg)
    avg_perc = calculate_average_matrices(perc)

    
    data_df = pd.DataFrame({
        "Average": avg["Average"],
        "Average Percentage Error": avg_perc["Average"]
    })
    
    
    matrices = normalize_matrices(matrices)
    matrices = matrices[::-1]
    matrices.append(("Summary Table", data_df))

    num_matrices = len(matrices)
    if num_matrices == 0:
        print("No matrices found in the folder.")
        return
    
    for i, (file_name, df) in enumerate(matrices):
        matrices[i] = (file_name, df.dropna(axis=1, how='all')) # drop empty columns

    widths = [df.shape[1] for _, df in matrices]
    fig, axes = plt.subplots(
        1, num_matrices, 
        figsize=(sum(widths) * 0.9, 4),
        gridspec_kw={'width_ratios': widths}, 
        constrained_layout=False
    )

    plt.subplots_adjust(wspace=0.4, bottom=0.4, top=0.9) 

    for i, (file_name, df) in enumerate(matrices):
        
        devices = file_name.replace(".json", "").split("-")  
        y_device = devices[0].upper() if len(devices) > 0 else "Y Device"
        x_device = devices[1].upper() if len(devices) > 1 else "X Device"

        cmap = ListedColormap(['white']) if file_name == "Summary Table" else "coolwarm"

        ax = axes[i] if num_matrices > 1 else axes
        sns.heatmap(
            df,
            annot=True,
            fmt=".2f",
            cmap=cmap,
            vmin=0,
            vmax=100,
            cbar=False,
            linewidths=1,  
            linecolor='black',
            ax=ax,
            mask=df.isna(),  # mask NaN values
        )
        
        # add rectangles over NaN cells to hide borders
        for y in range(df.shape[0]):
            for x in range(df.shape[1]):
                if pd.isna(df.iloc[y, x]):
                    rect = plt.Rectangle(
                        (x, y), 1, 1,  
                        facecolor="white",  
                        edgecolor="none",  
                        zorder=3 
                    )
                    ax.add_patch(rect)

        
        if file_name == "Summary Table":
            ax.xaxis.tick_top()  
            ax.xaxis.set_label_position("top")  
            ax.set_xticks([0.5, 1.5])  
            ax.set_xticklabels(["Avg", "% Err"], fontsize=12)  
            ax.yaxis.tick_right() 
            ax.yaxis.set_label_position("right")  
            ax.set_yticklabels([model_rename_dict.get(label, label) for label in df.index], rotation=0, fontsize=12)
            ax.tick_params(axis='y', labelsize=10)
        else:
            ax.set_xlabel(f"Influencing model\non {x_device}", fontsize=12)
            ax.set_ylabel(f"Affected model on {y_device}", fontsize=12)
            ax.set_xticklabels(df.columns, rotation=45, ha='right', fontsize=12)
            if file_name == "gpu-gpu.json":
                ax.set_yticklabels(df.index, rotation=0, fontsize=12)
            else:
                ax.set_yticklabels("", rotation=0, fontsize=8)
            ax.tick_params(axis='x', rotation=45, labelsize=10)
            ax.tick_params(axis='y', labelsize=10)
        
        fig.align_labels()  
            
    plt.savefig(output_path, dpi=300)  
    plt.close()

# Folder path containing the matrices
input_folder = "./out/"
output_file = "./png/combined_matrices.pdf"

# Plot all matrices side by side
plot_matrices_side_by_side(input_folder, output_file)