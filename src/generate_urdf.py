import argparse
import os

import xacrodoc as xd

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ros_path", type=str, required=True, help="Reachy 2 ROS workspace")
    parser.add_argument("--model", type=str, choices=["beta", "dvt"], default="dvt", help="Reachy 2 model []")
    args = parser.parse_args()

    xacro_file = os.path.join(args.ros_path, "reachy2_core/reachy_description/urdf/reachy.urdf.xacro")

    xd.packages.look_in([args.ros_path])

    doc = xd.XacroDoc.from_file(xacro_file, subargs={"robot_model": args.model})

    doc.to_urdf_file("reachy2.urdf")
