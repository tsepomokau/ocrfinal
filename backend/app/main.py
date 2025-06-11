import os
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import enhanced components
from app.document_processor.ocr_engine import OCREngine
from app.document_processor.ai_data_processor import AIDataProcessor
from app.database.cp_tariff_database import CPTariffDatabase

# Configuration
TEMP_FOLDER = "./temp"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
VERSION = "3.1.0"

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cp_tariff_api.log')
    ]
)
logger = logging.getLogger("cp_tariff_api")

# Create directories
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="CP Tariff OCR API",
    description="Enhanced OCR system for Canadian Pacific Railway tariff documents",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ProcessingStatus(BaseModel):
    status: str
    message: str
    document_id: Optional[int] = None
    processing_time_seconds: float
    extracted_data: Dict[str, Any]
    statistics: Dict[str, int]
    database_error: Optional[str] = None

class DatabaseTestResult(BaseModel):
    connected: bool
    tables_exist: bool
    can_write: bool
    error: Optional[str] = None
    connection_string_valid: bool

# Initialize components
def get_database_manager():
    """Dependency for database manager"""
    connection_string = os.getenv(
        "DB_CONNECTION_STRING",
        "DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-KL51D0H\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes"
    )
    return CPTariffDatabase(connection_string)

def get_ai_processor():
    """Dependency for AI processor"""
    return AIDataProcessor()

def get_ocr_engine():
    """Dependency for OCR engine"""
    return OCREngine(use_paddle=True, use_tesseract=True)

@app.on_event("startup")
async def startup_event():
    """Enhanced startup with database verification"""
    logger.info(f"Starting Enhanced CP Tariff OCR API v{VERSION}")
    
    # Test database connection at startup
    try:
        db_manager = get_database_manager()
        test_result = db_manager.test_database_connection()
        
        if test_result["connected"]:
            logger.info("Database connection verified at startup")
            if not test_result["tables_exist"]:
                logger.warning("Database tables missing - run database setup script")
        else:
            logger.error(f"Database connection failed at startup: {test_result.get('error')}")
    except Exception as e:
        logger.error(f"Database test failed at startup: {e}")

@app.get("/")
async def root():
    """Enhanced API root endpoint"""
    return {
        "service": "Enhanced CP Tariff OCR API",
        "version": VERSION,
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Multi-engine OCR (PaddleOCR + Tesseract)",
            "AI-enhanced data extraction",
            "Structured rate table processing",
            "Database persistence",
            "Enhanced error handling"
        ]
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "checks": {}
    }
    
    # Database health check
    try:
        db_manager = get_database_manager()
        db_test = db_manager.test_database_connection()
        health_status["checks"]["database"] = db_test
        
        if not db_test["connected"]:
            health_status["status"] = "unhealthy"
        elif not db_test["tables_exist"]:
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["checks"]["database"] = {"error": str(e)}
        health_status["status"] = "unhealthy"
    
    # OCR engines health check
    try:
        ocr_engine = get_ocr_engine()
        ocr_capabilities = ocr_engine.get_ocr_capabilities()
        health_status["checks"]["ocr_engines"] = ocr_capabilities
        
        if not any([ocr_capabilities.get("paddle_ocr"), ocr_capabilities.get("tesseract")]):
            health_status["status"] = "degraded" if health_status["status"] == "healthy" else health_status["status"]
            
    except Exception as e:
        health_status["checks"]["ocr_engines"] = {"error": str(e)}
        health_status["status"] = "degraded"
    
    # AI processor health check
    try:
        ai_processor = get_ai_processor()
        health_status["checks"]["ai_enhancement"] = {
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "ai_processor_available": ai_processor.ai_available
        }
    except Exception as e:
        health_status["checks"]["ai_enhancement"] = {"error": str(e)}
    
    return health_status

@app.get("/api/database/test")
async def test_database(db_manager: CPTariffDatabase = Depends(get_database_manager)):
    """Test database connection and setup"""
    try:
        test_result = db_manager.test_database_connection()
        return {
            "status": "success",
            "database_test": test_result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Database test error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database test failed: {str(e)}"
        )

@app.post("/api/process-tariff")
async def process_tariff_document(
    file: UploadFile = File(...),
    extract_tables: bool = Query(True, description="Extract table data"),
    save_to_database: bool = Query(True, description="Save results to database"),
    db_manager: CPTariffDatabase = Depends(get_database_manager),
    ai_processor: AIDataProcessor = Depends(get_ai_processor),
    ocr_engine: OCREngine = Depends(get_ocr_engine)
):
    """
    Enhanced tariff document processing with better error handling
    """
    temp_path = None
    start_time = time.time()
    processing_steps = []
    
    try:
        # Step 1: File validation
        processing_steps.append("file_validation")
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
        
        # Step 2: Save temporary file
        processing_steps.append("temp_file_creation")
        temp_id = str(uuid.uuid4())
        temp_path = Path(TEMP_FOLDER) / f"{temp_id}.{file_ext}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        # Step 3: OCR Processing
        processing_steps.append("ocr_extraction")
        logger.info("Starting OCR extraction")
        
        raw_ocr_data = ocr_engine.extract_text_from_pdf(str(temp_path))
        
        if not raw_ocr_data or len(raw_ocr_data.strip()) < 10:
            raise HTTPException(
                status_code=422,
                detail="Could not extract sufficient text from document"
            )
        
        # Step 4: AI-Enhanced Data Processing
        processing_steps.append("ai_data_processing")
        logger.info("Processing extracted data with AI enhancement")
        
        processed_data = ai_processor.process_tariff_data(
            raw_text=raw_ocr_data,
            filename=file.filename,
            file_size=file_size
        )
        
        # Add raw text to processed data for database storage
        processed_data['raw_text'] = raw_ocr_data[:4000]  # Truncate for database
        
        processing_time = time.time() - start_time
        logger.info(f"Processing completed in {processing_time:.2f}s")
        
        # Step 5: Database Save (if requested)
        document_id = None
        database_success = False
        database_error = None
        
        if save_to_database:
            processing_steps.append("database_save")
            try:
                logger.info("Saving to database")
                
                # Test database connection first
                db_test = db_manager.test_database_connection()
                if not db_test["connected"]:
                    raise Exception(f"Database not connected: {db_test.get('error')}")
                
                if not db_test["tables_exist"]:
                    raise Exception("Database tables do not exist - run setup script first")
                
                document_id = db_manager.save_document(processed_data)
                
                if document_id:
                    database_success = True
                    logger.info(f"Document saved with ID: {document_id}")
                else:
                    database_error = "Save operation returned no ID"
                    logger.warning("Database save failed: No ID returned")
                    
            except Exception as db_error:
                database_error = str(db_error)
                logger.error(f"Database save error: {db_error}")
        else:
            logger.info("Database save skipped (save_to_database=False)")
        
        # Step 6: Cleanup
        processing_steps.append("cleanup")
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        # Prepare enhanced response
        response_data = {
            "status": "success" if database_success or not save_to_database else "warning",
            "message": (
                "Document processed and saved successfully" if database_success 
                else "Document processed but not saved to database" if save_to_database
                else "Document processed successfully (database save disabled)"
            ),
            "document_id": document_id,
            "processing_time_seconds": round(processing_time, 2),
            "processing_steps": processing_steps,
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
                "tables_extracted": processed_data.get("metadata", {}).get("tables_found", 0),
                "text_length": len(raw_ocr_data),
                "extraction_method": processed_data.get("metadata", {}).get("extraction_method", "UNKNOWN")
            },
            "metadata": {
                "file_size_bytes": file_size,
                "ocr_engines_used": ocr_engine.get_ocr_capabilities(),
                "ai_enhancement_used": ai_processor.ai_available
            }
        }
        
        if database_error:
            response_data["database_error"] = database_error
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Processing error in step {processing_steps[-1] if processing_steps else 'unknown'}: {e}")
        
        # Clean up on error
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Processing failed: {str(e)}",
                "failed_step": processing_steps[-1] if processing_steps else "unknown",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/api/statistics")
async def get_statistics(db_manager: CPTariffDatabase = Depends(get_database_manager)):
    """Get enhanced database statistics"""
    try:
        stats = db_manager.get_database_statistics()
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
async def get_document(
    document_id: int, 
    db_manager: CPTariffDatabase = Depends(get_database_manager)
):
    """Retrieve processed document by ID"""
    try:
        document = db_manager.get_document_by_id(document_id)
        
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

@app.get("/api/debug/sample-data")
async def get_sample_data():
    """Return sample processed data for debugging"""
    return {
        "sample_header": {
            "item_number": "16024",
            "revision": 51,
            "cprs_number": "4445-B",
            "effective_date": "2024-08-01",
            "expiration_date": "2025-07-31"
        },
        "sample_commodity": {
            "name": "Wheat",
            "stcc_code": "01137XX",
            "description": "Wheat commodity for railway transport"
        },
        "sample_rate": {
            "origin": "Calgary AB",
            "destination": "Toronto ON",
            "rate_amount": "11947",
            "currency": "CAD",
            "equipment_type": "COVERED HOPPER"
        },
        "sample_note": {
            "type": "PROVISION",
            "text": "EQUIPMENT: COVERED HOPPER CARS. PRIVATE EQUIPMENT IS NOT SUBJECT TO MILEAGE ALLOWANCE."
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )