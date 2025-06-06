-- CP Tariff Database Schema for SQL Server
IF OBJECT_ID('tariff_rates', 'U') IS NOT NULL DROP TABLE tariff_rates;
IF OBJECT_ID('tariff_notes', 'U') IS NOT NULL DROP TABLE tariff_notes;
IF OBJECT_ID('tariff_commodities', 'U') IS NOT NULL DROP TABLE tariff_commodities;
IF OBJECT_ID('tariff_documents', 'U') IS NOT NULL DROP TABLE tariff_documents;

-- Main tariff documents table
CREATE TABLE tariff_documents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    item_number NVARCHAR(20) NOT NULL,
    revision INT,
    cprs_number NVARCHAR(20),
    issue_date DATE,
    effective_date DATE,
    expiration_date DATE,
    pdf_name NVARCHAR(255),
    pdf_path NVARCHAR(500),
    upload_timestamp DATETIME2 DEFAULT GETDATE(),
    origin_info NTEXT,
    destination_info NTEXT,
    currency NVARCHAR(10) DEFAULT 'USD',
    change_description NTEXT,
    status NVARCHAR(50) DEFAULT 'ACTIVE',
    raw_ocr_text NTEXT,
    processed_json NTEXT,
    CONSTRAINT UQ_item_revision UNIQUE(item_number, revision)
);

-- Commodities table
CREATE TABLE tariff_commodities (
    id INT IDENTITY(1,1) PRIMARY KEY,
    tariff_document_id INT NOT NULL,
    commodity_name NVARCHAR(255) NOT NULL,
    stcc_code NVARCHAR(20),
    description NTEXT,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT FK_commodities_document FOREIGN KEY (tariff_document_id) 
        REFERENCES tariff_documents(id) ON DELETE CASCADE
);

-- Rates table
CREATE TABLE tariff_rates (
    id INT IDENTITY(1,1) PRIMARY KEY,
    tariff_document_id INT NOT NULL,
    origin NVARCHAR(255),
    destination NVARCHAR(255),
    origin_state NVARCHAR(10),
    destination_state NVARCHAR(10),
    rate_category NVARCHAR(10),
    rate_amount DECIMAL(10,2),
    currency NVARCHAR(10) DEFAULT 'USD',
    train_type NVARCHAR(50),
    car_capacity_type NVARCHAR(20),
    route_code NVARCHAR(20),
    route_description NTEXT,
    additional_provisions NTEXT,
    provision_codes NVARCHAR(MAX),
    equipment_type NVARCHAR(100),
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT FK_rates_document FOREIGN KEY (tariff_document_id) 
        REFERENCES tariff_documents(id) ON DELETE CASCADE
);

-- Notes table
CREATE TABLE tariff_notes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    tariff_document_id INT NOT NULL,
    note_type NVARCHAR(50) NOT NULL,
    note_code NVARCHAR(10),
    note_text NTEXT NOT NULL,
    sort_order INT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT FK_notes_document FOREIGN KEY (tariff_document_id) 
        REFERENCES tariff_documents(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IX_documents_item ON tariff_documents(item_number);
CREATE INDEX IX_rates_origin_dest ON tariff_rates(origin, destination);
CREATE INDEX IX_commodities_stcc ON tariff_commodities(stcc_code);

PRINT 'CP Tariff database schema created successfully for SQL Server!';