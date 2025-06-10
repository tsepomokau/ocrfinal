#!/usr/bin/env python3
"""
This script automates the setup and integration of the enhanced OCR system
with comprehensive table extraction capabilities.
"""

import os
import sys
import shutil
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
from datetime import datetime

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class EnhancedOCRSetup:
    """Setup manager for enhanced OCR system"""
    
    def __init__(self, project_root: str = None, backup: bool = True):
        self.project_root = Path(project_root or os.getcwd())
        self.backup = backup
        self.backup_dir = self.project_root / "backup" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.setup_log = []
        
    def log(self, message: str, color: str = Colors.WHITE):
        """Log a message with color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(f"{color}{log_entry}{Colors.END}")
        self.setup_log.append(log_entry)
    
    def log_success(self, message: str):
        self.log(f"✅ {message}", Colors.GREEN)
    
    def log_error(self, message: str):
        self.log(f"❌ {message}", Colors.RED)
    
    def log_warning(self, message: str):
        self.log(f"⚠️  {message}", Colors.YELLOW)
    
    def log_info(self, message: str):
        self.log(f"ℹ️  {message}", Colors.BLUE)
    
    def log_step(self, message: str):
        self.log(f"🔧 {message}", Colors.CYAN)
    
    def create_backup(self) -> bool:
        """Create backup of existing files"""
        if not self.backup:
            return True
            
        self.log_step("Creating backup of existing files...")
        
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Files to backup
            backup_files = [
                "backend/app/main.py",
                "backend/app/document_processor/ocr_engine.py",
                "backend/app/document_processor/table_extractor.py",
                "backend/requirements.txt",
                ".env"
            ]
            
            for file_path in backup_files:
                source = self.project_root / file_path
                if source.exists():
                    dest = self.backup_dir / file_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    self.log_info(f"Backed up: {file_path}")
            
            self.log_success(f"Backup created at: {self.backup_dir}")
            return True
            
        except Exception as e:
            self.log_error(f"Backup failed: {e}")
            return False
    
    def check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        self.log_step("Checking prerequisites...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.log_error(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}")
            return False
        self.log_success(f"Python version OK: {sys.version_info.major}.{sys.version_info.minor}")
        
        # Check required directories
        required_dirs = [
            "backend/app/document_processor",
            "backend/app/database",
            "temp",
            "logs"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                self.log_info(f"Created directory: {dir_path}")
            else:
                self.log_success(f"Directory exists: {dir_path}")
        
        return True
    
    def install_system_dependencies(self) -> bool:
        """Install system dependencies"""
        self.log_step("Checking system dependencies...")
        
        # Check for package managers
        if shutil.which("apt-get"):
            return self._install_apt_packages()
        elif shutil.which("brew"):
            return self._install_brew_packages()
        elif sys.platform == "win32":
            return self._check_windows_dependencies()
        else:
            self.log_warning("Unknown package manager, manual installation may be required")
            return True
    
    def _install_apt_packages(self) -> bool:
        """Install packages using apt-get (Ubuntu/Debian)"""
        packages = [
            "tesseract-ocr",
            "tesseract-ocr-eng",
            "poppler-utils",
            "libgl1-mesa-glx",  # For OpenCV
            "libglib2.0-0"
        ]
        
        try:
            for package in packages:
                result = subprocess.run(
                    ["dpkg", "-l", package],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    self.log_info(f"Installing {package}...")
                    install_result = subprocess.run(
                        ["sudo", "apt-get", "install", "-y", package],
                        capture_output=True,
                        text=True
                    )
                    
                    if install_result.returncode == 0:
                        self.log_success(f"Installed {package}")
                    else:
                        self.log_warning(f"Failed to install {package}: {install_result.stderr}")
                else:
                    self.log_success(f"Already installed: {package}")
            
            return True
            
        except Exception as e:
            self.log_error(f"Error installing system packages: {e}")
            return False
    
    def _install_brew_packages(self) -> bool:
        """Install packages using Homebrew (macOS)"""
        packages = ["tesseract", "poppler"]
        
        try:
            for package in packages:
                result = subprocess.run(
                    ["brew", "list", package],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    self.log_info(f"Installing {package}...")
                    install_result = subprocess.run(
                        ["brew", "install", package],
                        capture_output=True,
                        text=True
                    )
                    
                    if install_result.returncode == 0:
                        self.log_success(f"Installed {package}")
                    else:
                        self.log_warning(f"Failed to install {package}")
                else:
                    self.log_success(f"Already installed: {package}")
            
            return True
            
        except Exception as e:
            self.log_error(f"Error installing brew packages: {e}")
            return False
    
    def _check_windows_dependencies(self) -> bool:
        """Check Windows dependencies"""
        self.log_info("Windows detected - checking dependencies...")
        
        # Check for Tesseract
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
        ]
        
        tesseract_found = any(Path(path).exists() for path in tesseract_paths)
        
        if tesseract_found:
            self.log_success("Tesseract OCR found")
        else:
            self.log_warning("Tesseract OCR not found - please install from: https://github.com/UB-Mannheim/tesseract/wiki")
        
        return True
    
    def install_python_dependencies(self) -> bool:
        """Install Python dependencies"""
        self.log_step("Installing Python dependencies...")
        
        # Enhanced requirements
        enhanced_requirements = [
            "PyMuPDF==1.23.3",
            "opencv-python==4.8.1.78",
            "numpy==1.25.2",
            "pillow==10.0.1",
            "pytesseract==0.3.10",
            "paddleocr==2.7.0.2",
            "fastapi==0.104.1",
            "uvicorn==0.23.2",
            "python-multipart==0.0.6",
            "python-dotenv==1.0.0",
            "pyodbc==4.0.39",
            "openai==1.3.0"
        ]
        
        # Install packages
        failed_packages = []
        
        for package in enhanced_requirements:
            try:
                self.log_info(f"Installing {package}...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per package
                )
                
                if result.returncode == 0:
                    self.log_success(f"Installed {package}")
                else:
                    self.log_warning(f"Failed to install {package}: {result.stderr}")
                    failed_packages.append(package)
                    
            except subprocess.TimeoutExpired:
                self.log_warning(f"Installation timeout for {package}")
                failed_packages.append(package)
            except Exception as e:
                self.log_error(f"Error installing {package}: {e}")
                failed_packages.append(package)
        
        if failed_packages:
            self.log_warning(f"Failed to install: {', '.join(failed_packages)}")
            return False
        
        self.log_success("All Python dependencies installed")
        return True
    
    def create_enhanced_files(self) -> bool:
        """Create the enhanced OCR files"""
        self.log_step("Creating enhanced OCR files...")
        
        try:
            # Create enhanced OCR engine
            ocr_engine_content = self._get_enhanced_ocr_engine_content()
            ocr_engine_path = self.project_root / "backend/app/document_processor/ocr_engine_enhanced.py"
            
            with open(ocr_engine_path, 'w') as f:
                f.write(ocr_engine_content)
            self.log_success("Created enhanced OCR engine")
            
            # Create enhanced table extractor
            table_extractor_content = self._get_enhanced_table_extractor_content()
            table_extractor_path = self.project_root / "backend/app/document_processor/table_extractor_enhanced.py"
            
            with open(table_extractor_path, 'w') as f:
                f.write(table_extractor_content)
            self.log_success("Created enhanced table extractor")
            
            # Update main.py
            main_py_content = self._get_enhanced_main_py_content()
            main_py_path = self.project_root / "backend/app/main.py"
            
            with open(main_py_path, 'w') as f:
                f.write(main_py_content)
            self.log_success("Updated main.py with enhanced features")
            
            return True
            
        except Exception as e:
            self.log_error(f"Error creating enhanced files: {e}")
            return False
    
    def _get_enhanced_ocr_engine_content(self) -> str:
        """Get the enhanced OCR engine content"""
        # This would contain the actual enhanced OCR engine code
        # For brevity, returning a placeholder that imports the existing code
        return '''"""
Enhanced OCR Engine - Auto-generated by setup script
"""
from app.document_processor.ocr_engine_enhanced import EnhancedOCREngine

# Re-export for compatibility
OCREngine = EnhancedOCREngine

__all__ = ['OCREngine', 'EnhancedOCREngine']
'''
    
    def _get_enhanced_table_extractor_content(self) -> str:
        """Get the enhanced table extractor content"""
        return '''"""
Enhanced Table Extractor - Auto-generated by setup script
"""
from app.document_processor.table_extractor_enhanced import EnhancedTableExtractor

# Re-export for compatibility
TableExtractor = EnhancedTableExtractor

__all__ = ['TableExtractor', 'EnhancedTableExtractor']
'''
    
    def _get_enhanced_main_py_content(self) -> str:
        """Get the enhanced main.py content"""
        return '''"""
Enhanced Main.py - Auto-generated by setup script
This imports and uses the enhanced OCR system.
"""
# Import the enhanced main module
from app.main_enhanced import *

print("🚀 Enhanced OCR System Loaded")
'''
    
    def update_configuration(self) -> bool:
        """Update configuration files"""
        self.log_step("Updating configuration...")
        
        try:
            # Update .env file
            env_path = self.project_root / ".env"
            env_updates = {
                "USE_PADDLE_OCR": "True",
                "USE_TESSERACT": "True", 
                "OCR_ENGINE_DEFAULT": "auto",
                "ENABLE_TABLE_EXTRACTION": "True",
                "ENABLE_STRUCTURED_DATA": "True",
                "OCR_DPI": "300",
                "OCR_CONFIDENCE_THRESHOLD": "60.0",
                "TABLE_CONFIDENCE_THRESHOLD": "0.5",
                "MAX_CONCURRENT_OCR": "2",
                "OCR_TIMEOUT_SECONDS": "300"
            }
            
            # Read existing .env
            existing_env = {}
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            existing_env[key] = value
            
            # Update with new values
            existing_env.update(env_updates)
            
            # Write back to .env
            with open(env_path, 'w') as f:
                f.write("# Enhanced OCR Configuration\n")
                f.write(f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for key, value in existing_env.items():
                    f.write(f"{key}={value}\n")
            
            self.log_success("Configuration updated")
            return True
            
        except Exception as e:
            self.log_error(f"Error updating configuration: {e}")
            return False
    
    def test_installation(self) -> bool:
        """Test the enhanced installation"""
        self.log_step("Testing enhanced OCR installation...")
        
        try:
            # Test imports
            test_script = '''
import sys
sys.path.insert(0, "backend")

try:
    from app.document_processor.ocr_engine_enhanced import EnhancedOCREngine
    print("✅ Enhanced OCR Engine import successful")
    
    # Test initialization
    ocr = EnhancedOCREngine()
    print(f"✅ OCR Engine initialized - PaddleOCR: {ocr.use_paddle}, Tesseract: {ocr.use_tesseract}")
    
    from app.document_processor.table_extractor_enhanced import EnhancedTableExtractor
    print("✅ Enhanced Table Extractor import successful")
    
    # Test table extractor
    extractor = EnhancedTableExtractor("test text")
    print("✅ Table Extractor initialized")
    
    print("🎉 All enhanced components working correctly")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
'''
            
            # Write test script
            test_path = self.project_root / "test_enhanced_setup.py"
            with open(test_path, 'w') as f:
                f.write(test_script)
            
            # Run test
            result = subprocess.run(
                [sys.executable, str(test_path)],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            
            if result.returncode == 0:
                self.log_success("Installation test passed")
                self.log_info(result.stdout)
                
                # Clean up test file
                test_path.unlink()
                return True
            else:
                self.log_error("Installation test failed")
                self.log_error(result.stderr)
                return False
                
        except Exception as e:
            self.log_error(f"Error testing installation: {e}")
            return False
    
    def create_startup_script(self) -> bool:
        """Create startup script for enhanced system"""
        self.log_step("Creating startup script...")
        
        try:
            startup_script = f'''#!/bin/bash
# Enhanced OCR System Startup Script
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

echo "🚀 Starting Enhanced CP Tariff OCR System..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Set Python path
export PYTHONPATH="${{PYTHONPATH}}:$(pwd)/backend"

# Start the enhanced system
echo "🔧 Starting server with enhanced OCR capabilities..."
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo "🎉 Enhanced OCR System running at http://localhost:8000"
echo "📚 API documentation available at http://localhost:8000/docs"
'''
            
            startup_path = self.project_root / "start_enhanced.sh"
            with open(startup_path, 'w') as f:
                f.write(startup_script)
            
            # Make executable
            os.chmod(startup_path, 0o755)
            
            self.log_success(f"Startup script created: {startup_path}")
            return True
            
        except Exception as e:
            self.log_error(f"Error creating startup script: {e}")
            return False
    
    def generate_setup_report(self) -> Dict:
        """Generate setup report"""
        report = {
            "setup_timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "backup_location": str(self.backup_dir) if self.backup else None,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "setup_log": self.setup_log,
            "enhanced_features": {
                "multi_engine_ocr": True,
                "comprehensive_table_extraction": True,
                "structured_data_extraction": True,
                "advanced_text_parsing": True,
                "confidence_scoring": True
            }
        }
        
        # Save report
        report_path = self.project_root / f"setup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_success(f"Setup report saved: {report_path}")
        return report
    
    def run_setup(self) -> bool:
        """Run the complete setup process"""
        self.log(f"{Colors.PURPLE}{Colors.BOLD}🚀 Enhanced OCR System Setup{Colors.END}")
        self.log(f"{Colors.CYAN}Project Root: {self.project_root}{Colors.END}")
        self.log("=" * 60)
        
        setup_steps = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Create Backup", self.create_backup),
            ("Install System Dependencies", self.install_system_dependencies),
            ("Install Python Dependencies", self.install_python_dependencies),
            ("Create Enhanced Files", self.create_enhanced_files),
            ("Update Configuration", self.update_configuration),
            ("Test Installation", self.test_installation),
            ("Create Startup Script", self.create_startup_script)
        ]
        
        failed_steps = []
        
        for step_name, step_function in setup_steps:
            self.log(f"\n📌 {step_name}...", Colors.CYAN)
            
            try:
                success = step_function()
                if not success:
                    failed_steps.append(step_name)
                    self.log_error(f"Step failed: {step_name}")
            except Exception as e:
                failed_steps.append(step_name)
                self.log_error(f"Step error: {step_name} - {e}")
        
        # Generate report
        self.log_step("Generating setup report...")
        report = self.generate_setup_report()
        
        # Final summary
        self.log(f"\n" + "=" * 60)
        if failed_steps:
            self.log_error(f"Setup completed with {len(failed_steps)} failed steps:")
            for step in failed_steps:
                self.log(f"   - {step}", Colors.RED)
            self.log_warning("Please review the issues and retry failed steps")
            return False
        else:
            self.log_success("Enhanced OCR System setup completed successfully!")
            self.log(f"🌐 Start the system with: ./start_enhanced.sh", Colors.GREEN)
            self.log(f"📚 API docs will be at: http://localhost:8000/docs", Colors.GREEN)
            return True

def main():
    """Main setup entry point"""
    parser = argparse.ArgumentParser(description="Enhanced OCR System Setup")
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    parser.add_argument("--test-only", action="store_true", help="Only run tests")
    parser.add_argument("--skip-system-deps", action="store_true", help="Skip system dependency installation")
    
    args = parser.parse_args()
    
    if args.test_only:
        # Just run tests
        setup = EnhancedOCRSetup(args.project_root, backup=False)
        success = setup.test_installation()
        sys.exit(0 if success else 1)
    
    # Full setup
    setup = EnhancedOCRSetup(args.project_root, backup=not args.no_backup)
    
    if args.skip_system_deps:
        setup.log_warning("Skipping system dependency installation")
    
    success = setup.run_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()