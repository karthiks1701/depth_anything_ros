#!/bin/bash

xhost +local:root
XAUTH=~/.Xauthority
image_tag=depth_anything_ros:latest
# enable SSH X11 forwarding inside container (https://stackoverflow.com/q/48235040)
# XAUTH=/tmp/.docker.xauth
# xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH nmerge -
# chmod 777 $XAUTH
    
docker run -it --rm --network=host \
                -v /dev:/dev \
                --privileged \
                --name depthanything_ros \
                --device-cgroup-rule="a *:* rmw" \
                --volume=/tmp/.X11-unix:/tmp/.X11-unix -v ${XAUTH}:${XAUTH} \
                -e XAUTHORITY=${XAUTH} \
                --runtime nvidia --gpus all \
                -v ${PWD}:/dpt_ros \
                -w=/dpt_ros \
                -e LIBGL_ALWAYS_SOFTWARE="1"\
                -e DISPLAY=${DISPLAY} \
                ${image_tag}
        