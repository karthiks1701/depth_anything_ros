#!/usr/bin/env python3
import rospy
import cv2
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo


class FisheyeRectifier:
    def __init__(self):
        rospy.init_node("fisheye_rectifier")

        # Parameters
        self.input_image_topic = rospy.get_param(
            "~input_image_topic", "/usb_cam/image_raw"
        )
        self.input_camera_info_topic = rospy.get_param(
            "~input_camera_info_topic", "/usb_cam/camera_info"
        )
        self.output_image_topic = rospy.get_param(
            "~output_image_topic", "/usb_cam/image_rectified"
        )
        self.output_camera_info_topic = rospy.get_param(
            "~output_camera_info_topic", "/usb_cam/camera_info_rectified"
        )

        self.new_width = rospy.get_param("~width", 640)
        self.new_height = rospy.get_param("~height", 480)
        self.balance = rospy.get_param("~balance", 1.0)
        self.fov_scale = rospy.get_param("~fov_scale", 0.6)

        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber(
            self.input_image_topic, Image, self.image_cb, queue_size=1
        )
        self.caminfo_sub = rospy.Subscriber(
            self.input_camera_info_topic, CameraInfo, self.caminfo_cb, queue_size=1
        )

        self.image_pub = rospy.Publisher(self.output_image_topic, Image, queue_size=1)
        self.caminfo_pub = rospy.Publisher(
            self.output_camera_info_topic, CameraInfo, queue_size=1
        )

        self.K = None
        self.D = None
        self.old_size = None
        self.map1 = None
        self.map2 = None

    def caminfo_cb(self, msg):
        # Only load once
        if self.K is None:
            self.K = np.array(msg.K).reshape(3, 3)
            self.D = np.array(msg.D)
            self.old_size = (msg.width, msg.height)

            # Compute new camera matrix
            self.new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
                self.K,
                self.D,
                self.old_size,
                np.eye(3),
                balance=self.balance,
                fov_scale=self.fov_scale,
            )

            # Precompute rectification maps
            self.map1, self.map2 = cv2.fisheye.initUndistortRectifyMap(
                self.K,
                self.D,
                np.eye(3),
                self.new_K,
                (self.new_width, self.new_height),
                cv2.CV_32FC1,
            )
            rospy.loginfo("Fisheye rectification maps initialized")

        # Prepare new CameraInfo
        self.caminfo_msg = CameraInfo()
        self.caminfo_msg.header.frame_id = msg.header.frame_id
        self.caminfo_msg.width = self.new_width
        self.caminfo_msg.height = self.new_height
        self.caminfo_msg.K = self.new_K.flatten().tolist()
        self.caminfo_msg.P = (
            np.hstack([self.new_K, np.zeros((3, 1))]).flatten().tolist()
        )
        self.caminfo_msg.distortion_model = "plumb_bob"
        self.caminfo_msg.D = [0.0] * 4
        self.caminfo_msg.R = np.eye(3).flatten().tolist()

    def image_cb(self, msg):
        if self.map1 is None:
            rospy.logwarn("Rectification maps not initialized yet")
            return

        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
        rect_image = cv2.remap(
            cv_image, self.map1, self.map2, interpolation=cv2.INTER_LINEAR
        )

        self.caminfo_msg.header.stamp = msg.header.stamp
        img_msg = self.bridge.cv2_to_imgmsg(rect_image, encoding="rgb8")

        # copy header from incoming message
        img_msg.header.stamp = msg.header.stamp
        img_msg.header.frame_id = msg.header.frame_id

# publish
        self.image_pub.publish(img_msg)
        self.caminfo_pub.publish(self.caminfo_msg)


if __name__ == "__main__":
    FisheyeRectifier()
    rospy.spin()
