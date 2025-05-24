import os
import cv2
import numpy as np
import pytesseract
from paddleocr import PaddleOCR
from PIL import Image
from typing import Dict, List, Any, Optional

class OCREngine:
    """Class for performing OCR on CP Tariff documents."""
    
    def __init__(self, use_paddle: bool = True, lang: str = "en"):
        """Initialize the OCR engine.
        
        Args:
            use_paddle: Whether to use PaddleOCR (True) or pytesseract (False)
            lang: Language code for OCR
        """
        self.use_paddle = use_paddle
        self.lang = lang
        
        if use_paddle:
            # Initialize PaddleOCR
            self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=False)
        
    def process_sections(self, document_sections: Dict[str, Dict[str, np.ndarray]]) -> Dict[str, Dict[str, str]]:
        """Process each section of the document with appropriate OCR settings.
        
        Args:
            document_sections: Dictionary of document sections by page
            
        Returns:
            Dictionary of OCR results by page and section
        """
        results = {}
        
        for page_key, sections in document_sections.items():
            page_results = {}
            
            # Process header with settings optimized for headers
            if "header" in sections:
                page_results["header"] = self._process_image(
                    sections["header"], 
                    is_table=False, 
                    config="--psm 6"
                )
            
            # Process table with settings optimized for tables
            if "table" in sections:
                page_results["table"] = self._process_image(
                    sections["table"], 
                    is_table=True, 
                    config="--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,*$-(){}[]"
                )
            
            # Process footer with settings optimized for multi-column text
            if "footer" in sections:
                page_results["footer"] = self._process_image(
                    sections["footer"], 
                    is_table=False, 
                    config="--psm 6"
                )
            
            # Also include full page OCR for context
            if "full" in sections:
                page_results["full"] = self._process_image(
                    sections["full"], 
                    is_table=False, 
                    config="--psm 6"
                )
            
            results[page_key] = page_results
        
        return results
    
    def _process_image(self, image: np.ndarray, is_table: bool = False, config: str = "") -> str:
        """Process a single image with OCR.
        
        Args:
            image: Image to process
            is_table: Whether the image contains a table
            config: Configuration string for tesseract
            
        Returns:
            Extracted text from the image
        """
        if self.use_paddle:
            return self._process_with_paddle(image, is_table)
        else:
            return self._process_with_tesseract(image, config)
    
    def _process_with_paddle(self, image: np.ndarray, is_table: bool) -> str:
        """Process image with PaddleOCR."""
        # Save image temporarily
        temp_path = "temp_ocr_image.jpg"
        cv2.imwrite(temp_path, image)
        
        try:
            # Process with PaddleOCR
            result = self.paddle_ocr.ocr(temp_path, cls=True)
            
            # Extract text
            text = ""
            for idx in range(len(result)):
                res = result[idx]
                for line in res:
                    text += line[1][0] + " "
            
            return text.strip()
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _process_with_tesseract(self, image: np.ndarray, config: str) -> str:
        """Process image with Tesseract OCR."""
        # Convert OpenCV image to PIL format
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # Perform OCR
        text = pytesseract.image_to_string(pil_image, config=config)
        
        return text.strip()