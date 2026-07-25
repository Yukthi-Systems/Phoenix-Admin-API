# Production PostgreSQL Initial Database & Role Setup

This performs the initial PostgreSQL setup for the Mail Service database. Admin user with full privileges "postgres" is already created. The following script creates the database, roles, and grants the necessary permissions.

## What it does

- Creates the `super_admin` PostgreSQL superuser.
- Creates the `mail_service_v3` database owned by `super_admin`.
- Creates `app_user` with **read-only** access to the database.
- Creates `app_admin` with **CRUD (SELECT, INSERT, UPDATE, DELETE)** permissions on all tables.
- Grants access to existing tables and sequences.
- Configures default privileges so future tables and sequences automatically inherit the correct permissions.

## Roles

| Role | Permissions | Intended Use |
|------|-------------|--------------|
| `super_admin` | Full PostgreSQL superuser | Database administration, schema changes, migrations |
| `app_admin` | CRUD only (no CREATE/ALTER/DROP) | Backend API / Application |
| `app_user` | Read-only | Reporting, analytics, monitoring, dashboards |

> **Note:** `app_admin` can modify data but **cannot** create, alter, or drop database objects. Schema changes must always be performed using `super_admin`.

```sql
-- Create the superuser
CREATE ROLE super_admin
WITH
    LOGIN
    SUPERUSER
    CREATEDB
    CREATEROLE
    PASSWORD 'example_super_admin_password';

-- Create the database owned by the superuser
CREATE DATABASE mail_service_v3
OWNER super_admin;

-- Create the read-only user
CREATE ROLE app_user
WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    PASSWORD 'example_app_user_password';

-- Connect to the new database
\c mail_service_v3

-- Allow read-only user to connect
GRANT CONNECT ON DATABASE mail_service_v3 TO app_user;

-- Allow access to the public schema
GRANT USAGE ON SCHEMA public TO app_user;

-- Read all existing tables and sequences
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Automatically grant read access on future tables/sequences
ALTER DEFAULT PRIVILEGES FOR ROLE super_admin IN SCHEMA public
GRANT SELECT ON TABLES TO app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE super_admin IN SCHEMA public
GRANT SELECT ON SEQUENCES TO app_user;

-- CRUD user
CREATE ROLE app_admin
WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    PASSWORD 'example_app_admin_password';

-- Allow connection
GRANT CONNECT ON DATABASE mail_service_v3 TO app_admin;

-- Allow schema usage
GRANT USAGE ON SCHEMA public TO app_admin;

-- CRUD on all existing tables
GRANT
    SELECT,
    INSERT,
    UPDATE,
    DELETE
ON ALL TABLES IN SCHEMA public
TO app_admin;

-- Use sequences (required for SERIAL/IDENTITY columns)
GRANT
    USAGE,
    SELECT
ON ALL SEQUENCES IN SCHEMA public
TO app_admin;

-- Future tables
ALTER DEFAULT PRIVILEGES FOR ROLE super_admin
IN SCHEMA public
GRANT
    SELECT,
    INSERT,
    UPDATE,
    DELETE
ON TABLES
TO app_admin;

-- Future sequences
ALTER DEFAULT PRIVILEGES FOR ROLE super_admin
IN SCHEMA public
GRANT
    USAGE,
    SELECT
ON SEQUENCES
TO app_admin;
```
