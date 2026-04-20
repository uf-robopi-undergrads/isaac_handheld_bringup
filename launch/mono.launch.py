from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

def generate_launch_description():
    # 1. Standard V4L2 Camera Node
    camera_node = ComposableNode(
        name='v4l2_camera',
        package='v4l2_camera',
        plugin='v4l2_camera::V4L2Camera',
        parameters=[{
            'video_device': '/dev/video0',
            'image_size': [640, 480],
            # WARNING: VSLAM requires calibration! 
            # You must provide a valid calibration file here:
            'camera_info_url': 'file:///workspaces/isaac_ros-dev/config/camera.yaml' 
        }],
        # Remap standard v4l2 outputs to the inputs expected by Isaac ROS VSLAM
        remappings=[
            ('image_raw', 'visual_slam/image_0'),
            ('camera_info', 'visual_slam/camera_info_0')
        ]
    )

    # 2. Isaac ROS Visual SLAM Node
    visual_slam_node = ComposableNode(
        name='visual_slam_node',
        package='isaac_ros_visual_slam',
        plugin='nvidia::isaac_ros::visual_slam::VisualSlamNode',
        parameters=[{
            'num_cameras': 1,                # Tell VSLAM to run in monocular mode
            'enable_imu_fusion': False,      # Disable IMU since we only have a camera
            'base_frame': 'camera_link',     # The physical location of the camera
            'odom_frame': 'odom',            # The frame the SLAM algorithm will publish to
            'map_frame': 'map',
            'enable_rectified_pose': False   # Depends on if your camera is pre-rectified
        }]
    )

    # 3. The Container
    # This runs both nodes in the same process for hardware-accelerated zero-copy sharing
    container = ComposableNodeContainer(
        name='isaac_ros_vslam_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        composable_node_descriptions=[
            camera_node,
            visual_slam_node
        ],
        output='screen'
    )

    return LaunchDescription([container])