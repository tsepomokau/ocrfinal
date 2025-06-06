import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ========================================
# API Configuration
# ========================================
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# ========================================
# OpenAI API Configuration
# ========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))

# ========================================
# Database Configuration
# ========================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "cp_tariff")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# Database connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Connection pool settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

# ========================================
# File Processing Configuration
# ========================================
TEMP_FOLDER = os.getenv("TEMP_FOLDER", "./temp")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./uploads")
LOG_FOLDER = os.getenv("LOG_FOLDER", "./logs")

# Create directories if they don't exist
for folder in [TEMP_FOLDER, UPLOAD_FOLDER, LOG_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# File size limits
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10 MB default
MAX_PAGES_PER_DOCUMENT = int(os.getenv("MAX_PAGES_PER_DOCUMENT", "50"))

# Allowed file types
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "tif", "bmp"}

# File retention settings
TEMP_FILE_RETENTION_HOURS = int(os.getenv("TEMP_FILE_RETENTION_HOURS", "24"))
PROCESSED_FILE_RETENTION_DAYS = int(os.getenv("PROCESSED_FILE_RETENTION_DAYS", "30"))

# ========================================
# OCR Configuration
# ========================================
DEFAULT_OCR_LANGUAGE = os.getenv("DEFAULT_OCR_LANGUAGE", "eng")
OCR_DPI = int(os.getenv("OCR_DPI", "300"))
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "60.0"))

# OCR Engine Settings
USE_PADDLE_OCR = os.getenv("USE_PADDLE_OCR", "True").lower() in ("true", "1", "t")
USE_TESSERACT = os.getenv("USE_TESSERACT", "True").lower() in ("true", "1", "t")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")  # Path to tesseract executable

# PaddleOCR specific settings
PADDLE_USE_ANGLE_CLS = os.getenv("PADDLE_USE_ANGLE_CLS", "True").lower() in ("true", "1", "t")
PADDLE_USE_GPU = os.getenv("PADDLE_USE_GPU", "False").lower() in ("true", "1", "t")
PADDLE_LANG = os.getenv("PADDLE_LANG", "en")

# ========================================
# AI Enhancement Configuration
# ========================================
ENABLE_AI_ENHANCEMENT = os.getenv("ENABLE_AI_ENHANCEMENT", "True").lower() in ("true", "1", "t")
AI_FALLBACK_TO_RULES = os.getenv("AI_FALLBACK_TO_RULES", "True").lower() in ("true", "1", "t")
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))
AI_RETRY_DELAY = float(os.getenv("AI_RETRY_DELAY", "1.0"))

# ========================================
# Rate Extraction Patterns
# ========================================
RATE_PATTERNS = {
    'currency_symbols': ['$', 'CAD', 'USD', 'C$', 'US$'],
    'rate_categories': ['A', 'B', 'C', 'D', 'E'],
    'train_types': [
        'SINGLE CARS', 'SINGLE CAR', 
        '25 CARS', '25 CAR',
        'UNIT TRAIN', 'UNIT',
        'SPLIT TRAIN', 'SPLIT',
        '8500\' UNIT TRAIN', '8500 UNIT TRAIN',
        '110 CARS', '134 CARS'
    ],
    'capacity_types': ['LOW CAP', 'HIGH CAP', 'LOW', 'HIGH'],
    'provision_markers': ['*', '1', '2', '3', '4', '5', '6', '7', '8', '9'],
    'route_patterns': [
        r'ROUTE:\s*(\d{4})',
        r'(\d{4})\s*-\s*([A-Z\s]+)',
        r'CPRS\s+([A-Z0-9\s]+)'
    ]
}

# ========================================
# Location and Geography Configuration
# ========================================
# State/Province mappings for location parsing
STATE_PROVINCE_CODES = {
    # Canadian Provinces and Territories
    'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba', 
    'NB': 'New Brunswick', 'NL': 'Newfoundland and Labrador', 'NS': 'Nova Scotia',
    'NT': 'Northwest Territories', 'NU': 'Nunavut', 'ON': 'Ontario', 
    'PE': 'Prince Edward Island', 'QC': 'Quebec', 'SK': 'Saskatchewan', 'YT': 'Yukon',
    'PQ': 'Quebec',  # Alternative code for Quebec
    
    # US States
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina',
    'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee',
    'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
    'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
}

# Major railway hubs and cities for context
MAJOR_RAILWAY_HUBS = [
    'CALGARY', 'VANCOUVER', 'TORONTO', 'MONTREAL', 'WINNIPEG', 'THUNDER BAY',
    'CHICAGO', 'MINNEAPOLIS', 'KANSAS CITY', 'ST PAUL', 'DETROIT', 'BUFFALO'
]

# ========================================
# STCC Code Reference
# ========================================
# Common STCC codes found in CP tariffs
COMMON_STCC_CODES = {
    # Grains and Agricultural Products
    '01 137': 'WHEAT',
    '01 135': 'RYE', 
    '01 144': 'SOYBEANS',
    '01 139 30': 'GRAIN SCREENINGS, UNGROUND',
    '01 139 90': 'GRAIN, NEC',
    
    # Feed and Grain Products
    '20 823 30': 'GRAIN SPENT',
    '20 859 45': 'MASH GRAIN SPENT',
    '20 859 40': 'DISTILLERS MASH SPENT',
    '20 342 32': 'PULSE/SPECIAL CROPS FRACTIONS: PROTEIN',
    '20 342 34': 'PEA FLOUR OR MEAL, DEHYDRATED, DRIED, EVAPORATED OR PARTIALLY COOKED',
    
    # Mill Products
    '20 412 08': 'SHORTS, WHEAT, PELLETIZED',
    '20 412 10': 'SHORTS, WHEAT, NON-PELLETIZED',
    '20 412 18': 'BRAN, WHEAT, PELLETIZED',
    '20 412 20': 'WHEAT BRAN, OTHER THAN PELLETIZED',
    '20 412 88': 'WHEAT GRAIN MILL FEED, PELLETIZED',
    '20 412 90': 'MILL FEED, GRAIN, EXCEPT WHEAT',
    
    # Other Commodities
    '20 413 15': 'CORN MEAL',
    '20 413 20': 'CORN FLOUR',
    '20 416 10': 'OAT FLOUR',
    '20 416 15': 'OAT MEAL',
    '20 418 15': 'RAPESEED SCREENINGS',
    '20 419 65': 'OAT BRAN',
    '20 419 66': 'OATS, CRUSHED OR GROUND'
}

# ========================================
# Processing Configuration
# ========================================
# Concurrent processing settings
MAX_CONCURRENT_UPLOADS = int(os.getenv("MAX_CONCURRENT_UPLOADS", "5"))
PROCESSING_TIMEOUT_SECONDS = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "300"))  # 5 minutes

# Cache settings
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "True").lower() in ("true", "1", "t")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour

# Background task settings
ENABLE_BACKGROUND_PROCESSING = os.getenv("ENABLE_BACKGROUND_PROCESSING", "True").lower() in ("true", "1", "t")
BACKGROUND_TASK_TIMEOUT = int(os.getenv("BACKGROUND_TASK_TIMEOUT", "600"))  # 10 minutes

# ========================================
# API Rate Limiting
# ========================================
ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "False").lower() in ("true", "1", "t")
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
RATE_LIMIT_BURST_SIZE = int(os.getenv("RATE_LIMIT_BURST_SIZE", "10"))

# ========================================
# Security Configuration
# ========================================
# CORS settings
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() in ("true", "1", "t")

# API Key settings (if authentication is enabled)
ENABLE_API_KEY_AUTH = os.getenv("ENABLE_API_KEY_AUTH", "False").lower() in ("true", "1", "t")
API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")
VALID_API_KEYS = os.getenv("VALID_API_KEYS", "").split(",") if os.getenv("VALID_API_KEYS") else []

# ========================================
# Logging Configuration
# ========================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_DATE_FORMAT = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
LOG_FILE_MAX_SIZE = int(os.getenv("LOG_FILE_MAX_SIZE", str(10 * 1024 * 1024)))  # 10 MB
LOG_FILE_BACKUP_COUNT = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': LOG_FORMAT,
            'datefmt': LOG_DATE_FORMAT
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
            'datefmt': LOG_DATE_FORMAT
        }
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'detailed',
            'filename': os.path.join(LOG_FOLDER, 'cp_tariff.log'),
            'maxBytes': LOG_FILE_MAX_SIZE,
            'backupCount': LOG_FILE_BACKUP_COUNT
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'detailed',
            'filename': os.path.join(LOG_FOLDER, 'cp_tariff_errors.log'),
            'maxBytes': LOG_FILE_MAX_SIZE,
            'backupCount': LOG_FILE_BACKUP_COUNT
        }
    },
    'root': {
        'level': LOG_LEVEL,
        'handlers': ['console', 'file', 'error_file']
    },
    'loggers': {
        'cp_tariff': {
            'level': LOG_LEVEL,
            'handlers': ['console', 'file'],
            'propagate': False
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        }
    }
}

# ========================================
# Performance Monitoring
# ========================================
ENABLE_PERFORMANCE_MONITORING = os.getenv("ENABLE_PERFORMANCE_MONITORING", "True").lower() in ("true", "1", "t")
PERFORMANCE_LOG_SLOW_REQUESTS = os.getenv("PERFORMANCE_LOG_SLOW_REQUESTS", "True").lower() in ("true", "1", "t")
SLOW_REQUEST_THRESHOLD_SECONDS = float(os.getenv("SLOW_REQUEST_THRESHOLD_SECONDS", "5.0"))

# Memory usage limits
MAX_MEMORY_USAGE_MB = int(os.getenv("MAX_MEMORY_USAGE_MB", "1024"))  # 1 GB
MEMORY_WARNING_THRESHOLD_MB = int(os.getenv("MEMORY_WARNING_THRESHOLD_MB", "768"))  # 768 MB

# ========================================
# Development and Testing
# ========================================
ENABLE_DEBUG_ENDPOINTS = os.getenv("ENABLE_DEBUG_ENDPOINTS", "False").lower() in ("true", "1", "t")
SAVE_INTERMEDIATE_RESULTS = os.getenv("SAVE_INTERMEDIATE_RESULTS", "False").lower() in ("true", "1", "t")
MOCK_AI_RESPONSES = os.getenv("MOCK_AI_RESPONSES", "False").lower() in ("true", "1", "t")

# Test data settings
TEST_DATA_FOLDER = os.getenv("TEST_DATA_FOLDER", "./tests/sample_documents")
ENABLE_TEST_ENDPOINTS = os.getenv("ENABLE_TEST_ENDPOINTS", "False").lower() in ("true", "1", "t")

# ========================================
# Version and Build Information
# ========================================
VERSION = "2.0.0"
BUILD_DATE = os.getenv("BUILD_DATE", "2024-01-01")
GIT_COMMIT = os.getenv("GIT_COMMIT", "unknown")

# ========================================
# Health Check Configuration
# ========================================
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "30"))
DATABASE_HEALTH_CHECK_QUERY = "SELECT 1"
OPENAI_HEALTH_CHECK_ENABLED = os.getenv("OPENAI_HEALTH_CHECK_ENABLED", "True").lower() in ("true", "1", "t")

# ========================================
# Validation Functions
# ========================================
def validate_config():
    """Validate configuration settings."""
    errors = []
    
    # Check required environment variables
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("your_"):
        errors.append("OPENAI_API_KEY is not properly configured")
    
    if not DB_PASSWORD or DB_PASSWORD == "password":
        errors.append("DB_PASSWORD should be changed from default")
    
    # Check file paths
    for folder in [TEMP_FOLDER, UPLOAD_FOLDER, LOG_FOLDER]:
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create directory {folder}: {e}")
    
    # Check numeric limits
    if MAX_FILE_SIZE < 1024:  # Less than 1KB
        errors.append("MAX_FILE_SIZE seems too small")
    
    if OCR_DPI < 72 or OCR_DPI > 600:
        errors.append("OCR_DPI should be between 72 and 600")
    
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")

# Validate configuration on import (only in non-test environments)
if not os.getenv("TESTING", "").lower() in ("true", "1", "t"):
    try:
        validate_config()
    except ValueError as e:
        print(f"⚠️  Configuration Warning: {e}")

# ========================================
# Export commonly used settings
# ========================================
__all__ = [
    'DEBUG', 'HOST', 'PORT',
    'OPENAI_API_KEY', 'OPENAI_MODEL', 'OPENAI_TEMPERATURE',
    'DATABASE_URL', 'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER',
    'TEMP_FOLDER', 'UPLOAD_FOLDER', 'LOG_FOLDER',
    'MAX_FILE_SIZE', 'ALLOWED_EXTENSIONS',
    'USE_PADDLE_OCR', 'USE_TESSERACT', 'OCR_DPI',
    'ENABLE_AI_ENHANCEMENT', 'AI_FALLBACK_TO_RULES',
    'RATE_PATTERNS', 'STATE_PROVINCE_CODES', 'COMMON_STCC_CODES',
    'LOGGING_CONFIG', 'VERSION'
]