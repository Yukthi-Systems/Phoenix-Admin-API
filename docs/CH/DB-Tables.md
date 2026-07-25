# Schema For Audit Logs

Audit logs are from UI and user interactions

## Schema Definition

```sql
CREATE TABLE audit_logs
(
    organization_id LowCardinality(String),

    user_id LowCardinality(String),
    message String,

    action_type LowCardinality(String),
    action_timestamp DateTime('Asia/Kolkata'),

    details JSON
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(action_timestamp)
ORDER BY (organization_id, action_timestamp)
TTL action_timestamp + INTERVAL 180 DAY
SETTINGS index_granularity = 8192;
```

## Recommended Indexes for Audit Logs

```sql
-- 1) Using ngrambf_v1 to speed up LIKE '%...%' style queries on message field
ALTER TABLE default.audit_logs ADD INDEX idx_message_token (message) TYPE ngrambf_v1(3, 4096, 2, 0) GRANULARITY 8192;

-- 2) set index on action_type to speed hasAny(...) style queries [Optional] (See if its required or not based on query patterns)
ALTER TABLE default.audit_logs ADD INDEX idx_action_type action_type TYPE set(2048) GRANULARITY 8192;
```


# Schema For Mail Flow Logs (Fuglu Logs)

Mail flow logs are from Fuglu only, where we will know what happened to the email

## Schema Definition

```sql
CREATE TABLE mail_flow_logs
(
    euid String,

    from_email_id String,
    to_email_ids Array(String),

    email_domains Array(String),
    subject String,

    type LowCardinality(String),
    status LowCardinality(String),
    status_description String,

    log_timestamp DateTime('Asia/Kolkata'),
    email_timestamp DateTime('Asia/Kolkata'),

    meta_data JSON
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(log_timestamp)
ORDER BY (log_timestamp, euid)
TTL log_timestamp + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
```

## Recommended Indexes for Mail Flow Logs

```sql
-- 1) Using ngrambf_v1 to speed up LIKE '%...%' style queries on subject field
ALTER TABLE default.mail_flow_logs ADD INDEX idx_subject_token (subject) TYPE ngrambf_v1(3, 4096, 2, 0) GRANULARITY 8192;

-- 2) Using tokenbf_v1 to speed up LIKE '...%' style queries on from_email_id field
ALTER TABLE default.mail_flow_logs ADD INDEX idx_from_ngram from_email_id TYPE tokenbf_v1(4096, 128, 2) GRANULARITY 4;

-- 3) set index on domains to speed hasAny(...) style queries
ALTER TABLE default.mail_flow_logs ADD INDEX idx_domains email_domains TYPE set(65536) GRANULARITY 8192;
```
