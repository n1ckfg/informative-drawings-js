import onnx
import sys
from onnxsim import simplify

def freeze(input_path, output_path, w, h):
    print(f"Loading {input_path}...")
    model = onnx.load(input_path)
    
    # Set fixed shape
    for x in model.graph.input:
        if x.name == 'input':
            # It's currently [1, 3, height, width] with dyn shapes or whatever
            x.type.tensor_type.shape.dim[0].dim_value = 1
            x.type.tensor_type.shape.dim[1].dim_value = 3
            x.type.tensor_type.shape.dim[2].dim_value = h
            x.type.tensor_type.shape.dim[3].dim_value = w
            print(f"Set input shape to 1x3x{h}x{w}")
            
    print("Simplifying...")
    model_simp, check = simplify(model)
    if not check:
        print("Warning: simplify check failed!")
        
    onnx.save(model_simp, output_path)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    freeze("models/model.onnx", "models/model_320x240.onnx", 320, 240)
    freeze("models/model.onnx", "models/model_640x480.onnx", 640, 480)
