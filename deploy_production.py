#!/usr/bin/env python3
"""
Production Deployment Script for CP Tariff OCR API
This script deploys production-ready code without any sample data.

Run this in your backend directory:
python deploy_production.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

def create_backup():
    """Create backup of current files"""
    print("📦 Creating backup of current files...")
    
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "app/main.py",
        "app/database/cp_tariff_database.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"   ✅ Backed up: {file_path} → {backup_path}")
    
    print(f"✅ Backup completed: {backup_dir}")
    return backup_dir

def deploy_production_main():
    """Deploy production main.py"""
    print("\n🚀 Deploying production main.py...")
    
    production_main_content = '''import os
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

# Import components
from app.document_processor.ocr_engine_enhanced import EnhancedOCREngine as OCREngine
from app.document_processor.production_ocr_processor import ProductionOCRProcessor
from app.database.cp_tariff_database import CPTariffDatabase

# Production Configuration
TEMP_FOLDER = "./temp"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
VERSION = "3.0.0-Production"

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cp_tariff_api")

# Create directories
os.makedirs(TEMP_FOLDER, exist_ok=True)

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(f"Starting CP Tariff OCR API v{VERSION}")
    yield
    logger.info("Shutting down CP Tariff OCR API")

# Initialize FastAPI app
app = FastAPI(
    title="CP Tariff OCR API",
    description="Production OCR system for CP Tariff documents",
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

# Initialize components
connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-KL51D0H\\\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes"
database_manager = CPTariffDatabase(connection_string)
ocr_processor = ProductionOCRProcessor()

@app.get("/")
async def get_api_root():
    """Root endpoint"""
    return {
        "message": "CP Tariff OCR API",
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
        health_status["checks"]["tesseract"] = "available" if test_ocr.use_tesseract else "unavailable"
        health_status["checks"]["paddle"] = "available" if test_ocr.use_paddle else "unavailable"
    except Exception as e:
        health_status["checks"]["ocr_engines"] = f"error: {str(e)}"
    
    # Test database connection
    try:
        conn = database_manager.get_database_connection()
        if conn:
            conn.close()
            health_status["checks"]["database"] = "connected"
        else:
            health_status["checks"]["database"] = "disconnected"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
    
    return health_status

@app.post("/api/process-tariff")
async def process_tariff_document(
    file: UploadFile = File(...),
    extract_tables: bool = Query(True, description="Extract table data"),
    ocr_engine: str = Query("tesseract", description="OCR engine to use")
):
    """Process tariff document with production OCR"""
    
    temp_path = None
    start_time = time.time()
    
    try:
        # Validate and save file
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_FILE_SIZE:,} bytes")
        
        file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")
        
        logger.info(f"Processing: {file.filename} ({file_size:,} bytes)")
        
        # Save uploaded file temporarily
        temp_id = str(uuid.uuid4())
        from pathlib import Path
        
        temp_dir = Path(TEMP_FOLDER)
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / f"{temp_id}.{file_ext}"
        
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        
        # OCR Processing
        logger.info("Starting OCR extraction")
        ocr_engine_instance = OCREngine(use_tesseract=True, use_paddle=False)
        raw_ocr_data = ocr_engine_instance.process_sections([], str(temp_path))
        
        # Production OCR Processing
        logger.info("Starting production data processing")
        processed_data = ocr_processor.process_document_data(
            raw_ocr_data=raw_ocr_data,
            pdf_name=file.filename,
            file_size_bytes=file_size
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        processed_data['processing_metadata']['processing_time_seconds'] = processing_time
        
        logger.info(f"Processing completed in {processing_time:.2f}s")
        logger.info(f"Extracted: {len(processed_data.get('rates', []))} rates, {len(processed_data.get('notes', []))} notes")
        
        # Database Save
        logger.info("Saving to database")
        try:
            document_id = database_manager.save_document(processed_data)
            
            if document_id:
                logger.info(f"Successfully saved with document ID: {document_id}")
                database_success = True
                database_error = None
            else:
                logger.warning("Database save returned None")
                database_success = False
                database_error = "Database save returned None"
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            database_success = False
            database_error = str(db_error)
            document_id = None
        
        # Clean up temp file
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        # Prepare response
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
                "tables_extracted": processed_data.get("processing_metadata", {}).get("tables_found", 0)
            },
            "processing_metadata": processed_data.get("processing_metadata", {})
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        
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

@app.get("/stats")
async def get_database_statistics():
    """Get database statistics"""
    try:
        stats = database_manager.get_database_statistics()
        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
'''
    
    with open("app/main.py", "w", encoding="utf-8") as f:
        f.write(production_main_content)
    
    print("✅ Production main.py deployed")

def deploy_production_processor():
    """Deploy production OCR processor"""
    print("\n🔧 Deploying production OCR processor...")
    
    # Create the processor directory if it doesn't exist
    processor_dir = "app/document_processor"
    os.makedirs(processor_dir, exist_ok=True)
    
    # Note: The actual processor content should be copied from the artifact above
    # This is a placeholder to show the deployment structure
    processor_file = os.path.join(processor_dir, "production_ocr_processor.py")
    
    if not os.path.exists(processor_file):
        print(f"   ⚠️  Please create {processor_file} with the Production OCR Processor content")
        print("   📝 Copy the content from the 'Production OCR Processor - Deployment Ready' artifact")
    else:
        print(f"   ✅ Production OCR processor already exists: {processor_file}")

def deploy_production_database():
    """Deploy production database handler"""
    print("\n💾 Deploying production database handler...")
    
    # Note: The actual database content should be copied from the artifact above
    database_file = "app/database/cp_tariff_database.py"
    
    # Check if the file needs updating
    if os.path.exists(database_file):
        with open(database_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if it's already the production version
        if "Production Database Handler" in content:
            print("   ✅ Production database handler already deployed")
        else:
            print("   ⚠️  Please update the database handler with production version")
            print("   📝 Copy the content from the 'Production Database Handler - Deployment Ready' artifact")
    else:
        print(f"   ⚠️  Database file not found: {database_file}")

def verify_deployment():
    """Verify deployment is correct"""
    print("\n🔍 Verifying deployment...")
    
    required_files = [
        "app/main.py",
        "app/database/cp_tariff_database.py",
        "app/document_processor/production_ocr_processor.py"
    ]
    
    all_good = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - MISSING")
            all_good = False
    
    if all_good:
        print("\n🎉 All required files are present!")
        print("\n📋 Next steps:")
        print("1. Copy the Production OCR Processor content to app/document_processor/production_ocr_processor.py")
        print("2. Copy the Production Database Handler content to app/database/cp_tariff_database.py")
        print("3. Restart your server:")
        print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        print("4. Test with: python test_api.py")
    else:
        print("\n⚠️  Some files are missing. Please create them before proceeding.")

def main():
    """Main deployment process"""
    print("🚀 CP Tariff OCR Production Deployment")
    print("=" * 50)
    print("This will deploy production-ready code without sample data.")
    print("")
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: app directory not found!")
        print("Please run this script from the backend directory.")
        return
    
    # Create backup
    backup_dir = create_backup()
    
    try:
        # Deploy components
        deploy_production_main()
        deploy_production_processor()
        deploy_production_database()
        
        # Verify deployment
        verify_deployment()
        
        print(f"\n🎊 Deployment completed!")
        print(f"📦 Backup created: {backup_dir}")
        print("\n🔄 Remember to restart your server after copying the remaining artifacts!")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        print(f"📦 Your files are backed up in: {backup_dir}")

if __name__ == "__main__":
    main()
'''