import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode

def generate_launch_description():

    # --- 1. Setup RViz2 ---
    bringup_share_dir = get_package_share_directory('isaac_handheld_bringup')

    rviz_config_file = os.path.join(bringup_share_dir, 'config', 'rviz', 'handheld.cfg.rviz')

    # RViz Node (This will launch immediately)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        output='log'
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
            'camera_frame_id': 'camera_link',
            'camera_info_url': 'file:///workspaces/isaac_ros-dev/src/isaac_handheld_bringup/config/camera.yaml' 
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
            # might need to add a transform later to make it make sense
            # keep these default for now
            'base_frame': 'base_link',
            # the v4l2_cam node doesn't publish frame id in camera info... manually specify here
            'camera_optical_frames': ['camera_link'],
            # 'odom_frame': 'odom',            # The frame the SLAM algorithm will publish to
            # 'map_frame': 'map',
            'enable_rectified_pose': False   # Depends on if your camera is pre-rectified
        }]
    )

    # account for upside down camera mount
    tf_publisher = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='board_to_camera_tf',
        # 180 deg rotation
        arguments=['0', '0', '0', '0', '0', '1.570796', 'base_link', 'camera_link'],
        output='screen'
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
        tf_publisher,
        delayed_container
    ])