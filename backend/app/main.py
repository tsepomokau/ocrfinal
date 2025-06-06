import os
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

# Import application modules
#from app.document_processor.preprocessor import DocumentPreprocessor
#from app.document_processor.ocr_engine import OCREngine
from app.document_processor.ocr_engine_debug import OCREngine
from app.document_processor.table_extractor import TableExtractor
from app.document_processor.enhanced_field_normalizer import EnhancedFieldNormalizer
from app.database.cp_tariff_database import CPTariffDatabase


from config import (
    TEMP_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, 
    CORS_ALLOW_ORIGINS, DEBUG, VERSION,
    ENABLE_API_KEY_AUTH, VALID_API_KEYS, API_KEY_HEADER_NAME,
    ENABLE_PERFORMANCE_MONITORING, SLOW_REQUEST_THRESHOLD_SECONDS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cp_tariff_api")

# Create directories
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Background task management
background_tasks_status = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting CP Tariff OCR API")
    logger.info(f"Version: {VERSION}")
    logger.info(f"Debug mode: {DEBUG}")
    
    # Initialize database connection
    try:
        db_manager = CPTariffDatabase()
        # Test connection
        conn = db_manager.get_connection()
        conn.close()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
    
    # Cleanup old temporary files on startup
    cleanup_temp_files()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down CP Tariff OCR API")
    cleanup_temp_files()

# Initialize FastAPI app
app = FastAPI(
    title="CP Tariff OCR API",
    description="AI-powered OCR system for Canadian Pacific Railway tariff documents with database integration",
    version=VERSION,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    lifespan=lifespan
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
    async def performance_middleware(request, call_next):
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

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key if authentication is enabled"""
    if not ENABLE_API_KEY_AUTH:
        return True
    
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")
    
    if credentials.credentials not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True

# Initialize database manager
db_manager = CPTariffDatabase()

def cleanup_temp_files():
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
async def root():
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
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "checks": {}
    }
    
    # Database health check
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        health_status["checks"]["database"] = "healthy"
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
async def test_endpoint():
    print("🧪 Test endpoint called!")
    return {"message": "Test endpoint working"}



@app.post("/api/process-tariff")
async def process_tariff(
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key)
):
    """Process a CP Tariff document synchronously and save to database"""
    start_time = time.time()
    
    # Validate file
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_FILE_SIZE:,} bytes")
    
    file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Create unique filename
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(TEMP_FOLDER, unique_filename)
    
    # Save file temporarily
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    try:
        logger.info(f"Processing document: {file.filename} ({file_size:,} bytes)")
        
        # 1. Preprocess the document
        preprocessor = DocumentPreprocessor(file_path)
        document_sections = preprocessor.process()
        
        # 2. Perform OCR on each section
        ocr_engine = OCREngine(use_paddle=True)
        ocr_results = ocr_engine.process_sections(document_sections)
        
        # Combine OCR text
        full_text = ""
        ocr_confidence_scores = []
        
        for page_key, page_results in ocr_results.items():
            page_full_text = page_results.get("full", "")
            full_text += page_full_text + "\n\n"
            
            # Extract confidence scores if available
            # This would depend on your OCR engine implementation
        
        # 3. Extract and normalize fields using AI
        field_normalizer = EnhancedFieldNormalizer(full_text, file.filename)
        normalized_data = field_normalizer.normalize()
        normalized_data['raw_text'] = full_text
        
        # 4. Extract table data from each page
        all_table_data = []
        for page_key, page_results in ocr_results.items():
            table_text = page_results.get("table", "")
            if table_text:
                table_extractor = TableExtractor(table_text)
                table_data = table_extractor.extract()
                all_table_data.append(table_data)
        
        # Combine table data
        combined_table_data = {
            "headers": all_table_data[0]["headers"] if all_table_data else [],
            "rows": [],
            "raw_data": []
        }
        
        for table in all_table_data:
            combined_table_data["rows"].extend(table["rows"])
            combined_table_data["raw_data"].extend(table["raw_data"])
        
        # 5. Save to database
        processing_time = time.time() - start_time
        
        try:
            # Add processing metadata
            normalized_data['processing_metadata'] = {
                'processing_time_seconds': int(processing_time),
                'file_size_bytes': file_size,
                'ocr_engine': 'PaddleOCR',
                'ai_processing_used': True,
                'pages_processed': len(ocr_results)
            }
            
            document_id = db_manager.save_tariff_document(normalized_data, file_path)
            
            logger.info(f"Document saved successfully with ID: {document_id}")
            
            result = {
                "success": True,
                "database_id": document_id,
                "message": "Document processed and saved to database successfully",
                "processing_time_seconds": round(processing_time, 2),
                "metadata": normalized_data.get('header', {}),
                "summary": {
                    "item_number": normalized_data.get('header', {}).get('item_number'),
                    "revision": normalized_data.get('header', {}).get('revision'),
                    "commodities_count": len(normalized_data.get('commodities', [])),
                    "rates_count": len(normalized_data.get('rates', [])),
                    "notes_count": len(normalized_data.get('notes', [])),
                    "currency": normalized_data.get('currency', 'USD'),
                    "file_size_bytes": file_size,
                    "pages_processed": len(ocr_results)
                },
                "tableData": combined_table_data
            }
            
            # Include full extracted data in debug mode
            if DEBUG:
                result["extractedData"] = normalized_data
            
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            result = {
                "success": False,
                "database_error": str(db_error),
                "message": "Document processed but failed to save to database",
                "processing_time_seconds": round(processing_time, 2),
                "metadata": normalized_data.get('header', {}),
                "tableData": combined_table_data,
                "extractedData": normalized_data if DEBUG else None
            }
        
        return result
    
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    
    finally:
        # Clean up
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not remove temporary file: {e}")
        
        # Clean up preprocessor files
        try:
            preprocessor.cleanup()
        except Exception as e:
            logger.warning(f"Preprocessor cleanup warning: {e}")

@app.post("/api/process-tariff-async")
async def process_tariff_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key)
):
    """Process a CP Tariff document asynchronously"""
    # Validate file
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Create unique task ID and filename
    task_id = str(uuid.uuid4())
    unique_filename = f"{task_id}.{file_ext}"
    file_path = os.path.join(TEMP_FOLDER, unique_filename)
    
    # Save file temporarily
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # Initialize task status
    background_tasks_status[task_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "file_name": file.filename,
        "file_size": file_size
    }
    
    # Start background processing
    background_tasks.add_task(
        process_document_task, 
        task_id, 
        file_path, 
        file.filename
    )
    
    return {
        "task_id": task_id, 
        "status": "processing",
        "message": "Document processing started",
        "estimated_time_minutes": "2-5"
    }

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str, _: bool = Depends(verify_api_key)):
    """Get the status of an asynchronous processing task"""
    # Check in-memory status first
    if task_id in background_tasks_status:
        return {
            "task_id": task_id,
            **background_tasks_status[task_id]
        }
    
    # Check for result file
    result_path = os.path.join(TEMP_FOLDER, f"{task_id}_result.json")
    error_path = os.path.join(TEMP_FOLDER, f"{task_id}_error.txt")
    
    if os.path.exists(result_path):
        try:
            with open(result_path, "r") as f:
                result = json.load(f)
            return {"task_id": task_id, "status": "completed", "result": result}
        except Exception as e:
            return {"task_id": task_id, "status": "error", "error": f"Could not read result: {e}"}
    
    if os.path.exists(error_path):
        try:
            with open(error_path, "r") as f:
                error = f.read()
            return {"task_id": task_id, "status": "error", "error": error}
        except Exception as e:
            return {"task_id": task_id, "status": "error", "error": f"Could not read error: {e}"}
    
    # Check if task file still exists (still processing)
    task_files = [f for f in os.listdir(TEMP_FOLDER) if f.startswith(task_id)]
    if task_files:
        return {"task_id": task_id, "status": "processing"}
    
    # Task not found
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/api/tariffs/search")
async def search_tariffs(
    origin: Optional[str] = Query(None, description="Origin location"),
    destination: Optional[str] = Query(None, description="Destination location"),
    commodity: Optional[str] = Query(None, description="Commodity name"),
    item_number: Optional[str] = Query(None, description="Tariff item number"),
    active_only: bool = Query(True, description="Only return active tariffs"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    _: bool = Depends(verify_api_key)
):
    """Search tariffs by various criteria"""
    try:
        if item_number:
            # Search by specific item number
            result = db_manager.get_tariff_by_item(item_number)
            return {
                "results": [result] if result else [], 
                "count": 1 if result else 0,
                "total": 1 if result else 0,
                "limit": limit,
                "offset": offset
            }
        else:
            # General search
            results = db_manager.search_tariffs(
                origin=origin,
                destination=destination,
                commodity=commodity,
                active_only=active_only
            )
            
            # Apply pagination
            total = len(results)
            paginated_results = results[offset:offset + limit]
            
            return {
                "results": paginated_results, 
                "count": len(paginated_results),
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/api/tariffs/{item_number}")
async def get_tariff_by_item(
    item_number: str, 
    revision: Optional[int] = Query(None, description="Specific revision number"),
    _: bool = Depends(verify_api_key)
):
    """Get specific tariff by item number and optional revision"""
    try:
        result = db_manager.get_tariff_by_item(item_number, revision)
        if not result:
            raise HTTPException(status_code=404, detail="Tariff not found")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tariff {item_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving tariff: {str(e)}")

@app.get("/api/rates/search")
async def search_rates(
    origin: str = Query(..., description="Origin location"),
    destination: str = Query(..., description="Destination location"),
    train_type: Optional[str] = Query(None, description="Train type filter"),
    car_capacity_type: Optional[str] = Query(None, description="Car capacity type"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    _: bool = Depends(verify_api_key)
):
    """Get all rates for a specific origin-destination pair"""
    try:
        results = db_manager.get_rates_for_route(origin, destination)
        
        # Apply filters
        if train_type:
            results = [r for r in results if r.get('train_type', '').upper() == train_type.upper()]
        
        if car_capacity_type:
            results = [r for r in results if r.get('car_capacity_type', '').upper() == car_capacity_type.upper()]
        
        # Apply limit
        results = results[:limit]
        
        return {
            "results": results, 
            "count": len(results),
            "origin": origin,
            "destination": destination,
            "filters": {
                "train_type": train_type,
                "car_capacity_type": car_capacity_type
            }
        }
    
    except Exception as e:
        logger.error(f"Rate search error: {e}")
        raise HTTPException(status_code=500, detail=f"Rate search error: {str(e)}")

@app.get("/api/tariffs/{document_id}/details")
async def get_tariff_details(
    document_id: int,
    include_raw_data: bool = Query(False, description="Include raw OCR text and processing data"),
    _: bool = Depends(verify_api_key)
):
    """Get complete tariff details including commodities, rates, and notes"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get main document
        cursor.execute("SELECT * FROM tariff_documents WHERE id = %s", (document_id,))
        document_row = cursor.fetchone()
        
        if not document_row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Convert to dict
        columns = [desc[0] for desc in cursor.description]
        document = dict(zip(columns, document_row))
        
        # Remove raw data unless requested
        if not include_raw_data:
            document.pop('raw_ocr_text', None)
            document.pop('processed_json', None)
        
        # Get related data
        cursor.execute("SELECT * FROM tariff_commodities WHERE tariff_document_id = %s", (document_id,))
        commodity_rows = cursor.fetchall()
        commodity_columns = [desc[0] for desc in cursor.description]
        commodities = [dict(zip(commodity_columns, row)) for row in commodity_rows]
        
        cursor.execute("SELECT * FROM tariff_rates WHERE tariff_document_id = %s ORDER BY rate_amount", (document_id,))
        rate_rows = cursor.fetchall()
        rate_columns = [desc[0] for desc in cursor.description]
        rates = [dict(zip(rate_columns, row)) for row in rate_rows]
        
        cursor.execute("SELECT * FROM tariff_notes WHERE tariff_document_id = %s ORDER BY sort_order", (document_id,))
        note_rows = cursor.fetchall()
        note_columns = [desc[0] for desc in cursor.description]
        notes = [dict(zip(note_columns, row)) for row in note_rows]
        
        cursor.close()
        conn.close()
        
        return {
            "document": document,
            "commodities": commodities,
            "rates": rates,
            "notes": notes,
            "summary": {
                "commodity_count": len(commodities),
                "rate_count": len(rates),
                "note_count": len(notes),
                "rate_range": {
                    "min": min(r.get('rate_amount', 0) for r in rates) if rates else None,
                    "max": max(r.get('rate_amount', 0) for r in rates) if rates else None
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving details for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving details: {str(e)}")

@app.get("/api/statistics")
async def get_database_statistics(_: bool = Depends(verify_api_key)):
    """Get comprehensive database statistics"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Document statistics
        cursor.execute("SELECT COUNT(*) FROM tariff_documents")
        stats['total_documents'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tariff_documents WHERE status = 'ACTIVE'")
        stats['active_documents'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tariff_documents WHERE expiration_date >= CURRENT_DATE OR expiration_date IS NULL")
        stats['current_documents'] = cursor.fetchone()[0]
        
        # Content statistics
        cursor.execute("SELECT COUNT(*) FROM tariff_commodities")
        stats['total_commodities'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tariff_rates")
        stats['total_rates'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tariff_notes")
        stats['total_notes'] = cursor.fetchone()[0]
        
        # Rate statistics
        cursor.execute("SELECT MIN(rate_amount), MAX(rate_amount), AVG(rate_amount) FROM tariff_rates WHERE rate_amount IS NOT NULL")
        rate_stats = cursor.fetchone()
        if rate_stats[0] is not None:
            stats['rate_statistics'] = {
                'min_rate': float(rate_stats[0]),
                'max_rate': float(rate_stats[1]),
                'avg_rate': float(rate_stats[2])
            }
        
        # Recent uploads
        cursor.execute("""
            SELECT item_number, revision, pdf_name, upload_timestamp, currency
            FROM tariff_documents 
            ORDER BY upload_timestamp DESC 
            LIMIT 10
        """)
        recent_uploads = []
        for row in cursor.fetchall():
            recent_uploads.append({
                'item_number': row[0],
                'revision': row[1],
                'pdf_name': row[2],
                'upload_timestamp': row[3].isoformat() if row[3] else None,
                'currency': row[4]
            })
        
        # Popular origins and destinations
        cursor.execute("""
            SELECT origin, COUNT(*) as count 
            FROM tariff_rates 
            WHERE origin IS NOT NULL 
            GROUP BY origin 
            ORDER BY count DESC 
            LIMIT 10
        """)
        popular_origins = [{'location': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT destination, COUNT(*) as count 
            FROM tariff_rates 
            WHERE destination IS NOT NULL 
            GROUP BY destination 
            ORDER BY count DESC 
            LIMIT 10
        """)
        popular_destinations = [{'location': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            "statistics": stats,
            "recent_uploads": recent_uploads,
            "popular_routes": {
                "origins": popular_origins,
                "destinations": popular_destinations
            },
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

# ========================================
# Background Task Functions
# ========================================

async def process_document_task(task_id: str, file_path: str, original_filename: str):
    """Background task for document processing"""
    try:
        # Update status
        background_tasks_status[task_id] = {
            **background_tasks_status.get(task_id, {}),
            "status": "processing",
            "stage": "preprocessing"
        }
        
        # Same processing logic as synchronous version
        preprocessor = DocumentPreprocessor(file_path)
        document_sections = preprocessor.process()
        
        background_tasks_status[task_id]["stage"] = "ocr"
        ocr_engine = OCREngine(use_paddle=True)
        ocr_results = ocr_engine.process_sections(document_sections)
        
        full_text = ""
        for page_key, page_results in ocr_results.items():
            page_full_text = page_results.get("full", "")
            full_text += page_full_text + "\n\n"
        
        background_tasks_status[task_id]["stage"] = "ai_processing"
        field_normalizer = EnhancedFieldNormalizer(full_text, original_filename)
        normalized_data = field_normalizer.normalize()
        normalized_data['raw_text'] = full_text
        
        background_tasks_status[task_id]["stage"] = "table_extraction"
        all_table_data = []
        for page_key, page_results in ocr_results.items():
            table_text = page_results.get("table", "")
            if table_text:
                table_extractor = TableExtractor(table_text)
                table_data = table_extractor.extract()
                all_table_data.append(table_data)
        
        combined_table_data = {
            "headers": all_table_data[0]["headers"] if all_table_data else [],
            "rows": [],
            "raw_data": []
        }
        
        for table in all_table_data:
            combined_table_data["rows"].extend(table["rows"])
            combined_table_data["raw_data"].extend(table["raw_data"])
        
        background_tasks_status[task_id]["stage"] = "database_save"
        # Save to database
        try:
            document_id = db_manager.save_tariff_document(normalized_data, file_path)
            
            result = {
                "success": True,
                "database_id": document_id,
                "message": "Document processed and saved to database successfully",
                "metadata": normalized_data.get('header', {}),
                "summary": {
                    "item_number": normalized_data.get('header', {}).get('item_number'),
                    "revision": normalized_data.get('header', {}).get('revision'),
                    "commodities_count": len(normalized_data.get('commodities', [])),
                    "rates_count": len(normalized_data.get('rates', [])),
                    "notes_count": len(normalized_data.get('notes', [])),
                    "currency": normalized_data.get('currency', 'USD')
                },
                "tableData": combined_table_data
            }
        except Exception as db_error:
            result = {
                "success": False,
                "database_error": str(db_error),
                "message": "Document processed but failed to save to database",
                "metadata": normalized_data.get('header', {}),
                "tableData": combined_table_data
            }
        
        # Save result to file
        result_path = os.path.join(TEMP_FOLDER, f"{task_id}_result.json")
        with open(result_path, "w") as f:
            json.dump(result, f, default=str)  # default=str to handle datetime objects
        
        # Update final status
        background_tasks_status[task_id] = {
            **background_tasks_status[task_id],
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        preprocessor.cleanup()
        
    except Exception as e:
        logger.error(f"Background task error: {e}")
        
        # Save error to file
        error_path = os.path.join(TEMP_FOLDER, f"{task_id}_error.txt")
        with open(error_path, "w") as f:
            f.write(str(e))
        
        # Update status
        background_tasks_status[task_id] = {
            **background_tasks_status.get(task_id, {}),
            "status": "error",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

# ========================================
# Debug Endpoints (only in debug mode)
# ========================================

if DEBUG:
    @app.get("/debug/info")
    async def debug_info():
        """Debug information endpoint"""
        return {
            "version": VERSION,
            "debug_mode": DEBUG,
            "temp_folder": TEMP_FOLDER,
            "max_file_size": MAX_FILE_SIZE,
            "allowed_extensions": list(ALLOWED_EXTENSIONS),
            "active_background_tasks": len(background_tasks_status),
            "temp_files": len([f for f in os.listdir(TEMP_FOLDER) if os.path.isfile(os.path.join(TEMP_FOLDER, f))]),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/debug/cleanup")
    async def debug_cleanup():
        """Manual cleanup endpoint for debugging"""
        cleanup_temp_files()
        background_tasks_status.clear()
        return {"message": "Cleanup completed", "timestamp": datetime.now().isoformat()}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "timestamp": datetime.now().isoformat()}
    )


# Replace your process-tariff endpoint in main.py with this:

@app.post("/api/process-tariff")
async def process_tariff_document(
    file: UploadFile = File(...),
    scheme: str = Query(...),
    credentials: str = Query(...),
    document_type: str = Query(default="tariff"),
    processing_mode: str = Query(default="full")
):
    """Process uploaded tariff document - completely self-contained version"""
    
    print("🚨 ENDPOINT CALLED!")
    temp_path = None
    try:
        # Get file content
        content = await file.read()
        print(f"📤 Processing document: {file.filename} ({len(content):,} bytes)")
        
        # Save uploaded file
        import uuid
        from pathlib import Path
        
        temp_id = str(uuid.uuid4())
        temp_dir = Path("./temp")
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / f"{temp_id}.pdf"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"💾 Saved to temp file: {temp_path}")
        
        # Create OCR engine and process directly
        from app.document_processor.ocr_engine_debug import OCREngine
        
        print(f"🔄 Creating OCR engine...")
        ocr_engine = OCREngine()
        
        print(f"🔄 Starting OCR processing with PDF path: '{temp_path}'")
        extracted_data = ocr_engine.process_sections([], str(temp_path))
        
        print("✅ OCR processing completed")
        print(f"📊 Extracted data type: {type(extracted_data)}")
        
        if not isinstance(extracted_data, dict):
            raise ValueError(f"OCR engine returned {type(extracted_data)}, expected dict")
        
        print(f"📊 OCR data keys: {list(extracted_data.keys())}")
        
        # Prepare final data structure
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
            "processing_metadata": extracted_data.get("processing_metadata", {})
        }
        
        print(f"✅ Final data prepared:")
        print(f"   Commodities: {len(final_data['commodities'])}")
        print(f"   Rates: {len(final_data['rates'])}")
        print(f"   Notes: {len(final_data['notes'])}")
        print(f"   Header: {final_data['header']}")
        
        # Save to database
        print("💾 Starting database save...")
        from app.database.cp_tariff_database import database
        
        document_id = database.save_tariff_document(final_data, str(temp_path))
        
        if document_id:
            print(f"🎉 SUCCESS: Document saved with ID: {document_id}")
        else:
            print("❌ WARNING: Database save returned None")
        
        # Clean up temp file
        if temp_path and temp_path.exists():
            temp_path.unlink()
            print("🧹 Temp file cleaned up")
        
        # Create response
        response_data = {
            "status": "success" if document_id else "warning",
            "message": "Tariff document processed successfully" if document_id else "Document processed but save failed",
            "document_id": document_id,
            "processing_time": final_data.get("processing_metadata", {}).get("processing_time_seconds", 0),
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
            }
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
        
        return {
            "status": "error", 
            "message": f"Error processing document: {str(e)}",
            "document_id": None,
            "error_details": str(e)
        }




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=DEBUG)