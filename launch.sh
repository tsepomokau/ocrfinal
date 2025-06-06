#!/bin/bash

# CP Tariff OCR System Launch Script
# This script sets up the environment and starts the application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

print_header() {
    echo ""
    print_color $PURPLE "=================================================="
    print_color $PURPLE "  CP Tariff OCR System"
    print_color $PURPLE "  AI-Powered Railway Tariff Processing"
    print_color $PURPLE "=================================================="
    echo ""
}

print_step() {
    print_color $CYAN "🔧 $1"
}

print_success() {
    print_color $GREEN "✅ $1"
}

print_error() {
    print_color $RED "❌ $1"
}

print_warning() {
    print_color $YELLOW "⚠️  $1"
}

print_info() {
    print_color $BLUE "ℹ️  $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.8"
        
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            print_success "Python version OK: $PYTHON_VERSION"
            return 0
        else
            print_error "Python 3.8+ required. Current: $PYTHON_VERSION"
            return 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.8 or higher."
        return 1
    fi
}

# Function to setup virtual environment
setup_virtualenv() {
    print_step "Setting up Python virtual environment..."
    
    if [ ! -d ".venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv .venv
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source .venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip > /dev/null 2>&1
    
    print_success "Virtual environment ready"
}

# Function to install dependencies
install_dependencies() {
    print_step "Installing Python dependencies..."
    
    if [ ! -f ".venv/installed" ] || [ "backend/requirements.txt" -nt ".venv/installed" ]; then
        print_info "Installing packages from requirements.txt..."
        
        # Install with progress
        pip install -r backend/requirements.txt
        
        # Mark as installed
        touch .venv/installed
        print_success "Dependencies installed successfully"
    else
        print_info "Dependencies already up to date"
    fi
}

# Function to check system dependencies
check_system_dependencies() {
    print_step "Checking system dependencies..."
    
    local missing_deps=()
    
    # Check for Tesseract
    if command_exists tesseract; then
        TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n1)
        print_success "Tesseract found: $TESSERACT_VERSION"
    else
        print_warning "Tesseract OCR not found (optional but recommended)"
        missing_deps+=("tesseract-ocr")
    fi
    
    # Check for PostgreSQL client
    if command_exists psql; then
        PSQL_VERSION=$(psql --version | head -n1)
        print_success "PostgreSQL client found: $PSQL_VERSION"
    else
        print_warning "PostgreSQL client not found"
        missing_deps+=("postgresql-client")
    fi
    
    # Check for poppler (PDF processing)
    if command_exists pdftoppm; then
        print_success "Poppler utils found"
    else
        print_warning "Poppler utils not found (needed for PDF processing)"
        missing_deps+=("poppler-utils")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_warning "Missing system dependencies: ${missing_deps[*]}"
        print_info "Install with: sudo apt-get install ${missing_deps[*]}"
        print_info "Or on macOS: brew install ${missing_deps[*]//postgresql-client/postgresql} ${missing_deps[*]//poppler-utils/poppler}"
    fi
}

# Function to check configuration
check_configuration() {
    print_step "Checking configuration..."
    
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_info "Creating .env from template..."
        
        if [ -f ".env.template" ]; then
            cp .env.template .env
            print_warning "Please edit .env file with your actual configuration:"
            print_info "  - Set OPENAI_API_KEY to your OpenAI API key"
            print_info "  - Set DB_PASSWORD to your database password"
            print_info "  - Adjust other settings as needed"
            
            # Ask if user wants to edit now
            read -p "Would you like to edit .env now? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ${EDITOR:-nano} .env
            fi
        else
            print_error ".env.template not found. Please create .env manually."
            return 1
        fi
    fi
    
    # Check for required environment variables
    source .env 2>/dev/null || true
    
    local config_issues=()
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        config_issues+=("OPENAI_API_KEY not configured")
    fi
    
    if [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" = "your_db_password_here" ]; then
        config_issues+=("DB_PASSWORD not configured")
    fi
    
    if [ ${#config_issues[@]} -gt 0 ]; then
        print_warning "Configuration issues:"
        for issue in "${config_issues[@]}"; do
            print_warning "  - $issue"
        done
        print_info "Please edit .env file to fix these issues"
        
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    else
        print_success "Configuration looks good"
    fi
}

# Function to check database connection
check_database() {
    print_step "Checking database connection..."
    
    # Load environment variables
    source .env 2>/dev/null || true
    
    # Set defaults
    DB_HOST=${DB_HOST:-localhost}
    DB_PORT=${DB_PORT:-5432}
    DB_NAME=${DB_NAME:-cp_tariff}
    DB_USER=${DB_USER:-postgres}
    
    if command_exists psql; then
        # Test database connection
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
            print_success "Database connection successful"
            
            # Check if tables exist
            TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'tariff_%';" 2>/dev/null | tr -d ' ')
            
            if [ "$TABLE_COUNT" -ge 4 ]; then
                print_success "Database schema is ready ($TABLE_COUNT tables found)"
            else
                print_warning "Database schema may not be complete ($TABLE_COUNT tables found)"
                print_info "You may need to run: psql -d $DB_NAME -f database/schema.sql"
            fi
        else
            print_warning "Cannot connect to database"
            print_info "Database details: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
            print_info "Please ensure PostgreSQL is running and credentials are correct"
        fi
    else
        print_warning "Cannot check database (psql not available)"
    fi
}

# Function to setup directories
setup_directories() {
    print_step "Setting up directories..."
    
    local dirs=("temp" "logs" "uploads" "tests/sample_documents")
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_info "Created directory: $dir"
        fi
    done
    
    print_success "Directories ready"
}

# Function to set Python path
setup_python_path() {
    print_step "Setting up Python path..."
    
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
    print_success "Python path configured"
}

# Function to start the application
start_application() {
    print_step "Starting CP Tariff OCR API..."
    
    # Final check
    if [ ! -f "backend/app/main.py" ]; then
        print_error "main.py not found in backend/app/"
        print_info "Please ensure all files are in the correct locations"
        return 1
    fi
    
    # Load environment variables
    source .env 2>/dev/null || true
    
    # Set defaults
    HOST=${HOST:-0.0.0.0}
    PORT=${PORT:-8000}
    
    print_success "Configuration loaded"
    print_info "Starting server on http://$HOST:$PORT"
    print_info "API documentation will be available at http://$HOST:$PORT/docs"
    print_info ""
    print_color $GREEN "🚀 Starting application..."
    print_info "Press Ctrl+C to stop the server"
    print_info ""
    
    # Change to backend directory and start
    cd backend
    
    # Start with uvicorn
    if command_exists uvicorn; then
        uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
    else
        print_error "uvicorn not found. Installing..."
        pip install uvicorn
        uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
    fi
}

# Function to run pre-start tests
run_pre_tests() {
    print_step "Running pre-start verification..."
    
    if [ -f "verify_installation.py" ]; then
        python verify_installation.py
        if [ $? -eq 0 ]; then
            print_success "Pre-start verification passed"
        else
            print_warning "Pre-start verification found issues"
            read -p "Continue anyway? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                return 1
            fi
        fi
    else
        print_info "Verification script not found, skipping pre-tests"
    fi
}

# Function to show help
show_help() {
    echo "CP Tariff OCR Launch Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --check-only        Only run checks, don't start the application"
    echo "  --skip-deps         Skip dependency installation"
    echo "  --skip-db-check     Skip database connection check"
    echo "  --skip-tests        Skip pre-start verification tests"
    echo "  --dev               Development mode (debug enabled)"
    echo "  --port PORT         Specify port (default: 8000)"
    echo "  --host HOST         Specify host (default: 0.0.0.0)"
    echo ""
    echo "Examples:"
    echo "  $0                  # Normal startup"
    echo "  $0 --check-only     # Just run system checks"
    echo "  $0 --dev --port 8080  # Development mode on port 8080"
}

# Main execution
main() {
    # Parse command line arguments
    CHECK_ONLY=false
    SKIP_DEPS=false
    SKIP_DB_CHECK=false
    SKIP_TESTS=false
    DEV_MODE=false
    CUSTOM_PORT=""
    CUSTOM_HOST=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0