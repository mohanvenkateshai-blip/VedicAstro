-- VedicShastra AI - PostgreSQL Schema
-- Run this after creating your database

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgvector; -- For future vector embeddings if needed

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'free' CHECK (role IN ('free', 'pro', 'premium', 'admin')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Horoscopes (Birth Charts)
CREATE TABLE horoscopes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    birth_date DATE NOT NULL,
    birth_time TIME,
    birth_place VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    timezone VARCHAR(50),
    chart_data JSONB NOT NULL,           -- Full computed chart (positions, houses, etc.)
    ayanamsa VARCHAR(50) DEFAULT 'Lahiri',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Predictions / Reports
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    horoscope_id UUID REFERENCES horoscopes(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    prediction_type VARCHAR(100),        -- 'short_term', 'long_term', 'dasha', 'transit', etc.
    content JSONB NOT NULL,              -- Structured prediction data + citations
    rules_used JSONB,                    -- Which rules from knowledge graph were triggered
    llm_trace JSONB,                     -- Trace of synthesis for explainability
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Feedback (for Continuous Evolution Loop)
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    prediction_id UUID REFERENCES predictions(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    feedback_type VARCHAR(50) DEFAULT 'prediction', -- 'prediction' or 'ui_ux'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,           -- 'free', 'pro', 'premium'
    status VARCHAR(50) DEFAULT 'active',
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments (store only references, never raw card data)
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    subscription_id UUID REFERENCES subscriptions(id),
    provider VARCHAR(50),                -- 'stripe', 'razorpay'
    provider_payment_id VARCHAR(255),
    amount INTEGER,
    currency VARCHAR(10),
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_horoscopes_user_id ON horoscopes(user_id);
CREATE INDEX idx_predictions_horoscope_id ON predictions(horoscope_id);
CREATE INDEX idx_feedback_prediction_id ON feedback(prediction_id);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);

-- Row Level Security (example - enable in production)
-- ALTER TABLE horoscopes ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY user_own_horoscopes ON horoscopes FOR ALL USING (user_id = auth.uid());