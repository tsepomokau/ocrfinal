#!/usr/bin/env python3
"""
CP Tariff OCR API - Automated Deployment Script
File: deploy.py (place in project root)

This script automates the deployment process including:
- Environment validation
- Database setup verification
- Application health checks
- Service startup
"""

import os
import sys
import subprocess
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
import requests

class CPTariffDeploymentManager:
    """Production deployment manager for CP Tariff OCR API"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.deployment_log = []
        self.start_time = datetime.now()
        
    def log_step(self, message: str, success: bool = True):
        """Log deployment step with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "✅" if success else "❌"
        log_entry = f"[{timestamp}] {status} {message}"
        print(log_entry)
        self.deployment_log.append(log_entry)
        
    def check_prerequisites(self) -> bool:
        """Check all deployment prerequisites"""
        self.log_step("Checking deployment prerequisites...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.log_step(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}", False)
            return False
        self.log_step(f"Python version {sys.version_info.major}.{sys.version_info.minor} OK")
        
        # Check required files
        required_files = [
            'config.py',
            'backend/app/main.py',
            'backend/app/database/cp_tariff_database.py',
            'backend/app/document_processor/enhanced_field_normalizer.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.log_step(f"Missing required files: {', '.join(missing_files)}", False)
            return False
        self.log_step("All required files present")
        
        # Check .env file
        env_file = self.project_root / '.env'
        if not env_file.exists():
            self.log_step("Creating .env file from template...")
            self.create_env_template()
        
        return True
    
    def create_env_template(self):
        """Create .env file from template"""
        env_content = """# CP Tariff OCR API Environment Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DB_SERVER=DESKTOP-KL51D0H\\SQLEXPRESS
DB_NAME=cp_tariff

# File Processing
TEMP_FOLDER=./temp
UPLOAD_FOLDER=./uploads
LOG_FOLDER=./logs
MAX_FILE_SIZE=10485760

# OCR Configuration
USE_PADDLE_OCR=False
USE_TESSERACT=True
"""
        
        env_file = self.project_root / '.env'
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        self.log_step("Created .env template - please update with your values")
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        self.log_step("Installing Python dependencies...")
        
        requirements_file = self.project_root / 'requirements.txt'
        
        if requirements_file.exists():
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
                ], check=True, capture_output=True)
                self.log_step("Dependencies installed from requirements.txt")
                return True
            except subprocess.CalledProcessError as e:
                self.log_step(f"Failed to install dependencies: {e}", False)
                return False
        else:
            # Install essential packages manually
            essential_packages = [
                'fastapi==0.104.1',
                'uvicorn==0.23.2',
                'pyodbc==2.9.7',
                'openai==1.3.0',
                'python-dotenv==1.0.0',
                'pillow==10.0.1',
                'python-multipart==0.0.6'
            ]
            
            for package in essential_packages:
                try:
                    subprocess.run([
                        sys.executable, '-m', 'pip', 'install', package
                    ], check=True, capture_output=True)
                    self.log_step(f"Installed {package}")
                except subprocess.CalledProcessError as e:
                    self.log_step(f"Failed to install {package}: {e}", False)
                    return False
            
            return True
    
    def setup_directories(self) -> bool:
        """Create required directories"""
        self.log_step("Setting up directories...")
        
        directories = ['temp', 'uploads', 'logs']
        
        for dir_name in directories:
            dir_path = self.project_root / dir_name
            try:
                dir_path.mkdir(exist_ok=True)
                self.log_step(f"Directory ready: {dir_name}")
            except Exception as e:
                self.log_step(f"Failed to create directory {dir_name}: {e}", False)
                return False
        
        return True
    
    def validate_configuration(self) -> bool:
        """Validate application configuration"""
        self.log_step("Validating configuration...")
        
        try:
            # Add project root to Python path for imports
            sys.path.insert(0, str(self.project_root))
            
            # Import and validate config
            import config
            
            # Check critical settings
            if not hasattr(config, 'OPENAI_API_KEY') or config.OPENAI_API_KEY.startswith('your_'):
                self.log_step("OPENAI_API_KEY needs to be configured", False)
                return False
            
            if not hasattr(config, 'DB_SERVER'):
                self.log_step("DB_SERVER not configured", False)
                return False
            
            self.log_step("Configuration validation passed")
            return True
            
        except ImportError as e:
            self.log_step(f"Configuration import failed: {e}", False)
            return False
        except Exception as e:
            self.log_step(f"Configuration validation failed: {e}", False)
            return False
    
    def test_database_connection(self) -> bool:
        """Test database connectivity"""
        self.log_step("Testing database connection...")
        
        try:
            sys.path.insert(0, str(self.project_root))
            from backend.app.database.cp_tariff_database import CPTariffDatabase
            
            db = CPTariffDatabase()
            if db.test_database_connection():
                self.log_step("Database connection successful")
                
                # Get database statistics
                stats = db.get_database_statistics()
                self.log_step(f"Database stats: {stats.get('total_documents', 0)} documents, "
                             f"{stats.get('total_rates', 0)} rates")
                return True
            else:
                self.log_step("Database connection failed", False)
                return False
                
        except Exception as e:
            self.log_step(f"Database test error: {e}", False)
            return False
    
    def start_application(self) -> bool:
        """Start the FastAPI application"""
        self.log_step("Starting application server...")
        
        try:
            # Start server in background
            main_py = self.project_root / 'backend' / 'app' / 'main.py'
            
            # For production, use uvicorn directly
            cmd = [
                sys.executable, '-m', 'uvicorn',
                'backend.app.main:app',
                '--host', '0.0.0.0',
                '--port', '8000',
                '--reload' if os.getenv('DEBUG', 'True').lower() == 'true' else '--no-reload'
            ]
            
            # Start process
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for startup
            self.log_step("Waiting for server startup...")
            time.sleep(5)
            
            # Check if process is running
            if process.poll() is None:
                self.log_step("Application server started successfully")
                return True
            else:
                stdout, stderr = process.communicate()
                self.log_step(f"Server startup failed: {stderr.decode()}", False)
                return False
                
        except Exception as e:
            self.log_step(f"Failed to start application: {e}", False)
            return False
    
    def run_health_checks(self) -> bool:
        """Run comprehensive health checks"""
        self.log_step("Running health checks...")
        
        # Wait a bit more for full startup
        time.sleep(3)
        
        try:
            # Test root endpoint
            response = requests.get('http://localhost:8000/', timeout=10)
            if response.status_code == 200:
                self.log_step("Root endpoint responding")
            else:
                self.log_step(f"Root endpoint failed: {response.status_code}", False)
                return False
            
            # Test health endpoint
            response = requests.get('http://localhost:8000/health', timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get('status') == 'healthy':
                    self.log_step("Health check passed")
                    
                    # Log health details
                    checks = health_data.get('checks', {})
                    for check_name, status in checks.items():
                        self.log_step(f"  {check_name}: {status}")
                    
                    return True
                else:
                    self.log_step(f"Health check failed: {health_data.get('status')}", False)
                    return False
            else:
                self.log_step(f"Health endpoint failed: {response.status_code}", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_step(f"Health check request failed: {e}", False)
            return False
    
    def run_api_tests(self) -> bool:
        """Run basic API functionality tests"""
        self.log_step("Running API functionality tests...")
        
        try:
            # Test debug info endpoint (if debug mode)
            try:
                response = requests.get('http://localhost:8000/debug/info', timeout=10)
                if response.status_code == 200:
                    debug_info = response.json()
                    self.log_step(f"Debug info: Python {debug_info.get('python_version')}, "
                                 f"Version {debug_info.get('version')}")
                else:
                    self.log_step("Debug endpoint not available (normal in production)")
            except:
                self.log_step("Debug endpoint not accessible (normal)")
            
            # Test statistics endpoint
            try:
                response = requests.get('http://localhost:8000/api/statistics', timeout=10)
                if response.status_code == 200:
                    stats = response.json()
                    self.log_step(f"Statistics endpoint working")
                elif response.status_code == 401:
                    self.log_step("Statistics endpoint requires authentication (normal)")
                else:
                    self.log_step(f"Statistics endpoint failed: {response.status_code}", False)
            except Exception as e:
                self.log_step(f"Statistics test failed: {e}", False)
            
            return True
            
        except Exception as e:
            self.log_step(f"API tests failed: {e}", False)
            return False
    
    def generate_deployment_report(self):
        """Generate deployment summary report"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        report = f"""
# CP Tariff OCR API - Deployment Report
Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
Duration: {duration.total_seconds():.1f} seconds

## Deployment Steps
"""
        
        for log_entry in self.deployment_log:
            report += f"{log_entry}\n"
        
        report += f"""
## Next Steps
1. Update .env file with your actual values:
   - OPENAI_API_KEY=your_actual_api_key
   - DB_SERVER=your_sql_server_instance
   
2. Test file upload functionality:
   curl -X POST -F "file=@test.pdf" http://localhost:8000/api/process-tariff
   
3. Access API documentation:
   http://localhost:8000/docs (if DEBUG=True)
   
4. Monitor logs:
   tail -f logs/app.log
   
5. For production deployment:
   - Set DEBUG=False in .env
   - Enable API key authentication
   - Configure proper CORS origins
   - Use a reverse proxy (nginx)
   - Set up SSL certificates

## Support
- Health check: http://localhost:8000/health
- API root: http://localhost:8000/
- Logs directory: {self.project_root}/logs/
"""
        
        # Save report
        report_file = self.project_root / f'deployment_report_{end_time.strftime("%Y%m%d_%H%M%S")}.md'
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n📋 Deployment report saved to: {report_file}")
        return report
    
    def deploy(self):
        """Execute full deployment process"""
        print("🚀 CP Tariff OCR API - Starting Deployment")
        print("=" * 50)
        
        deployment_steps = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Install Dependencies", self.install_dependencies),
            ("Setup Directories", self.setup_directories),
            ("Validate Configuration", self.validate_configuration),
            ("Test Database", self.test_database_connection),
            ("Start Application", self.start_application),
            ("Health Checks", self.run_health_checks),
            ("API Tests", self.run_api_tests)
        ]
        
        failed_steps = []
        
        for step_name, step_function in deployment_steps:
            print(f"\n📌 {step_name}...")
            try:
                success = step_function()
                if not success:
                    failed_steps.append(step_name)
                    self.log_step(f"Step failed: {step_name}", False)
            except Exception as e:
                failed_steps.append(step_name)
                self.log_step(f"Step error: {step_name} - {e}", False)
        
        # Generate report
        print(f"\n📊 Generating deployment report...")
        self.generate_deployment_report()
        
        # Final summary
        print(f"\n" + "=" * 50)
        if failed_steps:
            print(f"❌ Deployment completed with {len(failed_steps)} failed steps:")
            for step in failed_steps:
                print(f"   - {step}")
            print(f"\n🔧 Please review the deployment report and fix the issues.")
            return False
        else:
            print(f"✅ Deployment completed successfully!")
            print(f"🌐 API is now running at: http://localhost:8000")
            print(f"📚 API docs available at: http://localhost:8000/docs")
            return True

def main():
    """Main deployment entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'check':
            # Just run prerequisite checks
            deployer = CPTariffDeploymentManager()
            deployer.check_prerequisites()
        elif command == 'test':
            # Just run tests
            deployer = CPTariffDeploymentManager()
            deployer.run_health_checks()
            deployer.run_api_tests()
        elif command == 'deploy':
            # Full deployment
            deployer = CPTariffDeploymentManager()
            success = deployer.deploy()
            sys.exit(0 if success else 1)
        else:
            print("Usage: python deploy.py [check|test|deploy]")
            sys.exit(1)
    else:
        # Default: full deployment
        deployer = CPTariffDeploymentManager()
        success = deployer.deploy()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()