import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional

from app.utils.image_utils import (
    detect_skew, 
    rotate_image, 
    detect_horizontal_lines, 
    detect_vertical_lines,
    identify_table_region,
    convert_pdf_to_images
)

class DocumentPreprocessor:
    """Class for preprocessing CP Tariff documents for OCR."""
    
    def __init__(self, input_path: str):
        """Initialize with the document path."""
        self.input_path = input_path
        self.is_pdf = input_path.lower().endswith('.pdf')
        self.image_paths = []
        self.preprocessed_images = []
        self.document_sections = {}
    
    def process(self) -> Dict[str, Dict[str, np.ndarray]]:
        """Process the document and return sections for each page."""
        if self.is_pdf:
            self.image_paths = convert_pdf_to_images(self.input_path)
        else:
            self.image_paths = [self.input_path]
        
        result = {}
        
        for i, image_path in enumerate(self.image_paths):
            # Process each page/image
            page_num = i + 1
            result[f"page_{page_num}"] = self._process_single_image(image_path)
        
        return result
    
    def _process_single_image(self, image_path: str) -> Dict[str, np.ndarray]:
        """Process a single image and return its detected sections."""
        # Read image
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding
        threshold = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Correct skew if needed
        angle = detect_skew(threshold)
        if abs(angle) > 0.5:
            threshold = rotate_image(threshold, angle)
            img = rotate_image(img, angle)
        
        # Store preprocessed image
        self.preprocessed_images.append(threshold)
        
        # Detect lines for table structure
        horizontal_lines = detect_horizontal_lines(threshold)
        vertical_lines = detect_vertical_lines(threshold)
        
        # Divide the document into sections
        h, w = img.shape[:2]
        
        # Header section (top 20% of document)
        header_region = img[0:int(h * 0.2), :]
        
        # Try to detect table region
        table_region = identify_table_region(img.copy(), horizontal_lines, vertical_lines)
        
        # If table_region is None, use middle 60% of document as default
        if table_region is None:
            table_region = img[int(h * 0.2):int(h * 0.8), :]
        
        # Footer section (bottom 20% of document)
        footer_region = img[int(h * 0.8):, :]
        
        # Store the detected sections
        sections = {
            "header": header_region,
            "table": table_region,
            "footer": footer_region,
            "full": img
        }
        
        return sections
    
    def cleanup(self):
        """Clean up temporary files."""
        # Remove extracted PDF images if any
        for image_path in self.image_paths:
            if os.path.exists(image_path) and "extracted" in image_path:
                try:
                    os.remove(image_path)
                except:
                    pass
        
        # Try to remove the extracted directory if it exists
        if self.is_pdf:
            extracted_dir = os.path.join(os.path.dirname(self.input_path), "extracted")
            if os.path.exists(extracted_dir):
                try:
                    os.rmdir(extracted_dir)
                except:
                    pass