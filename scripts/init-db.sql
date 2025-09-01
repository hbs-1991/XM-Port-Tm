-- Initial database setup for XM-Port
-- This script runs when PostgreSQL container is first created

CREATE DATABASE xm_port_dev;
CREATE DATABASE xm_port_test;

-- Create user if not exists (for development)
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'xm_port_user') THEN

      CREATE ROLE xm_port_user LOGIN PASSWORD 'password';
   END IF;
END
$do$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE xm_port_dev TO xm_port_user;
GRANT ALL PRIVILEGES ON DATABASE xm_port_test TO xm_port_user;