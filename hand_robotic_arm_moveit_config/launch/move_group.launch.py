from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("hand_robotic_arm", package_name="hand_robotic_arm_moveit_config")
        .planning_pipelines(pipelines=["ompl"])  # Explicitly forces OMPL pipeline initialization
        .parameter("use_sim_time", True)
        .parameter("trajectory_execution.allowed_start_tolerance", 0.1)  # Pads gravity droop
        .parameter("trajectory_execution.allowed_goal_duration_margin", 2.0)
        .to_moveit_configs()
    )

    
    return generate_move_group_launch(moveit_config)


    