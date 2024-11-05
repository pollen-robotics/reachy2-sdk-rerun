# Reachy 2 - rerun

This repo demonstrates how to use [rerun](https://rerun.io) to log data from Reachy 2 using the SDK.


## Prerequisites

Dependencies are detailed in the `setup.cfg` file. To install them, run:
```
pip install -e .[dev]
```
Include *[dev]* for optional development tools.


## Usage 

### Generate urdf

The following command will generate *reachy2.urdf*.

```
python src/generate_urdf.py --ros_path <path>
```

The ROS path points to Reachy 2 workspace with the repo [listed here](https://github.com/pollen-robotics/docker_reachy2_core/blob/develop/sources_config/beta.src). There is no need for a ROS system to run this script. These repos can be checkout out anywhere. [vcstool](https://github.com/dirk-thomas/vcstool) can be used to clone all of them at once. 

### start rerun

```
python src/rerun_recorder.py --urdf reachy2.urdf --teleop_camera --depth_camera --ip localhost
```

You should see something like ![image](docs/rerun_screenshot.png)

```
python src/rerun_recorder.py --help
```
to get more information on the parameters.

## Troubleshooting

If the rerun page doesn't launch, you may have an issue of graphic driver (`Error: WGPU error: There was no valid format for the surface at all.`). If so, you can use this command : 

```console
WAYLAND_DISPLAY= python src/rerun_recorder.py --urdf reachy2.urdf
```

If you want more infos, you can visit [Rerun website](https://rerun.io/docs/getting-started/troubleshooting#graphics-issues) directly.