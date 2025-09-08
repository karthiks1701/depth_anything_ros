#!/usr/bin/env python3
import rospy
import torch
import numpy as np
import cv2
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField
import sensor_msgs.point_cloud2 as pc2

class FisheyeDepthToPointCloudTrue:
    def __init__(self):
        rospy.init_node("fisheye_depth_to_pointcloud_true")

        self.depth_topic = rospy.get_param("~depth_topic", "/camera/depth_predicted")
        self.info_topic = rospy.get_param("~camera_info_topic", "/camera/color/camera_info")
        self.pc_topic = rospy.get_param("~pointcloud_topic", "/camera/pointcloud_fisheye_true")

        self.bridge = CvBridge()
        self.K = None
        self.D = None
        self.height = None
        self.width = None

        rospy.Subscriber(self.info_topic, CameraInfo, self.info_cb, queue_size=1)
        rospy.Subscriber(self.depth_topic, Image, self.depth_cb, queue_size=1)

        self.depth_image = None
        self.pc_pub = rospy.Publisher(self.pc_topic, PointCloud2, queue_size=1)

        self.rate = rospy.Rate(30)  # 30 Hz

    def info_cb(self, msg: CameraInfo):
        self.K = np.array(msg.K).reshape(3,3)
        self.D = np.array(msg.D)
        self.height = msg.height
        self.width = msg.width
        rospy.loginfo("Fisheye intrinsics loaded")
        rospy.Subscriber(self.info_topic, CameraInfo, self.info_cb).unregister()

    def depth_cb(self, msg: Image):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="32FC1")
        self.try_publish()

    def try_publish(self):
        if self.depth_image is None or self.K is None:
            return

        depth = self.depth_image.astype(np.float32)
        mask = (depth > 0) & (~np.isnan(depth))
        if mask.sum() == 0:
            return

        # Generate pixel coordinates
        u, v = np.meshgrid(np.arange(self.width), np.arange(self.height))
        u_valid = u[mask].astype(np.float32)
        v_valid = v[mask].astype(np.float32)
        z_valid = depth[mask]

        pts = np.stack([u_valid, v_valid], axis=-1).reshape(-1,1,2)

        # Back-project using fisheye model (true rays)
        # Output is normalized ray coordinates
        rays = cv2.fisheye.undistortPoints(pts, self.K, self.D, P=None).reshape(-1,2)

        # Compute 3D points along rays
        X = rays[:,0] * z_valid
        Y = rays[:,1] * z_valid
        Z = z_valid

        points_list = [(float(X[i]), float(Y[i]), float(Z[i])) for i in range(len(X))]

        fields = [
            PointField("x", 0, PointField.FLOAT32, 1),
            PointField("y", 4, PointField.FLOAT32, 1),
            PointField("z", 8, PointField.FLOAT32, 1),
        ]

        pc2_msg = pc2.create_cloud(
            fields=fields,
            header=rospy.Header(stamp=rospy.Time.now(), frame_id="camera_optical_frame"),
            points=points_list
        )
        self.pc_pub.publish(pc2_msg)
        self.depth_image = None
        self.rate.sleep()


if __name__ == "__main__":
    FisheyeDepthToPointCloudTrue()
    rospy.spin()
