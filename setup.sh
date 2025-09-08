#!/bin/bash
# source ~/.bashrc

source /opt/ros/noetic/setup.bash
export PYTHONPATH=/dpt_ros/.packages_dpt_ros:$PYTHONPATH
source /dpt_ros/ws/devel/setup.bash
mkdir -p /root/.ros/camera_info/
cp /dpt_ros/ws/src/dpt/test/usb_cam.yaml /root/.ros/camera_info/usb_cam.yaml
exec "$@"