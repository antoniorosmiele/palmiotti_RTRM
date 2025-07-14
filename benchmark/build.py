import os
import subprocess

'''
This script builds TensorRT engines with expected flags from ONNX models located in the 'onnx' folder.
It creates separate engine files for GPU and DLA cores, and logs the output of each build process.
'''

# Path to the onnx folder
onnx_folder = 'onnx/'
engines_folder = 'engines/'
trtexec_path = '/usr/src/tensorrt/bin/trtexec'

# Iterate over all files in the onnx folder
for model_file in os.listdir(onnx_folder):
    if model_file.endswith('.onnx'):
        model_name = os.path.splitext(model_file)[0]
        model_engine_folder = os.path.join(engines_folder, model_name)
        
        # Create the directory if it doesn't exist
        os.makedirs(model_engine_folder, exist_ok=True)
        

        command = f"{trtexec_path} --onnx={onnx_folder}{model_file} --saveEngine={model_engine_folder}/gpu.engine --int8 --fp16 --useDLACore=-1 --allowGPUFallback --useSpinWait --separateProfileRun > {model_engine_folder}/log_gpu.log"
        print(f"\n\n\n\n\n\nRunning command: {command}\n\n")
        subprocess.run(command, shell=True, check=True, executable='/bin/bash')

        command = f"{trtexec_path} --onnx={onnx_folder}{model_file} --saveEngine={model_engine_folder}/dla0.engine --int8 --fp16 --useDLACore=0 --allowGPUFallback --useSpinWait --separateProfileRun > {model_engine_folder}/log_dla0.log"
        print(f"\n\n\n\n\n\nRunning command: {command}\n\n")
        subprocess.run(command, shell=True, check=True, executable='/bin/bash')

        command = f"{trtexec_path} --onnx={onnx_folder}{model_file} --saveEngine={model_engine_folder}/dla1.engine --int8 --fp16 --useDLACore=1 --allowGPUFallback --useSpinWait --separateProfileRun > {model_engine_folder}/log_dla1.log"
        print(f"\n\n\n\n\n\nRunning command: {command}\n\n")
        subprocess.run(command, shell=True, check=True, executable='/bin/bash')