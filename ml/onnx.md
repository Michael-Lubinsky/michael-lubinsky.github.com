## ONNX

# **ONNX File Format Deep Dive**

ONNX uses **Protocol Buffers (protobuf)** for serialization - a binary format developed by Google for efficient data serialization.

---

## **High-Level Structure**

```
┌─────────────────────────────────────┐
│     ONNX Model (.onnx file)         │
│                                     │
│  ┌───────────────────────────────┐ │
│  │      ModelProto               │ │
│  │                               │ │
│  │  - IR Version                 │ │
│  │  - Producer Info              │ │
│  │  - Domain                     │ │
│  │  - Model Version              │ │
│  │  - Metadata                   │ │
│  │                               │ │
│  │  ┌─────────────────────────┐ │ │
│  │  │    GraphProto           │ │ │
│  │  │                         │ │ │
│  │  │  - Nodes (operators)    │ │ │
│  │  │  - Initializers (weights)│ │ │
│  │  │  - Inputs               │ │ │
│  │  │  - Outputs              │ │ │
│  │  │  - Value Info           │ │ │
│  │  └─────────────────────────┘ │ │
│  │                               │ │
│  │  - Opset Imports              │ │
│  │  - Functions (optional)       │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## **Core Components**

### **1. ModelProto (Top Level)**

The outermost container with metadata:

```python
import onnx

model = onnx.load("model.onnx")

# ModelProto attributes
print(f"IR Version: {model.ir_version}")           # ONNX IR version
print(f"Producer: {model.producer_name}")          # e.g., "pytorch", "tensorflow"
print(f"Producer Version: {model.producer_version}") # e.g., "2.0.0"
print(f"Domain: {model.domain}")                   # e.g., "ai.onnx"
print(f"Model Version: {model.model_version}")     # User-defined version
print(f"Doc String: {model.doc_string}")           # Description

# Opset imports (which operator versions are used)
for opset in model.opset_import:
    print(f"Opset {opset.domain}: version {opset.version}")
```

**Example Output:**
```
IR Version: 8
Producer: pytorch
Producer Version: 2.0.0
Domain: 
Model Version: 0
Opset ai.onnx: version 17
```

---

### **2. GraphProto (Computation Graph)**

The actual computational graph containing nodes and tensors:

```python
graph = model.graph

print(f"Graph Name: {graph.name}")
print(f"Inputs: {len(graph.input)}")
print(f"Outputs: {len(graph.output)}")
print(f"Nodes (operators): {len(graph.node)}")
print(f"Initializers (weights): {len(graph.initializer)}")
```

**Key Parts:**

#### **A. Nodes (Operations)**
Each node represents an operation (Conv, MatMul, ReLU, etc.):

```python
for node in graph.node:
    print(f"Node: {node.name}")
    print(f"  Op Type: {node.op_type}")          # e.g., "Conv", "Gemm", "Relu"
    print(f"  Inputs: {node.input}")             # List of input tensor names
    print(f"  Outputs: {node.output}")           # List of output tensor names
    print(f"  Attributes: {node.attribute}")     # Op-specific parameters
```

**Example Node:**
```python
# A Conv node might look like:
Node: conv1
  Op Type: Conv
  Inputs: ['input', 'conv1.weight', 'conv1.bias']
  Outputs: ['conv1_output']
  Attributes: 
    - kernel_shape: [3, 3]
    - strides: [1, 1]
    - pads: [1, 1, 1, 1]
    - dilations: [1, 1]
```

#### **B. Initializers (Model Weights)**
Constant tensors (weights, biases):

```python
for init in graph.initializer:
    print(f"Initializer: {init.name}")
    print(f"  Data Type: {init.data_type}")     # 1=FLOAT, 7=INT64, etc.
    print(f"  Shape: {init.dims}")              # e.g., [64, 3, 7, 7]
    print(f"  Size: {len(init.raw_data)} bytes")
```

**Data storage:**
- Small tensors: stored inline in `float_data`, `int64_data`, etc.
- Large tensors: stored in `raw_data` as binary blob
- External tensors: stored in separate file (for large models >2GB)

#### **C. Inputs & Outputs**
Define the model interface:

```python
# Model Inputs
for input_tensor in graph.input:
    print(f"Input: {input_tensor.name}")
    print(f"  Type: {input_tensor.type.tensor_type.elem_type}")
    print(f"  Shape: {input_tensor.type.tensor_type.shape.dim}")

# Model Outputs  
for output_tensor in graph.output:
    print(f"Output: {output_tensor.name}")
    print(f"  Type: {output_tensor.type.tensor_type.elem_type}")
    print(f"  Shape: {output_tensor.type.tensor_type.shape.dim}")
```

**Shape representation:**
```python
# Fixed dimension: dim.dim_value = 224
# Dynamic dimension: dim.dim_param = "batch_size"

for dim in input_tensor.type.tensor_type.shape.dim:
    if dim.HasField('dim_value'):
        print(f"  Fixed: {dim.dim_value}")
    elif dim.HasField('dim_param'):
        print(f"  Dynamic: {dim.dim_param}")
```

#### **D. Value Info (Intermediate Tensors)**
Type and shape information for intermediate tensors:

```python
for value_info in graph.value_info:
    print(f"Tensor: {value_info.name}")
    print(f"  Shape: {value_info.type.tensor_type.shape.dim}")
```

---

## **File Format Details**

### **Binary Structure**

```
ONNX File (.onnx)
├── Header (protobuf metadata)
├── ModelProto (serialized)
│   ├── ir_version (varint)
│   ├── producer_name (string)
│   ├── graph (GraphProto)
│   │   ├── node[] (repeated NodeProto)
│   │   ├── initializer[] (repeated TensorProto)
│   │   ├── input[] (repeated ValueInfoProto)
│   │   ├── output[] (repeated ValueInfoProto)
│   │   └── value_info[] (repeated ValueInfoProto)
│   └── opset_import[] (repeated OperatorSetIdProto)
└── Optional: External data pointer
```

### **Protobuf Schema (Simplified)**

```protobuf
// onnx.proto (simplified)

message ModelProto {
  int64 ir_version = 1;
  repeated OperatorSetIdProto opset_import = 8;
  string producer_name = 2;
  string producer_version = 3;
  string domain = 4;
  int64 model_version = 5;
  string doc_string = 6;
  GraphProto graph = 7;
  repeated StringStringEntryProto metadata_props = 14;
}

message GraphProto {
  repeated NodeProto node = 1;
  string name = 2;
  repeated TensorProto initializer = 5;
  string doc_string = 10;
  repeated ValueInfoProto input = 11;
  repeated ValueInfoProto output = 12;
  repeated ValueInfoProto value_info = 13;
}

message NodeProto {
  repeated string input = 1;
  repeated string output = 2;
  string name = 3;
  string op_type = 4;
  string domain = 7;
  repeated AttributeProto attribute = 5;
  string doc_string = 6;
}

message TensorProto {
  repeated int64 dims = 1;
  int32 data_type = 2;
  bytes raw_data = 9;  // For large tensors
  // Or type-specific fields:
  repeated float float_data = 4;
  repeated int64 int64_data = 7;
  string name = 8;
  string doc_string = 12;
}
```

---

## **Practical Examples**

### **Example 1: Reading ONNX File**

```python
import onnx
import numpy as np

# Load model
model = onnx.load("resnet50.onnx")

# Check model is valid
onnx.checker.check_model(model)

# Get graph
graph = model.graph

# Inspect first Conv layer
conv_node = graph.node[0]
print(f"First layer: {conv_node.op_type}")

# Get weight tensor
weight_name = conv_node.input[1]  # Usually input[0]=data, input[1]=weight
weight_tensor = None
for init in graph.initializer:
    if init.name == weight_name:
        weight_tensor = init
        break

# Extract weight data
if weight_tensor:
    # Convert to numpy array
    weight_array = onnx.numpy_helper.to_array(weight_tensor)
    print(f"Weight shape: {weight_array.shape}")
    print(f"Weight dtype: {weight_array.dtype}")
```

### **Example 2: Modifying ONNX Model**

```python
import onnx
from onnx import helper, TensorProto

# Load model
model = onnx.load("model.onnx")
graph = model.graph

# Add a new node (e.g., Clip operation for output clamping)
clip_node = helper.make_node(
    'Clip',
    inputs=['old_output'],
    outputs=['clipped_output'],
    min=0.0,
    max=1.0
)

# Add node to graph
graph.node.append(clip_node)

# Update graph output
graph.output[0].name = 'clipped_output'

# Save modified model
onnx.save(model, "model_modified.onnx")
```

### **Example 3: Extracting Model Statistics**

```python
def analyze_onnx_model(model_path):
    model = onnx.load(model_path)
    graph = model.graph
    
    # Count operators
    op_types = {}
    for node in graph.node:
        op_types[node.op_type] = op_types.get(node.op_type, 0) + 1
    
    # Count parameters
    total_params = 0
    for init in graph.initializer:
        param_count = np.prod(init.dims)
        total_params += param_count
    
    # Calculate model size
    import os
    size_mb = os.path.getsize(model_path) / (1024 * 1024)
    
    return {
        'operators': op_types,
        'total_nodes': len(graph.node),
        'total_params': total_params,
        'model_size_mb': size_mb,
        'opset_version': model.opset_import[0].version
    }

# Usage
stats = analyze_onnx_model("model.onnx")
print(stats)
```

**Output:**
```python
{
    'operators': {
        'Conv': 53,
        'BatchNormalization': 53,
        'Relu': 49,
        'MaxPool': 1,
        'GlobalAveragePool': 1,
        'Flatten': 1,
        'Gemm': 1
    },
    'total_nodes': 159,
    'total_params': 25557032,
    'model_size_mb': 97.8,
    'opset_version': 17
}
```

---

## **External Data Storage**

For large models (>2GB), weights are stored externally:

```python
# Save with external data
onnx.save(
    model,
    "large_model.onnx",
    save_as_external_data=True,
    location="large_model.data"
)

# This creates:
# - large_model.onnx (graph structure, small)
# - large_model.data (weights, large)

# Load with external data
model = onnx.load("large_model.onnx", load_external_data=True)
```

---

## **Data Types**

ONNX supports these tensor data types:

```python
from onnx import TensorProto

UNDEFINED = 0
FLOAT = 1        # float32
UINT8 = 2
INT8 = 3
UINT16 = 4
INT16 = 5
INT32 = 6
INT64 = 7
STRING = 8
BOOL = 9
FLOAT16 = 10     # half precision
DOUBLE = 11      # float64
UINT32 = 12
UINT64 = 13
COMPLEX64 = 14
COMPLEX128 = 15
BFLOAT16 = 16    # brain float
```

---

## **Key Insights for Your Tool**

When building your PyTorch→ONNX validator:

1. **Check opset versions** - Newer operators need newer opsets
2. **Validate tensor shapes** - Look at `graph.value_info` for intermediate shapes
3. **Track tensor flow** - Follow `node.input` → `node.output` connections
4. **Extract operator attributes** - Critical for understanding semantics
5. **Handle external data** - Large models need special handling
6. **Validate data types** - Type mismatches cause runtime errors

**Useful for validation:**
```python
# Check if all tensors are connected properly
def validate_graph(graph):
    # Build set of available tensors
    available = set()
    available.update([inp.name for inp in graph.input])
    available.update([init.name for init in graph.initializer])
    
    # Check each node's inputs exist
    for node in graph.node:
        for inp in node.input:
            if inp and inp not in available:
                print(f"ERROR: Node {node.name} missing input: {inp}")
        available.update(node.output)
```

## **Alternatives to ONNX Format**

## **1. Framework-Native Formats**

### **TensorFlow SavedModel**
**What**: TensorFlow's native serialization format
- **URL**: https://www.tensorflow.org/guide/saved_model
- **Extension**: Directory with `saved_model.pb` + variables/

**Pros:**
- ✅ Native TensorFlow support (no conversion)
- ✅ Includes full computation graph + metadata
- ✅ TensorFlow Serving integration
- ✅ Support for signatures (multiple endpoints)

**Cons:**
- ❌ TensorFlow-specific (limited portability)
- ❌ Larger file sizes
- ❌ Requires TensorFlow runtime

**Use Case:** Production deployment within TensorFlow ecosystem

```python
# Save
model.save('model_dir')

# Load
loaded_model = tf.saved_model.load('model_dir')
```

---

### **PyTorch (.pt, .pth, .bin)**
**What**: PyTorch's native checkpoint format
- **Docs**: https://pytorch.org/tutorials/beginner/saving_loading_models.html

**Pros:**
- ✅ Native PyTorch support
- ✅ Simple to save/load
- ✅ Flexible (can save optimizer state, etc.)

**Cons:**
- ❌ PyTorch-only
- ❌ Not standardized (pickle-based, security concerns)
- ❌ No cross-framework support

**Use Case:** PyTorch research & development

```python
# Save
torch.save(model.state_dict(), 'model.pth')

# Load
model.load_state_dict(torch.load('model.pth'))
```

---

### **TorchScript**
**What**: PyTorch's intermediate representation for deployment
- **Docs**: https://pytorch.org/docs/stable/jit.html

**Pros:**
- ✅ Static graph (unlike dynamic PyTorch)
- ✅ C++ runtime (no Python dependency)
- ✅ Mobile deployment (iOS/Android)
- ✅ Better than raw .pth for production

**Cons:**
- ❌ Still PyTorch ecosystem
- ❌ Tracing/scripting limitations (similar to ONNX)
- ❌ Less hardware backend support than ONNX

**Use Case:** PyTorch production deployment

```python
# Trace
traced = torch.jit.trace(model, example_input)
traced.save('model.pt')

# Script
scripted = torch.jit.script(model)
scripted.save('model.pt')
```

---

## **2. Hardware/Platform-Specific Formats**

### **TensorRT (.plan, .engine)**
**What**: NVIDIA's optimized inference engine format
- **URL**: https://developer.nvidia.com/tensorrt
- **GitHub**: https://github.com/NVIDIA/TensorRT

**Pros:**
- ✅ Fastest on NVIDIA GPUs (heavily optimized)
- ✅ Layer fusion, precision calibration (FP16/INT8)
- ✅ Dynamic shapes support
- ✅ Can consume ONNX as input

**Cons:**
- ❌ NVIDIA GPU only
- ❌ Hardware-specific (recompile for different GPUs)
- ❌ Not portable across platforms
- ❌ Proprietary (though free to use)

**Use Case:** High-performance inference on NVIDIA GPUs

```python
import tensorrt as trt

# Build from ONNX
builder = trt.Builder(logger)
network = builder.create_network()
parser = trt.OnnxParser(network, logger)
parser.parse_from_file('model.onnx')

# Build optimized engine
engine = builder.build_cuda_engine(network)
```

---

### **CoreML (.mlmodel, .mlpackage)**
**What**: Apple's ML format for iOS/macOS
- **URL**: https://developer.apple.com/documentation/coreml
- **GitHub**: https://github.com/apple/coremltools

**Pros:**
- ✅ Native Apple hardware acceleration (Neural Engine)
- ✅ iOS/macOS/watchOS integration
- ✅ Privacy-first (on-device)
- ✅ Can convert from ONNX, PyTorch, TensorFlow

**Cons:**
- ❌ Apple devices only
- ❌ Limited operator support
- ❌ Proprietary format

**Use Case:** Mobile ML on Apple devices

```python
import coremltools as ct

# Convert from PyTorch
traced_model = torch.jit.trace(model, example_input)
mlmodel = ct.convert(
    traced_model,
    inputs=[ct.TensorType(shape=input_shape)]
)
mlmodel.save('model.mlpackage')
```

---

### **TensorFlow Lite (.tflite)**
**What**: TensorFlow's mobile/edge format
- **URL**: https://www.tensorflow.org/lite

**Pros:**
- ✅ Optimized for mobile/edge (iOS, Android, embedded)
- ✅ Quantization support (INT8, FP16)
- ✅ Small model sizes
- ✅ Hardware acceleration (GPU, NPU, DSP)

**Cons:**
- ❌ Reduced operator coverage vs TensorFlow
- ❌ TensorFlow ecosystem dependency
- ❌ Less flexible than full TensorFlow

**Use Case:** Mobile/edge deployment (Android, iOS, embedded)

```python
# Convert
converter = tf.lite.TFLiteConverter.from_saved_model('model_dir')
tflite_model = converter.convert()

# Save
with open('model.tflite', 'wb') as f:
    f.write(tflite_model)
```

---

### **OpenVINO IR (.xml + .bin)**
**What**: Intel's intermediate representation
- **GitHub**: https://github.com/openvinotoolkit/openvino

**Pros:**
- ✅ Optimized for Intel hardware (CPU, GPU, NPU, VPU)
- ✅ Can consume ONNX, TensorFlow, PyTorch
- ✅ Good quantization support
- ✅ Cross-platform (x86, ARM)

**Cons:**
- ❌ Best on Intel hardware
- ❌ Requires OpenVINO runtime
- ❌ Two-file format (.xml + .bin)

**Use Case:** Deployment on Intel hardware

```bash
# Convert from ONNX
mo --input_model model.onnx --output_dir output/
```

---

## **3. Emerging Interchange Formats**

### **MLIR (Multi-Level Intermediate Representation)**
**What**: Compiler infrastructure for ML (Google/LLVM)
- **URL**: https://mlir.llvm.org/
- **GitHub**: https://github.com/llvm/llvm-project/tree/main/mlir

**Pros:**
- ✅ Multiple abstraction levels (high to low)
- ✅ Extensible dialect system
- ✅ Powerful compiler optimizations
- ✅ Used by TensorFlow, PyTorch, JAX internally

**Cons:**
- ❌ Lower-level (compiler IR, not end-user format)
- ❌ Steeper learning curve
- ❌ Still evolving
- ❌ Not a direct ONNX replacement

**Use Case:** Framework developers, compiler optimization

---

### **StableHLO**
**What**: Portable ML ops for XLA-based frameworks (JAX, TF)
- **GitHub**: https://github.com/openxla/stablehlo

**Pros:**
- ✅ Stable versioning (hence "Stable")
- ✅ JAX/XLA ecosystem integration
- ✅ Better versioning than older HLO

**Cons:**
- ❌ Primarily for JAX/XLA users
- ❌ Limited adoption outside Google ecosystem
- ❌ Not as universal as ONNX

**Use Case:** JAX model deployment

---

### **GGML/GGUF** ⭐ (For LLMs)
**What**: Format optimized for LLM inference (llama.cpp)
- **GitHub GGML**: https://github.com/ggerganov/ggml
- **GitHub GGUF**: https://github.com/ggerganov/llama.cpp

**Pros:**
- ✅ Extremely efficient LLM inference on CPU
- ✅ Quantization (4-bit, 5-bit, 8-bit)
- ✅ Cross-platform (x86, ARM, even WASM)
- ✅ Simple C implementation
- ✅ Popular for local LLM deployment

**Cons:**
- ❌ LLM-specific (not general purpose)
- ❌ Limited operator set
- ❌ No training support

**Use Case:** Running LLMs on consumer hardware (Llama, Mistral, etc.)

```bash
# Convert to GGUF
python convert.py --model llama-7b --outfile llama-7b.gguf

# Run inference
./main -m llama-7b.gguf -p "Hello world"
```

---

### **SafeTensors**
**What**: Safe, fast tensor serialization (Hugging Face)
- **GitHub**: https://github.com/huggingface/safetensors

**Pros:**
- ✅ Safe (no pickle, no arbitrary code execution)
- ✅ Fast loading (zero-copy, lazy loading)
- ✅ Cross-framework (PyTorch, TensorFlow, JAX)
- ✅ Simple format

**Cons:**
- ❌ **Weights only** (no computation graph!)
- ❌ Not a complete model format
- ❌ Requires framework to define architecture

**Use Case:** Secure weight sharing (Hugging Face Hub)

```python
from safetensors.torch import save_file, load_file

# Save
save_file(model.state_dict(), "model.safetensors")

# Load
weights = load_file("model.safetensors")
model.load_state_dict(weights)
```

---

## **4. Specialized/Legacy Formats**

### **Caffe Model (.caffemodel)**
**What**: Caffe's original format
- Legacy, mostly superseded by ONNX/TensorFlow

### **MXNet (.params + .json)**
**What**: Apache MXNet format
- Less popular now, ONNX preferred

### **PaddlePaddle (.pdmodel + .pdiparams)**
**What**: Baidu's PaddlePaddle format
- Primarily used in China

---

## **Comparison Table**

| Format | Portability | Hardware Support | Ease of Use | Adoption |
|--------|-------------|------------------|-------------|----------|
| **ONNX** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **TensorRT** | ⭐ (NVIDIA only) | ⭐⭐⭐⭐⭐ (NVIDIA) | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **CoreML** | ⭐ (Apple only) | ⭐⭐⭐⭐⭐ (Apple) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **TFLite** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **TorchScript** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **GGUF** | ⭐⭐⭐⭐ (LLMs) | ⭐⭐⭐⭐ (CPU) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ (LLMs) |
| **SavedModel** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **OpenVINO IR** | ⭐⭐⭐ | ⭐⭐⭐⭐ (Intel) | ⭐⭐⭐ | ⭐⭐⭐ |

---

## **Decision Tree: Which Format to Use?**

```
Start
│
├─ Deploying LLMs on CPU?
│  └─> GGUF/GGML
│
├─ Apple devices only?
│  └─> CoreML
│
├─ NVIDIA GPUs + need max performance?
│  └─> TensorRT (can start from ONNX)
│
├─ Mobile/Edge (Android/iOS)?
│  ├─ TensorFlow-based? → TFLite
│  └─ PyTorch-based? → CoreML or TorchScript Mobile
│
├─ Intel hardware?
│  └─> OpenVINO (can consume ONNX)
│
├─ Cross-platform/multi-backend?
│  └─> **ONNX** ⭐
│
├─ Research/Development?
│  ├─ PyTorch → .pth / TorchScript
│  └─ TensorFlow → SavedModel
│
└─ Sharing weights only (no graph)?
   └─> SafeTensors
```

---

## **Why ONNX Still Dominates for Interchange**

Despite alternatives, ONNX has unique advantages:

1. **True Interchange Format**: Works between frameworks (PyTorch ↔ TensorFlow ↔ etc.)
2. **Broad Hardware Support**: CPU, GPU, NPU, VPU, TPU, custom accelerators
3. **Runtime Ecosystem**: ONNX Runtime, TensorRT, OpenVINO all support it
4. **Industry Standard**: Microsoft, Meta, Amazon, NVIDIA, Intel support
5. **Active Development**: Regular updates, new operators

**But ONNX isn't perfect for:**
- LLM deployment (GGUF is better)
- Maximum performance on specific hardware (use native formats)
- Mobile-first (TFLite/CoreML are more optimized)
- Research iteration (native formats are simpler)

