import onnx
from onnxconverter_common import float16

def to_fp16(input_path, output_path):
    print(f"Converting {input_path} to fp16...")
    model = onnx.load(input_path)
    model_fp16 = float16.convert_float_to_float16(model, keep_io_types=True)
    onnx.save(model_fp16, output_path)
    print(f"Saved to {output_path}")

to_fp16("model_320x240.onnx", "model_320x240_fp16.onnx")
to_fp16("model_640x480.onnx", "model_640x480_fp16.onnx")
to_fp16("model.onnx", "model_fp16.onnx")
