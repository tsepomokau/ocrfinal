#!/usr/bin/env python3
"""
Installation Verification Script for CP Tariff OCR System
This script checks if all components are properly installed and configured.
"""

import os
import sys
import subprocess
import importlib.util
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class VerificationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.total = 0
        self.issues = []

    def add_pass(self, message: str):
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
        self.passed += 1
        self.total += 1

    def add_fail(self, message: str, issue: str = ""):
        print(f"{Colors.RED}❌ {message}{Colors.END}")
        self.failed += 1
        self.total += 1
        if issue:
            self.issues.append(issue)

    def add_warning(self, message: str, issue: str = ""):
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
        self.warnings += 1
        self.total += 1
        if issue:
            self.issues.append(f"Warning: {issue}")

    def add_info(self, message: str):
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

    def add_header(self, message: str):
        print(f"\n{Colors.CYAN}{Colors.BOLD}📋 {message}{Colors.END}")

class InstallationVerifier:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.result = VerificationResult()

    def check_python_version(self) -> bool:
        """Check Python version compatibility"""
        self.result.add_header("Python Version Check")
        
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major == 3 and version.minor >= 8:
            self.result.add_pass(f"Python version OK: {version_str}")
            return True
        else:
            self.result.add_fail(
                f"Python 3.8+ required. Current: {version_str}",
                "Install Python 3.8 or higher"
            )
            return False

    def check_system_dependencies(self) -> bool:
        """Check system-level dependencies"""
        self.result.add_header("System Dependencies Check")
        
        dependencies = {
            'tesseract': {
                'command': ['tesseract', '--version'],
                'required': False,
                'description': 'Tesseract OCR engine'
            },
            'psql': {
                'command': ['psql', '--version'],
                'required': True,
                'description': 'PostgreSQL client'
            },
            'pdftoppm': {
                'command': ['pdftoppm', '-v'],
                'required': True,
                'description': 'Poppler PDF utilities'
            }
        }
        
        all_good = True
        
        for dep_name, dep_info in dependencies.items():
            try:
                result = subprocess.run(
                    dep_info['command'], 
                    capture_output=True, 
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Extract version info
                    version_output = result.stdout.strip() or result.stderr.strip()
                    first_line = version_output.split('\n')[0]
                    self.result.add_pass(f"{dep_info['description']}: {first_line}")
                else:
                    if dep_info['required']:
                        self.result.add_fail(
                            f"{dep_info['description']} not working properly",
                            f"Install or fix {dep_name}"
                        )
                        all_good = False
                    else:
                        self.result.add_warning(
                            f"{dep_info['description']} not working (optional)",
                            f"Consider installing {dep_name} for better OCR support"
                        )
                        
            except FileNotFoundError:
                if dep_info['required']:
                    self.result.add_fail(
                        f"{dep_info['description']} not found",
                        f"Install {dep_name}"
                    )
                    all_good = False
                else:
                    self.result.add_warning(
                        f"{dep_info['description']} not found (optional)",
                        f"Install {dep_name} for better functionality"
                    )
            except subprocess.TimeoutExpired:
                self.result.add_warning(f"{dep_info['description']} check timed out")
            except Exception as e:
                self.result.add_warning(f"Error checking {dep_name}: {e}")
        
        return all_good

    def check_python_packages(self) -> Tuple[bool, List[str]]:
        """Check Python package dependencies"""
        self.result.add_header("Python Packages Check")
        
        # Read requirements.txt
        requirements_file = Path("backend/requirements.txt")
        if not requirements_file.exists():
            self.result.add_fail(
                "requirements.txt not found",
                "Ensure backend/requirements.txt exists"
            )
            return False, []
        
        # Parse requirements
        required_packages = []
        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before == or >=)
                    package_name = re.split(r'[=><]', line)[0].strip()
                    required_packages.append(package_name)
        
        missing_packages = []
        installed_packages = []
        
        # Package name mappings for import vs pip names
        package_mappings = {
            'opencv-python': 'cv2',
            'pillow': 'PIL',
            'python-multipart': 'multipart',
            'python-dotenv': 'dotenv',
            'psycopg2-binary': 'psycopg2',
            'python-dateutil': 'dateutil',
            'typing-extensions': 'typing_extensions'
        }
        
        for package in required_packages:
            # Determine the import name
            import_name = package_mappings.get(package, package)
            
            try:
                # Try to import the package
                importlib.import_module(import_name)
                self.result.add_pass(f"{package} is installed")
                installed_packages.append(package)
            except ImportError:
                self.result.add_fail(f"{package} not found")
                missing_packages.append(package)
            except Exception as e:
                self.result.add_warning(f"Error checking {package}: {e}")
        
        if missing_packages:
            self.result.add_fail(
                f"{len(missing_packages)} packages missing",
                f"Run: pip install {' '.join(missing_packages)}"
            )
        
        return len(missing_packages) == 0, missing_packages

    def check_file_structure(self) -> Tuple[bool, List[str]]:
        """Check if all required files and directories exist"""
        self.result.add_header("File Structure Check")
        
        required_files = [
            "backend/app/main.py",
            "backend/app/__init__.py",
            "backend/app/document_processor/__init__.py",
            "backend/app/document_processor/enhanced_field_normalizer.py",
            "backend/app/database/__init__.py",
            "backend/app/database/cp_tariff_database.py",
            "backend/config.py",
            "backend/requirements.txt",
            "database/schema.sql",
            ".env.template"
        ]
        
        required_directories = [
            "backend/app/document_processor",
            "backend/app/database",
            "backend/app/models",
            "backend/app/utils",
            "database",
            "temp",
            "logs"
        ]
        
        missing_files = []
        missing_dirs = []
        
        # Check files
        for file_path in required_files:
            if Path(file_path).exists():
                # Check if file is not empty (basic validation)
                if Path(file_path).stat().st_size > 0:
                    self.result.add_pass(f"File: {file_path}")
                else:
                    self.result.add_warning(f"File exists but is empty: {file_path}")
            else:
                self.result.add_fail(f"Missing file: {file_path}")
                missing_files.append(file_path)
        
        # Check directories
        for dir_path in required_directories:
            if Path(dir_path).exists() and Path(dir_path).is_dir():
                self.result.add_pass(f"Directory: {dir_path}")
            else:
                self.result.add_fail(f"Missing directory: {dir_path}")
                missing_dirs.append(dir_path)
        
        # Check for existing code files that should be kept
        existing_files = [
            "backend/app/document_processor/preprocessor.py",
            "backend/app/document_processor/ocr_engine.py",
            "backend/app/document_processor/table_extractor.py",
            "backend/app/models/tariff.py",
            "backend/app/utils/image_utils.py"
        ]
        
        for file_path in existing_files:
            if Path(file_path).exists():
                self.result.add_pass(f"Existing code file: {file_path}")
            else:
                self.result.add_warning(
                    f"Expected existing file not found: {file_path}",
                    f"Copy from your original project: {file_path}"
                )
        
        return len(missing_files) == 0 and len(missing_dirs) == 0, missing_files + missing_dirs

    def check_environment_config(self) -> bool:
        """Check environment configuration"""
        self.result.add_header("Environment Configuration Check")
        
        if not Path('.env').exists():
            if Path('.env.template').exists():
                self.result.add_fail(
                    ".env file not found",
                    "Copy .env.template to .env and configure it"
                )
            else:
                self.result.add_fail(
                    ".env and .env.template files not found",
                    "Create .env file with required configuration"
                )
            return False
        
        self.result.add_pass(".env file exists")
        
        # Load and check environment variables
        env_vars = {}
        try:
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            self.result.add_fail(f"Error reading .env file: {e}")
            return False
        
        # Check required variables
        required_vars = {
            'OPENAI_API_KEY': 'OpenAI API key for AI-enhanced processing',
            'DB_PASSWORD': 'Database password',
            'DB_NAME': 'Database name',
            'DB_USER': 'Database user'
        }
        
        optional_vars = {
            'DB_HOST': 'Database host (default: localhost)',
            'DB_PORT': 'Database port (default: 5432)',
            'DEBUG': 'Debug mode (default: True)',
            'HOST': 'API host (default: 0.0.0.0)',
            'PORT': 'API port (default: 8000)'
        }
        
        config_ok = True
        
        for var, description in required_vars.items():
            if var in env_vars and env_vars[var] and not env_vars[var].startswith('your_'):
                self.result.add_pass(f"{var} is configured")
            else:
                self.result.add_fail(
                    f"{var} not properly configured",
                    f"Set {var} in .env file - {description}"
                )
                config_ok = False
        
        for var, description in optional_vars.items():
            if var in env_vars:
                self.result.add_pass(f"{var} is configured: {env_vars[var]}")
            else:
                self.result.add_info(f"{var} using default - {description}")
        
        return config_ok

    def check_database_connection(self) -> bool:
        """Check database connectivity and schema"""
        self.result.add_header("Database Connection Check")
        
        # Load environment variables
        env_vars = {}
        if Path('.env').exists():
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        db_host = env_vars.get('DB_HOST', 'localhost')
        db_port = env_vars.get('DB_PORT', '5432')
        db_name = env_vars.get('DB_NAME', 'cp_tariff')
        db_user = env_vars.get('DB_USER', 'postgres')
        db_password = env_vars.get('DB_PASSWORD', '')
        
        if not db_password or db_password.startswith('your_'):
            self.result.add_warning(
                "Database password not configured",
                "Set DB_PASSWORD in .env file"
            )
            return False
        
        try:
            # Test basic connection
            cmd = [
                'psql', 
                f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}',
                '-c', 'SELECT 1;'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.result.add_pass(f"Database connection successful ({db_user}@{db_host}:{db_port}/{db_name})")
                
                # Check schema
                schema_cmd = [
                    'psql',
                    f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}',
                    '-t', '-c',
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'tariff_%';"
                ]
                
                schema_result = subprocess.run(
                    schema_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if schema_result.returncode == 0:
                    table_count = int(schema_result.stdout.strip())
                    if table_count >= 4:
                        self.result.add_pass(f"Database schema complete ({table_count} tables)")
                    else:
                        self.result.add_warning(
                            f"Database schema incomplete ({table_count} tables)",
                            "Run: psql -d cp_tariff -f database/schema.sql"
                        )
                else:
                    self.result.add_warning("Could not check database schema")
                
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.result.add_fail(
                    f"Database connection failed: {error_msg}",
                    "Check database credentials and ensure PostgreSQL is running"
                )
                return False
                
        except FileNotFoundError:
            self.result.add_warning(
                "psql command not found",
                "Install PostgreSQL client to test database connection"
            )
            return False
        except subprocess.TimeoutExpired:
            self.result.add_fail(
                "Database connection timed out",
                "Check database server and network connectivity"
            )
            return False
        except Exception as e:
            self.result.add_fail(f"Database check error: {e}")
            return False

    def check_import_compatibility(self) -> bool:
        """Check if main modules can be imported"""
        self.result.add_header("Import Compatibility Check")
        
        # Add backend to Python path
        import sys
        backend_path = str(Path.cwd() / "backend")
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        modules_to_test = [
            ("config", "Configuration module"),
            ("app.main", "Main application module"),
            ("app.document_processor.enhanced_field_normalizer", "Enhanced field normalizer"),
            ("app.database.cp_tariff_database", "Database manager")
        ]
        
        all_imports_ok = True
        
        for module_name, description in modules_to_test:
            try:
                importlib.import_module(module_name)
                self.result.add_pass(f"{description} imports successfully")
            except ImportError as e:
                self.result.add_fail(
                    f"{description} import failed: {e}",
                    f"Check {module_name} and its dependencies"
                )
                all_imports_ok = False
            except Exception as e:
                self.result.add_fail(
                    f"{description} error: {e}",
                    f"Fix issues in {module_name}"
                )
                all_imports_ok = False
        
        return all_imports_ok

    def generate_installation_report(self) -> Dict:
        """Generate a detailed installation report"""
        return {
            "timestamp": subprocess.run(['date'], capture_output=True, text=True).stdout.strip(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
            "working_directory": str(Path.cwd()),
            "results": {
                "total_checks": self.result.total,
                "passed": self.result.passed,
                "failed": self.result.failed,
                "warnings": self.result.warnings,
                "success_rate": (self.result.passed / self.result.total * 100) if self.result.total > 0 else 0
            },
            "issues": self.result.issues
        }

    def run_all_checks(self) -> bool:
        """Run all verification checks"""
        print(f"{Colors.PURPLE}{Colors.BOLD}🔍 CP Tariff OCR Installation Verification{Colors.END}")
        print(f"{Colors.CYAN}{'=' * 50}{Colors.END}")
        
        checks = [
            ("Python Version", self.check_python_version),
            ("System Dependencies", self.check_system_dependencies),
            ("Python Packages", lambda: self.check_python_packages()[0]),
            ("File Structure", lambda: self.check_file_structure()[0]),
            ("Environment Configuration", self.check_environment_config),
            ("Database Connection", self.check_database_connection),
            ("Import Compatibility", self.check_import_compatibility),
        ]
        
        critical_failures = 0
        
        for check_name, check_func in checks:
            try:
                success = check_func()
                if not success and check_name in ["Python Version", "File Structure", "Environment Configuration"]:
                    critical_failures += 1
            except Exception as e:
                self.result.add_fail(f"{check_name} check crashed: {e}")
                critical_failures += 1
        
        # Print summary
        print(f"\n{Colors.CYAN}{Colors.BOLD}📊 Verification Summary{Colors.END}")
        print(f"{Colors.CYAN}{'=' * 30}{Colors.END}")
        
        total = self.result.total
        passed = self.result.passed
        failed = self.result.failed
        warnings = self.result.warnings
        
        print(f"Total checks: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {failed}{Colors.END}")
        print(f"{Colors.YELLOW}Warnings: {warnings}{Colors.END}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if critical_failures == 0 and failed == 0:
            print(f"\n{Colors.GREEN}🎉 Installation verification successful!{Colors.END}")
            print(f"{Colors.GREEN}✅ System is ready to run CP Tariff OCR{Colors.END}")
            print(f"\n{Colors.CYAN}Next steps:{Colors.END}")
            print(f"1. Run: ./launch.sh")
            print(f"2. Test with: python tests/test_api.py")
            print(f"3. Access API docs at: http://localhost:8000/docs")
            return True
        elif critical_failures == 0:
            print(f"\n{Colors.YELLOW}⚠️  Installation has some issues but may still work{Colors.END}")
            print(f"{Colors.YELLOW}Check the warnings above and consider fixing them{Colors.END}")
            return True
        else:
            print(f"\n{Colors.RED}❌ Installation verification failed{Colors.END}")
            print(f"{Colors.RED}Critical issues must be fixed before running the system{Colors.END}")
            
            if self.result.issues:
                print(f"\n{Colors.YELLOW}Issues to fix:{Colors.END}")
                for i, issue in enumerate(self.result.issues, 1):
                    print(f"  {i}. {issue}")
            
            return False

def main():
    """Main verification function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CP Tariff OCR Installation Verifier")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--report", "-r", help="Save detailed report to file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    if args.quiet:
        # Redirect stdout to suppress most output
        import io
        import contextlib
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            verifier = InstallationVerifier(verbose=False)
            success = verifier.run_all_checks()
        
        # Only show final result
        if success:
            print(f"{Colors.GREEN}✅ Verification passed{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Verification failed{Colors.END}")
    else:
        verifier = InstallationVerifier(verbose=args.verbose)
        success = verifier.run_all_checks()
    
    # Generate report if requested
    if args.report:
        report = verifier.generate_installation_report()
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {args.report}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()