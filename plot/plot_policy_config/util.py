import os
import pandas as pd

'''
This script is used to append a "label" column to all CSV files in a specified directory and its subdirectories.
Use this before plotting the data, as the csvs are incomplete
'''

def process_csv_files(root_dir):
    # Walk through all files and subdirectories in the root directory
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(subdir, file)
                process_csv(file_path)

def process_csv(file_path):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(file_path)
    
    # Sort by "engine_name" and then by "target"
    df = df.sort_values(by=["engine_name", "target"])
    
    # Add a "label" column with "App K" where K is the row number
    df["label"] = ["App " + str(i + 1) for i in range(len(df))]
    
    # Save the updated DataFrame back to the CSV file
    df.to_csv(file_path, index=False)
    print(f"Processed and updated: {file_path}")

# Example usage
if __name__ == "__main__":
    root_directory = "/home/davide/Desktop/out/5config_large"  # Change this to your root directory
    process_csv_files(root_directory)