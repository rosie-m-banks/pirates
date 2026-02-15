from extract_tiles import TileExtractor
from process_image import ImageProcessor
import requests
import logging
import cv2
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TilePublisher():
    def __init__(self) -> None: 
        self.backend_url = "http://localhost:3000/update-image"
        # Create a dedicated session for update-image requests to avoid connection interference
        # with update-data requests
        self.image_session = requests.Session()
        # Set connection pool size to ensure isolation from data requests
        adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1)
        self.image_session.mount('http://', adapter)
        

    def publish(self, frame):
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tiles = self.extract_tiles(frame_gray)
        tiles = self.remove_blank_tiles(frame_gray, tiles)
        bboxes = self.cluster_tiles(tiles)
        img = self.annotate_image(frame_gray, bboxes)
        
        # Convert image to base64 for JSON serialization
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        try:
            # Use dedicated session for update-image requests to avoid interference with update-data
            response = self.image_session.post(
                self.backend_url,
                json={"image": img_base64},
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Publisher: Posted image to backend successfully (Status: {response.status_code})")
            
        except Exception as e:
            logger.error(f"Publisher: Failed to post image to backend: {e}")
        
        # Return the annotated image so it can be displayed in the stream
        return img
            

    def extract_tiles(self, frame):
        return TileExtractor._detect_tiles(frame)

    def remove_blank_tiles(self, frame, tiles):
        """Remove blank tiles in parallel."""
        if not tiles:
            return []
        
        def check_tile(tile):
            """Check if a single tile is blank."""
            crop = ImageProcessor._crop_tile(frame, tile)
            return tile if not ImageProcessor._is_blank(crop) else None
        
        # Process tiles in parallel
        with ThreadPoolExecutor() as executor:
            results = executor.map(check_tile, tiles)
            # Filter out None values (blank tiles)
            tile_arr = [tile for tile in results if tile is not None]
        
        return tile_arr

    def cluster_tiles(self, tiles):
        """Cluster adjacent tiles into larger bounding boxes.
        
        Args:
            tiles: List of RotatedRect tuples ((cx, cy), (w, h), angle)
            
        Returns:
            List of RotatedRect tuples representing clustered bounding boxes
        """
        if not tiles:
            return []
        
        # Convert rotated rects to axis-aligned bounding boxes for distance checking
        def get_bbox_points(rect):
            """Get the 4 corner points of a rotated rectangle."""
            box = cv2.boxPoints(rect)
            return box
        
        def are_adjacent(rect1, rect2, threshold_factor=0.35):
            """Check if two rectangles are adjacent/close to each other.
            
            Args:
                rect1, rect2: RotatedRect tuples
                threshold_factor: Multiplier for determining adjacency threshold (much tighter now)
                
            Returns:
                True if rectangles are adjacent
            """
            # Get bounding boxes
            box1 = get_bbox_points(rect1)
            box2 = get_bbox_points(rect2)
            
            # Calculate average width/height for threshold
            w1, h1 = rect1[1]
            w2, h2 = rect2[1]
            avg_size = (w1 + h1 + w2 + h2) / 4
            
            # Check if any point of box1 is close to any point of box2
            # or if the bounding boxes overlap/are close
            min_dist = float('inf')
            for p1 in box1:
                for p2 in box2:
                    dist = np.linalg.norm(p1 - p2)
                    min_dist = min(min_dist, dist)
            
            # Also check center-to-center distance
            cx1, cy1 = rect1[0]
            cx2, cy2 = rect2[0]
            center_dist = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
            
            # Tiles are adjacent if they're within threshold_factor * avg_size distance
            # Using much tighter threshold (0.35 instead of 1.5)
            threshold = avg_size * threshold_factor
            return min_dist < threshold or center_dist < threshold * 1.2
        
        # Simple clustering: group adjacent tiles
        clusters = []
        used = [False] * len(tiles)
        
        for i, tile in enumerate(tiles):
            if used[i]:
                continue
            
            # Start a new cluster with this tile
            cluster = [tile]
            used[i] = True
            
            # Find all tiles adjacent to any tile in this cluster
            changed = True
            while changed:
                changed = False
                for j, other_tile in enumerate(tiles):
                    if used[j]:
                        continue
                    
                    # Check if this tile is adjacent to any tile in the cluster
                    for cluster_tile in cluster:
                        if are_adjacent(cluster_tile, other_tile):
                            cluster.append(other_tile)
                            used[j] = True
                            changed = True
                            break
            
            clusters.append(cluster)
        
        # For each cluster, compute the bounding box that contains all tiles
        clustered_bboxes = []
        for cluster in clusters:
            if len(cluster) == 1:
                # Single tile, keep as is
                clustered_bboxes.append(cluster[0])
            else:
                # Multiple tiles: compute bounding box containing all
                all_points = []
                for rect in cluster:
                    box_points = get_bbox_points(rect)
                    all_points.extend(box_points)
                
                all_points = np.array(all_points, dtype=np.float32)
                
                # Compute minimum area rectangle containing all points
                rect = cv2.minAreaRect(all_points)
                clustered_bboxes.append(rect)
        
        return clustered_bboxes

    def annotate_image(self, frame, bboxes):
        return TileExtractor._draw_boxes(frame, bboxes)
    

def main():

    ## Testing harness
    pubber = TilePublisher()
    frame = cv2.imread("pirate.jpg")
    pubber.publish(frame)

if __name__ == "__main__":
    main()