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

# Import enhanced components
from app.document_processor.ocr_engine_enhanced import EnhancedOCREngine as OCREngine
from app.document_processor.enhanced_data_processor import EnhancedDataProcessor
from app.database.cp_tariff_database_fixed import CPTariffDatabaseFixed

# Configuration
TEMP_FOLDER = "./temp"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
DEBUG = True
VERSION = "2.2.0-Enhanced"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cp_tariff_api_enhanced")

# Create directories
os.makedirs(TEMP_FOLDER, exist_ok=True)

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting Enhanced CP Tariff OCR API")
    logger.info(f"Version: {VERSION}")
    logger.info("✨ Features: Enhanced Data Processing + Fixed Database")
    
    yield
    
    logger.info("🛑 Shutting down Enhanced CP Tariff OCR API")

# Initialize FastAPI app
app = FastAPI(
    title="CP Tariff OCR API - Enhanced",
    description="Enhanced OCR system for CP Tariff documents with improved data processing and database handling",
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

# Initialize enhanced components
connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-KL51D0H\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes"
database_manager = CPTariffDatabaseFixed(connection_string)
data_processor = EnhancedDataProcessor()

@app.get("/")
async def get_api_root():
    """Root endpoint"""
    return {
        "message": "CP Tariff OCR API - Enhanced with Data Processing",
        "version": VERSION,
        "status": "operational",
        "features": [
            "Enhanced OCR Processing",
            "Improved Data Extraction",
            "Fixed Database Handling",
            "Better Error Recovery"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def get_health_status():
    """Enhanced health check endpoint"""
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
            "paddle_available": test_ocr.use_paddle,
            "status": "operational"
        }
    except Exception as e:
        health_status["checks"]["ocr_engines"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test database connection
    try:
        db_test = database_manager.test_database_connection()
        health_status["checks"]["database"] = {
            "status": "connected" if db_test else "disconnected",
            "connection_string": "SQL Server Express (configured)"
        }
        
        if db_test:
            stats = database_manager.get_database_statistics()
            health_status["checks"]["database"]["statistics"] = stats
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test data processor
    try:
        test_data = {'header': {'item_number': 'TEST'}, 'commodities': [], 'rates': [], 'notes': []}
        processed = data_processor.process_extracted_data(test_data)
        health_status["checks"]["data_processor"] = {
            "status": "operational",
            "test_processing": "successful"
        }
    except Exception as e:
        health_status["checks"]["data_processor"] = {
            "status": "error",
            "error": str(e)
        }
    
    return health_status

@app.post("/api/process-tariff")
async def process_tariff_document_enhanced(
    file: UploadFile = File(...),
    extract_tables: bool = Query(True, description="Extract table data"),
    ocr_engine: str = Query("tesseract", description="OCR engine to use"),
    enhance_data: bool = Query(True, description="Use enhanced data processing")
):
    """Enhanced tariff document processing with improved data handling"""
    
    print("🚨 ENHANCED TARIFF PROCESSING CALLED!")
    print(f"🔧 Enhanced Data Processing: {'Enabled' if enhance_data else 'Disabled'}")
    
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
        print("🔄 Starting enhanced OCR extraction...")
        ocr_engine_instance = OCREngine(use_tesseract=True, use_paddle=False)
        
        raw_extracted_data = ocr_engine_instance.process_sections([], str(temp_path))
        
        print("✅ OCR extraction completed")
        
        # Enhanced Data Processing
        if enhance_data:
            print("🚀 Starting enhanced data processing...")
            
            # Add file metadata
            raw_extracted_data['pdf_name'] = file.filename
            raw_extracted_data['file_size_bytes'] = file_size
            
            processed_data = data_processor.process_extracted_data(raw_extracted_data)
            print("✅ Enhanced data processing completed")
        else:
            print("⚠️  Using basic data processing (enhanced disabled)")
            processed_data = raw_extracted_data
        
        # Prepare final data with processing time
        processing_time = time.time() - start_time
        processed_data['processing_metadata']['processing_time_seconds'] = processing_time
        processed_data['processing_metadata']['file_size_bytes'] = file_size
        
        print(f"📊 Final data summary:")
        print(f"   Rates: {len(processed_data.get('rates', []))}")
        print(f"   Notes: {len(processed_data.get('notes', []))}")
        print(f"   Commodities: {len(processed_data.get('commodities', []))}")
        print(f"   Processing time: {processing_time:.2f}s")
        
        # Enhanced Database Save
        print("💾 Starting enhanced database save...")
        try:
            document_id = database_manager.save_document(processed_data)
            
            if document_id:
                print(f"🎉 Successfully saved with ID: {document_id}")
                database_success = True
                database_error = None
            else:
                database_success = False
                database_error = database_manager.get_last_error()
                print(f"❌ Database save failed: {database_error}")
        except Exception as db_error:
            print(f"❌ Database error: {db_error}")
            database_success = False
            database_error = str(db_error)
            document_id = None
        
        # Clean up
        if temp_path and temp_path.exists():
            temp_path.unlink()
            print("🧹 Cleaned up temp file")
        
        # Enhanced Response
        response_data = {
            "status": "success" if database_success else "warning",
            "message": "Document processed successfully" if database_success else "Processed but database save failed",
            "document_id": document_id,
            "processing_time": round(processing_time, 2),
            "database_error": database_error,
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
                "total_rates_found": len(processed_data.get("rates", [])),
                "total_notes_found": len(processed_data.get("notes", [])),
                "total_commodities_found": len(processed_data.get("commodities", [])),
                "tables_extracted": processed_data.get("processing_metadata", {}).get("tables_found", 0),
                "rates_processed": processed_data.get("processing_metadata", {}).get("rates_processed", 0),
                "notes_processed": processed_data.get("processing_metadata", {}).get("notes_processed", 0),
                "commodities_processed": processed_data.get("processing_metadata", {}).get("commodities_processed", 0)
            },
            "processing_metadata": processed_data.get("processing_metadata", {}),
            "enhancement_features": {
                "enhanced_data_processing": enhance_data,
                "improved_database_handling": True,
                "advanced_error_recovery": True,
                "data_validation": True
            }
        }
        
        # Log final status
        if database_success:
            print(f"🎊 PROCESSING COMPLETE - SUCCESS!")
        else:
            print(f"⚠️  PROCESSING COMPLETE - WITH WARNINGS")
        
        print(f"📤 Returning response with status: {response_data['status']}")
        return response_data
        
    except Exception as e:
        print(f"❌ PROCESSING ERROR: {e}")
        
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Error processing document: {str(e)}",
                "document_id": None,
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/api/statistics")
async def get_database_statistics():
    """Get enhanced database statistics"""
    try:
        stats = database_manager.get_database_statistics()
        
        # Add additional computed statistics
        enhanced_stats = {
            "statistics": stats,
            "computed_metrics": {
                "documents_per_day": 0,  # Could be calculated from upload timestamps
                "average_rates_per_document": 0,
                "most_common_commodities": [],
                "processing_success_rate": "N/A"
            },
            "system_info": {
                "version": VERSION,
                "database_type": "SQL Server Express",
                "ocr_engines": ["Tesseract", "Enhanced Processing"],
                "features_enabled": [
                    "Enhanced Data Processing",
                    "Improved Database Handling",
                    "Advanced Error Recovery"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate averages if we have data
        if stats.get("total_documents", 0) > 0:
            total_rates = stats.get("total_rates", 0)
            total_docs = stats["total_documents"]
            enhanced_stats["computed_metrics"]["average_rates_per_document"] = round(total_rates / total_docs, 2)
        
        return enhanced_stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Error retrieving statistics: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/debug/info")
async def get_enhanced_debug_info():
    """Enhanced debug information"""
    try:
        test_ocr = OCREngine()
        ocr_info = {
            "tesseract_available": test_ocr.use_tesseract,
            "paddle_available": test_ocr.use_paddle
        }
    except Exception as e:
        ocr_info = {"error": str(e)}
    
    # Test database
    try:
        db_test = database_manager.test_database_connection()
        db_info = {
            "connection_status": "connected" if db_test else "disconnected",
            "last_error": database_manager.get_last_error()
        }
    except Exception as e:
        db_info = {"error": str(e)}
    
    return {
        "version": VERSION,
        "platform": "Windows",
        "temp_folder": TEMP_FOLDER,
        "ocr_engines": ocr_info,
        "database": db_info,
        "data_processor": {
            "status": "available",
            "features": [
                "Enhanced Rate Parsing",
                "Improved Location Extraction", 
                "Advanced Data Validation",
                "Smart Error Recovery"
            ]
        },
        "enhancement_features": {
            "enhanced_data_processing": True,
            "improved_database_handling": True,
            "advanced_error_recovery": True,
            "data_quality_validation": True
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/debug/test-processing")
async def test_enhanced_processing():
    """Test enhanced processing components"""
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Test OCR Engine
    try:
        ocr_engine = OCREngine()
        test_results["tests"]["ocr_engine"] = {
            "status": "success",
            "tesseract_available": ocr_engine.use_tesseract,
            "paddle_available": ocr_engine.use_paddle
        }
    except Exception as e:
        test_results["tests"]["ocr_engine"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test Data Processor
    try:
        test_data = {
            'header': {'item_number': '12345', 'revision': '1'},
            'commodities': [{'name': 'Test Grain', 'stcc_code': '01 123 45'}],
            'rates': [{'origin': 'Test City AB', 'destination': 'Test Dest IL', 'rate_amount': '123.45'}],
            'notes': [{'type': 'TEST', 'text': 'Test note'}]
        }
        
        processor = EnhancedDataProcessor()
        processed = processor.process_extracted_data(test_data)
        
        test_results["tests"]["data_processor"] = {
            "status": "success",
            "processed_rates": len(processed.get('rates', [])),
            "processed_notes": len(processed.get('notes', [])),
            "processed_commodities": len(processed.get('commodities', []))
        }
    except Exception as e:
        test_results["tests"]["data_processor"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test Database
    try:
        db_test = database_manager.test_database_connection()
        test_results["tests"]["database"] = {
            "status": "success" if db_test else "failed",
            "connection_test": db_test
        }
        
        if db_test:
            stats = database_manager.get_database_statistics()
            test_results["tests"]["database"]["statistics"] = stats
    except Exception as e:
        test_results["tests"]["database"] = {
            "status": "error",
            "error": str(e)
        }
    
    return test_results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=DEBUG)