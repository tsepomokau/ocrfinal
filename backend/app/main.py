"""
CP Tariff OCR API - Production Version
Clean production-ready FastAPI application for processing CP Rail tariff documents.
"""

import os
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import production components
from app.document_processor.ocr_engine import OCREngine
from app.document_processor.ai_data_processor import AIDataProcessor
from app.database.cp_tariff_database import CPTariffDatabase

# Production Configuration
TEMP_FOLDER = "./temp"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
VERSION = "3.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cp_tariff_api")

# Create directories
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="CP Tariff OCR API",
    description="Production OCR system for Canadian Pacific Railway tariff documents",
    version=VERSION,
    docs_url="/docs"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize production components
connection_string = os.getenv(
    "DB_CONNECTION_STRING",
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes"
)
database_manager = CPTariffDatabase(connection_string)
ai_processor = AIDataProcessor()

@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info(f"Starting CP Tariff OCR API v{VERSION}")
    logger.info("Production mode: Sample data disabled")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Shutting down CP Tariff OCR API")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "CP Tariff OCR API",
        "version": VERSION,
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "checks": {}
    }
    
    # Test database connection
    try:
        conn = database_manager.get_database_connection()
        if conn:
            conn.close()
            health_status["checks"]["database"] = "connected"
        else:
            health_status["checks"]["database"] = "disconnected"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Test OCR engines
    try:
        ocr_engine = OCREngine()
        ocr_capabilities = ocr_engine.get_ocr_capabilities()
        health_status["checks"]["ocr_engines"] = {
            "paddle_ocr": ocr_capabilities.get("paddle_ocr", False),
            "tesseract": ocr_capabilities.get("tesseract", False),
            "pdf_text_layer": ocr_capabilities.get("pdf_text_layer", True)
        }
        
        if not any([ocr_capabilities.get("paddle_ocr"), ocr_capabilities.get("tesseract")]):
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["checks"]["ocr_engines"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Test AI processor
    try:
        health_status["checks"]["ai_enhancement"] = {
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "ai_processor_available": ai_processor.ai_available
        }
    except Exception as e:
        health_status["checks"]["ai_enhancement"] = f"error: {str(e)}"
    
    return health_status

@app.post("/api/process-tariff")
async def process_tariff_document(
    file: UploadFile = File(...),
    extract_tables: bool = Query(True, description="Extract table data")
):
    """
    Process CP tariff document and extract structured data
    
    Args:
        file: PDF or image file containing tariff document
        extract_tables: Whether to extract table structures
    
    Returns:
        Structured tariff data including rates, commodities, and notes
    """
    temp_path = None
    start_time = time.time()
    
    try:
        # Validate file
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE:,} bytes"
            )
        
        file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        logger.info(f"Processing document: {file.filename} ({file_size:,} bytes)")
        
        # Save temporary file
        temp_id = str(uuid.uuid4())
        temp_path = Path(TEMP_FOLDER) / f"{temp_id}.{file_ext}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        # OCR Processing
        logger.info("Starting OCR extraction")
        ocr_engine = OCREngine(use_paddle=True, use_tesseract=True)
        raw_ocr_data = ocr_engine.extract_text_from_pdf(str(temp_path))
        
        # AI-Enhanced Data Processing
        logger.info("Processing extracted data with AI enhancement")
        processed_data = ai_processor.process_tariff_data(
            raw_text=raw_ocr_data,
            filename=file.filename,
            file_size=file_size
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Processing completed in {processing_time:.2f}s")
        
        # Database Save
        document_id = None
        database_success = False
        database_error = None
        
        try:
            logger.info("Saving to database")
            document_id = database_manager.save_document(processed_data)
            
            if document_id:
                database_success = True
                logger.info(f"Document saved with ID: {document_id}")
            else:
                database_error = "Save operation returned no ID"
                logger.warning("Database save failed: No ID returned")
                
        except Exception as db_error:
            database_error = str(db_error)
            logger.error(f"Database save error: {db_error}")
        
        # Clean up
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        # Prepare response
        response = {
            "status": "success" if database_success else "warning",
            "message": "Document processed successfully" if database_success else "Processed but not saved to database",
            "document_id": document_id,
            "processing_time_seconds": round(processing_time, 2),
            "extracted_data": {
                "header": processed_data.get("header", {}),
                "commodities": processed_data.get("commodities", []),
                "rates": processed_data.get("rates", []),
                "notes": processed_data.get("notes", []),
                "origin_info": processed_data.get("origin_info", ""),
                "destination_info": processed_data.get("destination_info", ""),
                "currency": processed_data.get("currency", "USD")
            },
            "statistics": {
                "rates_found": len(processed_data.get("rates", [])),
                "notes_found": len(processed_data.get("notes", [])),
                "commodities_found": len(processed_data.get("commodities", [])),
                "tables_extracted": processed_data.get("metadata", {}).get("tables_found", 0)
            }
        }
        
        if database_error:
            response["database_error"] = database_error
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Processing error: {e}")
        
        # Clean up on error
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Processing failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/api/statistics")
async def get_statistics():
    """Get database statistics"""
    try:
        stats = database_manager.get_database_statistics()
        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )

@app.get("/api/document/{document_id}")
async def get_document(document_id: int):
    """Retrieve processed document by ID"""
    try:
        document = database_manager.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": "success",
            "document": document,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Production mode
        log_level="info"
    )