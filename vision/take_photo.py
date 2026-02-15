from oak import Oak
import cv2
import numpy as np
import time
import sys

class TakePhoto:
    def __init__(self, output_path):
        self.oak = Oak("camera.yaml")
        self.output_path = output_path

    def take_photo(self):
        frame = self.oak.get_gray()
        cv2.imwrite(self.output_path, frame)
        return self.output_path

def main():
    # Parse command-line argument for output path
    # Usage: python3 take_photo.py [output_path]
    output_path = sys.argv[1] if len(sys.argv) > 1 else "output_photo.jpg"
    
    take_photo = TakePhoto(output_path)
    time.sleep(10)
    print("Taking photo...")
    take_photo.take_photo()
    print("Photo taken and saved to", take_photo.output_path)

if __name__ == "__main__":
    main()