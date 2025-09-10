#!/usr/bin/env sh

if [ $# -eq 0 ]; then
    echo "Usage: $0 <onnx_dir>"
    exit 1
fi

onnx_dir="$1"

if [ ! -d "$onnx_dir" ]; then
    echo "Directory $onnx_dir does not exist."
    exit 1
fi

TRT_BIN=/usr/src/tensorrt/bin/trtexec

for onnx_file in "$onnx_dir"/*.onnx
do
    if [ -f "$onnx_file" ]; then
        base_name=$(basename "${onnx_file%.onnx}")
        $TRT_BIN --onnx="$onnx_file" --saveEngine="$onnx_dir/${base_name}.engine" --explicitBatch --workspace=2048 
        echo "Exported $onnx_file to $onnx_dir/${base_name}.engine"
    fi
done
echo "Exported all ONNX files to TensorRT engines."
