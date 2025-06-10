"""
Production OCR Engine for CP Tariff Documents
Supports both PaddleOCR and Tesseract for maximum accuracy.
"""

import os
import re
import fitz  # PyMuPDF
import logging
import io
from typing import Dict, List, Any, Optional
from pathlib import Path

# Tesseract OCR
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    # Configure Tesseract path for Windows if needed
    if os.name == 'nt':
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    TESSERACT_AVAILABLE = False

# PaddleOCR
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCREngine:
    """Production OCR engine with PaddleOCR and Tesseract support"""
    
    def __init__(self, use_paddle: bool = True, use_tesseract: bool = True):
        """
        Initialize OCR engine with multiple backends
        
        Args:
            use_paddle: Enable PaddleOCR (recommended for complex layouts)
            use_tesseract: Enable Tesseract OCR (good for simple text)
        """
        self.use_paddle = use_paddle and PADDLE_AVAILABLE
        self.use_tesseract = use_tesseract and TESSERACT_AVAILABLE
        
        # Initialize PaddleOCR if available
        if self.use_paddle:
            try:
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='en',
                    use_gpu=False,  # Set to True if GPU available
                    show_log=False
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.warning(f"PaddleOCR initialization failed: {e}")
                self.use_paddle = False
        
        if not (self.use_paddle or self.use_tesseract):
            logger.error("No OCR engines available")
        else:
            logger.info(f"OCR engine initialized - PaddleOCR: {self.use_paddle}, Tesseract: {self.use_tesseract}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using multiple methods
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        logger.info(f"Extracting text from: {pdf_path}")
        
        # Method 1: Try direct text extraction from PDF
        pdf_text = self._extract_pdf_text_layer(pdf_path)
        
        if pdf_text and len(pdf_text.strip()) > 100:
            logger.info(f"Extracted {len(pdf_text)} characters from PDF text layer")
            return pdf_text
        
        # Method 2: OCR if no text layer or insufficient text
        logger.info("PDF has minimal text layer, attempting OCR")
        ocr_text = self._perform_ocr(pdf_path)
        
        if ocr_text:
            logger.info(f"Extracted {len(ocr_text)} characters via OCR")
            return ocr_text
        
        # Fallback
        logger.warning("Limited text could be extracted from PDF")
        return pdf_text or ""
    
    def _extract_pdf_text_layer(self, pdf_path: str) -> str:
        """Extract text from PDF text layer using PyMuPDF"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                if text.strip():
                    full_text += f"\n--- Page {page_num + 1} ---\n{text}"
            
            doc.close()
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    def _perform_ocr(self, pdf_path: str) -> str:
        """Perform OCR on PDF pages using available engines"""
        
        # Try PaddleOCR first (generally more accurate for complex layouts)
        if self.use_paddle:
            paddle_text = self._paddle_ocr_extract(pdf_path)
            if paddle_text and len(paddle_text.strip()) > 50:
                return paddle_text
        
        # Fallback to Tesseract
        if self.use_tesseract:
            tesseract_text = self._tesseract_ocr_extract(pdf_path)
            if tesseract_text:
                return tesseract_text
        
        logger.error("All OCR methods failed")
        return ""
    
    def _paddle_ocr_extract(self, pdf_path: str) -> str:
        """Extract text using PaddleOCR"""
        try:
            logger.info("Starting PaddleOCR extraction")
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Save image temporarily for PaddleOCR
                temp_img_path = f"temp_page_{page_num}.png"
                with open(temp_img_path, "wb") as f:
                    f.write(img_data)
                
                try:
                    # Run PaddleOCR
                    result = self.paddle_ocr.ocr(temp_img_path, cls=True)
                    
                    # Extract text from results
                    page_text = ""
                    if result and result[0]:
                        for line in result[0]:
                            if len(line) > 1 and line[1][1] > 0.5:  # Confidence threshold
                                page_text += line[1][0] + " "
                    
                    if page_text.strip():
                        full_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                
                finally:
                    # Clean up temp image
                    if os.path.exists(temp_img_path):
                        os.unlink(temp_img_path)
            
            doc.close()
            logger.info(f"PaddleOCR extracted {len(full_text)} characters")
            return full_text
            
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed: {e}")
            return ""
    
    def _tesseract_ocr_extract(self, pdf_path: str) -> str:
        """Extract text using Tesseract OCR"""
        if not TESSERACT_AVAILABLE:
            logger.error("Tesseract not available for OCR")
            return ""
        
        try:
            logger.info("Starting Tesseract OCR extraction")
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # OCR the image
                image = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(
                    image,
                    lang='eng',
                    config='--psm 6'  # Single uniform block
                )
                
                if page_text.strip():
                    full_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            doc.close()
            logger.info(f"Tesseract extracted {len(full_text)} characters")
            return full_text
            
        except Exception as e:
            logger.error(f"Tesseract OCR extraction failed: {e}")
            return ""
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract table structures from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of extracted tables
        """
        tables = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Find tables on the page
                page_tables = page.find_tables()
                
                for table_idx, table in enumerate(page_tables):
                    try:
                        # Extract table data
                        table_data = table.extract()
                        
                        if table_data and len(table_data) > 1:  # At least header + 1 row
                            tables.append({
                                "page": page_num + 1,
                                "table_index": table_idx,
                                "headers": table_data[0] if table_data else [],
                                "rows": table_data[1:] if len(table_data) > 1 else [],
                                "row_count": len(table_data) - 1,
                                "column_count": len(table_data[0]) if table_data else 0
                            })
                            
                    except Exception as e:
                        logger.warning(f"Error extracting table {table_idx} from page {page_num + 1}: {e}")
                        continue
            
            doc.close()
            logger.info(f"Extracted {len(tables)} tables from PDF")
            
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
        
        return tables
    
    def get_ocr_capabilities(self) -> Dict[str, bool]:
        """Get available OCR capabilities"""
        return {
            "paddle_ocr": self.use_paddle,
            "tesseract": self.use_tesseract,
            "pdf_text_layer": True,
            "table_extraction": True
        }
    
    def get_document_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract document metadata
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Document metadata
        """
        metadata = {
            "filename": Path(pdf_path).name,
            "file_size": 0,
            "page_count": 0,
            "has_text_layer": False,
            "creation_date": None,
            "modification_date": None,
            "ocr_engines_used": []
        }
        
        try:
            # File info
            file_path = Path(pdf_path)
            metadata["file_size"] = file_path.stat().st_size
            
            # PDF info
            doc = fitz.open(pdf_path)
            metadata["page_count"] = len(doc)
            
            # Check if document has text layer
            for page_num in range(min(3, len(doc))):  # Check first 3 pages
                page = doc.load_page(page_num)
                text = page.get_text()
                if text and len(text.strip()) > 50:
                    metadata["has_text_layer"] = True
                    break
            
            # Document properties
            doc_metadata = doc.metadata
            if doc_metadata:
                metadata["creation_date"] = doc_metadata.get("creationDate")
                metadata["modification_date"] = doc_metadata.get("modDate")
                metadata["title"] = doc_metadata.get("title", "")
                metadata["author"] = doc_metadata.get("author", "")
            
            # OCR capabilities
            if self.use_paddle:
                metadata["ocr_engines_used"].append("PaddleOCR")
            if self.use_tesseract:
                metadata["ocr_engines_used"].append("Tesseract")
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
        
        return metadata