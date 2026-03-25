# GPSR Behviour Tree Generation with SLM

## Installation

1. Install ROS 2 Jazzy (preferably in linux environment): [https://docs.ros.org/en/humble/Installation.html](https://docs.ros.org/en/jazzy/Installation.html)

2. [Create](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html) a ROS 2 workspace

3. Clone the repository and build

```shell
cd ~/ros2_ws/src
git clone https://github.com/raunakb47/BT-NFR.git
cd ~/ros2_ws
colcon build
```

## Run

Activate the GPSR planning node

```shell
ros2 run gpsr_planning planning_node
```

## Demo

```shell
ros2 run gpsr_demo gpsr_demo_node
```
