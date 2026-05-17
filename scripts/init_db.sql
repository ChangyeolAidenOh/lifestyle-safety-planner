-- Lifestyle Safety Planner - Database Schema
-- 3-tier: raw → staging → mart

-- ============================================================
-- LAYER: raw (공공데이터 원본 적재)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.traffic_accidents (
    id              SERIAL PRIMARY KEY,
    year            INT NOT NULL,
    sido            VARCHAR(20),
    sigungu         VARCHAR(30),
    spot_name       VARCHAR(200),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    accident_count  INT,
    death_count     INT,
    injury_count    INT,
    road_type       VARCHAR(50),
    collected_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.crime_stats (
    id              SERIAL PRIMARY KEY,
    year            INT NOT NULL,
    sido            VARCHAR(20),
    sigungu         VARCHAR(30),
    crime_type      VARCHAR(50),
    occurrence      INT,
    arrest          INT,
    collected_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.flood_history (
    id              SERIAL PRIMARY KEY,
    year            INT NOT NULL,
    gu              VARCHAR(20),
    dong            VARCHAR(30),
    address         VARCHAR(200),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    flood_depth_cm  INT,
    collected_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.medical_facilities (
    id              SERIAL PRIMARY KEY,
    facility_name   VARCHAR(200),
    facility_type   VARCHAR(50),
    sido            VARCHAR(20),
    sigungu         VARCHAR(30),
    address         VARCHAR(300),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    bed_count       INT,
    emergency_yn    BOOLEAN DEFAULT FALSE,
    collected_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.air_quality (
    id              SERIAL PRIMARY KEY,
    measure_date    DATE NOT NULL,
    station_name    VARCHAR(50),
    sido            VARCHAR(20),
    pm10            DOUBLE PRECISION,
    pm25            DOUBLE PRECISION,
    o3              DOUBLE PRECISION,
    no2             DOUBLE PRECISION,
    co              DOUBLE PRECISION,
    so2             DOUBLE PRECISION,
    aqi             INT,
    collected_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.fire_stats (
    id              SERIAL PRIMARY KEY,
    year            INT NOT NULL,
    sido            VARCHAR(20),
    sigungu         VARCHAR(30),
    fire_count      INT,
    death_count     INT,
    injury_count    INT,
    property_damage BIGINT,
    cause           VARCHAR(100),
    collected_at    TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- LAYER: staging (정제 + 읍면동 공간 보간)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.location_safety (
    id              SERIAL PRIMARY KEY,
    region_code     VARCHAR(10),
    sido            VARCHAR(20),
    sigungu         VARCHAR(30),
    dong            VARCHAR(30),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    category        VARCHAR(30) NOT NULL,
    metric_name     VARCHAR(50) NOT NULL,
    metric_value    DOUBLE PRECISION,
    year            INT,
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_location_safety_region
    ON staging.location_safety(sido, sigungu, dong);

CREATE INDEX IF NOT EXISTS idx_location_safety_category
    ON staging.location_safety(category);

CREATE INDEX IF NOT EXISTS idx_location_safety_coords
    ON staging.location_safety(latitude, longitude);

-- ============================================================
-- LAYER: mart (대시보드/LLM 소비용)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS mart.safety_profile (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(64) NOT NULL,
    home_lat        DOUBLE PRECISION,
    home_lng        DOUBLE PRECISION,
    work_lat        DOUBLE PRECISION,
    work_lng        DOUBLE PRECISION,
    transport_mode  VARCHAR(20),
    profile_json    JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mart.safety_score (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(64) NOT NULL,
    location_type   VARCHAR(20),
    category        VARCHAR(30) NOT NULL,
    level           VARCHAR(10) NOT NULL,
    score           DOUBLE PRECISION,
    detail_json     JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mart.reward_mission (
    id              SERIAL PRIMARY KEY,
    category        VARCHAR(30) NOT NULL,
    trigger_level   VARCHAR(10),
    mission_title   VARCHAR(200),
    mission_desc    TEXT,
    points          INT,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS mart.guide_output (
    id              SERIAL PRIMARY KEY,
    session_id      VARCHAR(64) NOT NULL,
    guide_type      VARCHAR(20),
    source          VARCHAR(20),
    content         TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON COLUMN mart.guide_output.source IS 'rule_based or llm';
