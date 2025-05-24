import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shutil
from typing import Dict, List, Any, Optional
import json

from app.document_processor.preprocessor import DocumentPreprocessor
from app.document_processor.ocr_engine import OCREngine
from app.document_processor.table_extractor import TableExtractor
from app.document_processor.field_normalizer import FieldNormalizer
from app.models.tariff import TariffDocument
from config import TEMP_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE

app = FastAPI(title="CP Tariff OCR API")

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp folder if it doesn't exist
os.makedirs(TEMP_FOLDER, exist_ok=True)

@app.get("/")
async def root():
    return {"message": "CP Tariff OCR API"}

@app.post("/api/process-tariff")
async def process_tariff(file: UploadFile = File(...)):
    """Process a CP Tariff document and extract structured information."""
    # Check file size
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Check file extension
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Create a unique filename
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(TEMP_FOLDER, unique_filename)
    
    # Save the file temporarily
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    try:
        # 1. Preprocess the document
        preprocessor = DocumentPreprocessor(file_path)
        document_sections = preprocessor.process()
        
        # 2. Perform OCR on each section
        ocr_engine = OCREngine(use_paddle=True)
        ocr_results = ocr_engine.process_sections(document_sections)
        
        # Combine OCR text for further processing
        full_text = ""
        for page_key, page_results in ocr_results.items():
            page_full_text = page_results.get("full", "")
            full_text += page_full_text + "\n\n"
        
        # 3. Normalize fields using ChatGPT
        field_normalizer = FieldNormalizer(full_text)
        normalized_fields = field_normalizer.normalize()
        
        # 4. Extract table data from each page
        all_table_data = []
        for page_key, page_results in ocr_results.items():
            table_text = page_results.get("table", "")
            if table_text:
                table_extractor = TableExtractor(table_text)
                table_data = table_extractor.extract()
                all_table_data.append(table_data)
        
        # Combine table data if there are multiple pages
        combined_table_data = {
            "headers": all_table_data[0]["headers"] if all_table_data else [],
            "rows": [],
            "raw_data": []
        }
        
        for table in all_table_data:
            combined_table_data["rows"].extend(table["rows"])
            combined_table_data["raw_data"].extend(table["raw_data"])
        
        # 5. Construct the complete result
        result = {
            "metadata": normalized_fields,
            "tableData": combined_table_data,
            "rawText": full_text
        }
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Clean up preprocessor files
        try:
            preprocessor.cleanup()
        except:
            pass

@app.post("/api/process-tariff-async")
async def process_tariff_async(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Process a CP Tariff document asynchronously."""
    # Check file size and type (same as above)
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Create a unique filename and task ID
    task_id = str(uuid.uuid4())
    unique_filename = f"{task_id}.{file_ext}"
    file_path = os.path.join(TEMP_FOLDER, unique_filename)
    
    # Save the file temporarily
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # Start background processing
    background_tasks.add_task(process_document_task, task_id, file_path)
    
    return {"task_id": task_id, "status": "processing"}

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of an asynchronous processing task."""
    result_path = os.path.join(TEMP_FOLDER, f"{task_id}_result.json")
    
    if os.path.exists(result_path):
        with open(result_path, "r") as f:
            result = json.load(f)
        return {"task_id": task_id, "status": "completed", "result": result}
    
    # Check if task is still processing
    if any(filename.startswith(task_id) for filename in os.listdir(TEMP_FOLDER)):
        return {"task_id": task_id, "status": "processing"}
    
    # Task not found
    raise HTTPException(status_code=404, detail="Task not found")

async def process_document_task(task_id: str, file_path: str):
    """Background task for document processing."""
    try:
        # Same processing logic as in process_tariff
        preprocessor = DocumentPreprocessor(file_path)
        document_sections = preprocessor.process()
        
        ocr_engine = OCREngine(use_paddle=True)
        ocr_results = ocr_engine.process_sections(document_sections)
        
        full_text = ""
        for page_key, page_results in ocr_results.items():
            page_full_text = page_results.get("full", "")
            full_text += page_full_text + "\n\n"
        
        field_normalizer = FieldNormalizer(full_text)
        normalized_fields = field_normalizer.normalize()
        
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
        
        result = {
            "metadata": normalized_fields,
            "tableData": combined_table_data,
            "rawText": full_text
        }
        
        # Save result to file
        result_path = os.path.join(TEMP_FOLDER, f"{task_id}_result.json")
        with open(result_path, "w") as f:
            json.dump(result, f)
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
        
        preprocessor.cleanup()
    
    except Exception as e:
        # Save error to file
        error_path = os.path.join(TEMP_FOLDER, f"{task_id}_error.txt")
        with open(error_path, "w") as f:
            f.write(str(e))
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)