#!/usr/bin/env python3
import subprocess
import time
import sys

def trigger_reset():
    world_name = "default"
    model_name = "soda_can"
    
    # 1. Remove the old can
    delete_cmd = [
        "gz", "service", "-s", f"/world/{world_name}/remove",
        "--reqtype", "gz.msgs.Entity",
        "--reptype", "gz.msgs.Boolean",
        "--req", f'name: "{model_name}", type: 2'
    ]
    subprocess.run(delete_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Small buffer for the physics pipeline to catch up
    time.sleep(0.3)
    
    # Composite SDF: Cylinder with a hidden 2mm stabilization pad embedded inside the base
    sdf_string = f"""
    <sdf version='1.6'>
      <model name='{model_name}'>
        <link name='link'>
          <inertial>
            <mass>0.350</mass>
            <inertia>
              <ixx>0.00048</ixx><ixy>0</ixy><ixz>0</ixz>
              <iyy>0.00048</iyy><iyz>0</iyz>
              <izz>0.00019</izz>
            </inertia>
          </inertial>
          
          <collision name='cylinder_collision'>
            <geometry>
              <cylinder><radius>0.03</radius><length>0.115</length></cylinder>
            </geometry>
          </collision>
          
          <collision name='bullet_stabilizer_pad'>
            <pose>0 0 -0.0575 0 0 0</pose>
            <geometry>
              <box><size>0.04 0.04 0.002</size></box>
            </geometry>
          </collision>
          
          <visual name='visual'>
            <geometry>
              <cylinder><radius>0.03</radius><length>0.115</length></cylinder>
            </geometry>
            <material>
              <ambient>0.8 0.0 0.0 1</ambient>
              <diffuse>0.8 0.0 0.0 1</diffuse>
              <specular>0.5 0.5 0.5 1.0</specular>
            </material>
          </visual>
        </link>
      </model>
    </sdf>
    """
    
    clean_sdf = sdf_string.replace("\n", "").replace("'", '"')
    
    spawn_req_string = (
        f'sdf: \'{clean_sdf}\', '
        f'name: "{model_name}", '
        f'pose: {{position: {{x: 0.09, y: 0.70, z: 0.2575}}}}'
    )
    
    spawn_cmd = [
        "gz", "service", "-s", f"/world/{world_name}/create",
        "--reqtype", "gz.msgs.EntityFactory",
        "--reptype", "gz.msgs.Boolean",
        "--req", spawn_req_string
    ]
    
    subprocess.run(spawn_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("=" * 50)
    print(" Gazebo Harmonic / ROS 2 Jazzy Live Scene Resetter")
    print("=" * 50)
    print("Keep this terminal window visible alongside your simulation.")
    print("-> Press [ENTER] to instantly teleport a fresh soda_can onto the box.")
    print("-> Press [Ctrl + C] to close this reset tool.")
    print("-" * 50)
    
    # Spawn the initial can right away when the script starts
    trigger_reset()
    print("[*] Initial soda_can spawned successfully.")

    try:
        while True:
            input("\n[Ready] Press Enter to reset the target can... ")
            sys.stdout.write("\033[A\033[K") # Clears the "Press Enter" text to keep terminal clean
            print("[-] Resetting can... ", end="", flush=True)
            trigger_reset()
            print("Done! \u2714") # Prints a clean checkmark
    except KeyboardInterrupt:
        print("\n\nExiting scene reset tool. Happy training!")

if __name__ == "__main__":
    main()
