# Helpful SQL Queries

- Locked Domains with Mailboxes on Unauthorized Servers

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


- Re-Assign Mailboxes to Locked Servers but Only if a specific server is currently assigned

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
