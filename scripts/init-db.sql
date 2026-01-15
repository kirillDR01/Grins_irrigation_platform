-- Initialize Grins Irrigation Platform Database
-- This script sets up the initial database structure
--
-- USAGE:
-- This script is automatically executed when PostgreSQL is enabled in docker-compose.yml
-- It runs on first container startup via the docker-entrypoint-initdb.d mechanism
--
-- TO ENABLE:
-- 1. Uncomment the 'postgres' service in docker-compose.yml
-- 2. Uncomment the 'postgres_data' volume
-- 3. Run: docker-compose up
-- 4. This script will initialize the database automatically
--
-- NOTE: Currently PostgreSQL is commented out in docker-compose.yml (not in use)

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS grins_platform;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default schema
SET search_path TO grins_platform, public;

-- Create basic tables for the platform

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Services table
CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2),
    unit VARCHAR(50), -- per hour, per visit, per square foot, etc.
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Jobs/Appointments table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    service_id UUID REFERENCES services(id) ON DELETE RESTRICT,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME,
    status VARCHAR(50) DEFAULT 'scheduled', -- scheduled, in_progress, completed, cancelled
    estimated_duration INTEGER, -- in minutes
    actual_duration INTEGER, -- in minutes
    notes TEXT,
    special_instructions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE INDEX IF NOT EXISTS idx_jobs_customer_id ON jobs(customer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_service_id ON jobs(service_id);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled_date ON jobs(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_services_updated_at BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data
INSERT INTO services (name, description, base_price, unit) VALUES
    ('Sprinkler System Installation', 'Complete sprinkler system installation for residential properties', 2500.00, 'per_job'),
    ('Sprinkler System Maintenance', 'Regular maintenance and inspection of existing sprinkler systems', 150.00, 'per_visit'),
    ('Drip Irrigation Setup', 'Installation of water-efficient drip irrigation systems', 800.00, 'per_job'),
    ('System Repair', 'Repair of broken or malfunctioning irrigation components', 75.00, 'per_hour'),
    ('Seasonal Winterization', 'Prepare irrigation systems for winter weather', 200.00, 'per_visit'),
    ('Spring Startup', 'Activate and test irrigation systems for spring season', 175.00, 'per_visit')
ON CONFLICT DO NOTHING;

-- Create a default admin user (password: admin123 - change in production!)
INSERT INTO users (email, username, full_name, hashed_password, is_superuser) VALUES
    ('admin@grins-irrigations.com', 'admin', 'System Administrator', 
     crypt('admin123', gen_salt('bf')), true)
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA grins_platform TO grins_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA grins_platform TO grins_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA grins_platform TO grins_user;

COMMIT;