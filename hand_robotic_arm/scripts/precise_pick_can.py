#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

# Standard MoveIt Action and Message primitives
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, JointConstraint

class HumanoidPrecisePicker(Node):
    def __init__(self):
        super().__init__('humanoid_precise_picker')
        
        # 1. Enable reentrant threading to handle simultaneous action processing
        self.callback_group = ReentrantCallbackGroup()
        
        # Connect to your system's motion planning action server with the callback group
        self.action_client = ActionClient(
            self, 
            MoveGroup, 
            '/move_action', 
            callback_group=self.callback_group
        )
        self.get_logger().info('Action client initialized. Awaiting connection channel...')

    def run_sequence(self):
        """ALL STEP STEPS LIVE HERE: Runs on a background thread keeping network pipelines clear."""
        self.get_logger().info('Connecting to MoveGroup engine channels...')

        # Non-blocking connection hook
        while not self.action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn('/move_group server not active yet, retrying...')
        
        self.get_logger().info('Connected! Starting multi-stage precise pick sequence.')

        # Define explicit joint string keys matching your hardware layer
        arm_joints = [
            'base_joint', 'shoulder_joint', 'elbow_joint', 
            'rotating_forearm_joint', 'wrist_pitch_joint', 'wrist_yaw_joint'
        ]
        hand_joints = ['thumb_base_joint', 'thumb_joint']
        
        # Map out the explicit multi-stage trajectory positions (in Radians)
        pose_arm_home     = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        pose_arm_approach = [-1.7700, 1.10, 0.60, 1.6250, 0.0, -0.40]  # Hovers safely ABOVE the can
        pose_arm_grasp    = [-1.7700, 1.51, 0.50, 1.6250, 0.0, -0.40] # Lowers flush to encircle it
        pose_arm_lift     = [-1.7700, 1.10, 0.60, 1.6250, 0.0, -0.40]  # Lifts the object into the air
        pose_arm_place    = [-1.7700, 1.51, 0.50, 1.6200, 0.0, -0.45]  # Places the object on the box
        
        pose_hand_open    = [-0.55, 0.50]
        pose_hand_grasp   = [0.14, 0.50]
        pose_hand_close   = [0.10, -0.12]
        pose_hand_home    = [0.0, 0.0]

        # Synchronized Execution Pipeline Queue
        time.sleep(1.0)
        
        # Step 1: Open the hand while vertical at home
        self.get_logger().info('Step 1: Opening hand wide...')
        self.send_joint_target('hand_group', hand_joints, pose_hand_open)
        time.sleep(1.0)
        
        # Step 2: Approach above the can (Swinging cleanly over the top)
        self.get_logger().info('Step 2: Swinging safely above the target can axis...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_approach)
        time.sleep(1.0)
        
        # Step 3: Descend straight down to encircle the cylinder wall
        self.get_logger().info('Step 3: Descending vertically to encircle the can...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_grasp)
        self.send_joint_target('hand_group', hand_joints, pose_hand_grasp)
        time.sleep(1.0)
        
        # Step 4: Close fingers securely around the can
        self.get_logger().info('Step 4: Closing hand onto the can...')
        self.send_joint_target('hand_group', hand_joints, pose_hand_close)
        time.sleep(1.0)
        
        # Step 5: Lift the can straight up off the ground plane
        self.get_logger().info('Step 5: Lifting the can off the floor...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_lift)
        time.sleep(1.0)
        
        # Step 6: Return safely to vertical home state carrying the can
        self.get_logger().info('Step 6: Returning to home carrying the object...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_home)
        time.sleep(1.0)

        # Step 7: Descend straight down to place back the can on the table
        self.get_logger().info('Step 7: Swinging safely above the table...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_approach)
        time.sleep(1.0)

        # Step 8: Descend straight down to place back the can on the table
        self.get_logger().info('Step 8: Descending vertically to place the can...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_place)
        time.sleep(1.0)

        # Step 9: Open the hand to release the can
        self.get_logger().info('Step 9: Opening hand wide...')
        self.send_joint_target('hand_group', hand_joints, pose_hand_open)
        time.sleep(1.0)

        # Step 10: Descend straight down to place back the can on the table
        self.get_logger().info('Step 10: Lifting safely above the table...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_lift)
        time.sleep(1.0)

        # Step 11: Return safely to vertical home state
        self.get_logger().info('Step 11: Returning to home...')
        self.send_joint_target('arm_group', arm_joints, pose_arm_home)
        self.send_joint_target('hand_group', hand_joints, pose_hand_home)
        
        self.get_logger().info('Precise pick and lift operation completed successfully!')

        # Shutdown the executor directly from the worker thread
        self.executor.shutdown()


    def send_joint_target(self, group_name, joint_names, joint_positions):
        """Submits target parameters safely using thread polling to bypass execution lockups."""
        goal_msg = MoveGroup.Goal()
        req = MotionPlanRequest()
        req.group_name = group_name
        req.num_planning_attempts = 10
        req.allowed_planning_time = 5.0

        # 🛠️ ADD THESE PARAMETERS TO FIX THE "TIME NOT INCREASING" TRAJECTORY ERROR
        req.max_velocity_scaling_factor = 0.5  # Cap at 50% speed for smooth physics
        req.max_acceleration_scaling_factor = 0.5
        
        constraints = Constraints()
        for name, pos in zip(joint_names, joint_positions):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = pos
            jc.tolerance_above = 0.05
            jc.tolerance_below = 0.05
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
            
        req.goal_constraints.append(constraints)
        goal_msg.request = req
        goal_msg.planning_options.plan_only = False

        # 🛠️ FORCE MOVEIT TO PROCESS TIME-STAMPS ON THE TRACE
        goal_msg.planning_options.look_around = False
        goal_msg.planning_options.replan = False

        # Asynchronously send the goal request
        send_goal_future = self.action_client.send_goal_async(goal_msg)
        
        # Check completion state via non-blocking polling loops
        while not send_goal_future.done():
            time.sleep(0.05)
            
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f'MoveIt rejected trajectory configuration for {group_name}.')
            return False
            
        get_result_future = goal_handle.get_result_async()
        while not get_result_future.done():
            time.sleep(0.05)
            
        result_response = get_result_future.result()
        return result_response.status == 4

def main(args=None):
    rclpy.init(args=args)
    picker = HumanoidPrecisePicker()
    
    # Instantiate the MultiThreadedExecutor array allocation pool
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(picker)
    
    # Spin up an independent background thread to run your execution queue
    import threading
    sequence_thread = threading.Thread(target=picker.run_sequence)
    sequence_thread.start()
    
    try:
        # Give control over to the executor to handle network packets
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        picker.destroy_node()
        rclpy.shutdown()
        sequence_thread.join()

if __name__ == '__main__':
    main()
