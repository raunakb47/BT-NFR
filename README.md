# GPSR Behviour Tree Generation with SLM

This ROS 2 package provides a planning node for the General Purpose Service Robot (GPSR) task category in RoboCup@Home

It converts natural language commands into structured behavior tree action sequences using a local **Small Language Model (SLM)**, while actively incorporating **Non-Functional Requirements (NFRs)** to improve plan quality and compliance with robot constraints.

## Features

- Uses Qwen3-8B (Q8 quantized GGUF) running locally via llama_ros
- Single monolithic prompt for improved consistency and reduced hallucinations
- Grammar-constrained JSON output for reliable parsing
- NFR Integration: Relevant Non-Functional Requirements are considered for each chosen action to enhance explanations, add safety checks, or include fallbacks when beneficial
- Dynamic NFR filtering: Only NFR profiles matching the selected actions are taken into account

## Technology Stack

- **Model**: Qwen3-8B (local SLM, Q8 GGUF)
- **Backend**: llama_ros + llama.cpp
- **Framework**: ROS 2 Jazzy + LangChain
- **Output**: Structured JSON → Behavior Tree XML

## How It Works

1. Receives a natural language GPSR command via service
2. Generates a base functional plan using only the defined robot actions
3. Identifies which NFR profiles match the actions in the plan
4. Incorporates relevant NFR constraints to improve action explanations
5. Add safety checks or verification steps when appropriate
6. Returns a structured JSON plan that is converted into a Behavior Tree

NFR integration helps ensure the generated plans respect robot capabilities, operational constraints, and quality attributes defined for RoboCup@Home.

## Key Design Principles

- **Monolithic Prompt**: Single prompt for better stability
- **NFR as Active Guidance**: Relevant NFRs are considered to meaningfully improve the plan
- **Functional Consistency**: Core actions and parameters remain stable and aligned with the original implementation
- **Safety**: Automatic fallback to base plan if refinement produces invalid output

## Configuration
- **Model temperature**: 0.3
- Grammar enforcement ensures valid JSON output
- NFR profiles can be easily extended or modified in `nfr_profiles.json`

## Dependencies
- ROS 2 Jazzy
- llama_ros package
- Qwen3-8B Q8 GGUF model (can be changed as needed; may require updating llama.cpp for updated architecture support)
- langchain-core

## Installation

1. [Install](https://docs.ros.org/en/jazzy/Installation.html) ROS 2 Jazzy (preferably in linux environment)

2. [Create](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html) a ROS 2 workspace

3. [Setup](https://docs.python.org/3/library/venv.html) python 3 virtual environment to install dependencies

4. [Install](https://github.com/mgonzs13/llama_ros) `llama_ros`

5. Clone the repository and build

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
