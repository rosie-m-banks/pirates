from oak import Oak
import cv2
import numpy as np
import time

class TakePhoto:
    def __init__(self, output_path):
        self.oak = Oak("camera.yaml")
        self.output_path = output_path

    def take_photo(self):
        frame = self.oak.get_gray()
        cv2.imwrite(self.output_path, frame)
        return self.output_path

def main():
    take_photo = TakePhoto("output_photo6.jpg")
    time.sleep(10)
    print("Taking photo...")
    take_photo.take_photo()
    print("Photo taken and saved to", take_photo.output_path)

if __name__ == "__main__":
    main()