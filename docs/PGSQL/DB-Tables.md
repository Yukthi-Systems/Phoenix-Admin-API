# SQL Schema (Normalized & Scalable)

```sql
-- USERS
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL UNIQUE,  -- e.g., 'john_doe'
    user_email VARCHAR(254) UNIQUE NOT NULL,
    primary_phone VARCHAR(20) NOT NULL,  -- e.g., '+1234567890'
    display_name VARCHAR(100) NOT NULL,

    password_hash TEXT NOT NULL,
    user_details JSONB NOT NULL,  -- just for storing extra info (not indexed)
    ui_info JSONB NOT NULL,  -- e.g., theme, state, etc. (not indexed)
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_email_verified BOOLEAN DEFAULT FALSE NOT NULL,  -- Is email verified
    is_phone_verified BOOLEAN DEFAULT FALSE NOT NULL,  -- Is phone number verified

    permissions_template JSONB NOT NULL,  -- template for permissions (Specific to user)
    permissions TEXT[] NOT NULL,            -- e.g., ['user:create', 'user:delete']

    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    is_totp_2fa_active BOOLEAN DEFAULT FALSE NOT NULL,  -- Is TOTP 2FA enabled for this user
    is_sms_2fa_active BOOLEAN DEFAULT FALSE NOT NULL,  -- Is SMS 2FA enabled for this user
    is_email_2fa_active BOOLEAN DEFAULT FALSE NOT NULL,  -- Is Email 2FA enabled for this user

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (display_name, organization_id)  -- Unique display name per organization
);

-- DOMAINS
CREATE TABLE domains (
    domain_name VARCHAR(254) PRIMARY KEY,
    managed_by UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    -- TODO: Send the Anti-Phishing Secret Code for all kinds of emails (e.g., registration, password reset, etc.)
    anti_phishing_secret_code VARCHAR(20) NOT NULL,  -- Secret key for anti-phishing (used in email body directly, to help users identify phishing emails)
    details JSONB NOT NULL,  -- metadata, not indexed

    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    -- TODO: Check DNS TXT verification for a domain (for it to enable all kinds of services, if not then dont even allow to create identities or mailboxes for this domain)
    is_dns_txt_verified BOOLEAN DEFAULT FALSE NOT NULL,  -- Is the domain verified (TXT DNS record checked and verified) [ms25-domain-verification=some-secret-key]
    dns_txt_verification_key VARCHAR(32) NOT NULL,  -- The TXT record value for domain verification

    spam_destination VARCHAR(100) NOT NULL,
    spam_destination_properties JSONB NOT NULL,

    filter_policy_id UUID REFERENCES filter_policies(policy_id) ON DELETE SET NULL,
    attachment_policy_id UUID REFERENCES attachment_policies(policy_id) ON DELETE SET NULL,

    catch_all BOOLEAN DEFAULT FALSE NOT NULL,
    catch_all_forward_to_email VARCHAR(254) REFERENCES mailboxes(email) ON DELETE SET NULL,
    
    is_hybrid BOOLEAN DEFAULT FALSE NOT NULL,   -- If the domain is hybrid (means it has external connectors, enabled/disabled)
    connector_properties JSONB NOT NULL,    -- { "fqdn": "example.com", "port": 587, "ipv4": "1.1.1.1", "ipv6": "2001:db8::1" }
    
    is_locked BOOLEAN DEFAULT FALSE NOT NULL,
    locked_servers_group UUID[],  -- List of server IDs that are locked for this domain (Can be NULL if not locked)

    max_password_age INT NOT NULL,
    max_password_age_properties JSONB NOT NULL,
    
    session_timeout INT NOT NULL DEFAULT 720 CHECK (session_timeout BETWEEN 30 AND 720),  -- in minutes

    disclaimer_id UUID REFERENCES disclaimers(disclaimer_id) ON DELETE SET NULL,
    caution_id UUID REFERENCES cautions(caution_id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- E-Mail ID's - Users
CREATE TABLE email_identities (
    email VARCHAR(254) PRIMARY KEY,
    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    first_name TEXT NOT NULL,
    last_name TEXT,
    primary_phone VARCHAR(20) NOT NULL, -- Used for 2FA/recovery/notifications
    secondary_email VARCHAR(254),   -- Used for 2FA/recovery/notifications

    password_hash_ssha1 TEXT NOT NULL,
    password_bcrypt TEXT NOT NULL,

    is_app_2fa_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Is app-based 2FA enabled
    is_sms_2fa_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Is SMS-based 2FA enabled
    is_email_2fa_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Is Email-based 2FA enabled
    -- TODO: Add a TOTP and Backup Codes too

    restriction_policy_id UUID REFERENCES restriction_policies(policy_id) ON DELETE SET NULL,
    department_id UUID REFERENCES departments(department_id) ON DELETE SET NULL,

    is_password_expired BOOLEAN DEFAULT FALSE NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,

    password_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- MailBoxes (Actual MailBox) [E-Mail Service]
CREATE TABLE mailboxes (
    email VARCHAR(254) PRIMARY KEY REFERENCES email_identities(email) ON DELETE CASCADE,
    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    server_id UUID NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,

    is_locked BOOLEAN DEFAULT FALSE NOT NULL,   -- TODO: Do we need it? Else remove
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,

    forwarding_policy_id UUID REFERENCES forwarding_policies(policy_id) ON DELETE SET NULL,
    distribution_policy_id UUID REFERENCES distribution_policies(policy_id) ON DELETE SET NULL,
    general_policy_id UUID REFERENCES general_policies(policy_id) ON DELETE SET NULL,

    quota_allocated NUMERIC(10,2) NOT NULL,
    quota_utilized_bytes BIGINT NOT NULL,
    total_messages_count BIGINT NOT NULL DEFAULT 0
);

-- Quota Pools and What we sell (Hierarchy)
CREATE TABLE organizations (
    organization_id UUID PRIMARY KEY,
    organization_name VARCHAR(250) UNIQUE NOT NULL,
    organization_info JSONB NOT NULL,  -- metadata, not indexed
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    allocated_email_identities INT NOT NULL,  -- Total email identities allocated for the organization (-1 for unlimited)
    utilized_email_identities INT NOT NULL,  -- Total email identities utilized for the organization

    quota_allocated NUMERIC(10,2) NOT NULL,
    quota_utilized NUMERIC(10,2) NOT NULL,

    chat_service_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    email_service_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    file_service_enabled BOOLEAN DEFAULT FALSE NOT NULL,

    parent_organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE NOT NULL,
    hierarchy_path TEXT[] NOT NULL,       -- e.g., { 'org_name_1', 'org_name_2', 'org_name_3' }

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- MailBox Servers
CREATE TABLE servers (
    server_id UUID PRIMARY KEY,
    host_name VARCHAR(250) UNIQUE NOT NULL,   -- FQDN or IP
    server_info JSONB NOT NULL,  -- metadata, not indexed

    -- TODO: Fetch all servers based on the is_monitoring flag and show the stats on the UI and for dropdown selection
    is_monitoring BOOLEAN DEFAULT FALSE NOT NULL,   -- Is monitoring enabled on this server or not

    -- TODO: Actual storage stats should appear there for the given storage_path on UI (and a button to set the space based on it)
    is_mailbox_server BOOLEAN DEFAULT FALSE NOT NULL,  -- Is this server a mailbox server (Cloud Server) or not

    -- TODO: Stop the AI from adding new mailboxes to this server
    is_accepting_new_mailboxes BOOLEAN DEFAULT FALSE NOT NULL,  -- Is this server accepting new mailboxes or not
    -- TODO: Stop the AI from doing any of the following actions
    -- 1. Manual MailBox migration
    -- 2. Automated MailBox migration
    -- 3. Create new MailBox

    -- TODO: Remove the is_active field
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    quota_allocated NUMERIC(10,2) NOT NULL,
    quota_utilized NUMERIC(10,2) NOT NULL,

    smtp_port INT NOT NULL DEFAULT 25,  -- SMTP port
    storage_path TEXT NOT NULL,  -- e.g., '/data/vmail/'

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- MailBox that are currently being migrated/moved across servers
CREATE TABLE mailbox_migrations (
    migration_id UUID PRIMARY KEY,

    email VARCHAR(254) NOT NULL REFERENCES mailboxes(email) ON DELETE CASCADE,
    migration_status VARCHAR(50) NOT NULL,  -- e.g., 'INITIALIZING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'

    source_server_id UUID NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    target_server_id UUID NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,

    start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_time TIMESTAMPTZ,  -- NULL if still in progress

    migration_details JSONB NOT NULL  -- metadata, not indexed
);

-- IMAP Sync Jobs for Mailbox Migration
CREATE TABLE imap_sync_jobs (
    job_id UUID PRIMARY KEY,

    from_email TEXT NOT NULL,
    from_email_password TEXT NOT NULL,
    from_imap_server TEXT NOT NULL,
    from_imap_port INT NOT NULL,

    to_email TEXT NOT NULL REFERENCES mailboxes(email) ON DELETE CASCADE,
    to_domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,
    sync_status VARCHAR(50) NOT NULL,  -- e.g., 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'

    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--------------------- ### Enum Types ### ---------------------


-- Enum Type for Status Maintenance Severity
CREATE TYPE maintenance_severity_enum AS ENUM (
    'LOW',        -- Low Severity
    'MEDIUM',     -- Medium Severity
    'HIGH',       -- High Severity
    'CRITICAL'    -- Critical Severity
);

-- Enum Type for Policy Rules
CREATE TYPE rule_type_enum AS ENUM (
    'ANYONE',           -- Anyone can send email to this group of mailboxes
    'GROUP_MEMBER',     -- Any group member can send email to this group of mailboxes
    'DOMAIN_MEMBER',    -- Any one in the domain can send email
    'SPECIFIC_EMAILS'   -- Specific email addresses can send email
);

-- Enum Type for Ticket Status
CREATE TYPE ticket_status_enum AS ENUM (
    'OPEN',            -- Ticket is open
    'IN_PROGRESS',     -- Ticket is being worked on
    'RESOLVED'        -- Ticket has been resolved / closed
);


--------------------- ### Chat Service Tables ### ---------------------


-- Service Settings
CREATE TABLE chat_settings (
    organization_id UUID PRIMARY KEY REFERENCES organizations(organization_id) ON DELETE CASCADE,

    enable_file_sharing BOOLEAN DEFAULT FALSE NOT NULL, -- Enable or disable file sharing in chat
    file_size_limit_mb INT NOT NULL DEFAULT 0,  -- 0 to 1000 (in MB) [0 means no file sharing allowed]
    enable_group_chat BOOLEAN DEFAULT FALSE NOT NULL,   -- Channels / Groups / Team / Rooms
    enable_direct_chat BOOLEAN DEFAULT FALSE NOT NULL,  -- one-on-one

    -- Global Quota for Chat Service (Taken from the organization's total quota)
    quota_allocated NUMERIC(10,2) NOT NULL,
    quota_utilized NUMERIC(10,2) NOT NULL,

    -- TODO: Files should be deleted after deleting the msg

    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Users
CREATE TABLE chat_users (
    email VARCHAR(254) PRIMARY KEY REFERENCES email_identities(email) ON DELETE CASCADE,
    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,

    last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--------------------- ### File Service Tables ### ---------------------


-- Service Settings
CREATE TABLE file_settings (
    organization_id UUID PRIMARY KEY REFERENCES organizations(organization_id) ON DELETE CASCADE,

    is_file_versioning_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Enable or disable file versioning
    is_sharing_enabled BOOLEAN DEFAULT FALSE NOT NULL,  -- Enable or disable file sharing

    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Users
CREATE TABLE file_users (
    email VARCHAR(254) PRIMARY KEY REFERENCES email_identities(email) ON DELETE CASCADE,
    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,

    quota_allocated NUMERIC(10,2) NOT NULL,
    quota_utilized NUMERIC(10,2) NOT NULL,

    last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--------------------- ### CRM Tables ### ---------------------


-- Purchase Order
CREATE TABLE purchase_orders (
    po_id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    po_name VARCHAR(100) NOT NULL,  -- Purchase Order Number / Name
    po_description TEXT NOT NULL,    -- Description of the Purchase Order
    po_status VARCHAR(50) NOT NULL,  -- e.g., 'pending', 'approved', 'rejected'
    po_date TIMESTAMPTZ NOT NULL,        -- Date of the Purchase Order
    total_amount NUMERIC(10,2) NOT NULL,  -- Total amount of the Purchase Order

    details JSONB NOT NULL  -- metadata, not indexed
);

-- 1 Month prior to the po_date, we will send a renewal reminder to the organization (if the po_status is not 'approved' yet)

-- Services We Sell
CREATE TABLE services (
    service_code VARCHAR(7) PRIMARY KEY,  -- e.g., 'CFS' -> 'Cloud File Storage' (code for the service)
    service_name VARCHAR(250) NOT NULL,
    service_description TEXT NOT NULL,  -- Description of the service
    service_info JSONB NOT NULL,  -- metadata, not indexed
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- Service Assignments to Purchase Orders
CREATE TABLE service_assignments (
    assignment_id UUID PRIMARY KEY,
    po_id UUID NOT NULL REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
    service_code VARCHAR(7) NOT NULL REFERENCES services(service_code) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    notes TEXT NOT NULL,  -- Description of the service assignment
    service_details JSONB NOT NULL  -- metadata, not indexed
);

-- TODO: Have a meet with Chetan, Nik, Sreedevi (Acc.) [Alerts for Invoice, Payment, Renewal, etc.]
-- TODO: PerformaInvoice as a new table, 

-- Invoice for Organization
CREATE TABLE invoices (
    invoice_id VARCHAR(20) PRIMARY KEY,  -- e.g., '2025-26/001'
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    invoice_date TIMESTAMPTZ NOT NULL,  -- Date of the invoice
    is_paid BOOLEAN DEFAULT FALSE NOT NULL,  -- Is the invoice paid

    alerts JSONB NOT NULL,  -- metadata, not indexed will have alerts like Reminder setups, whome to send, etc.
    due_date TIMESTAMPTZ NOT NULL,  -- Due date for the invoice payment

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Revision Version of the Invoice (First invoice will be the first revision)
CREATE TABLE invoice_revisions (
    revision_id UUID PRIMARY KEY,
    invoice_id VARCHAR(20) NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,

    revision_number INT NOT NULL CHECK (revision_number > 0),  -- e.g., 1, 2, 3, etc.
    revision_date TIMESTAMPTZ NOT NULL,  -- Date of the revision
    revision_details JSONB NOT NULL,  -- Details of the revision (e.g., changes, description, etc.)

    invoice_details JSONB NOT NULL,  -- Full details of the invoice at this revision (e.g., items, amounts, etc.)

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (invoice_id, revision_number)  -- Unique constraint on invoice_id and revision_number
);


--------------------- ### Other Tables ### ---------------------


-- Disclaimer to add on every email
CREATE TABLE disclaimers (
    disclaimer_id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    disclaimer_name VARCHAR(250) NOT NULL,
    info JSONB NOT NULL,  -- metadata, not indexed

    html_content TEXT NOT NULL,  -- HTML content of the disclaimer
    text_content TEXT NOT NULL,  -- Text content of the disclaimer

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (organization_id, disclaimer_name)
);

-- Department for mailbox
CREATE TABLE departments (
    department_id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    department_name VARCHAR(250) NOT NULL,
    details JSONB NOT NULL,  -- metadata, not indexed

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (organization_id, department_name)
);

-- Caution for domains
CREATE TABLE cautions (
    caution_id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    caution_name VARCHAR(250) NOT NULL,
    info JSONB NOT NULL,  -- metadata, not indexed

    html_content TEXT NOT NULL,  -- HTML content of the caution
    text_content TEXT NOT NULL,  -- Text content of the caution

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (organization_id, caution_name)
);

-- Time Based One-Time Passwords (TOTP) for 2FA
CREATE TABLE totp (
    totp_id UUID PRIMARY KEY,
    totp_name VARCHAR(100) NOT NULL,  -- e.g., 'My Office Phone'
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    totp_secret TEXT NOT NULL,  -- Base32 encoded secret for TOTP
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (user_id, totp_name)
);

-- Backup Codes for any 2FA method
CREATE TABLE backup_codes (
    code_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code VARCHAR(6) NOT NULL,  -- e.g., 'ABC123'
    is_used BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (user_id, code)
);

-- Filters Policy List for Domains (Black White List)
CREATE TABLE filter_policies (
    policy_id UUID PRIMARY KEY,
    policy_name TEXT NOT NULL,  -- e.g., 'Corporate White List'

    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,
    white_entries TEXT[] NOT NULL,  -- e.g., ['example.com', 'test@example.com']
    black_entries TEXT[] NOT NULL,  -- e.g., ['spam.com', 'spammer@example.com']

    is_active BOOLEAN DEFAULT TRUE NOT NULL,  -- Is the policy active
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    UNIQUE (domain_name, policy_name)
);

-- General Policicy
CREATE TABLE general_policies (
    policy_id UUID PRIMARY KEY,
    policy_name TEXT NOT NULL,  -- e.g., 'Corporate Email Sending/Receiving Policy'
    policy_description TEXT NOT NULL,  -- Description of the policy

    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    block_all_incoming_emails BOOLEAN DEFAULT FALSE NOT NULL,  -- Block all incoming emails if TRUE
    block_all_outgoing_emails BOOLEAN DEFAULT FALSE NOT NULL,  -- Block all outgoing emails if TRUE

    block_all_incoming_domains BOOLEAN DEFAULT FALSE NOT NULL,  -- Block all incoming emails from all domains if TRUE
    block_all_outgoing_domains BOOLEAN DEFAULT FALSE NOT NULL,  -- Block all outgoing emails to all domains if TRUE

    incoming_exception_domains TEXT[] NOT NULL,  -- e.g., ['example.com', 'another.com']
    outgoing_exception_domains TEXT[] NOT NULL,  -- e.g., ['example.com', 'another.com']

    incoming_exception_emails TEXT[] NOT NULL,  -- e.g., ['test@test.com', 'test2@test.com']
    outgoing_exception_emails TEXT[] NOT NULL,  -- e.g., ['test@test.com', 'test2@test.com']

    outgoing_size_limit_mb NUMERIC(5,2) NOT NULL,  -- Size limit for outgoing emails in MB

    is_active BOOLEAN DEFAULT TRUE NOT NULL,  -- Is the policy active
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    UNIQUE (domain_name, policy_name)
);

-- Attachment Policies for Domains (Attachment Restrictions)
CREATE TABLE attachment_policies (
    policy_id UUID PRIMARY KEY,
    policy_name TEXT NOT NULL,  -- e.g., 'Corporate Attachment Policy'
    policy_description TEXT NOT NULL,  -- Description of the policy

    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,
    blocked_file_types TEXT[] NOT NULL,  -- e.g., ['exe', 'bat', 'cmd']
    allowed_file_types TEXT[] NOT NULL,  -- e.g., ['pdf', 'docx', 'xlsx']
    max_attachment_size_mb NUMERIC(5,2) NOT NULL,  -- Max attachment size in MB

    is_active BOOLEAN DEFAULT TRUE NOT NULL,  -- Is the policy active
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    UNIQUE (domain_name, policy_name)
);

-- Restriction Policies for E-Mail Identities (IP/Geo Restrictions)
CREATE TABLE restriction_policies (
    policy_id UUID PRIMARY KEY,
    policy_name TEXT NOT NULL,  -- e.g., 'Corporate IP/Geo Restriction Policy'
    policy_description TEXT NOT NULL,  -- Description of the policy

    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    ip_restriction TEXT[],  -- e.g., ['0.0.0.0/0', '123.123.123.123/32']
    geo_restriction TEXT[],  -- e.g., ['US', 'IN'] (ISO country codes)

    is_active BOOLEAN DEFAULT TRUE NOT NULL,  -- Is the policy active

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    UNIQUE (organization_id, policy_name)
);

-- Conditional Email Forwarding Policies for Mailboxes (e.g., based on subject, from email, etc.)
CREATE TABLE forwarding_policies (
    policy_id UUID PRIMARY KEY,
    policy_name TEXT NOT NULL,  -- e.g., 'Important Emails Forwarding Policy'
    policy_description TEXT NOT NULL,  -- Description of the policy

    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    subject_contains TEXT[],  -- e.g., ['Important', 'Urgent']
    from_emails TEXT[],  -- e.g., ['from@nekonik.com']
    forward_to_emails TEXT[],  -- e.g., ['destination@email.com']

    is_active BOOLEAN DEFAULT TRUE NOT NULL,  -- Is the policy active

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    UNIQUE (domain_name, policy_name)
);

-- Mailbox Distribution Policies (For GROUP or ALIAS type mailboxes)
CREATE TABLE distribution_policies (
    policy_id UUID PRIMARY KEY,
    policy_name TEXT NOT NULL,  -- e.g., 'Team Distribution Policy'
    policy_description TEXT NOT NULL,  -- Description of the policy

    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    rule_type rule_type_enum NOT NULL DEFAULT 'ANYONE',
    specific_emails TEXT[] NOT NULL DEFAULT '{}',  -- e.g., ['specific@mail.com']
    internal_members TEXT[],  -- List of internal mailbox emails
    external_members TEXT[],  -- List of external email addresses

    is_active BOOLEAN DEFAULT TRUE NOT NULL,  -- Is the policy active

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    UNIQUE (domain_name, policy_name)
);

-- IP based Geo Locations
CREATE TABLE ip_geo_locations (
    network CIDR PRIMARY KEY,
    country_iso_code TEXT NOT NULL,
    country_name TEXT NOT NULL
);

-- Status Maintenance Alerts
CREATE TABLE maintenance_alerts (
    maintenance_id SERIAL PRIMARY KEY,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    title TEXT NOT NULL,
    description TEXT NOT NULL,
    affected TEXT[] NOT NULL,

    severity maintenance_severity_enum NOT NULL,
    type TEXT NOT NULL,

    start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_time TIMESTAMPTZ NOT NULL
);

-- Ticketing System / Support Tickets Table
CREATE TABLE support_tickets (
    ticket_id SERIAL PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    ticket_title TEXT NOT NULL,
    ticket_description TEXT NOT NULL,
    ticket_status ticket_status_enum NOT NULL DEFAULT 'OPEN',
    details JSONB NOT NULL,  -- e.g., { "priority": "high", "category": "billing", "attachments": [file_id1, file_id2] }

    created_by VARCHAR(254) REFERENCES users(user_name) ON DELETE SET NULL,
    assigned_to TEXT[],  -- List of user_ids assigned to the ticket

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Ticket Follow-ups / Discussions (Chat-like)
CREATE TABLE ticket_follow_ups (
    follow_up_id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES support_tickets(ticket_id) ON DELETE CASCADE,

    message TEXT NOT NULL,
    details JSONB NOT NULL,  -- e.g., { "attachments": [file_id1, file_id2] }

    created_by VARCHAR(254) REFERENCES users(user_name) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- API Keys for external clients
CREATE TABLE api_keys (
    key_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    api_key UUID UNIQUE NOT NULL,  -- Actual API Key (to be given to clients)
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    key_name VARCHAR(100) NOT NULL,
    permissions TEXT[] NOT NULL,  -- e.g., ['read:mailboxes', 'write:mailboxes']

    details JSONB NOT NULL,  -- metadata, not indexed
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    -- TODO: Add expiration date for API keys
    expired_at TIMESTAMPTZ NOT NULL,

    UNIQUE (organization_id, key_name)
);

-- Email Client Sessions
CREATE TABLE mailbox_sessions (
    origin_ip VARCHAR(45) NOT NULL,  -- IPv4 or IPv6
    attempted_by VARCHAR(254) NOT NULL REFERENCES mailboxes(email) ON DELETE CASCADE,
    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    geo_ip_location JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,    -- Is the session active

    attempted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    session_expires_at TIMESTAMPTZ NOT NULL,

    PRIMARY KEY (origin_ip, attempted_by)
);  -- TODO: Every 1 Minute, we run the clean up cron job, to delete the expired sessions

-- Auth App Sessions
CREATE TABLE mail25_app_sessions (
    session_id UUID PRIMARY KEY,
    email VARCHAR(254) NOT NULL REFERENCES email_identities(email) ON DELETE CASCADE,
    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,

    phone VARCHAR(20) NOT NULL,  -- Phone number used for authentication
    fcm_token TEXT NOT NULL,  -- FCM token for push notifications

    device_details JSONB NOT NULL,

    last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
    -- TODO: Add session expiry on App level (e.g., after 10 days of inactivity) [Maintain Last Active At timestamp]
    -- Add Last Active At timestamp, then run a cron job to delete expired sessions
);

-- SSO (Single Sign-On) Sessions (only for MailBox/E-Mail based users)
CREATE TABLE sso_sessions (
    session_id UUID PRIMARY KEY,    -- Cookie based session ID for SSO session
    email VARCHAR(254) NOT NULL REFERENCES email_identities(email) ON DELETE CASCADE,
    domain_name VARCHAR(254) NOT NULL REFERENCES domains(domain_name) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,

    encrypted_password TEXT NOT NULL,  -- We need it for IMAP / SMTP calls

    device_details JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,    -- Is the session active

    -- When the SSO session was created
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    -- When the user last authenticated using this SSO session
    last_auth_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--------------------- ### INDEXES ### ---------------------


CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_support_tickets_ticket_title_gin ON support_tickets USING GIN (ticket_title gin_trgm_ops);
CREATE INDEX idx_restriction_policies_policy_name_gin ON restriction_policies USING GIN (policy_name gin_trgm_ops);
CREATE INDEX idx_mailboxes_email_gin ON mailboxes USING GIN (email gin_trgm_ops);
CREATE INDEX idx_forwarding_policies_policy_name_gin ON forwarding_policies USING GIN (policy_name gin_trgm_ops);
CREATE INDEX idx_distribution_policies_policy_name_gin ON distribution_policies USING GIN (policy_name gin_trgm_ops);
CREATE INDEX idx_general_policies_policy_name_gin ON general_policies USING GIN (policy_name gin_trgm_ops);
CREATE INDEX idx_filter_policies_policy_name_gin ON filter_policies USING GIN (policy_name gin_trgm_ops);
CREATE INDEX idx_departments_department_name_gin ON departments USING GIN (department_name gin_trgm_ops);
CREATE INDEX idx_cautions_caution_name_gin ON cautions USING GIN (caution_name gin_trgm_ops);
CREATE INDEX idx_disclaimers_disclaimer_name_gin ON disclaimers USING GIN (disclaimer_name gin_trgm_ops);
CREATE INDEX idx_domains_domain_name_gin ON domains USING GIN (domain_name gin_trgm_ops);
CREATE INDEX idx_attachment_policies_policy_name_gin ON attachment_policies USING GIN (policy_name gin_trgm_ops);
CREATE INDEX idx_distribution_policy_active ON distribution_policies(policy_id) WHERE is_active;
CREATE INDEX idx_domains_active ON domains(domain_name) WHERE is_active;
CREATE INDEX idx_org_active ON organizations(organization_id) WHERE is_active;
CREATE INDEX idx_general_policy_active ON general_policies(policy_id) WHERE is_active;
CREATE INDEX idx_mailbox_enabled ON mailboxes(email) WHERE is_enabled;
CREATE INDEX idx_email_identity_login ON email_identities(email) WHERE is_enabled AND NOT is_password_expired;
CREATE INDEX idx_server_active ON servers(server_id) WHERE is_active;
CREATE INDEX idx_forwarding_policy_active ON forwarding_policies(policy_id) WHERE is_active;
CREATE INDEX idx_mailboxes_domain_enabled ON mailboxes(domain_name) WHERE is_enabled;
CREATE INDEX idx_mailbox_login ON mailboxes(email, server_id) WHERE is_enabled AND NOT is_locked;
CREATE INDEX idx_mailbox_server_lookup ON mailboxes(server_id,email) WHERE is_enabled AND NOT is_locked;
CREATE INDEX idx_domains_created ON domains(created_at);
CREATE INDEX idx_mailbox_email_cover ON mailboxes(email) INCLUDE(server_id, forwarding_policy_id, distribution_policy_id, general_policy_id, domain_name) WHERE is_enabled;
CREATE INDEX idx_mailboxes_server ON mailboxes(server_id);
CREATE INDEX idx_mailboxes_distribution_policy ON mailboxes(distribution_policy_id);
CREATE INDEX idx_mailboxes_forwarding_policy ON mailboxes(forwarding_policy_id);
CREATE INDEX idx_mailboxes_general_policy ON mailboxes(general_policy_id);
CREATE INDEX idx_domains_managed_by ON domains(managed_by);
CREATE INDEX idx_email_identities_domain ON email_identities(domain_name);
CREATE INDEX ON ip_geo_locations USING gist (network inet_ops);
CREATE INDEX idx_users_org_created_at ON users (organization_id, created_at DESC);
CREATE INDEX idx_support_tickets_org_updated ON support_tickets (organization_id, updated_at DESC);
CREATE INDEX idx_ticket_follow_ups_ticket_created ON ticket_follow_ups (ticket_id, created_at DESC);
CREATE INDEX idx_mailbox_migrations_source_start ON mailbox_migrations (source_server_id, start_time DESC);
CREATE INDEX idx_mailbox_migrations_email_start ON mailbox_migrations (email, start_time DESC);
CREATE INDEX idx_mailbox_migrations_target_server ON mailbox_migrations (target_server_id);
CREATE INDEX idx_mailbox_migrations_email_inprogress ON mailbox_migrations (email) WHERE migration_status IN ('INITIALIZING','IN_PROGRESS');
CREATE INDEX idx_imap_sync_jobs_domain_updated ON imap_sync_jobs (to_domain_name, updated_at DESC);
CREATE INDEX idx_mailboxes_domain_email ON mailboxes (domain_name, email);
CREATE INDEX idx_mailboxes_server_email ON mailboxes (server_id, email);
CREATE INDEX idx_domains_managed_by_domain ON domains (managed_by, domain_name);
CREATE INDEX idx_org_parent_name ON organizations (parent_organization_id, organization_name);
CREATE INDEX idx_api_keys_org_created ON api_keys (organization_id, created_at DESC);
CREATE INDEX idx_purchase_orders_org_podate ON purchase_orders (organization_id, po_date DESC);
CREATE INDEX idx_service_assignments_po_id ON service_assignments (po_id);
CREATE INDEX idx_invoices_org_date ON invoices (organization_id, invoice_date DESC);
CREATE INDEX idx_invoices_invoice_id_trgm ON invoices USING GIN (invoice_id gin_trgm_ops);
CREATE INDEX idx_servers_host_name_trgm ON servers USING GIN (host_name gin_trgm_ops);
CREATE INDEX idx_chat_users_domain_last_active ON chat_users (domain_name, last_active_at DESC);
CREATE INDEX idx_file_users_domain_last_active ON file_users (domain_name, last_active_at DESC);
CREATE INDEX idx_mail25_app_sessions_domain_last_active ON mail25_app_sessions (domain_name, last_active_at DESC);
CREATE INDEX idx_sso_sessions_domain_last_auth ON sso_sessions (domain_name, last_auth_at DESC);
CREATE INDEX idx_cautions_org_updated ON cautions (organization_id, updated_at DESC);
CREATE INDEX idx_departments_org_updated ON departments (organization_id, updated_at DESC);
CREATE INDEX idx_disclaimers_org_created ON disclaimers (organization_id, created_at DESC);
CREATE INDEX idx_email_identities_domain_updated ON email_identities (domain_name, updated_at DESC);
CREATE INDEX idx_support_tickets_org_status_updated ON support_tickets (organization_id, ticket_status, updated_at DESC);
CREATE INDEX idx_support_tickets_created_by ON support_tickets (created_by);
CREATE INDEX idx_support_tickets_assigned_to_gin ON support_tickets USING GIN (assigned_to);
CREATE INDEX idx_support_tickets_open_updated ON support_tickets (organization_id, updated_at DESC) WHERE ticket_status <> 'RESOLVED';
CREATE INDEX idx_mailbox_sessions_domain_attempted_at ON mailbox_sessions (domain_name, attempted_at DESC);
CREATE INDEX idx_mailbox_sessions_expires_at ON mailbox_sessions (session_expires_at);
CREATE INDEX idx_totp_user_created_at ON totp (user_id, created_at DESC);
CREATE INDEX idx_totp_user_active ON totp (user_id) WHERE is_active = TRUE;
CREATE INDEX idx_backup_codes_user_unused ON backup_codes (user_id) WHERE is_used = FALSE;
CREATE INDEX idx_sso_sessions_domain_active_last_auth ON sso_sessions (domain_name, is_active, last_auth_at DESC);
CREATE INDEX idx_filter_policies_domain_updated ON filter_policies (domain_name, updated_at DESC);
CREATE INDEX idx_forwarding_policies_domain_updated ON forwarding_policies (domain_name, updated_at DESC);
CREATE INDEX idx_distribution_policies_domain_updated ON distribution_policies (domain_name, updated_at DESC);
CREATE INDEX idx_general_policies_domain_updated ON general_policies (domain_name, updated_at DESC);
CREATE INDEX idx_attachment_policies_domain_updated ON attachment_policies (domain_name, updated_at DESC);
CREATE INDEX idx_restriction_policies_org_updated ON restriction_policies (organization_id, updated_at DESC);
```


# Assumptions for the System Design and Scaling

- There will be around `500 organizations` in the system (`2 distributors`, `50 partners`, and `400 normal organizations`)
- Users will be around `10,000` in total
- Each organization will have around `20 users` on average
- Domains will be around `2,000` in total (around `4 domains` per organization)
- Mailboxes will be around `2,00,000` in total (around `400 mailboxes` per organization)


# TODO: Automatically move mailboxes to another server if the current server is full or has high load
    - Have a Cron Job that checks every day for servers that are full or have high load with lots of MailBoxes
    - Based on the MailBox usage, move the MailBoxes to another server that has less load and more space
    - Note: Make sure that the MailBox migration is done in a way that the user does not notice any downtime or loss of emails
    - Note: The MailBox migration should follow the Server Lock / MailBox Lock / Domain Lock rules to avoid any unexpected issues
