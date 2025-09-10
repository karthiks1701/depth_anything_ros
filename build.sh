#!/bin/bash

ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    BUILDARCH=amd64
elif [ "$ARCH" = "aarch64" ]; then
    BUILDARCH=arm64
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

image_tag=depth_anything_ros

# docker system prune
docker build --build-arg CACHE_BUST=$(date +%s) --build-arg TARGETARCH=$BUILDARCH . -t ${image_tag}