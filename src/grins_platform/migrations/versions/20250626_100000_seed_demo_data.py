"""Seed demo data for demonstration purposes.

Revision ID: 20250626_100000
Revises: 20250625_100000
Create Date: 2025-01-31

This migration seeds demo data including:
- Sample customers with properties
- Additional staff members (technicians)
- Service offerings (seasonal, repair, installation)
- Sample jobs in various statuses

This data is for demonstration and testing purposes.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "20250626_100000"
down_revision: Union[str, None] = "20250625_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Bcrypt hash for password 'tech123' with cost factor 12
TECH_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.S3vZ3vZ3vZ3vZ3"


def upgrade() -> None:
    """Seed demo data for demonstration purposes."""
    
    # ==========================================================================
    # 1. SEED SERVICE OFFERINGS
    # ==========================================================================
    op.execute(
        text(
            """
            INSERT INTO service_offerings (
                name, category, description, base_price, price_per_zone,
                pricing_model, estimated_duration_minutes, duration_per_zone_minutes,
                staffing_required, equipment_required, lien_eligible, is_active
            ) VALUES
            -- Seasonal Services
            ('Spring Startup', 'seasonal', 'Activate and test irrigation system for spring season. Includes zone testing, head adjustment, and leak inspection.', 75.00, 5.00, 'zone_based', 30, 5, 1, '["standard_tools"]', false, true),
            ('Summer Tune-Up', 'seasonal', 'Mid-season system check and optimization. Adjust heads, check coverage, optimize watering schedule.', 65.00, 4.00, 'zone_based', 25, 4, 1, '["standard_tools"]', false, true),
            ('Winterization', 'seasonal', 'Prepare irrigation system for winter. Blow out lines with compressed air, drain backflow preventer.', 85.00, 6.00, 'zone_based', 35, 5, 1, '["compressor", "standard_tools"]', false, true),
            
            -- Repair Services
            ('Sprinkler Head Replacement', 'repair', 'Replace broken or malfunctioning sprinkler heads. Price per head.', 50.00, NULL, 'flat', 20, NULL, 1, '["standard_tools"]', false, true),
            ('Valve Repair', 'repair', 'Diagnose and repair zone valve issues. Includes solenoid replacement if needed.', 125.00, NULL, 'flat', 45, NULL, 1, '["standard_tools", "valve_parts"]', false, true),
            ('Pipe Repair', 'repair', 'Repair broken or leaking pipes. Price varies by complexity.', 150.00, NULL, 'hourly', 60, NULL, 1, '["pipe_puller", "standard_tools"]', true, true),
            ('System Diagnostic', 'diagnostic', 'Full system diagnostic to identify issues. First hour included, additional time billed hourly.', 100.00, NULL, 'hourly', 60, NULL, 1, '["standard_tools", "diagnostic_tools"]', false, true),
            
            -- Installation Services
            ('New Zone Installation', 'installation', 'Install new irrigation zone. Includes trenching, pipe, heads, and valve.', 700.00, NULL, 'custom', 240, NULL, 2, '["pipe_puller", "trencher", "standard_tools"]', true, true),
            ('Drip Irrigation Setup', 'installation', 'Install drip irrigation for gardens and landscaping beds.', 350.00, NULL, 'custom', 120, NULL, 1, '["standard_tools", "drip_supplies"]', true, true),
            ('Full System Installation', 'installation', 'Complete irrigation system installation for new properties.', 700.00, 700.00, 'zone_based', 480, 60, 2, '["pipe_puller", "trencher", "standard_tools", "utility_trailer"]', true, true)
            
            ON CONFLICT DO NOTHING;
            """
        )
    )

    # ==========================================================================
    # 2. SEED ADDITIONAL STAFF (TECHNICIANS)
    # ==========================================================================
    op.execute(
        text(
            """
            INSERT INTO staff (
                name, phone, email, role, skill_level, certifications,
                is_available, hourly_rate, is_active, assigned_equipment,
                default_start_address, default_start_city, default_start_lat, default_start_lng,
                username, password_hash, is_login_enabled
            ) VALUES
            -- Senior Technician - Vas
            ('Vas Grin', '6125552001', 'vas@grins-irrigations.com', 'tech', 'senior',
             '["irrigation_certified", "backflow_certified"]', true, 35.00, true,
             '["compressor", "pipe_puller"]', '123 Tech Lane', 'Eden Prairie', 44.8547, -93.4708,
             'vas', :password_hash, true),
            
            -- Lead Technician - Steven
            ('Steven Miller', '6125552002', 'steven@grins-irrigations.com', 'tech', 'lead',
             '["irrigation_certified", "backflow_certified", "landscaping_certified"]', true, 40.00, true,
             '["compressor", "pipe_puller", "trencher"]', '456 Service Rd', 'Plymouth', 45.0105, -93.4555,
             'steven', :password_hash, true),
            
            -- Junior Technician - Dad
            ('Viktor Sr', '6125552003', 'viktor.sr@grins-irrigations.com', 'tech', 'junior',
             '["irrigation_certified"]', true, 28.00, true,
             '["standard_tools"]', '789 Helper Ave', 'Maple Grove', 45.0724, -93.4557,
             NULL, NULL, false),
            
            -- Part-time Technician - Vitallik
            ('Vitallik Petrov', '6125552004', 'vitallik@grins-irrigations.com', 'tech', 'senior',
             '["irrigation_certified", "landscaping_certified"]', true, 32.00, true,
             '["compressor", "standard_tools"]', '321 Seasonal St', 'Brooklyn Park', 45.0941, -93.3563,
             'vitallik', :password_hash, true)
             
            ON CONFLICT DO NOTHING;
            """
        ).bindparams(password_hash=TECH_PASSWORD_HASH)
    )

    # ==========================================================================
    # 3. SEED SAMPLE CUSTOMERS
    # ==========================================================================
    op.execute(
        text(
            """
            INSERT INTO customers (
                first_name, last_name, phone, email, status,
                is_priority, is_red_flag, is_slow_payer, is_new_customer,
                sms_opt_in, email_opt_in, lead_source
            ) VALUES
            -- Priority customer - long-time client
            ('John', 'Anderson', '6125551001', 'john.anderson@email.com', 'active',
             true, false, false, false, true, true, 'referral'),
            
            -- Regular customer
            ('Sarah', 'Johnson', '6125551002', 'sarah.j@email.com', 'active',
             false, false, false, false, true, false, 'google'),
            
            -- New customer from website
            ('Michael', 'Williams', '6125551003', 'mwilliams@email.com', 'active',
             false, false, false, true, true, true, 'website'),
            
            -- Commercial customer - priority
            ('Twin Cities Landscaping', 'LLC', '6125551004', 'info@tcllandscaping.com', 'active',
             true, false, false, false, true, true, 'referral'),
            
            -- Slow payer - flagged
            ('Robert', 'Davis', '6125551005', 'rdavis@email.com', 'active',
             false, false, true, false, false, false, 'google'),
            
            -- Red flag customer
            ('Karen', 'Thompson', '6125551006', NULL, 'active',
             false, true, false, false, false, false, 'word_of_mouth'),
            
            -- Regular residential
            ('David', 'Martinez', '6125551007', 'david.m@email.com', 'active',
             false, false, false, false, true, true, 'referral'),
            
            -- New customer
            ('Emily', 'Garcia', '6125551008', 'emily.garcia@email.com', 'active',
             false, false, false, true, true, true, 'website'),
            
            -- Long-time customer
            ('James', 'Wilson', '6125551009', 'jwilson@email.com', 'active',
             false, false, false, false, true, false, 'word_of_mouth'),
            
            -- Commercial property manager
            ('Sunrise Property Management', 'Inc', '6125551010', 'maintenance@sunriseprop.com', 'active',
             true, false, false, false, true, true, 'referral')
             
            ON CONFLICT DO NOTHING;
            """
        )
    )

    # ==========================================================================
    # 4. SEED PROPERTIES FOR CUSTOMERS
    # ==========================================================================
    op.execute(
        text(
            """
            INSERT INTO properties (
                customer_id, address, city, state, zip_code,
                latitude, longitude, zone_count, system_type, property_type,
                is_primary, access_instructions, gate_code, has_dogs, special_notes
            )
            SELECT 
                c.id,
                p.address,
                p.city,
                'MN',
                p.zip_code,
                p.latitude,
                p.longitude,
                p.zone_count,
                p.system_type,
                p.property_type,
                true,
                p.access_instructions,
                p.gate_code,
                p.has_dogs,
                p.special_notes
            FROM customers c
            CROSS JOIN (VALUES
                -- John Anderson - Eden Prairie
                ('6125551001', '1234 Lakeside Dr', 'Eden Prairie', '55344', 44.8547, -93.4708, 8, 'standard', 'residential', 'Gate code at side entrance', '1234', false, 'Large backyard, premium system'),
                -- Sarah Johnson - Plymouth
                ('6125551002', '5678 Oak Street', 'Plymouth', '55441', 45.0105, -93.4555, 6, 'standard', 'residential', 'Ring doorbell on arrival', NULL, true, 'Friendly dog, will bark'),
                -- Michael Williams - Maple Grove
                ('6125551003', '910 Maple Ave', 'Maple Grove', '55369', 45.0724, -93.4557, 5, 'standard', 'residential', NULL, NULL, false, 'New construction, system installed 2024'),
                -- Twin Cities Landscaping - Brooklyn Park (Commercial)
                ('6125551004', '2000 Commerce Blvd', 'Brooklyn Park', '55445', 45.0941, -93.3563, 24, 'standard', 'commercial', 'Check in at main office first', '9999', false, 'Large commercial property, multiple buildings'),
                -- Robert Davis - Rogers
                ('6125551005', '333 Country Rd', 'Rogers', '55374', 45.1886, -93.5530, 4, 'lake_pump', 'residential', 'Lake pump system - check pump house first', NULL, false, 'Lake pump system, requires extra time'),
                -- Karen Thompson - Eden Prairie
                ('6125551006', '777 Difficult Lane', 'Eden Prairie', '55346', 44.8600, -93.4800, 7, 'standard', 'residential', 'Call before arriving', NULL, true, 'Customer prefers advance notice'),
                -- David Martinez - Plymouth
                ('6125551007', '456 Pleasant Way', 'Plymouth', '55447', 45.0200, -93.4600, 6, 'standard', 'residential', NULL, NULL, false, 'Well-maintained system'),
                -- Emily Garcia - Maple Grove
                ('6125551008', '789 New Home Ct', 'Maple Grove', '55311', 45.0800, -93.4700, 5, 'standard', 'residential', NULL, NULL, false, 'Brand new system, first service'),
                -- James Wilson - Brooklyn Park
                ('6125551009', '1111 Veteran Blvd', 'Brooklyn Park', '55443', 45.1000, -93.3700, 9, 'standard', 'residential', 'Use side gate', '5555', false, 'Long-time customer, knows the system well'),
                -- Sunrise Property Management - Multiple locations
                ('6125551010', '500 Office Park Dr', 'Eden Prairie', '55344', 44.8700, -93.4900, 18, 'standard', 'commercial', 'Contact property manager on arrival', NULL, false, 'Office complex, 3 buildings')
            ) AS p(phone, address, city, zip_code, latitude, longitude, zone_count, system_type, property_type, access_instructions, gate_code, has_dogs, special_notes)
            WHERE c.phone = p.phone
            ON CONFLICT DO NOTHING;
            """
        )
    )

    # ==========================================================================
    # 5. SEED SAMPLE JOBS
    # ==========================================================================
    op.execute(
        text(
            """
            INSERT INTO jobs (
                customer_id, property_id, job_type, category, status,
                description, estimated_duration_minutes, priority_level,
                weather_sensitive, staffing_required, quoted_amount, source
            )
            SELECT 
                c.id as customer_id,
                p.id as property_id,
                j.job_type,
                j.category,
                j.status,
                j.description,
                j.estimated_duration_minutes,
                j.priority_level,
                j.weather_sensitive,
                j.staffing_required,
                j.quoted_amount,
                j.source
            FROM customers c
            JOIN properties p ON p.customer_id = c.id AND p.is_primary = true
            CROSS JOIN (VALUES
                -- John Anderson - Spring startup (approved, ready to schedule)
                ('6125551001', 'spring_startup', 'ready_to_schedule', 'approved', 'Spring startup - 8 zone system, check all heads and adjust coverage', 70, 1, true, 1, 115.00, 'phone'),
                -- Sarah Johnson - Repair needed (requested)
                ('6125551002', 'repair', 'ready_to_schedule', 'requested', 'Zone 3 not turning on - possible valve issue', 45, 0, false, 1, 125.00, 'website'),
                -- Michael Williams - First service (approved)
                ('6125551003', 'spring_startup', 'ready_to_schedule', 'approved', 'First spring startup for new system - full inspection', 50, 0, true, 1, 100.00, 'website'),
                -- Twin Cities Landscaping - Commercial maintenance (scheduled)
                ('6125551004', 'spring_startup', 'ready_to_schedule', 'scheduled', 'Commercial spring startup - 24 zones, full system check', 180, 1, true, 2, 350.00, 'partner'),
                -- Robert Davis - Lake pump service (requires estimate)
                ('6125551005', 'repair', 'requires_estimate', 'requested', 'Lake pump making noise - needs diagnostic', 60, 0, false, 1, NULL, 'phone'),
                -- David Martinez - Tune-up (approved)
                ('6125551007', 'tune_up', 'ready_to_schedule', 'approved', 'Summer tune-up requested - adjust heads for dry season', 40, 0, true, 1, 89.00, 'referral'),
                -- Emily Garcia - New customer startup (approved, priority)
                ('6125551008', 'spring_startup', 'ready_to_schedule', 'approved', 'First service for new customer - full system walkthrough', 55, 1, true, 1, 100.00, 'website'),
                -- James Wilson - Winterization (completed)
                ('6125551009', 'winterization', 'ready_to_schedule', 'completed', 'Fall winterization - 9 zones blown out successfully', 65, 0, false, 1, 139.00, 'phone'),
                -- Sunrise Property - Commercial diagnostic (in progress)
                ('6125551010', 'diagnostic', 'requires_estimate', 'in_progress', 'Water pressure issues in building B - investigating', 120, 1, false, 1, 100.00, 'referral')
            ) AS j(phone, job_type, category, status, description, estimated_duration_minutes, priority_level, weather_sensitive, staffing_required, quoted_amount, source)
            WHERE c.phone = j.phone
            ON CONFLICT DO NOTHING;
            """
        )
    )


def downgrade() -> None:
    """Remove demo data.
    
    Note: This will cascade delete related records due to foreign key constraints.
    """
    # Delete jobs first (depends on customers and properties)
    op.execute(
        text(
            """
            DELETE FROM jobs 
            WHERE customer_id IN (
                SELECT id FROM customers 
                WHERE phone IN ('6125551001', '6125551002', '6125551003', '6125551004', 
                               '6125551005', '6125551006', '6125551007', '6125551008',
                               '6125551009', '6125551010')
            );
            """
        )
    )
    
    # Delete properties (depends on customers)
    op.execute(
        text(
            """
            DELETE FROM properties 
            WHERE customer_id IN (
                SELECT id FROM customers 
                WHERE phone IN ('6125551001', '6125551002', '6125551003', '6125551004', 
                               '6125551005', '6125551006', '6125551007', '6125551008',
                               '6125551009', '6125551010')
            );
            """
        )
    )
    
    # Delete demo customers
    op.execute(
        text(
            """
            DELETE FROM customers 
            WHERE phone IN ('6125551001', '6125551002', '6125551003', '6125551004', 
                           '6125551005', '6125551006', '6125551007', '6125551008',
                           '6125551009', '6125551010');
            """
        )
    )
    
    # Delete demo staff (keep admin)
    op.execute(
        text(
            """
            DELETE FROM staff 
            WHERE phone IN ('6125552001', '6125552002', '6125552003', '6125552004');
            """
        )
    )
    
    # Delete demo service offerings
    op.execute(
        text(
            """
            DELETE FROM service_offerings 
            WHERE name IN ('Spring Startup', 'Summer Tune-Up', 'Winterization',
                          'Sprinkler Head Replacement', 'Valve Repair', 'Pipe Repair',
                          'System Diagnostic', 'New Zone Installation', 
                          'Drip Irrigation Setup', 'Full System Installation');
            """
        )
    )
