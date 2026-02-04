## ONNX

Book
https://www.amazon.com/Ultimate-ONNX-Deep-Learning-Optimization/dp/9349887207 


# **Alternatives to ONNX Format**

Great question! There are several alternatives, each with different trade-offs. Let me break them down by category:

---

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

