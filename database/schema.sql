-- CP Tariff Database Schema
-- PostgreSQL database schema for CP Railway tariff document processing
-- Version: 2.0.0
-- Created: 2024

-- Drop existing tables if they exist (for development/updates)
DROP TABLE IF EXISTS tariff_rates CASCADE;
DROP TABLE IF EXISTS tariff_notes CASCADE;
DROP TABLE IF EXISTS tariff_commodities CASCADE;
DROP TABLE IF EXISTS tariff_documents CASCADE;

-- Drop existing views
DROP VIEW IF EXISTS active_tariffs;
DROP VIEW IF EXISTS tariff_summary;

-- ========================================
-- Main tariff documents table
-- ========================================
CREATE TABLE tariff_documents (
    id SERIAL PRIMARY KEY,
    
    -- Document identification
    item_number VARCHAR(20) NOT NULL,
    revision INTEGER,
    cprs_number VARCHAR(20),
    
    -- Important dates
    issue_date DATE,
    effective_date DATE,
    expiration_date DATE,
    
    -- File information
    pdf_name VARCHAR(255),
    pdf_path VARCHAR(500),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Basic document info
    origin_info TEXT,
    destination_info TEXT,
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Document status and changes
    change_description TEXT,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    
    -- Raw and processed data
    raw_ocr_text TEXT,
    processed_json JSONB,
    
    -- Processing metadata
    processing_time_seconds INTEGER,
    ocr_confidence_score DECIMAL(5,2),
    ai_processing_used BOOLEAN DEFAULT FALSE,
    
    -- Constraints
    UNIQUE(item_number, revision),
    CHECK (revision >= 0),
    CHECK (currency IN ('USD', 'CAD')),
    CHECK (status IN ('ACTIVE', 'EXPIRED', 'SUPERSEDED', 'DRAFT'))
);

-- Add comments to the main table
COMMENT ON TABLE tariff_documents IS 'Main table storing CP Railway tariff document metadata and content';
COMMENT ON COLUMN tariff_documents.item_number IS 'CP Tariff item number (e.g., 70001, 75603)';
COMMENT ON COLUMN tariff_documents.revision IS 'Document revision number';
COMMENT ON COLUMN tariff_documents.cprs_number IS 'CPRS reference number';
COMMENT ON COLUMN tariff_documents.processed_json IS 'Complete processed data in JSON format';

-- ========================================
-- Commodities table
-- ========================================
CREATE TABLE tariff_commodities (
    id SERIAL PRIMARY KEY,
    tariff_document_id INTEGER NOT NULL REFERENCES tariff_documents(id) ON DELETE CASCADE,
    
    -- Commodity information
    commodity_name VARCHAR(255) NOT NULL,
    stcc_code VARCHAR(20),
    description TEXT,
    
    -- Additional commodity details
    commodity_type VARCHAR(50), -- 'GRAIN', 'FEED', 'SPECIALTY', etc.
    unit_of_measure VARCHAR(20), -- 'CAR', 'TON', etc.
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (LENGTH(commodity_name) > 0)
);

COMMENT ON TABLE tariff_commodities IS 'Commodities covered by each tariff document';
COMMENT ON COLUMN tariff_commodities.stcc_code IS 'Standard Transportation Commodity Code';

-- ========================================
-- Tariff rates table - handles all rate structures
-- ========================================
CREATE TABLE tariff_rates (
    id SERIAL PRIMARY KEY,
    tariff_document_id INTEGER NOT NULL REFERENCES tariff_documents(id) ON DELETE CASCADE,
    
    -- Origin and destination
    origin VARCHAR(255),
    destination VARCHAR(255),
    origin_state VARCHAR(10),
    destination_state VARCHAR(10),
    origin_country VARCHAR(10) DEFAULT 'CA',
    destination_country VARCHAR(10) DEFAULT 'US',
    
    -- Rate information
    rate_category VARCHAR(10), -- 'A', 'B', 'C', 'D', etc.
    rate_amount DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Train and car specifications
    train_type VARCHAR(50), -- 'SINGLE_CARS', '25_CARS', 'SPLIT_TRAIN', 'UNIT_TRAIN', '8500_UNIT_TRAIN'
    car_capacity_type VARCHAR(20), -- 'LOW_CAP', 'HIGH_CAP'
    car_capacity_threshold INTEGER DEFAULT 4800,
    minimum_cars INTEGER,
    maximum_cars INTEGER,
    
    -- Route information
    route_code VARCHAR(20),
    route_description TEXT,
    
    -- Additional provisions and notes
    additional_provisions TEXT,
    provision_codes TEXT[], -- Array of provision codes like '1', '2', '*'
    
    -- Equipment specifications
    equipment_type VARCHAR(100),
    equipment_notes TEXT,
    mileage_allowance_applicable BOOLEAN DEFAULT TRUE,
    
    -- Rate validity
    rate_effective_date DATE,
    rate_expiration_date DATE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (rate_amount >= 0),
    CHECK (currency IN ('USD', 'CAD')),
    CHECK (car_capacity_threshold > 0),
    CHECK (minimum_cars IS NULL OR minimum_cars >= 1),
    CHECK (maximum_cars IS NULL OR maximum_cars >= minimum_cars)
);

COMMENT ON TABLE tariff_rates IS 'Individual shipping rates for origin-destination pairs';
COMMENT ON COLUMN tariff_rates.train_type IS 'Type of train service (single cars, unit train, etc.)';
COMMENT ON COLUMN tariff_rates.provision_codes IS 'Array of provision reference codes';

-- ========================================
-- Notes and provisions table
-- ========================================
CREATE TABLE tariff_notes (
    id SERIAL PRIMARY KEY,
    tariff_document_id INTEGER NOT NULL REFERENCES tariff_documents(id) ON DELETE CASCADE,
    
    -- Note classification
    note_type VARCHAR(50) NOT NULL, -- 'EQUIPMENT', 'ROUTING', 'RATE', 'PROVISION', 'GENERAL', 'ASTERISK'
    note_code VARCHAR(10), -- '1', '2', '*', 'A', 'B', etc.
    note_text TEXT NOT NULL,
    
    -- Note organization
    section VARCHAR(50), -- 'HEADER', 'RATES', 'FOOTER', 'EQUIPMENT'
    sort_order INTEGER DEFAULT 0,
    
    -- Note metadata
    is_critical BOOLEAN DEFAULT FALSE,
    applies_to_all_rates BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (LENGTH(note_text) > 0),
    CHECK (note_type IN ('EQUIPMENT', 'ROUTING', 'RATE', 'PROVISION', 'GENERAL', 'ASTERISK', 'RESTRICTION'))
);

COMMENT ON TABLE tariff_notes IS 'All notes, provisions, and restrictions from tariff documents';
COMMENT ON COLUMN tariff_notes.note_type IS 'Category of note for organization and filtering';
COMMENT ON COLUMN tariff_notes.is_critical IS 'Whether this note contains critical shipping restrictions';

-- ========================================
-- Additional tables for enhanced functionality
-- ========================================

-- Processing log table
CREATE TABLE processing_log (
    id SERIAL PRIMARY KEY,
    tariff_document_id INTEGER REFERENCES tariff_documents(id) ON DELETE SET NULL,
    
    -- Processing details
    processing_stage VARCHAR(50) NOT NULL, -- 'OCR', 'AI_EXTRACTION', 'DATABASE_SAVE', 'VALIDATION'
    status VARCHAR(20) NOT NULL, -- 'SUCCESS', 'ERROR', 'WARNING'
    message TEXT,
    error_details TEXT,
    
    -- Performance metrics
    processing_time_ms INTEGER,
    memory_used_mb INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (status IN ('SUCCESS', 'ERROR', 'WARNING', 'INFO'))
);

COMMENT ON TABLE processing_log IS 'Log of document processing stages and performance metrics';

-- Document relationships table (for revisions and updates)
CREATE TABLE document_relationships (
    id SERIAL PRIMARY KEY,
    parent_document_id INTEGER NOT NULL REFERENCES tariff_documents(id) ON DELETE CASCADE,
    child_document_id INTEGER NOT NULL REFERENCES tariff_documents(id) ON DELETE CASCADE,
    relationship_type VARCHAR(20) NOT NULL, -- 'REVISION', 'SUPERSEDES', 'AMENDMENT'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(parent_document_id, child_document_id),
    CHECK (parent_document_id != child_document_id),
    CHECK (relationship_type IN ('REVISION', 'SUPERSEDES', 'AMENDMENT', 'RELATED'))
);

COMMENT ON TABLE document_relationships IS 'Tracks relationships between tariff document versions';

-- ========================================
-- Indexes for performance optimization
-- ========================================

-- Primary search indexes
CREATE INDEX idx_tariff_documents_item_number ON tariff_documents(item_number);
CREATE INDEX idx_tariff_documents_item_revision ON tariff_documents(item_number, revision);
CREATE INDEX idx_tariff_documents_dates ON tariff_documents(effective_date, expiration_date);
CREATE INDEX idx_tariff_documents_status ON tariff_documents(status);
CREATE INDEX idx_tariff_documents_upload_date ON tariff_documents(upload_timestamp);

-- Rate search indexes
CREATE INDEX idx_tariff_rates_origin_dest ON tariff_rates(origin, destination);
CREATE INDEX idx_tariff_rates_origin ON tariff_rates(origin);
CREATE INDEX idx_tariff_rates_destination ON tariff_rates(destination);
CREATE INDEX idx_tariff_rates_route ON tariff_rates(route_code);
CREATE INDEX idx_tariff_rates_train_type ON tariff_rates(train_type);
CREATE INDEX idx_tariff_rates_amount ON tariff_rates(rate_amount);

-- Commodity search indexes
CREATE INDEX idx_tariff_commodities_stcc ON tariff_commodities(stcc_code);
CREATE INDEX idx_tariff_commodities_name ON tariff_commodities(commodity_name);
CREATE INDEX idx_tariff_commodities_type ON tariff_commodities(commodity_type);

-- Notes search indexes
CREATE INDEX idx_tariff_notes_type ON tariff_notes(note_type);
CREATE INDEX idx_tariff_notes_code ON tariff_notes(note_code);
CREATE INDEX idx_tariff_notes_critical ON tariff_notes(is_critical);

-- Foreign key indexes
CREATE INDEX idx_tariff_commodities_doc_id ON tariff_commodities(tariff_document_id);
CREATE INDEX idx_tariff_rates_doc_id ON tariff_rates(tariff_document_id);
CREATE INDEX idx_tariff_notes_doc_id ON tariff_notes(tariff_document_id);

-- Full-text search indexes (for PostgreSQL full-text search)
CREATE INDEX idx_tariff_documents_text_search ON tariff_documents USING gin(to_tsvector('english', coalesce(raw_ocr_text, '')));
CREATE INDEX idx_tariff_notes_text_search ON tariff_notes USING gin(to_tsvector('english', note_text));

-- ========================================
-- Views for common queries
-- ========================================

-- Active tariffs view
CREATE VIEW active_tariffs AS
SELECT 
    td.*,
    CASE 
        WHEN td.expiration_date >= CURRENT_DATE OR td.expiration_date IS NULL THEN 'ACTIVE'
        WHEN td.expiration_date < CURRENT_DATE THEN 'EXPIRED'
        ELSE 'UNKNOWN'
    END as current_status,
    CASE
        WHEN td.effective_date > CURRENT_DATE THEN 'FUTURE'
        WHEN td.effective_date <= CURRENT_DATE AND (td.expiration_date >= CURRENT_DATE OR td.expiration_date IS NULL) THEN 'CURRENT'
        ELSE 'PAST'
    END as time_status
FROM tariff_documents td
WHERE td.status = 'ACTIVE';

COMMENT ON VIEW active_tariffs IS 'View of active tariff documents with calculated status fields';

-- Tariff summary view
CREATE VIEW tariff_summary AS
SELECT 
    td.id,
    td.item_number,
    td.revision,
    td.pdf_name,
    td.effective_date,
    td.expiration_date,
    td.origin_info,
    td.destination_info,
    td.currency,
    td.upload_timestamp,
    COUNT(DISTINCT tc.id) as commodity_count,
    COUNT(DISTINCT tr.id) as rate_count,
    COUNT(DISTINCT tn.id) as note_count,
    MIN(tr.rate_amount) as min_rate,
    MAX(tr.rate_amount) as max_rate,
    AVG(tr.rate_amount) as avg_rate
FROM tariff_documents td
LEFT JOIN tariff_commodities tc ON td.id = tc.tariff_document_id
LEFT JOIN tariff_rates tr ON td.id = tr.tariff_document_id
LEFT JOIN tariff_notes tn ON td.id = tn.tariff_document_id
GROUP BY td.id, td.item_number, td.revision, td.pdf_name, 
         td.effective_date, td.expiration_date, td.origin_info, 
         td.destination_info, td.currency, td.upload_timestamp;

COMMENT ON VIEW tariff_summary IS 'Summary view with counts and rate statistics for each tariff';

-- Rate comparison view
CREATE VIEW rate_comparison AS
SELECT 
    tr.origin,
    tr.destination,
    tr.train_type,
    tr.car_capacity_type,
    COUNT(*) as rate_count,
    MIN(tr.rate_amount) as min_rate,
    MAX(tr.rate_amount) as max_rate,
    AVG(tr.rate_amount) as avg_rate,
    STDDEV(tr.rate_amount) as rate_stddev,
    td.currency
FROM tariff_rates tr
JOIN tariff_documents td ON tr.tariff_document_id = td.id
WHERE td.status = 'ACTIVE' 
  AND (td.expiration_date >= CURRENT_DATE OR td.expiration_date IS NULL)
  AND tr.rate_amount IS NOT NULL
GROUP BY tr.origin, tr.destination, tr.train_type, tr.car_capacity_type, td.currency
HAVING COUNT(*) > 0;

COMMENT ON VIEW rate_comparison IS 'Statistical comparison of rates by route and service type';

-- ========================================
-- Functions for common operations
-- ========================================

-- Function to get latest revision of a tariff
CREATE OR REPLACE FUNCTION get_latest_tariff_revision(item_num VARCHAR)
RETURNS TABLE(
    id INTEGER,
    item_number VARCHAR,
    revision INTEGER,
    effective_date DATE,
    expiration_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT td.id, td.item_number, td.revision, td.effective_date, td.expiration_date
    FROM tariff_documents td
    WHERE td.item_number = item_num
      AND td.status = 'ACTIVE'
    ORDER BY td.revision DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_latest_tariff_revision(VARCHAR) IS 'Get the latest active revision of a tariff by item number';

-- Function to search rates by route
CREATE OR REPLACE FUNCTION search_rates_by_route(
    origin_pattern VARCHAR DEFAULT '%',
    dest_pattern VARCHAR DEFAULT '%',
    active_only BOOLEAN DEFAULT TRUE
)
RETURNS TABLE(
    document_id INTEGER,
    item_number VARCHAR,
    origin VARCHAR,
    destination VARCHAR,
    rate_amount DECIMAL,
    currency VARCHAR,
    train_type VARCHAR,
    effective_date DATE,
    expiration_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tr.tariff_document_id,
        td.item_number,
        tr.origin,
        tr.destination,
        tr.rate_amount,
        tr.currency,
        tr.train_type,
        td.effective_date,
        td.expiration_date
    FROM tariff_rates tr
    JOIN tariff_documents td ON tr.tariff_document_id = td.id
    WHERE UPPER(tr.origin) LIKE UPPER(origin_pattern)
      AND UPPER(tr.destination) LIKE UPPER(dest_pattern)
      AND (NOT active_only OR (td.status = 'ACTIVE' AND (td.expiration_date >= CURRENT_DATE OR td.expiration_date IS NULL)))
    ORDER BY tr.rate_amount ASC, td.effective_date DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_rates_by_route(VARCHAR, VARCHAR, BOOLEAN) IS 'Search rates by origin and destination patterns';

-- ========================================
-- Triggers for automatic updates
-- ========================================

-- Function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update last_updated on tariff_documents
CREATE TRIGGER trigger_update_tariff_documents_timestamp
    BEFORE UPDATE ON tariff_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated();

-- ========================================
-- Initial data and reference values
-- ========================================

-- Insert common STCC codes for reference
INSERT INTO tariff_commodities (tariff_document_id, commodity_name, stcc_code, description, commodity_type) VALUES
(-1, 'WHEAT', '01 137', 'Wheat grain', 'GRAIN'),
(-1, 'RYE', '01 135', 'Rye grain', 'GRAIN'),
(-1, 'SOYBEANS', '01 144', 'Soybean grain', 'GRAIN'),
(-1, 'GRAIN SPENT', '20 823 30', 'Spent grain from brewing/distilling', 'FEED'),
(-1, 'MASH GRAIN SPENT', '20 859 45', 'Spent mash grain', 'FEED'),
(-1, 'DISTILLERS MASH SPENT', '20 859 40', 'Spent distillers mash', 'FEED')
ON CONFLICT DO NOTHING;

-- Note: The tariff_document_id = -1 is used for reference data only

-- ========================================
-- Database maintenance
-- ========================================

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cp_tariff_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cp_tariff_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO cp_tariff_user;

-- ========================================
-- Performance optimization settings
-- ========================================

-- Update table statistics
ANALYZE tariff_documents;
ANALYZE tariff_commodities;
ANALYZE tariff_rates;
ANALYZE tariff_notes;

-- Success message
SELECT 'CP Tariff database schema created successfully!' as message;