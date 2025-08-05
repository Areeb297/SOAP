-- =========================================
-- SOAP Note Generator Medical Caching Schema
-- =========================================

-- Table 1: Cache medical term processing results
CREATE TABLE IF NOT EXISTS medical_term_cache (
    id SERIAL PRIMARY KEY,
    term_text VARCHAR(255) NOT NULL,
    term_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 hash of normalized term
    is_medical BOOLEAN NOT NULL DEFAULT false,
    is_correct BOOLEAN NOT NULL DEFAULT false,
    category VARCHAR(100) DEFAULT 'medical',
    confidence_score DECIMAL(3,2) DEFAULT 0.00,
    llm_identified BOOLEAN DEFAULT false,
    snomed_validated BOOLEAN DEFAULT false,
    needs_correction BOOLEAN DEFAULT false,
    source VARCHAR(50), -- 'llm_identified', 'snomed', 'drug_correction', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 1
);

CREATE INDEX idx_term_hash ON medical_term_cache (term_hash);
CREATE INDEX idx_term_text ON medical_term_cache (term_text);
CREATE INDEX idx_category ON medical_term_cache (category);
CREATE INDEX idx_last_accessed ON medical_term_cache (last_accessed);

-- Table 2: Cache SNOMED API results
CREATE TABLE IF NOT EXISTS snomed_api_cache (
    id SERIAL PRIMARY KEY,
    search_term VARCHAR(255) NOT NULL,
    search_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 hash of search term
    api_response JSONB NOT NULL, -- Full API response as JSON
    concept_count INTEGER DEFAULT 0,
    is_valid BOOLEAN DEFAULT false,
    response_time_ms INTEGER, -- Track API response time
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX idx_search_hash ON snomed_api_cache (search_hash);
CREATE INDEX idx_search_term ON snomed_api_cache (search_term);
CREATE INDEX idx_expires_at ON snomed_api_cache (expires_at);
CREATE INDEX idx_is_valid ON snomed_api_cache (is_valid);

-- Table 3: Cache spell check suggestions
CREATE TABLE IF NOT EXISTS spell_suggestion_cache (
    id SERIAL PRIMARY KEY,
    original_term VARCHAR(255) NOT NULL,
    original_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of original term
    suggested_terms JSONB NOT NULL, -- Array of suggestions with scores
    suggestion_source VARCHAR(50) NOT NULL, -- 'llm', 'snomed', 'database', 'drug_correction'
    suggestion_count INTEGER DEFAULT 0,
    confidence_score DECIMAL(3,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days'),
    access_count INTEGER DEFAULT 1
);

CREATE INDEX idx_original_hash ON spell_suggestion_cache (original_hash);
CREATE INDEX idx_original_term ON spell_suggestion_cache (original_term);
CREATE INDEX idx_suggestion_source ON spell_suggestion_cache (suggestion_source);
CREATE INDEX idx_spell_expires_at ON spell_suggestion_cache (expires_at);

-- Table 4: LLM processing cache
CREATE TABLE IF NOT EXISTS llm_processing_cache (
    id SERIAL PRIMARY KEY,
    text_input TEXT NOT NULL,
    text_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 hash of input text
    llm_response JSONB NOT NULL, -- Full LLM response as JSON
    medical_terms_found INTEGER DEFAULT 0,
    processing_time_ms INTEGER, -- Track LLM processing time
    model_used VARCHAR(50) DEFAULT 'gpt-4o-mini',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '12 hours')
);

CREATE INDEX idx_text_hash ON llm_processing_cache (text_hash);
CREATE INDEX idx_llm_expires_at ON llm_processing_cache (expires_at);
CREATE INDEX idx_medical_terms_found ON llm_processing_cache (medical_terms_found);

-- Table 5: Performance analytics and usage stats
CREATE TABLE IF NOT EXISTS api_usage_stats (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(100) NOT NULL, -- 'snomed', 'llm', 'spell_check'
    operation VARCHAR(50) NOT NULL, -- 'search', 'validate', 'suggest'
    cache_hit BOOLEAN NOT NULL DEFAULT false,
    processing_time_ms INTEGER,
    response_size_bytes INTEGER,
    error_occurred BOOLEAN DEFAULT false,
    error_message TEXT,
    user_session VARCHAR(100), -- Optional session tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_endpoint ON api_usage_stats (endpoint);
CREATE INDEX idx_cache_hit ON api_usage_stats (cache_hit);
CREATE INDEX idx_api_created_at ON api_usage_stats (created_at);
CREATE INDEX idx_error_occurred ON api_usage_stats (error_occurred);

-- Table 6: Dynamic medicine list extensions
CREATE TABLE IF NOT EXISTS medicine_list_extended (
    id SERIAL PRIMARY KEY,
    medicine_name VARCHAR(255) NOT NULL UNIQUE,
    medicine_hash VARCHAR(64) NOT NULL UNIQUE,
    category VARCHAR(100) DEFAULT 'medication',
    confirmed_correct BOOLEAN DEFAULT false,
    user_confirmed BOOLEAN DEFAULT false,
    snomed_code VARCHAR(50),
    generic_name VARCHAR(255),
    brand_names JSONB, -- Array of brand names
    common_misspellings JSONB, -- Array of common misspellings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 1
);

CREATE INDEX idx_medicine_hash ON medicine_list_extended (medicine_hash);
CREATE INDEX idx_medicine_name ON medicine_list_extended (medicine_name);
CREATE INDEX idx_medicine_category ON medicine_list_extended (category);
CREATE INDEX idx_confirmed_correct ON medicine_list_extended (confirmed_correct);

-- =========================================
-- CACHE MAINTENANCE FUNCTIONS
-- =========================================

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    snomed_deleted INTEGER := 0;
    spell_deleted INTEGER := 0;
    llm_deleted INTEGER := 0;
    stats_deleted INTEGER := 0;
    total_deleted INTEGER := 0;
BEGIN
    -- Clean up expired SNOMED API cache
    DELETE FROM snomed_api_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS snomed_deleted = ROW_COUNT;
    
    -- Clean up expired spell suggestion cache
    DELETE FROM spell_suggestion_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS spell_deleted = ROW_COUNT;
    
    -- Clean up expired LLM processing cache
    DELETE FROM llm_processing_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS llm_deleted = ROW_COUNT;
    
    -- Clean up old usage stats (keep last 30 days)
    DELETE FROM api_usage_stats WHERE created_at < (NOW() - INTERVAL '30 days');
    GET DIAGNOSTICS stats_deleted = ROW_COUNT;
    
    -- Sum all deleted
    total_deleted := snomed_deleted + spell_deleted + llm_deleted + stats_deleted;
    RETURN total_deleted;
END;
$$ LANGUAGE plpgsql;
-- Function to update cache access statistics
CREATE OR REPLACE FUNCTION update_cache_access(cache_table TEXT, cache_id INTEGER)
RETURNS VOID AS $$
BEGIN
    CASE cache_table
        WHEN 'medical_term_cache' THEN
            UPDATE medical_term_cache 
            SET access_count = access_count + 1, last_accessed = NOW() 
            WHERE id = cache_id;
        WHEN 'spell_suggestion_cache' THEN
            UPDATE spell_suggestion_cache 
            SET access_count = access_count + 1 
            WHERE id = cache_id;
        WHEN 'medicine_list_extended' THEN
            UPDATE medicine_list_extended 
            SET usage_count = usage_count + 1 
            WHERE id = cache_id;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- PERFORMANCE VIEWS
-- =========================================

-- View for cache hit rates
CREATE OR REPLACE VIEW cache_performance AS
SELECT 
    endpoint,
    COUNT(*) as total_requests,
    COUNT(*) FILTER (WHERE cache_hit = true) as cache_hits,
    COUNT(*) FILTER (WHERE cache_hit = false) as cache_misses,
    ROUND(
        (COUNT(*) FILTER (WHERE cache_hit = true) * 100.0 / COUNT(*)), 2
    ) as hit_rate_percentage,
    AVG(processing_time_ms) as avg_processing_time_ms,
    COUNT(*) FILTER (WHERE error_occurred = true) as error_count
FROM api_usage_stats 
WHERE created_at > (NOW() - INTERVAL '24 hours')
GROUP BY endpoint;

-- View for most frequently accessed terms
CREATE OR REPLACE VIEW popular_medical_terms AS
SELECT 
    term_text,
    category,
    access_count,
    is_correct,
    confidence_score,
    source,
    last_accessed
FROM medical_term_cache 
ORDER BY access_count DESC, last_accessed DESC
LIMIT 100;

-- =========================================
-- SCHEDULED MAINTENANCE
-- =========================================

-- Note: The following would be set up as a cron job or scheduled task
-- SELECT cleanup_expired_cache(); -- Run daily to clean up expired entries

-- =========================================
-- INITIAL DATA SEEDING (Optional)
-- =========================================

-- Seed some common medical terms for better performance
INSERT INTO medicine_list_extended (medicine_name, medicine_hash, category, confirmed_correct, common_misspellings) VALUES
('warfarin', encode(sha256('warfarin'::bytea), 'hex'), 'anticoagulant', true, '["wolfrin", "walfarin", "warfrin"]'::jsonb),
('metformin', encode(sha256('metformin'::bytea), 'hex'), 'antidiabetic', true, '["metformim", "metformine"]'::jsonb),
('insulin', encode(sha256('insulin'::bytea), 'hex'), 'hormone', true, '["insuline", "insolin"]'::jsonb),
('lisinopril', encode(sha256('lisinopril'::bytea), 'hex'), 'ace_inhibitor', true, '["lisanopril", "lisinoprill"]'::jsonb),
('atorvastatin', encode(sha256('atorvastatin'::bytea), 'hex'), 'statin', true, '["atorvastain", "atorvastatine"]'::jsonb)
ON CONFLICT (medicine_name) DO NOTHING;

-- =========================================
-- USAGE NOTES
-- =========================================

-- 1. All cache tables use SHA-256 hashes for efficient lookups
-- 2. JSONB is used for flexible storage of API responses and suggestions
-- 3. Automatic expiration prevents stale data accumulation
-- 4. Performance indexes are optimized for common query patterns
-- 5. Usage statistics help monitor and optimize cache performance
-- 6. Functions provide automated maintenance capabilities

-- Example queries:
-- SELECT * FROM cache_performance; -- Check cache hit rates
-- SELECT * FROM popular_medical_terms LIMIT 10; -- Most used terms
-- SELECT cleanup_expired_cache(); -- Manual cache cleanup
