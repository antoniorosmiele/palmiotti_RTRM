import argparse
import tensorrt as trt
import torch
import torchvision
import time
from datetime import datetime
import torchvision.transforms as transforms

'''
This script benchmarks a TensorRT engine on a GPU or DLA core.
It runs mock inferences for a specified duration and calculates throughput.
'''


parser = argparse.ArgumentParser()
parser.add_argument('--engine', type=str, required=True, help='Path to the TensorRT engine file')
parser.add_argument('--duration', type=int, required=True, help='Duration to run mock inferences (in seconds)')
parser.add_argument('--input_shape', type=str, default="1,3,224,224", help='Input shape for the model (e.g., "1,3,224,224")')
parser.add_argument('--output_shapes', type=str, default="1,1000", help='Comma-separated list of output shapes for the model (e.g., "1,1000;1,10")')
parser.add_argument('--throughput', type=int, default=-1, help='Target throughput (in inferences per second), < 0 for no limit')
args = parser.parse_args()

print(f'Engine: {args.engine}')
print(f'Duration: {args.duration} seconds')
print(f'Input shape: {args.input_shape}')
print(f'Output shapes: {args.output_shapes}')

logger = trt.Logger()
runtime = trt.Runtime(logger)

with open(args.engine, 'rb') as f:
    engine = runtime.deserialize_cuda_engine(f.read())

if "dla0.engine" in args.engine:
    runtime.DLA_core=0
elif "dla1.engine" in args.engine:
    runtime.DLA_core=1

context = engine.create_execution_context()

input_tensor_name = engine.get_tensor_name(0)  # Assuming 'input' is the first tensor
output_tensor_name = engine.get_tensor_name(1)  # Assuming 'output' is the second tensor

input_shape = tuple(map(int, args.input_shape.split(',')))
batch_size = input_shape[0]
output_shapes = [tuple(map(int, shape.split(','))) for shape in args.output_shapes.split(';')]

context.set_input_shape(input_tensor_name, input_shape)

input_buffer = torch.zeros(input_shape, dtype=torch.float32, device=torch.device('cuda')).contiguous()
output_buffers = [torch.zeros((batch_size, *shape[1:]), dtype=torch.float32, device=torch.device('cuda')).contiguous() for shape in output_shapes]

bindings = [None] * (1 + len(output_shapes))
bindings[0] = input_buffer.data_ptr()
for i, output_buffer in enumerate(output_buffers):
    bindings[i + 1] = output_buffer.data_ptr()

# Define the preprocessing steps
preprocess = transforms.Compose([
    transforms.Resize(input_shape[2:]), 
    transforms.ToTensor(),               
])

images = []
imglen = 2000
for _ in range(imglen):
    image, _ = next(iter(torchvision.datasets.FakeData(size=1, image_size=(3,224,224))))
    images.append(image)

# Warmup runs
print("Running warmup runs...")
i = 0
start_warmup_time = time.time()
while time.time() - start_warmup_time < 30:
    batch_images = images[i % imglen : (i % imglen) + batch_size]
    batch_images = torch.stack([preprocess(image) for image in batch_images])
    input_buffer[0:batch_size].copy_(batch_images)
    context.execute_async_v2(
        bindings,
        torch.cuda.current_stream().cuda_stream
    )
    torch.cuda.current_stream().synchronize()
    i += batch_size


print("Starting benchmark...")
i = 0
num_batches = 0
start_time = time.time()
while time.time() - start_time < args.duration:
    batch_images = images[i % imglen : (i % imglen) + batch_size]
    batch_images = torch.stack([preprocess(image) for image in batch_images])
    input_buffer[0:batch_size].copy_(batch_images)
    context.execute_async_v2(
        bindings,   
        torch.cuda.current_stream().cuda_stream
    )
    torch.cuda.current_stream().synchronize()

    output = [output_buffer[0:batch_size].cpu().numpy() for output_buffer in output_buffers]

    # here you should check the output against a label

    num_batches += 1
    i += batch_size

    if args.throughput > 0:
        elapsed_time = time.time() - start_time
        target_time = num_batches / args.throughput
        if elapsed_time < target_time:
            time.sleep(target_time - elapsed_time)

end_time = time.time()
total_time = end_time - start_time

throughput = num_batches * batch_size / total_time

start_time_str = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S.%f')
end_time_str = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S.%f')

print(f'Start timestamp: {start_time_str}')
print(f'End timestamp: {end_time_str}')
print(f'Throughput: {throughput:.2f} inferences per second')
