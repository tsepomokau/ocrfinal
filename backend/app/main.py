"""
CP Tariff OCR API - Main FastAPI Application
File: backend/app/main.py
"""
import os
import sys 
import uuid
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import shutil
import json
import logging
from contextlib import asynccontextmanager

# Import application modules - FIXED: Added conditional imports
try:
    from app.document_processor.preprocessor import DocumentPreprocessor
    PREPROCESSOR_AVAILABLE = True
except ImportError:
    PREPROCESSOR_AVAILABLE = False
    print("⚠️  DocumentPreprocessor not available, using direct OCR processing")

from app.document_processor.ocr_engine_debug import OCREngine
from app.document_processor.table_extractor import TableExtractor


try:
    from app.document_processor.enhanced_field_normalizer import EnhancedFieldNormalizer
    AI_NORMALIZER_AVAILABLE = True
except ImportError:
    AI_NORMALIZER_AVAILABLE = False
    print("⚠️  Enhanced field normalizer not available")

from app.database.cp_tariff_database import CPTariffDatabase


try:
    from config import (
        TEMP_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, 
        CORS_ALLOW_ORIGINS, DEBUG, VERSION,
        ENABLE_API_KEY_AUTH, VALID_API_KEYS, API_KEY_HEADER_NAME,
        ENABLE_PERFORMANCE_MONITORING, SLOW_REQUEST_THRESHOLD_SECONDS
    )
except ImportError:
    # Fallback configuration if config.py has issues
    TEMP_FOLDER = "./temp"
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    CORS_ALLOW_ORIGINS = ["*"]
    DEBUG = True
    VERSION = "2.0.1"
    ENABLE_API_KEY_AUTH = False
    VALID_API_KEYS = []
    API_KEY_HEADER_NAME = "X-API-Key"
    ENABLE_PERFORMANCE_MONITORING = True
    SLOW_REQUEST_THRESHOLD_SECONDS = 5.0
    print("⚠️  Using fallback configuration")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cp_tariff_api")

# Create directories
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Background task management
background_tasks_status = {}

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    # Startup
    logger.info("🚀 Starting CP Tariff OCR API")
    logger.info(f"Version: {VERSION}")
    logger.info(f"Debug mode: {DEBUG}")
    
    # Initialize database connection
    try:
        db_manager = CPTariffDatabase()
        if db_manager.test_database_connection():
            logger.info("✅ Database connection established")
        else:
            logger.error("❌ Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Cleanup old temporary files on startup
    cleanup_temporary_files()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down CP Tariff OCR API")
    cleanup_temporary_files()

# Initialize FastAPI app
app = FastAPI(
    title="CP Tariff OCR API",
    description="AI-powered OCR system for Canadian Pacific Railway tariff documents with database integration",
    version=VERSION,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    lifespan=application_lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance monitoring middleware
if ENABLE_PERFORMANCE_MONITORING:
    @app.middleware("http")
    async def performance_monitoring_middleware(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log slow requests
        if process_time > SLOW_REQUEST_THRESHOLD_SECONDS:
            logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
        
        # Add performance header
        response.headers["X-Process-Time"] = str(process_time)
        return response

# Security dependencies
security = HTTPBearer(auto_error=False) if ENABLE_API_KEY_AUTH else None

async def verify_api_key_authentication(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key if authentication is enabled"""
    if not ENABLE_API_KEY_AUTH:
        return True
    
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")
    
    if credentials.credentials not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True

# Initialize database manager
database_manager = CPTariffDatabase()

def cleanup_temporary_files():
    """Clean up old temporary files"""
    try:
        import glob
        import time
        
        # Remove files older than 24 hours
        cutoff_time = time.time() - (24 * 60 * 60)
        
        for file_path in glob.glob(os.path.join(TEMP_FOLDER, "*")):
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                try:
                    os.remove(file_path)
                    logger.debug(f"Cleaned up old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not remove file {file_path}: {e}")
                    
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")

# ========================================
# API Endpoints
# ========================================

@app.get("/")
async def get_api_root():
    """Root endpoint with API information"""
    return {
        "message": "CP Tariff OCR API with Database Integration",
        "version": VERSION,
        "description": "AI-powered OCR system for Canadian Pacific Railway tariff documents",
        "documentation": "/docs" if DEBUG else "Documentation disabled in production",
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
    
    # Database health check
    try:
        if database_manager.test_database_connection():
            health_status["checks"]["database"] = "healthy"
        else:
            health_status["checks"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # File system health check
    try:
        test_file = os.path.join(TEMP_FOLDER, "health_check.txt")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        health_status["checks"]["filesystem"] = "healthy"
    except Exception as e:
        health_status["checks"]["filesystem"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/api/test")
async def get_test_endpoint():
    """Test endpoint for API connectivity"""
    print("🧪 Test endpoint called!")
    return {"message": "Test endpoint working"}

# FIXED: Single process_tariff endpoint (removed duplicate)
@app.post("/api/process-tariff")
async def process_tariff_document_upload(
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key_authentication)
):
    """Process uploaded tariff document with OCR and AI enhancement"""
    
    print("🚨 TARIFF PROCESSING ENDPOINT CALLED!")
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
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        print(f"📤 Processing document: {file.filename} ({file_size:,} bytes)")
        
        # Save uploaded file
        temp_id = str(uuid.uuid4())
        from pathlib import Path
        
        temp_dir = Path(TEMP_FOLDER)
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / f"{temp_id}.{file_ext}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"💾 Saved to temp file: {temp_path}")
        
        # Step 1: Preprocess document (if available)
        document_sections = []
        if PREPROCESSOR_AVAILABLE:
            try:
                preprocessor = DocumentPreprocessor(str(temp_path))
                document_sections = preprocessor.process()
                print("✅ Document preprocessing completed")
            except Exception as e:
                print(f"⚠️  Preprocessing failed, using direct OCR: {e}")
                document_sections = []
        else:
            print("⚠️  Using direct OCR processing (no preprocessor)")
        
        # Step 2: OCR Processing
        print(f"🔄 Creating OCR engine...")
        ocr_engine = OCREngine()
        
        print(f"🔄 Starting OCR processing with PDF path: '{temp_path}'")
        extracted_data = ocr_engine.process_sections(document_sections, str(temp_path))
        
        print("✅ OCR processing completed")
        print(f"📊 Extracted data type: {type(extracted_data)}")
        
        if not isinstance(extracted_data, dict):
            raise ValueError(f"OCR engine returned {type(extracted_data)}, expected dict")
        
        print(f"📊 OCR data keys: {list(extracted_data.keys())}")
        
        # Step 3: AI Enhancement (if available)
        if AI_NORMALIZER_AVAILABLE and extracted_data.get('raw_text'):
            try:
                print("🤖 Starting AI enhancement...")
                field_normalizer = EnhancedFieldNormalizer(extracted_data['raw_text'], file.filename)
                ai_enhanced_data = field_normalizer.normalize_tariff_data()
                
                # Merge AI results with OCR results
                for key in ['header', 'commodities', 'rates', 'notes']:
                    if key in ai_enhanced_data and ai_enhanced_data[key]:
                        extracted_data[key] = ai_enhanced_data[key]
                        print(f"✅ AI enhanced {key}")
                        
            except Exception as e:
                print(f"⚠️  AI enhancement failed, using OCR only: {e}")
        
        # Prepare final data structure
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
                "ocr_engine": "Debug OCR",
                "ai_processing_used": AI_NORMALIZER_AVAILABLE,
                "pages_processed": 1,
                "preprocessor_used": PREPROCESSOR_AVAILABLE
            }
        }
        
        print(f"✅ Final data prepared:")
        print(f"   Commodities: {len(final_data['commodities'])}")
        print(f"   Rates: {len(final_data['rates'])}")
        print(f"   Notes: {len(final_data['notes'])}")
        print(f"   Header: {final_data['header']}")
        
        # Step 4: Save to database
        print("💾 Starting database save...")
        
        try:
            document_id = database_manager.save_tariff_document_complete(final_data, str(temp_path))
            
            if document_id:
                print(f"🎉 SUCCESS: Document saved with ID: {document_id}")
                database_success = True
                database_error = None
            else:
                print("❌ WARNING: Database save returned None")
                database_success = False
                database_error = "Database save returned None"
                
        except Exception as db_error:
            print(f"❌ Database save failed: {db_error}")
            database_success = False
            database_error = str(db_error)
            document_id = None
        
        # Clean up temp file
        if temp_path and temp_path.exists():
            temp_path.unlink()
            print("🧹 Temp file cleaned up")
        
        # Create response
        response_data = {
            "status": "success" if database_success else "warning",
            "message": "Tariff document processed successfully" if database_success else "Document processed but database save failed",
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
                "asterisk_notes_found": len([n for n in final_data["notes"] if isinstance(n, dict) and n.get("type") == "ASTERISK"])
            },
            "processing_metadata": final_data["processing_metadata"]
        }
        
        print(f"📤 Returning response with status: {response_data['status']}")
        return response_data
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up temp file if it exists
        if temp_path and temp_path.exists():
            temp_path.unlink()
            print("🧹 Temp file cleaned up after error")
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error", 
                "message": f"Error processing document: {str(e)}",
                "document_id": None,
                "error_details": str(e)
            }
        )

@app.get("/api/statistics")
async def get_database_statistics(_: bool = Depends(verify_api_key_authentication)):
    """Get comprehensive database statistics"""
    try:
        stats = database_manager.get_database_statistics()
        return {
            "statistics": stats,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

@app.get("/api/search-tariffs")
async def search_tariff_documents(
    origin: Optional[str] = Query(None, description="Origin location"),
    destination: Optional[str] = Query(None, description="Destination location"),
    item_number: Optional[str] = Query(None, description="Item number"),
    _: bool = Depends(verify_api_key_authentication)
):
    """Search tariff documents by criteria"""
    try:
        criteria = {}
        if origin:
            criteria['origin'] = origin
        if destination:
            criteria['destination'] = destination
        if item_number:
            criteria['item_number'] = item_number
        
        results = database_manager.search_tariff_documents(**criteria)
        return {
            "results": results,
            "count": len(results),
            "criteria": criteria,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error searching tariffs: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching tariffs: {str(e)}")

# Debug endpoints (only in debug mode)
if DEBUG:
    @app.get("/debug/info")
    async def get_debug_information():
        """Debug information endpoint"""
        return {
            "version": VERSION,
            "debug_mode": DEBUG,
            "temp_folder": TEMP_FOLDER,
            "max_file_size": MAX_FILE_SIZE,
            "allowed_extensions": list(ALLOWED_EXTENSIONS),
            "active_background_tasks": len(background_tasks_status),
            "temp_files": len([f for f in os.listdir(TEMP_FOLDER) if os.path.isfile(os.path.join(TEMP_FOLDER, f))]),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",  # FIXED: Now sys is imported
            "preprocessor_available": PREPROCESSOR_AVAILABLE,
            "ai_normalizer_available": AI_NORMALIZER_AVAILABLE,
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/debug/cleanup")
    async def perform_debug_cleanup():
        """Manual cleanup endpoint for debugging"""
        cleanup_temporary_files()
        background_tasks_status.clear()
        return {"message": "Cleanup completed", "timestamp": datetime.now().isoformat()}

# Error handlers
@app.exception_handler(404)
async def handle_not_found_error(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def handle_internal_server_error(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": datetime.now().isoformat()}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=DEBUG)