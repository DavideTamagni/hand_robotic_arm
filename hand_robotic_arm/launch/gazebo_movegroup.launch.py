import os
import yaml
from moveit_configs_utils import MoveItConfigsBuilder
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

# This launch file integrates necessary moveit dependencies with gazebo nodes without loading rViz

def load_yaml(package_name, file_path):
    """Helper function to load raw MoveIt yaml configs as dictionary objects"""
    pkg_share = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(pkg_share, file_path)
    try:
        with open(absolute_file_path, "r") as file:
            return yaml.safe_load(file)
    except EnvironmentError:
        return None

def generate_launch_description():
    package_name = 'hand_robotic_arm'
    urdf_file_name = 'hand_robotic_arm.urdf'
    #moveit_pkg_name = 'hand_robotic_arm_moveit_config'

    pkg_share = get_package_share_directory(package_name)
    world_path = os.path.join(pkg_share, 'worlds', 'my_world.sdf')
    urdf_path = os.path.join(pkg_share, 'urdf', urdf_file_name)
    controllers_yaml_path = os.path.join(pkg_share, 'config', 'ros2_controllers.yaml')

    # Read the URDF file and replace the template flag with your actual system absolute path
    with open(urdf_path, 'r') as infp:
        urdf_content = infp.read()
    
    robot_desc_processed = urdf_content.replace('@CONTROLLER_CONFIG_PATH@', controllers_yaml_path)

    # Node to publish your TF kinematic transforms using the resolved text data
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc_processed, 
            'use_sim_time': True
        }]
    )

    # Append your installation tree path to Gazebo's resource search paths. Harmonic needs this to resolve your mesh paths
    workspace_install_dir = os.path.dirname(pkg_share) 
    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[workspace_install_dir]
    )

    # Start Gazebo Sim pointing to your customized Bullet my_world.sdf via the --physics-engine tag
    gazebo_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ]),
        launch_arguments={
            # '-r' tells it to start the simulation unpaused immediately
            'gz_args': f' -r {world_path} --physics-engine gz-physics-bullet-featherstone-plugin'
        }.items(), 
    )

    # Node to spawn your robot entity into the active Bullet physics simulation Gazebo grid as a string
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'hand_robotic_arm', # Name tag matching your workspace declarations
            '-string', robot_desc_processed, # Pass the resolved XML string text data directly
            '-x', '0.0', '-y', '0.0', '-z', '0.05', # Absolute global start position
        ],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # Clean, modular parameter bridge handling your bridge.yaml
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='isolated_clock_bridge',
        parameters=[{
            'config_file': os.path.join(get_package_share_directory('hand_robotic_arm'), 'config', 'bridge.yaml'),
            'use_sim_time': True,
            'lazy': False  
        }],
        on_exit=Shutdown(), # If the bridge drops, it exits cleanly without silently hanging in the background
        output='screen'
    )

    # Spawner nodes to activate your software controllers inside Gazebo
    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        parameters=[{'use_sim_time': True}], 
        output='screen'
    )

    arm_group_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_group_controller'],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    hand_group_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['hand_group_controller'],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # NATIVE PARAMETER CONFIGURATION USING COPIED URDF
   
    moveit_config = (
        MoveItConfigsBuilder("hand_robotic_arm", package_name="hand_robotic_arm_moveit_config")
        .robot_description(file_path="config/hand_robotic_arm.urdf") 
        .robot_description_semantic(file_path="config/hand_robotic_arm.srdf")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(), 
            {
                "use_sim_time": True,
                "use_fake_hardware": False,
                "moveit_controller_manager": "moveit_simple_controller_manager/MoveItSimpleControllerManager",
                "moveit_manage_controllers": True,

                # 🛠️ THE CRITICAL TIME FIX: Nested explicitly inside the ompl planning namespace
                "ompl.planning_plugins": ["ompl_interface/OMPLPlanner"],
                "ompl.request_adapters": [
                    "default_planning_request_adapters/ResolveConstraintFrames",
                    "default_planning_request_adapters/ValidateWorkspaceBounds",
                    "default_planning_request_adapters/CheckStartStateBounds",
                    "default_planning_request_adapters/CheckStartStateCollision",
                ],
                "ompl.response_adapters": [
                    "default_planning_response_adapters/AddTimeOptimalParameterization",
                    "default_planning_response_adapters/ValidateSolution",
                ],
                
                # Execution tracking controls
                "trajectory_execution.allowed_execution_duration_scaling": 2.0,
                "start_state_max_bounds_error": 0.05,
                "trajectory_execution.allowed_start_tolerance": 0.05,
                "trajectory_execution.execution_duration_monitoring": False,
                "publish_robot_description": True,
                "publish_robot_description_semantic": True,           
            }
        ],
    )


    return LaunchDescription([
        set_gz_resource_path,  
        gazebo_sim,
        robot_state_publisher,
        spawn_robot,
        ros_gz_bridge,
        joint_state_broadcaster,
        arm_group_controller,
        hand_group_controller,
        move_group
    ])
