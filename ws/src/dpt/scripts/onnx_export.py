import argparse
import os
import sys
import torch
import tensorrt as trt
# DEPTH_ANYTHING_V2_PATH = os.path.join(os.path.dirname(__file__), "../../../../../", "Depth-Anything-V2", "metric_depth")
DEPTH_ANYTHING_V2_PATH = "/dpt_ros/Depth-Anything-V2/metric_depth"
sys.path.append(DEPTH_ANYTHING_V2_PATH)
# for p in sys.path:
#     print(p)
# print("Added path exists:", os.path.exists(DEPTH_ANYTHING_V2_PATH))
from depth_anything_v2.dpt import DepthAnythingV2

MODEL_CONFIG = {
    "vits": {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]},
    "vitb": {"encoder": "vitb", "features": 128, "out_channels": [96, 192, 384, 768]},
    "vitl": {"encoder": "vitl", "features": 256, "out_channels": [256, 512, 1024, 1024]},
    "vitg": {"encoder": "vitg", "features": 384, "out_channels": [1536, 1536, 1536, 1536]},
}


def main(args):
    depth_anything = DepthAnythingV2(**{**MODEL_CONFIG[args.model], "max_depth": args.max_depth})
    depth_anything.load_state_dict(torch.load(args.checkpoint, map_location="cpu"))
    depth_anything = depth_anything.to("cpu").eval()

    # Define dummy input data
    dummy_input = torch.ones((3, args.input_size, args.input_size)).unsqueeze(0)

    # Provide an example input to the model, this is necessary for exporting to ONNX
    example_output = depth_anything.forward(dummy_input)

    # replace the extension of the checkpoint file with .onnx
    onnx_path = args.checkpoint.replace(".pth", ".onnx")
    engine_path = args.checkpoint.replace(".pth", ".engine")

    # Export the PyTorch model to ONNX format
    torch.onnx.export(
        depth_anything,
        dummy_input,
        onnx_path,
        opset_version=11,
        input_names=["input"],
        output_names=["output"],
        verbose=True,
    )

    print(f"Model exported to {onnx_path}")

    logger = trt.Logger(trt.Logger.VERBOSE)
    builder = trt.Builder(logger)
    network = builder.create_network(1 << (int)(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, logger)
    
    with open(onnx_path, "rb") as model:
        if not parser.parse(model.read()):
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            raise ValueError('Failed to parse the ONNX model.')
    
    # Set up the builder config
    config = builder.create_builder_config()
    config.set_flag(trt.BuilderFlag.FP16) # FP16
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 2 << 30) # 2 GB
    
    serialized_engine = builder.build_serialized_network(network, config)
    
    with open(engine_path, "wb") as f:
        f.write(serialized_engine)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Depth Anything V2")
    parser.add_argument("--input-size", type=int, default=518)
    parser.add_argument("-m", "--model", type=str, default="vits", choices=["vits", "vitb", "vitl", "vitg"])
    parser.add_argument(
        "-ckpt", "--checkpoint", type=str, default="/dpt_ros/ws/src/dpt/depth_anything_v2_metric_hypersim_vits.pth"
    )
    parser.add_argument("--max-depth", type=float, default=20)
    args = parser.parse_args()
    main(args)
