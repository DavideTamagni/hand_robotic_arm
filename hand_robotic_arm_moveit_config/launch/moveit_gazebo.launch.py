import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    # 1. Include your working Gazebo simulation world pipeline
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(
                get_package_share_directory('hand_robotic_arm'),
                'launch',
                'gazebo.launch.py'
            )
        ])
        
    )

    # 2. Build your clean MoveIt configurations
    moveit_config = (
        MoveItConfigsBuilder("hand_robotic_arm", package_name="hand_robotic_arm_moveit_config")
        .planning_pipelines(pipelines=["ompl"])
        .trajectory_execution(moveit_manage_controllers=False)
        .robot_description_kinematics(file_path="config/kinematics.yaml") 
        .to_moveit_configs()
    )

    # 3. Create the standard MoveGroup executable node directly
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.trajectory_execution,
            moveit_config.planning_scene_monitor,
            moveit_config.joint_limits,

            {
                "use_sim_time": True,
                "start_state_max_bounds_error": 0.05,  # Allows up to 3 degrees of physics overshoot
                "trajectory_execution.allowed_start_tolerance": 0.05,
                "trajectory_execution.execution_duration_monitoring": False, # Prevents false timeouts on slow simulation steps
                
                "ompl.request_adapters": [
                    "default_planning_request_adapters/ResolveConstraintFrames",
                    "default_planning_request_adapters/ValidateWorkspaceBounds",
                    "default_planning_request_adapters/CheckStartStateBounds",
                    "default_planning_request_adapters/CheckStartStateCollision",
                ],
                "ompl.response_adapters": [
                    "default_planning_response_adapters/AddTimeOptimalParameterization", # Safe time step interpolation calculator
                    "default_planning_response_adapters/ValidateSolution",
                    "default_planning_response_adapters/DisplayMotionPath",
                ],
            }
        ],
    )

    # 4. Locate the RViz view configuration profile
    rviz_config_path = os.path.join(
        get_package_share_directory("hand_robotic_arm_moveit_config"),
        "config",
        "moveit.rviz"
    )

    # 5. Create the visual RViz node mapping
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        output="screen",
        arguments=["-d", rviz_config_path],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,    
            moveit_config.robot_description_kinematics,  
            moveit_config.planning_pipelines, 
            {"use_sim_time": True} # Hardcoded override inside node memory tree
        ],
    )

    # Add the Joint State Publisher node
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{
            # Explicitly tell it to look at the topic from ros2_control
            'source_list': ['/joint_states'], 
            'rate': 30  # Refresh rate in Hz
        }]
    )

    return LaunchDescription([
        gazebo_launch,   
        move_group_node, 
        rviz_node,        
        joint_state_publisher_node
    ])
