import os
import sys 
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import logging
from contextlib import asynccontextmanager

# Import enhanced OCR engine
from app.document_processor.ocr_engine_enhanced import EnhancedOCREngine as OCREngine

# Import database
from app.database.cp_tariff_database import CPTariffDatabase

# Configuration
TEMP_FOLDER = "./temp"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
DEBUG = True
VERSION = "2.1.0-Windows"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cp_tariff_api")

# Create directories
os.makedirs(TEMP_FOLDER, exist_ok=True)

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting Enhanced CP Tariff OCR API (Windows)")
    logger.info(f"Version: {VERSION}")
    
    yield
    
    logger.info("🛑 Shutting down CP Tariff OCR API")

# Initialize FastAPI app
app = FastAPI(
    title="CP Tariff OCR API - Enhanced (Windows)",
    description="Enhanced OCR system for CP Tariff documents optimized for Windows",
    version=VERSION,
    docs_url="/docs",
    lifespan=application_lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database manager
connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-KL51D0H\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes"
database_manager = CPTariffDatabase(connection_string)

@app.get("/")
async def get_api_root():
    """Root endpoint"""
    return {
        "message": "CP Tariff OCR API - Enhanced for Windows",
        "version": VERSION,
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def get_health_status():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "checks": {}
    }
    
    # Test OCR engine
    try:
        test_ocr = OCREngine()
        health_status["checks"]["ocr_engines"] = {
            "tesseract_available": test_ocr.use_tesseract,
            "paddle_available": test_ocr.use_paddle
        }
    except Exception as e:
        health_status["checks"]["ocr_engines"] = f"error: {str(e)}"
    
    return health_status

@app.post("/api/process-tariff")
async def process_tariff_document(
    file: UploadFile = File(...),
    extract_tables: bool = Query(True, description="Extract table data"),
    ocr_engine: str = Query("tesseract", description="OCR engine to use")
):
    """Process tariff document with enhanced OCR"""
    
    print("🚨 ENHANCED TARIFF PROCESSING (WINDOWS) CALLED!")
    temp_path = None
    start_time = time.time()
    
    try:
        # Get file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_FILE_SIZE:,} bytes")
        
        file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")
        
        print(f"📤 Processing: {file.filename} ({file_size:,} bytes)")
        
        # Save uploaded file
        temp_id = str(uuid.uuid4())
        from pathlib import Path
        
        temp_dir = Path(TEMP_FOLDER)
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / f"{temp_id}.{file_ext}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"💾 Saved to: {temp_path}")
        
        # Enhanced OCR Processing
        print("🔄 Starting enhanced OCR...")
        ocr_engine_instance = OCREngine(use_tesseract=True, use_paddle=False)
        
        extracted_data = ocr_engine_instance.process_sections([], str(temp_path))
        
        print("✅ Enhanced OCR completed")
        
        # Prepare final data
        processing_time = time.time() - start_time
        final_data = {
            "header": extracted_data.get("header", {}),
            "commodities": extracted_data.get("commodities", []),
            "rates": extracted_data.get("rates", []),
            "notes": extracted_data.get("notes", []),
            "origin_info": extracted_data.get("origin_info", ""),
            "destination_info": extracted_data.get("destination_info", ""),
            "currency": extracted_data.get("currency", "USD"),
            "pdf_name": file.filename,
            "raw_text": extracted_data.get("raw_text", ""),
            "processing_metadata": {
                "processing_time_seconds": int(processing_time),
                "file_size_bytes": file_size,
                "ocr_engine": "Enhanced OCR (Windows)",
                "tables_found": extracted_data.get("processing_metadata", {}).get("tables_found", 0),
                "text_blocks_found": extracted_data.get("processing_metadata", {}).get("text_blocks_found", 0)
            }
        }
        
        print(f"✅ Data prepared:")
        print(f"   Rates: {len(final_data['rates'])}")
        print(f"   Notes: {len(final_data['notes'])}")
        print(f"   Tables: {final_data['processing_metadata']['tables_found']}")
        
        # Save to database
        print("💾 Saving to database...")
        try:
            document_id = database_manager.save_document(final_data)
            if document_id:
                print(f"🎉 Saved with ID: {document_id}")
                database_success = True
                database_error = None
            else:
                database_success = False
                database_error = "Database save returned None"
        except Exception as db_error:
            print(f"❌ Database error: {db_error}")
            database_success = False
            database_error = str(db_error)
            document_id = None
        
        # Clean up
        if temp_path and temp_path.exists():
            temp_path.unlink()
            print("🧹 Cleaned up temp file")
        
        # Response
        response_data = {
            "status": "success" if database_success else "warning",
            "message": "Document processed successfully" if database_success else "Processed but database save failed",
            "document_id": document_id,
            "processing_time": round(processing_time, 2),
            "database_error": database_error,
            "extracted_data": {
                "header": final_data["header"],
                "commodities": final_data["commodities"],
                "rates": final_data["rates"],
                "notes": final_data["notes"],
                "origin_info": final_data["origin_info"],
                "destination_info": final_data["destination_info"],
                "currency": final_data["currency"]
            },
            "statistics": {
                "total_rates_found": len(final_data["rates"]),
                "total_notes_found": len(final_data["notes"]),
                "total_commodities_found": len(final_data["commodities"]),
                "tables_extracted": final_data["processing_metadata"]["tables_found"]
            },
            "processing_metadata": final_data["processing_metadata"]
        }
        
        print(f"📤 Returning: {response_data['status']}")
        return response_data
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Error processing document: {str(e)}",
                "document_id": None
            }
        )

@app.get("/debug/info")
async def get_debug_info():
    """Debug information"""
    try:
        test_ocr = OCREngine()
        ocr_info = {
            "tesseract_available": test_ocr.use_tesseract,
            "paddle_available": test_ocr.use_paddle
        }
    except Exception as e:
        ocr_info = {"error": str(e)}
    
    return {
        "version": VERSION,
        "platform": "Windows",
        "temp_folder": TEMP_FOLDER,
        "ocr_engines": ocr_info,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=DEBUG)