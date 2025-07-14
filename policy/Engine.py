import torch
import torchvision
import time
import tensorrt as trt
from torchvision import transforms
import json
import datetime

'''
This module defines the Engine class, which is responsible for managing a TensorRT engine.
It includes methods for reading engine information, building the engine, creating the mock data for inference
and executing inference with the engine.

In order to execute an Engine, it must first be initialized using "build_engine"
and then executed using "execute".
'''

def get_ts():
    return datetime.datetime.now().strftime('%d/%m/%Y-%H:%M:%S')

class Engine:
    def __init__(self):
        self.name = None
        self.input_shape = None
        self.output_shapes = None
        self.batch_size = None
        self.device = None
        self.throughput = None

        self.heartbeats = []
        self.heartbeats_actual = []
        self.images = None
        self.enginepath = None
        self.engineinfopath = None

    def print_engine(self):
        '''
        Prints the engine essential info
        '''
        print(f"Name: {self.name}")
        print(f"Input shape: {self.input_shape}")
        print(f"Output shapes: {self.output_shapes}")
        print(f"Device: {self.device}")
        print(f"Throughput: {self.throughput}")

    def get_heartbeats(self):
        '''
        Returns heartbeat information of an execute run
        name: Name of the engine
        device: Device used for the engine (DLA0, DLA1, or GPU)
        throughput: Target throughput of the engine
        heartbeats: List of throughput values recorded at each heartbeat interval INCLUDING AUTOSLEEP
        heartbeats_actual: List of predicted throughput values recorded at each heartbeat interval EXCLUDING AUTOSLEEP
        '''
        return (self.name, self.device, self.throughput, self.heartbeats, self.heartbeats_actual)

    def read_info(self, engineinfopath: str):

        '''
        Reads the engine information from a JSON file and sets the engine attributes accordingly.
        engineinfopath: Path to the JSON file containing engine information (name, input_shape, output_shape).
        '''

        print(f"[{get_ts()}] [Engine.py] [D] Reading engine info from {engineinfopath}")
        with open(engineinfopath, 'r') as f:
            engine_info = json.load(f)

        self.name = engine_info.get("name")
        input_shape_str = engine_info.get("input_shape", "1,3,224,224")
        self.input_shape = tuple(map(int, input_shape_str.split(',')))
        self.batch_size = self.input_shape[0]
        output_shapes_str = engine_info.get("output_shapes", "1,1000")
        self.output_shapes = [tuple(map(int, shape.split(','))) for shape in output_shapes_str.split(';')]

        printts = get_ts()
        print(f"[{printts}] [Engine.py] [D] \tName: {self.name}")
        print(f"[{printts}] [Engine.py] [D] \tInput shape: {self.input_shape}")
        print(f"[{printts}] [Engine.py] [D] \tOutput shapes: {self.output_shapes}")
        print(f"[{printts}] [Engine.py] [D] Correctly read engine info")

    def create_data(self, numimgs=2000):
        '''
        Creates mock data for inference. This method generates a list of random images
        to simulate the input data for the engine and assigns it to the `self.images` attribute.
        '''

        print(f"[{get_ts()}] [Engine.py] [D] Creating mock data...")
        images = []
        print(f"[{get_ts()}] [Engine.py] [D] Creating mock image array of length {numimgs}")
        for _ in range(numimgs):
            image, _ = next(iter(torchvision.datasets.FakeData(size=1, image_size=(3,224,224))))
            images.append(image)
        self.images = images
        print(f"[{get_ts()}] [Engine.py] [D] Correctly created mock data")

    def build_engine(self, enginepath: str, engineinfopath: str):
        '''
        Builds the engine from the specified path and reads its information.
        enginepath: Path to the TensorRT engine file.
        engineinfopath: Path to the JSON file containing engine information.
        '''
        print(f"[{get_ts()}] [Engine.py] [D] Building engine from {enginepath}")
        self.enginepath = enginepath
        self.engineinfopath = engineinfopath
        self.read_info(engineinfopath)
        self.device = "DLA0" if "dla0.engine" in enginepath else "DLA1" if "dla1.engine" in enginepath else "GPU"
        print(f"[{get_ts()}] [Engine.py] [D] \tDevice: {self.device}")

    def execute(self, heartbeat: int, duration=None, start_barrier=None, warmup=-1):
        '''
        Executes the TensorRT engine.
        It first initializes the CUDA context and TensorRT Runtime context and then runs inference on the mock data created by create_data().
        It enters the inference loop and prints heartbeat information every specified interval.

        heartbeat: Interval in seconds to print the throughput.
        duration: Total duration in seconds to run the inference. If None, runs indefinitely until manually stopped.
        start_barrier: Optional barrier to synchronize the start of the inference across multiple processes.
        '''

        # Flush heartbeats
        self.heartbeats = []
        self.heartbeats_actual = []

        # ------- Initialize CUDA context and TensorRT engine within the process -------

        logger = trt.Logger()
        runtime = trt.Runtime(logger)

        # Necessary to specificy to the runtime which DLA core to use
        if self.device == "DLA0":
            runtime.DLA_core = 0
        elif self.device == "DLA1":
            runtime.DLA_core = 1

        with open(self.enginepath, 'rb') as f:
            engine = runtime.deserialize_cuda_engine(f.read())

        context = engine.create_execution_context()

        input_tensor_name = engine.get_tensor_name(0)
        context.set_input_shape(input_tensor_name, self.input_shape)

        input_buffer = torch.zeros(self.input_shape, dtype=torch.float32, device=torch.device('cuda')).contiguous()
        output_buffers = [torch.zeros((self.batch_size, *shape[1:]), dtype=torch.float32, device=torch.device('cuda')).contiguous() for shape in self.output_shapes]

        bindings = [None] * (1 + len(self.output_shapes))
        bindings[0] = input_buffer.data_ptr()
        for i, output_buffer in enumerate(output_buffers):
            bindings[i + 1] = output_buffer.data_ptr()

        print(f"[{get_ts()}] [Engine.py] [D] Correctly generated context for {self.name}")

        # ------- Data preprocessing and image generation ---------

        # We define a preprocess function that simply resizes the input to the model desired dimensions.
        # We perform preprocessing of the batch within the inference loop
        preprocess = transforms.Compose([
            transforms.Resize(self.input_shape[2:]),  
            transforms.ToTensor(),                   
        ])
        self.create_data()
        images = self.images
        imglen = len(images)

        # ------- Warmup phase ---------
        
        if warmup > 0:
            print(f"[{get_ts()}] [Engine.py] [I] Warmup phase for {self.name}...")
            num_warmup_batches = 5
            for i in range(num_warmup_batches):
                batch_images = images[i % imglen : (i % imglen) + self.batch_size]
                batch_images = torch.stack([preprocess(image) for image in batch_images])
                input_buffer[0:self.batch_size].copy_(batch_images)

                context.execute_async_v2(
                    bindings,
                    torch.cuda.current_stream().cuda_stream
                )
                torch.cuda.current_stream().synchronize()
            print(f"[{get_ts()}] [Engine.py] [I] Warmup phase completed for {self.name}")
        
         # OPTIONAL: Wait for all processes to be ready (barrier used to synchronize multiple applications within a configuration)
        if start_barrier:
            print(f"[{get_ts()}] [Engine.py] [D] {self.name} waiting at the barrier...")
            start_barrier.wait()

        # ------- Inference loop ---------

        print(f"[{get_ts()}] [Engine.py] [I] Begin running engine {self.name}")
        num_batches = 0
        start_time = time.time()
        hb_time = time.time()
        op_time = 0
        i = 0
        if duration is None:
            duration = float('inf')
        while time.time() - start_time < duration:
            start_op_time = time.time()

            # Copy to input buffer + preprocess
            batch_images = images[i % imglen : (i % imglen) + self.batch_size]
            batch_images = torch.stack([preprocess(image) for image in batch_images])
            input_buffer[0:self.batch_size].copy_(batch_images)

            # Execute engine run
            context.execute_async_v2(
                bindings,
                torch.cuda.current_stream().cuda_stream
            )
            torch.cuda.current_stream().synchronize()

            # Copy output from output buffers to numpy arrays
            # NOTE: We don't perform any postprocessing
            output = [output_buffer[0:self.batch_size].cpu().numpy() for output_buffer in output_buffers]
            num_batches += 1
            op_time += time.time() - start_op_time
            
            # Heartbeat handling
            if time.time() - hb_time >= heartbeat:
                elapsed_time_hb = time.time() - hb_time
                throughput_hb = num_batches * self.batch_size / elapsed_time_hb
                throughput_hb_actual = num_batches * self.batch_size / op_time
                print(f"[{get_ts()}] [Engine.py] [I] \tHeartbeat for {self.name}: {throughput_hb:.2f} img/s", end=" ")
                print(f"(Actual throughput: {throughput_hb_actual:.2f} img/s)")
                self.heartbeats.append(throughput_hb)
                self.heartbeats_actual.append(throughput_hb_actual)
                
                op_time = 0
                hb_time = time.time()
                num_batches = 0
            i += self.batch_size
            
            # Autosleep
            if self.throughput > 0:
                elapsed_time = time.time() - start_time
                time.sleep(max(0, (i * self.batch_size / self.throughput) - elapsed_time))

        print(f"[{get_ts()}] [Engine.py] [I] Finished running engine {self.name} (Duration expired)")
