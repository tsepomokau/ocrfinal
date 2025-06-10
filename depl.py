#!/usr/bin/env python3
"""
Production Deployment Script for CP Tariff OCR API
Cleans up development files and prepares for production deployment.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

class ProductionDeployer:
    """Handles production deployment tasks"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def create_backup(self):
        """Create backup of existing files"""
        print("📦 Creating backup of existing files...")
        
        self.backup_dir.mkdir(exist_ok=True)
        
        # Files to backup
        backup_files = [
            "backend/app/main.py",
            "backend/app/document_processor/ocr_engine.py",
            "backend/app/document_processor/data_processor.py",
            "backend/app/database/cp_tariff_database.py",
            "backend/requirements.txt"
        ]
        
        for file_path in backup_files:
            source = self.project_root / file_path
            if source.exists():
                dest = self.backup_dir / source.name
                shutil.copy2(source, dest)
                print(f"   ✅ Backed up: {file_path}")
        
        print(f"✅ Backup completed: {self.backup_dir}")
    
    def remove_development_files(self):
        """Remove development and test files"""
        print("\n🧹 Removing development files...")
        
        files_to_remove = [
            # Test files
            "backend/test_api.py",
            "backend/debug_test.py",
            "backend/app/document_processor/test_enhanced_*.py",
            "backend/app/document_processor/*_debug.py",
            "backend/app/document_processor/*_test.py",
            
            # Enhanced/old files
            "backend/app/document_processor/ocr_engine_enhanced.py",
            "backend/app/document_processor/ocr_engine_improved.py",
            "backend/app/document_processor/ocr_engine_simple.py",
            "backend/app/document_processor/enhanced_*.py",
            "backend/app/document_processor/table_extractor_enhanced.py",
            "backend/app/document_processor/production_ocr_processor.py",
            "backend/app/database/cp_tariff_database_*.py",
            
            # Setup and deployment scripts
            "backend/app/document_processor/setup_*.py",
            "deploy_production.py",
            
            # Backup directories
            "backend/app/document_processor/backup*",
            "backend/backup*",
            
            # Log files
            "backend/app/document_processor/*.json",
            "backend/app/document_processor/*.log",
            
            # Temp files
            "backend/app/document_processor/.env",
            "backend/app/document_processor/start_enhanced.sh"
        ]
        
        removed_count = 0
        for pattern in files_to_remove:
            pattern_path = self.project_root / pattern
            
            # Handle glob patterns
            if '*' in pattern:
                parent = pattern_path.parent
                if parent.exists():
                    import glob
                    matches = glob.glob(str(pattern_path))
                    for match in matches:
                        match_path = Path(match)
                        if match_path.exists():
                            if match_path.is_file():
                                match_path.unlink()
                            elif match_path.is_dir():
                                shutil.rmtree(match_path)
                            print(f"   🗑️  Removed: {match}")
                            removed_count += 1
            else:
                # Handle specific files/directories
                if pattern_path.exists():
                    if pattern_path.is_file():
                        pattern_path.unlink()
                    elif pattern_path.is_dir():
                        shutil.rmtree(pattern_path)
                    print(f"   🗑️  Removed: {pattern}")
                    removed_count += 1
        
        print(f"✅ Removed {removed_count} development files")
    
    def create_production_structure(self):
        """Create clean production file structure"""
        print("\n📁 Creating production file structure...")
        
        # Ensure required directories exist
        required_dirs = [
            "backend/app",
            "backend/app/document_processor",
            "backend/app/database",
            "backend/temp",
            "backend/logs"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"   📂 Directory: {dir_path}")
        
        # Create __init__.py files
        init_files = [
            "backend/app/__init__.py",
            "backend/app/document_processor/__init__.py",
            "backend/app/database/__init__.py"
        ]
        
        for init_file in init_files:
            init_path = self.project_root / init_file
            if not init_path.exists():
                init_path.write_text("")
                print(f"   📄 Created: {init_file}")
    
    def create_production_env(self):
        """Create production environment file"""
        print("\n⚙️  Creating production environment configuration...")
        
        env_content = """# CP Tariff OCR API - Production Configuration
# Database
DB_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# API Configuration
DEBUG=False
HOST=0.0.0.0
PORT=8000

# File Processing
MAX_FILE_SIZE=10485760
TEMP_FOLDER=./temp
LOG_LEVEL=INFO

# OCR Configuration
OCR_DPI=300
TESSERACT_CMD=tesseract
"""
        
        env_path = self.project_root / "backend" / ".env"
        env_path.write_text(env_content)
        print(f"   ✅ Created: {env_path}")
    
    def create_startup_script(self):
        """Create production startup script"""
        print("\n🚀 Creating startup script...")
        
        startup_content = """#!/bin/bash
# CP Tariff OCR API - Production Startup Script

echo "Starting CP Tariff OCR API (Production Mode)"

# Navigate to backend directory
cd backend

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

echo "Server started at http://0.0.0.0:8000"
echo "API documentation available at http://0.0.0.0:8000/docs"
"""
        
        startup_path = self.project_root / "start_production.sh"
        startup_path.write_text(startup_content)
        
        # Make executable on Unix systems
        try:
            os.chmod(startup_path, 0o755)
        except:
            pass
        
        print(f"   ✅ Created: {startup_path}")
    
    def verify_production_setup(self):
        """Verify production setup is correct"""
        print("\n🔍 Verifying production setup...")
        
        required_files = [
            "backend/app/main.py",
            "backend/app/document_processor/ocr_engine.py",
            "backend/app/document_processor/ai_data_processor.py",
            "backend/app/database/cp_tariff_database.py",
            "backend/requirements.txt"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} - MISSING")
                missing_files.append(file_path)
        
        if missing_files:
            print(f"\n⚠️  Missing files: {len(missing_files)}")
            print("Please copy the production files from the artifacts to these locations.")
            return False
        else:
            print("\n🎉 All required files are present!")
            return True
    
    def deploy(self):
        """Run the complete deployment process"""
        print("🚀 CP Tariff OCR API - Production Deployment")
        print("=" * 60)
        
        try:
            # Create backup
            self.create_backup()
            
            # Remove development files
            self.remove_development_files()
            
            # Create production structure
            self.create_production_structure()
            
            # Create environment configuration
            self.create_production_env()
            
            # Create startup script
            self.create_startup_script()
            
            # Verify setup
            setup_valid = self.verify_production_setup()
            
            print(f"\n📋 Deployment Summary:")
            print(f"   Backup created: {self.backup_dir}")
            print(f"   Development files removed")
            print(f"   Production structure created")
            print(f"   Environment configured")
            print(f"   Startup script created")
            
            if setup_valid:
                print(f"\n🎊 Production deployment completed successfully!")
                print(f"\n📝 Next steps:")
                print(f"1. Copy the production files from artifacts to their locations:")
                print(f"   - main.py → backend/app/main.py")
                print(f"   - ocr_engine.py → backend/app/document_processor/ocr_engine.py")
                print(f"   - ai_data_processor.py → backend/app/document_processor/ai_data_processor.py")
                print(f"   - cp_tariff_database.py → backend/app/database/cp_tariff_database.py")
                print(f"2. Install dependencies: pip install -r backend/requirements.txt")
                print(f"3. Configure your database connection and OpenAI API key in backend/.env")
                print(f"4. Start the server: ./start_production.sh")
            else:
                print(f"\n⚠️  Deployment completed with missing files")
                print(f"Please copy the production artifacts before starting")
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            print(f"📦 Your original files are backed up in: {self.backup_dir}")

def main():
    """Main deployment entry point"""
    deployer = ProductionDeployer()
    deployer.deploy()

if __name__ == "__main__":
    main()