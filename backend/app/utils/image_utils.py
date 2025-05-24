import os
import cv2
import numpy as np
import uuid
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from typing import List, Tuple, Optional

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension."""
    filename, extension = os.path.splitext(original_filename)
    return f"{uuid.uuid4()}{extension}"

def convert_pdf_to_images(pdf_path: str, dpi: int = 300) -> List[str]:
    """Convert PDF to images and save them to temporary files."""
    output_paths = []
    
    # Create directory for extracted images
    output_dir = os.path.join(os.path.dirname(pdf_path), "extracted")
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=dpi)
    
    # Save each page as an image
    for i, image in enumerate(images):
        output_path = os.path.join(output_dir, f"page_{i+1}.jpg")
        image.save(output_path, "JPEG")
        output_paths.append(output_path)
    
    return output_paths

def detect_skew(image: np.ndarray) -> float:
    """Detect the skew angle of the document."""
    # Convert to grayscale if it's a color image
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply threshold to get a binary image
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Apply Hough Line Transform
    lines = cv2.HoughLinesP(thresh, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
    
    if lines is None or len(lines) == 0:
        return 0.0
    
    # Calculate angles and find most common angle
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:  # Avoid division by zero
            continue
        angle = np.arctan((y2 - y1) / (x2 - x1)) * 180 / np.pi
        angles.append(angle)
    
    if not angles:
        return 0.0
    
    # Calculate the median angle
    angle = np.median(angles)
    
    return angle

def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate the image by the given angle."""
    # Get image dimensions
    (h, w) = image.shape[:2]
    
    # Calculate the center of the image
    center = (w // 2, h // 2)
    
    # Get rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Perform the rotation
    rotated = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    
    return rotated

def detect_horizontal_lines(image: np.ndarray, min_line_length: int = 100) -> List[Tuple[int, int, int, int]]:
    """Detect horizontal lines in an image."""
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply threshold
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Create structure element for horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_line_length, 1))
    
    # Apply morphology operations
    horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Extract line coordinates (x1, y1, x2, y2)
    lines = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > min_line_length:
            lines.append((x, y, x + w, y))
    
    return lines

def detect_vertical_lines(image: np.ndarray, min_line_length: int = 100) -> List[Tuple[int, int, int, int]]:
    """Detect vertical lines in an image."""
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply threshold
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Create structure element for vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_line_length))
    
    # Apply morphology operations
    vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Extract line coordinates (x1, y1, x2, y2)
    lines = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h > min_line_length:
            lines.append((x, y, x, y + h))
    
    return lines

def identify_table_region(image: np.ndarray, horizontal_lines: List, vertical_lines: List) -> Optional[np.ndarray]:
    """Identify the region containing a table based on line intersections."""
    if not horizontal_lines or not vertical_lines:
        return None
    
    # Get image dimensions
    h, w = image.shape[:2]
    
    # Find the bounding box of the table
    min_x = w
    min_y = h
    max_x = 0
    max_y = 0
    
    for x1, y1, x2, y2 in horizontal_lines:
        min_x = min(min_x, x1)
        min_y = min(min_y, y1)
        max_x = max(max_x, x2)
        max_y = max(max_y, y2)
    
    for x1, y1, x2, y2 in vertical_lines:
        min_x = min(min_x, x1)
        min_y = min(min_y, y1)
        max_x = max(max_x, x2)
        max_y = max(max_y, y2)
    
    # Add some padding
    padding = 20
    min_x = max(0, min_x - padding)
    min_y = max(0, min_y - padding)
    max_x = min(w, max_x + padding)
    max_y = min(h, max_y + padding)
    
    # Extract the table region
    table_region = image[min_y:max_y, min_x:max_x]
    
    return table_region