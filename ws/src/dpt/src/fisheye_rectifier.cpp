#include <ros/ros.h>
#include <sensor_msgs/Image.h>
#include <sensor_msgs/CameraInfo.h>
#include <cv_bridge/cv_bridge.h>
#include <opencv2/opencv.hpp>
#include <opencv2/calib3d.hpp>
#include <vector>

class FisheyeRectifier {
public:
    FisheyeRectifier(ros::NodeHandle& nh) : nh_(nh) {
        // Load camera parameters from ROS params
        XmlRpc::XmlRpcValue K_list, D_list;
        if (!nh_.getParam("usb_cam/K", K_list) || !nh_.getParam("usb_cam/D", D_list)) {
            ROS_ERROR("Camera parameters not found!");
            ros::shutdown();
        }

        nh_.param("usb_cam/width", width_, 640);
        nh_.param("usb_cam/height", height_, 480);
        nh_.param("balance", balance_, 1.0);
        nh_.param("fov_scale", fov_scale_, 0.6);

        old_size_ = cv::Size(width_, height_);

        // Convert K
        K_ = cv::Mat::eye(3,3,CV_64F);
        for (int i=0;i<3;i++)
            for (int j=0;j<3;j++)
                K_.at<double>(i,j) = static_cast<double>(K_list[i][j]);

        // Convert D
        D_ = cv::Mat(D_list.size(),1,CV_64F);
        for (int i=0;i<D_list.size();i++)
            D_.at<double>(i) = static_cast<double>(D_list[i]);

        // Compute new camera matrix
        new_K_ = cv::Mat::eye(3,3,CV_64F);
        cv::fisheye::estimateNewCameraMatrixForUndistortRectify(
            K_, D_, old_size_, cv::Mat::eye(3,3,CV_64F),
            new_K_, balance_, old_size_, fov_scale_
        );

        // Compute rectification maps
        cv::fisheye::initUndistortRectifyMap(
            K_, D_, cv::Mat::eye(3,3,CV_64F), new_K_, old_size_, CV_32FC1, map1_, map2_
        );

        ROS_INFO("Fisheye rectification maps initialized.");

        // Prepare CameraInfo message template
        caminfo_msg_.width = width_;
        caminfo_msg_.height = height_;
        caminfo_msg_.distortion_model = "equidistant";

        // Fill D vector with zeros (we will keep new_K_ in K)
        caminfo_msg_.D.assign(D_list.size(),0.0);

        // Fill K
        for(int i=0;i<3;i++)
            for(int j=0;j<3;j++)
                caminfo_msg_.K[i*3+j] = new_K_.at<double>(i,j);

        // Fill P
        cv::Mat P = cv::Mat::zeros(3,4,CV_64F);
        new_K_.copyTo(P(cv::Rect(0,0,3,3)));
        for(int i=0;i<12;i++)
            caminfo_msg_.P[i] = P.at<double>(i/4,i%4);

        // Fill R
        double R_vals[9] = {1,0,0, 0,1,0, 0,0,1};
        for(int i=0;i<9;i++)
            caminfo_msg_.R[i] = R_vals[i];

        std::string input_image_topic, output_image_topic, output_camera_info_topic;
        nh_.param<std::string>("input_image", input_image_topic, "/usb_cam/image_raw");
        nh_.param<std::string>("image_rectified", output_image_topic, "/usb_cam/image_rect");
        nh_.param<std::string>("camera_info_rectified", output_camera_info_topic, "/usb_cam/camera_info_rect");

        // Subscribers & publishers using the param values
        image_sub_ = nh_.subscribe(input_image_topic, 10, &FisheyeRectifier::imageCb, this);
        image_pub_ = nh_.advertise<sensor_msgs::Image>(output_image_topic, 10);
        caminfo_pub_ = nh_.advertise<sensor_msgs::CameraInfo>(output_camera_info_topic, 10);


    }

private:
    ros::NodeHandle nh_;
    ros::Subscriber image_sub_;
    ros::Publisher image_pub_, caminfo_pub_;
    cv::Mat K_, D_, new_K_, map1_, map2_;
    int width_, height_;
    double balance_, fov_scale_;
    cv::Size old_size_;
    sensor_msgs::CameraInfo caminfo_msg_;
    bool caminfo_received_ = false;


    void imageCb(const sensor_msgs::ImageConstPtr& msg) {
        if(!caminfo_received_) return;

        cv_bridge::CvImagePtr cv_ptr;
        try {
            cv_ptr = cv_bridge::toCvCopy(msg, "rgb8");
        } catch (cv_bridge::Exception& e) {
            ROS_ERROR("cv_bridge exception: %s", e.what());
            return;
        }

        cv::Mat rect_image;
        cv::remap(cv_ptr->image, rect_image, map1_, map2_, cv::INTER_LINEAR);

        sensor_msgs::ImagePtr out_msg = cv_bridge::CvImage(msg->header, "rgb8", rect_image).toImageMsg();
        caminfo_msg_.header.stamp = msg->header.stamp;

        image_pub_.publish(out_msg);
        caminfo_pub_.publish(caminfo_msg_);
    }
};

int main(int argc, char** argv) {
    ros::init(argc, argv, "fisheye_rectifier");
    ros::NodeHandle nh("~");
    FisheyeRectifier rectifier(nh);
    ros::spin();
    return 0;
}
