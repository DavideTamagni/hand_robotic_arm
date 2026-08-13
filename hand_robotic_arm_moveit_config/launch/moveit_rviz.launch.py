from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_moveit_rviz_launch


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("hand_robotic_arm", package_name="hand_robotic_arm_moveit_config")
        .to_moveit_configs()
    )

    launch_desc = generate_moveit_rviz_launch(moveit_config)
    
    # Overwrite the node parameters list directly to bypass builder formatting quirks
    for action in launch_desc.entities:
        if hasattr(action, 'parameters') and action.parameters is not None:
            action.parameters.append({'use_sim_time': True})
            
    return launch_desc
    
