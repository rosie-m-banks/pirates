#!/usr/bin/env python3
import depthai as dai
import os
import cv2
import time
from generic_camera import GenericCamera
from threading import Timer

resolution_map = {
    "400P": dai.MonoCameraProperties.SensorResolution.THE_400_P,
    "480P": dai.MonoCameraProperties.SensorResolution.THE_480_P,
    "720P": dai.MonoCameraProperties.SensorResolution.THE_720_P,
    "800P": dai.MonoCameraProperties.SensorResolution.THE_800_P,
    "1080P": dai.MonoCameraProperties.SensorResolution.THE_1200_P,
}

preset_map = {
    "FAST_ACCURACY": dai.node.StereoDepth.PresetMode.FAST_ACCURACY,
    "FAST_DENSITY": dai.node.StereoDepth.PresetMode.FAST_DENSITY,
}


def config_rgb_image(pipeline, key, cam_cfg):
    rgb_cfg = cam_cfg.get("rgb")

    width = rgb_cfg.get("rgb_width", 640)
    height = rgb_cfg.get("rgb_height", 480)
    fps = rgb_cfg.get("rgb_fps", 30)

    cam_rgb = pipeline.create(dai.node.ColorCamera)
    cam_rgb.setPreviewSize(width, height)
    cam_rgb.setFps(fps)
    cam_rgb.setInterleaved(False)
    cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

    video_queue = cam_rgb.video.createOutputQueue()
    return video_queue

class Oak(GenericCamera):
    def __init__(self, path):
        super().__init__("oak_node", path)

        # self.path = path
        # self._camera_info = self.get_cam_data(self.load_cameras_yaml(), "oak")
        # self.gray = None

        # for key, cam_cfg in self._camera_info.items():
        #     cam_cfg = cam_cfg.get("ros__parameters")

        #     self.logger.info(
        #         f"Starting OAK camera: {key} (mxid={cam_cfg['camera']['i_mx_id']})"
        #     )

        #     device = self._open_device_with_retry(cam_cfg["camera"]["i_mx_id"])
        #     pipeline = dai.Pipeline(device)

        #     rgb = config_rgb_image(pipeline, key, cam_cfg)
            
        #     self.devices[key] = pipeline
        #     self.queues[key] = {
        #         "rgb": rgb
        #     }

        #     pipeline.start()

        # self.timer = Timer(1.0 / 30.0, self.publish_frames)
        # self.timer.start()

    def _open_device_with_retry(self, mxid, max_attempts=5, delay_s=1.0):
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.info(
                    f"Connecting to OAK device (mxid={mxid}), attempt {attempt}/{max_attempts}"
                )
                device_info = self._wait_for_device_info(mxid, delay_s)
                return dai.Device(device_info)
            except RuntimeError as exc:
                last_exc = exc
                available = self._get_available_mxids()
                available_str = ", ".join(available) if available else "none"
                self.logger.warning(
                    f"Failed to open OAK device (mxid={mxid}) on attempt {attempt}/{max_attempts}.\n Available devices: {available_str}. Error: {exc}",
                )
                if attempt < max_attempts:
                    time.sleep(delay_s)
        raise last_exc

    def _wait_for_device_info(self, mxid, delay_s):
        devices = dai.Device.getAllAvailableDevices()
        for device in devices:
            if device.getDeviceId() == mxid:
                return device
        time.sleep(delay_s)
        return dai.DeviceInfo(mxid)

    @staticmethod
    def _get_available_mxids():
        try:
            return [device.getMxId() for device in dai.Device.getAllAvailableDevices()]
        except Exception:
            return []

    def publish_frames(self):
        for key in self.devices.keys():
            rgb_frame = self.queues[key]["rgb"].tryGet()

            if rgb_frame is not None:
                self.gray = cv2.cvtColor(rgb_frame.getCvFrame(), cv2.COLOR_BGR2GRAY)

    def get_gray(self):
        img = cv2.imread('pirate.jpg')
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img


