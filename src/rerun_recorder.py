import argparse
import logging
import time
from typing import List, Tuple
from uuid import uuid4

import numpy as np
import numpy.typing as npt
import rerun as rr
from reachy2_sdk import ReachySDK
from reachy2_sdk.media.camera import CameraView
from rerun_loader_urdf import URDFLogger
from urdf_parser_py import urdf


def _log_camera_parameters(side: CameraView, reachy: ReachySDK) -> Tuple[int, int, npt.NDArray[np.uint8]]:
    side_str = "right"
    if side == CameraView.LEFT:
        side_str = "left"
    height, width, distortion_model, D, K, R, P = reachy.cameras.teleop.get_parameters(side)
    rr.log(f"/teleop_camera/{side_str}/camera_info/height", rr.Scalar(height), static=True)
    rr.log(f"/teleop_camera/{side_str}/camera_info/width", rr.Scalar(width), static=True)
    rr.log(
        f"/teleop_camera/{side_str}/camera_info/distortion_model", rr.TextLog(text=distortion_model, level="INFO"), static=True
    )

    rr.log(f"/teleop_camera/{side_str}/camera_info/D", rr.Tensor(D), static=True)
    rr.log(f"/teleop_camera/{side_str}/camera_info/K", rr.Tensor(K), static=True)
    rr.log(f"/teleop_camera/{side_str}/camera_info/R", rr.Tensor(R), static=True)
    rr.log(f"/teleop_camera/{side_str}/camera_info/P", rr.Tensor(P), static=True)

    return height, width, K


def _log_teleop_cameras(
    height: int, width: int, K: npt.NDArray[np.uint8], joint_cam: str, side: CameraView, reachy: ReachySDK
) -> None:
    frame, ts = reachy.cameras.teleop.get_compressed_frame(side)

    rr.set_time_nanos("reachy_ROS_time", ts)

    rr.log(f"{joint_cam}/image", rr.ImageEncoded(contents=frame, format=rr.ImageFormat.JPEG))

    rr.log(
        f"{joint_cam}/image",
        rr.Pinhole(
            image_from_camera=rr.datatypes.Mat3x3(K),
            width=width,
            height=height,
            image_plane_distance=0.7,
            camera_xyz=rr.ViewCoordinates.RDF,
        ),
    )


def _log_depth_camera_parameters(side: CameraView, reachy: ReachySDK) -> Tuple[int, int, npt.NDArray[np.uint8]]:
    side_str = "color"
    if side == CameraView.DEPTH:
        side_str = "depth"
    height, width, distortion_model, D, K, R, P = reachy.cameras.depth.get_parameters(side)
    rr.log(f"/depth_camera/{side_str}/camera_info/height", rr.Scalar(height), static=True)
    rr.log(f"/depth_camera/{side_str}/camera_info/width", rr.Scalar(width), static=True)
    rr.log(
        f"/depth_camera/{side_str}/camera_info/distortion_model", rr.TextLog(text=distortion_model, level="INFO"), static=True
    )

    rr.log(f"/depth_camera/{side_str}/camera_info/D", rr.Tensor(D), static=True)
    rr.log(f"/depth_camera/{side_str}/camera_info/K", rr.Tensor(K), static=True)
    rr.log(f"/depth_camera/{side_str}/camera_info/R", rr.Tensor(R), static=True)
    rr.log(f"/depth_camera/{side_str}/camera_info/P", rr.Tensor(P), static=True)

    return height, width, K


def _log_depth_color_cameras(height: int, width: int, K: npt.NDArray[np.uint8], joint_cam: str, reachy: ReachySDK) -> None:
    frame, ts = reachy.cameras.depth.get_compressed_frame(CameraView.LEFT)

    rr.set_time_nanos("reachy_ROS_time", ts)

    rr.log(f"{joint_cam}/image", rr.ImageEncoded(contents=frame, format=rr.ImageFormat.JPEG))

    rr.log(
        f"{joint_cam}/image",
        rr.Pinhole(
            image_from_camera=rr.datatypes.Mat3x3(K),
            width=width,
            height=height,
            image_plane_distance=0.8,
            camera_xyz=rr.ViewCoordinates.RDF,
        ),
    )


def _log_depth_cameras(height: int, width: int, K: npt.NDArray[np.uint8], joint_cam: str, reachy: ReachySDK) -> None:
    frame, ts = reachy.cameras.depth.get_depth_frame(CameraView.DEPTH)

    rr.set_time_nanos("reachy_ROS_time", ts)

    rr.log(f"{joint_cam}/image", rr.DepthImage(frame, meter=1000.0, colormap=rr.components.Colormap.Viridis))

    rr.log(
        f"{joint_cam}/image",
        rr.Pinhole(
            image_from_camera=rr.datatypes.Mat3x3(K),
            width=width,
            height=height,
            image_plane_distance=0.8,
            camera_xyz=rr.ViewCoordinates.RDF,
        ),
    )


def _get_joints(joint_name: str, urdf: urdf) -> urdf.Joint:
    for j in urdf.joints:
        if j.name == joint_name:
            return j
    raise RuntimeError("Invalid joint name")


def _log_arm_joints_poses(arm_pos: List[float], urdf_logger: URDFLogger, left: bool) -> None:
    side = "r"
    if left:
        side = "l"
    joint = _get_joints(f"{side}_shoulder_pitch", urdf_logger.urdf)
    joint.origin.rotation = [0.0, arm_pos[0], 0.0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_shoulder_roll", urdf_logger.urdf)
    joint.origin.rotation = [arm_pos[1], 0.0, 0.0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_elbow_pitch", urdf_logger.urdf)
    joint.origin.rotation = [0.0, arm_pos[3], 0.0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_elbow_yaw", urdf_logger.urdf)
    joint.origin.rotation = [0.0, 0.0, arm_pos[2]]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_wrist_roll", urdf_logger.urdf)
    joint.origin.rotation = [arm_pos[4], 0.0, 0.0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_wrist_pitch", urdf_logger.urdf)
    joint.origin.rotation = [0.0, arm_pos[5], 0.0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_wrist_yaw", urdf_logger.urdf)
    joint.origin.rotation = [0.0, 0.0, arm_pos[6]]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)


def _log_head_poses(rpy_head: List[float], urdf_logger: URDFLogger) -> None:
    joint = _get_joints("neck_roll", urdf_logger.urdf)
    joint.origin.rotation = [rpy_head[0], 0.0, 0.0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints("neck_pitch", urdf_logger.urdf)
    joint.origin.rotation = [0.0, rpy_head[1], 0.0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints("neck_yaw", urdf_logger.urdf)
    joint.origin.rotation = [0.0, 0.0, rpy_head[2]]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)


def _log_gripper(left: bool, reachy: ReachySDK, urdf_logger: URDFLogger) -> None:
    side = "r"
    part = reachy.r_arm
    if left:
        side = "l"
        part = reachy.l_arm

    rr.log(f"reachy/{side}_arm/wrist/gripper", rr.Scalar(part.gripper.opening))

    # this is for visual rendering only. coef are from the URDF
    scaled_opening = part.gripper.opening / 100 * 2 - 1  # from [0;100] to [-1;1]

    joint = _get_joints(f"{side}_hand_finger_proximal", urdf_logger.urdf)
    joint.origin.rotation = [scaled_opening * -0.4689, 0.0, 0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_hand_finger_distal", urdf_logger.urdf)
    joint.origin.rotation = [scaled_opening * 0.4689, 0.0, 0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_hand_finger_proximal_mimic", urdf_logger.urdf)
    joint.origin.rotation = [scaled_opening * -0.4689, 0.0, np.pi]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)

    joint = _get_joints(f"{side}_hand_finger_distal_mimic", urdf_logger.urdf)
    joint.origin.rotation = [scaled_opening * 0.4689, 0.0, 0]
    urdf_logger.log_joint(urdf_logger.joint_entity_path(joint), joint=joint)


def check_reachy(reachy: ReachySDK) -> None:
    if not reachy.is_connected():
        exit("Reachy is not connected.")
    elif args.teleop_camera and reachy.cameras.teleop is None:
        exit("Teleop camera is not connected.")
    elif args.depth_camera and reachy.cameras.depth is None:
        exit("Depth camera is not connected.")


def main_loop(args: argparse.Namespace) -> None:
    reachy = ReachySDK(host=args.ip)

    check_reachy(reachy)

    rr.init("recorder_example", recording_id=uuid4())
    rr.spawn(memory_limit="50%")
    if args.save:
        rr.save(path=args.save)

    torso_entity = "world/world_joint/base_link/back_bar_joint/back_bar/torso_base/torso"

    urdf_logger = URDFLogger(args.urdf, torso_entity)

    rr.set_time_nanos("reachy_ROS_time", reachy.get_update_timestamp())

    urdf_logger.log()

    if args.teleop_camera:
        height, width, K_left = _log_camera_parameters(CameraView.LEFT, reachy)
        _, _, K_right = _log_camera_parameters(CameraView.RIGHT, reachy)
        joint_left_cam = _get_joints("left_camera_optical_joint", urdf_logger.urdf)
        name_joint_left_cam = urdf_logger.joint_entity_path(joint_left_cam)
        joint_right_cam = _get_joints("right_camera_optical_joint", urdf_logger.urdf)
        name_joint_right_cam = urdf_logger.joint_entity_path(joint_right_cam)

    if args.depth_camera:
        height_depth, width_depth, K_color_depth = _log_depth_camera_parameters(CameraView.LEFT, reachy)
        _, _, K_depth = _log_depth_camera_parameters(CameraView.DEPTH, reachy)
        # ToDo : fix names for depth camera
        joint_depth_color_cam = _get_joints("depth_cam_l_optical_joint", urdf_logger.urdf)
        name_joint_depth_color_cam = urdf_logger.joint_entity_path(joint_depth_color_cam)
        joint_depth_cam = _get_joints("depth_cam_r_optical_joint", urdf_logger.urdf)
        name_joint_depth_cam = urdf_logger.joint_entity_path(joint_depth_cam)

    # configure vizualisers
    rr.log("reachy/l_arm/wrist/gripper", rr.SeriesLine(color=[255, 0, 0], name="left gripper", width=2), static=True)
    rr.log("reachy/r_arm/wrist/gripper", rr.SeriesLine(color=[0, 255, 0], name="right gripper", width=2), static=True)

    try:
        sampling_rate = 1.0 / args.rec_freq

        while True:
            rr.set_time_nanos("reachy_ROS_time", reachy.get_update_timestamp())
            rpy_head = np.deg2rad(reachy.head.get_current_positions())
            _log_head_poses(rpy_head, urdf_logger)

            l_arm_pos = reachy.l_arm.get_current_positions(degrees=False)
            _log_arm_joints_poses(l_arm_pos, urdf_logger, True)

            r_arm_pos = reachy.r_arm.get_current_positions(degrees=False)
            _log_arm_joints_poses(r_arm_pos, urdf_logger, False)

            _log_gripper(left=True, reachy=reachy, urdf_logger=urdf_logger)
            _log_gripper(left=False, reachy=reachy, urdf_logger=urdf_logger)

            if args.teleop_camera:
                _log_teleop_cameras(height, width, K_left, name_joint_left_cam, CameraView.LEFT, reachy)
                _log_teleop_cameras(height, width, K_right, name_joint_right_cam, CameraView.RIGHT, reachy)

            if args.depth_camera:
                _log_depth_color_cameras(height_depth, width_depth, K_color_depth, name_joint_depth_color_cam, reachy)
                _log_depth_cameras(height_depth, width_depth, K_depth, name_joint_depth_cam, reachy)

            time.sleep(sampling_rate)

    except KeyboardInterrupt:
        logging.info("User Interrupt")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", type=str, required=True, help="reachy2.urdf")
    parser.add_argument("--ip", type=str, default="localhost", help="IP address of the ReachySDK host")
    parser.add_argument("--save", type=str, help="path to save the data")
    parser.add_argument("--teleop_camera", action="store_true", help="Enable recording of teleop camera")
    parser.add_argument("--depth_camera", action="store_true", help="Enable recording of depth camera")
    parser.add_argument("--rec_freq", type=int, default=5, help="recording frequency (Hz)")
    args = parser.parse_args()

    main_loop(args)
