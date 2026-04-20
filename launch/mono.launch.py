import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode

def generate_launch_description():

    # --- 1. Setup RViz2 ---
    isaac_vslam_share_dir = get_package_share_directory('isaac_ros_visual_slam')
    rviz_config_file = os.path.join(isaac_vslam_share_dir, 'rviz', 'default.cfg.rviz')

    # RViz Node (This will launch immediately)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )

    # --- 2. Setup Composable Nodes ---
    # Standard V4L2 Camera Node
    camera_node = ComposableNode(
        name='v4l2_camera',
        package='v4l2_camera',
        plugin='v4l2_camera::V4L2Camera',
        parameters=[{
            'video_device': '/dev/video0',
            'image_size': [640, 480],
            'camera_info_url': 'file:///workspaces/isaac_ros-dev/config/camera.yaml' 
        }],
        # Remap standard v4l2 outputs to the inputs expected by Isaac ROS VSLAM
        remappings=[
            ('image_raw', 'visual_slam/image_0'),
            ('camera_info', 'visual_slam/camera_info_0')
        ]
    )

    # Isaac ROS Visual SLAM Node
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

    # The Container for hardware-accelerated zero-copy sharing
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

    # --- 3. Delay the Container ---
    # Wait 3 seconds for RViz to initialize before starting the camera and SLAM pipeline
    delayed_container = TimerAction(
        period=3.0,
        actions=[container]
    )

    # --- 4. Return the LaunchDescription ---
    return LaunchDescription([
        rviz_node,
        delayed_container
    ])