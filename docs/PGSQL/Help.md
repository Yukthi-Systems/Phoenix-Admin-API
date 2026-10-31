# Helpful SQL Queries

This document contains helpful SQL queries for managing domains, mailboxes, and database information in PostgreSQL.

## Locked Domains with Mailboxes on Unauthorized Servers

```sql
SELECT
    d.domain_name,
    mb.email,
    mb.server_id AS mailbox_server_id,
    d.locked_servers_group AS allowed_locked_server_ids
FROM domains d
JOIN mailboxes mb
    ON mb.domain_name = d.domain_name
WHERE d.is_locked = TRUE
  AND NOT (mb.server_id = ANY(d.locked_servers_group))
ORDER BY d.domain_name, mb.email;
```


## Re-Assign Mailboxes to Locked Servers but Only if a specific server is currently assigned

```sql
UPDATE mailboxes AS mb
SET server_id = d.locked_servers_group[1]
FROM domains AS d
WHERE mb.domain_name = d.domain_name
  AND d.is_locked = TRUE
  AND d.locked_servers_group IS NOT NULL
  AND array_length(d.locked_servers_group, 1) = 1
  AND NOT (mb.server_id = ANY(d.locked_servers_group))
  AND mb.server_id = 'xxxx-xxxx-xxxx-xxxx-xxxx'::UUID
RETURNING
    mb.domain_name,
    mb.email,
    mb.server_id AS updated_server_id;
```


## Database Size

```sql
SELECT
    current_database() AS database_name,
    pg_size_pretty(pg_database_size(current_database())) AS database_size,
    pg_database_size(current_database()) AS database_size_bytes;
```


## Table Sizes

```sql
SELECT
    schemaname AS schema_name,
    relname AS table_name,
    n_live_tup AS estimated_row_count,
    pg_size_pretty(pg_table_size(relid)) AS table_size,
    pg_size_pretty(pg_indexes_size(relid)) AS indexes_size,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_total_relation_size(relid) AS total_size_bytes
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```


## Cache Hit Ratio

```sql
SELECT
    sum(blks_hit) AS cache_hits,
    sum(blks_read) AS disk_reads,
    ROUND(
        100.0 * sum(blks_hit) /
        NULLIF(sum(blks_hit) + sum(blks_read), 0),
        2
    ) AS cache_hit_ratio
FROM pg_stat_database
WHERE datname = current_database();
```


## Database Activity

```sql
SELECT
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit,
    tup_returned,
    tup_fetched,
    tup_inserted,
    tup_updated,
    tup_deleted,
    conflicts,
    deadlocks
FROM pg_stat_database
WHERE datname = current_database();
```


## Top 20 Most Accessed Tables

```sql
SELECT
    relname AS table_name,
    seq_scan,
    idx_scan,
    n_live_tup,
    n_dead_tup,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables
ORDER BY
    seq_scan + idx_scan DESC
LIMIT 20;
```


## Top 20 Tables by Sequential Reads

```sql
SELECT
    relname AS table_name,
    seq_scan,
    seq_tup_read,
    idx_scan,
    n_live_tup,
    CASE
        WHEN seq_scan > 0
        THEN ROUND(seq_tup_read::numeric / seq_scan, 2)
        ELSE 0
    END AS avg_rows_per_seq_scan
FROM pg_stat_user_tables
ORDER BY seq_tup_read DESC
LIMIT 20;
```
