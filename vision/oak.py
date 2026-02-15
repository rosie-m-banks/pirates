#!/usr/bin/env python3
import depthai as dai
import os
import cv2
import time
import atexit
from generic_camera import GenericCamera
from threading import Timer, Lock

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
    
    # Set queue size to 1 to prevent frame accumulation and ensure we always get the latest frame
    # This helps prevent getting stale/cropped frames when captures happen at different times
    video_queue = cam_rgb.video.createOutputQueue(maxSize=1, blocking=False)
    return video_queue

class Oak(GenericCamera):
    def __init__(self, path):
        super().__init__("oak_node", path)

        self.path = path
        self._camera_info = self.get_cam_data(self.load_cameras_yaml(), "oak")
        self.rgb = None
        self._device_objects = {}  # Store device objects to prevent garbage collection

        for key, cam_cfg in self._camera_info.items():
            cam_cfg = cam_cfg.get("ros__parameters")

            self.logger.info(
                f"Starting OAK camera: {key} (mxid={cam_cfg['camera']['i_mx_id']})"
            )

            device = self._open_device_with_retry(cam_cfg["camera"]["i_mx_id"])
            pipeline = dai.Pipeline(device)

            rgb = config_rgb_image(pipeline, key, cam_cfg)
            
            self.devices[key] = pipeline
            self._device_objects[key] = device  # Store device to keep it alive
            self.queues[key] = {
                "rgb": rgb
            }

            pipeline.start()

        # self.timer = Timer(1.0 / 30.0, self.publish_frames)
        # self.timer.start()
        
        # Register cleanup to happen at Python exit
        atexit.register(self._cleanup_on_exit)

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
                print("we have a frame")
                frame = rgb_frame.getCvFrame()
                
    def get_rgb(self):
        self.get_frame()
        return self.rgb

    def get_frame(self):
        """Get the latest grayscale frame from the camera.
        
        Drains old frames from the queue to ensure we always get the most recent frame.
        This prevents getting stale/cropped frames when captures happen at different times.
        """
        # Drain all old frames from the queue to get the latest one
        latest_frame = None
        for key in self.devices.keys():
            queue = self.queues[key]["rgb"]
            # Keep getting frames until queue is empty (drain old frames)
            while True:
                rgb_frame = queue.tryGet()
                if rgb_frame is None:
                    break
                latest_frame = rgb_frame
        
        # Process the latest frame if we got one
        if latest_frame is not None:
            frame = latest_frame.getCvFrame()
            self.rgb = frame
            
    def get_gray(self):
        self.get_frame()
        return cv2.cvtColor(self.rgb, cv2.COLOR_BGR2GRAY)

    def _cleanup_on_exit(self):
        """Cleanup method registered with atexit - runs at Python shutdown."""
        # Just clear references - let depthai handle device cleanup
        # Explicit close() causes deadlocks, so we just let Python GC handle it
        self.queues.clear()
        self._device_objects.clear()
        self.devices.clear()

    def close(self):
        """Properly close all devices and cleanup resources."""
        # Note: Explicit close() can cause deadlocks with depthai
        # This method is kept for API compatibility but may not work reliably
        self._cleanup_on_exit()

    def __del__(self):
        """Cleanup on object destruction."""
        # Don't do anything - let atexit handle cleanup
        pass