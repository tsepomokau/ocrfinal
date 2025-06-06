# Simple OCR engine without PaddleOCR for testing
class OCREngine:
    def __init__(self, use_paddle=True):
        self.use_paddle = False  # Temporarily disable
        print("⚠️  Using simplified OCR engine (PaddleOCR disabled)")
    
    def process_sections(self, document_sections):
        """Simplified OCR processing"""
        return {
            "page_0": {
                "full": "Sample OCR text for testing",
                "table": "Sample table data"
            }
        }