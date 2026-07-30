# This file contains the permissions for the mail service v3

| Basic                     | View                                    | Create                    | Edit                                    | Delete                    |
| ------------------------- | --------------------------------------- | ------------------------- | --------------------------------------- | ------------------------- |
| Admin User                | user:view                               | user:create               | user:edit                               | user:delete               |
| Update Password           |                                         |                           | user:security:password:edit             |                           |
| Set Permissions           | user:security:permissions:view          |                           | user:security:permissions:edit          |                           |
| Permission Template       | user:security:permissions:template:view |                           | user:security:permissions:template:edit |                           |
| Configure Email - 2FA     |                                         |                           | user:security:2fa:email:edit            |                           |
| Backup Codes              | user:security:backup_codes:view         |                           | user:security:backup_codes:edit         |                           |
| Configure Phone SMS - 2FA |                                         |                           | user:security:2fa:sms_phone:edit        |                           |
| Organization              | organization:view                       | organization:create       | organization:edit                       | organization:delete       |
| Configure TOTP - 2FA      | user:security:2fa:totp:view             |                           | user:security:2fa:totp:edit             |                           |
| Email Client Sessions     | session:view                            |                           | session:edit                            | session:delete            |
| Support Tickets User-end  | support_ticket:view                     | support_ticket:create     | support_ticket:edit                     |                           |
| Support Admin             | support_admin:view                      | support_admin:create      | support_admin:edit                      | support_admin:delete      |
| Maintenance Details       |                                         | maintenance:create        | maintenance:edit                        | maintenance:delete        |
| API Keys                  | api_keys:view                           | api_keys:create           | api_keys:edit                           | api_keys:delete           |
| Chat Service Config       | chat:view                               | chat:create               | chat:edit                               | chat:delete               |
| E-Mail Identities         | identity:view                           | identity:create           | identity:edit                           | identity:delete           |
| E-Mail Identity Admin     | identity:admin:view                     |                           |                                         |                           |
| File Service Config       | file:view                               | file:create               | file:edit                               | file:delete               |


| CRM                       | View                                    | Create                    | Edit                                    | Delete                    |
| ------------------------- | --------------------------------------- | ------------------------- | --------------------------------------- | ------------------------- |
| Servers                   | server:view                             | server:create             | server:edit                             | server:delete             |
| Mail Queue                | mailq:view                              |                           | mailq:edit                              |                           |
| Service                   | crm:service:view                        | crm:service:create        | crm:service:edit                        | crm:service:delete        |
| Purchase Order            | crm:purchase_order:view                 | crm:purchase_order:create | crm:purchase_order:edit                 | crm:purchase_order:delete |
| MailBox Migration         | mailbox:migration:view                  | mailbox:migration:create  |                                         |                           |
| Invoice                   | crm:invoice:view                        | crm:invoice:create        | crm:invoice:edit                        |                           |
| Domain Migration          | domain:migration:view                   | domain:migration:create   |                                         |                           |


| Logs                      | View                                    | Create                    | Edit                                    | Delete                    |
| ------------------------- | --------------------------------------- | ------------------------- | --------------------------------------- | ------------------------- |
| Audit Logs                | logs:audit:view                         |                           |                                         |                           |
| Mail Flow Logs            | logs:mail_flow:view                     |                           |                                         |                           |
| Dashboard Metric          | dashboard:view                          |                           |                                         |                           |
| Email Login Attempts      | logs:login_attempts:view                |                           |                                         |                           |


| Mail Flow                 | View                                    | Create                    | Edit                                    | Delete                    |
| ------------------------- | --------------------------------------- | ------------------------- | --------------------------------------- | ------------------------- |
| Domains                   | domain:view                             | domain:create             | domain:edit                             | domain:delete             |
| Departments               | department:view                         | department:create         | department:edit                         | department:delete         |
| MailBox                   | mailbox:view                            | mailbox:create            | mailbox:edit                            | mailbox:delete            |
| Email Disclaimer          | disclaimer:view                         | disclaimer:create         | disclaimer:edit                         | disclaimer:delete         |
| Email Caution             | caution:view                            | caution:create            | caution:edit                            | caution:delete            |
| IMAP Sync Jobs            | imap_sync:view                          | imap_sync:create          |                                         |                           |


| Policies                  | View                                    | Create                    | Edit                                    | Delete                    |
| ------------------------- | --------------------------------------- | ------------------------- | --------------------------------------- | ------------------------- |
| Filters Policy            | policy:filters:view                     | policy:filters:create     | policy:filters:edit                     | policy:filters:delete     |
| General Policy            | policy:general:view                     | policy:general:create     | policy:general:edit                     | policy:general:delete     |
| Attachment Policy         | policy:attachment:view                  | policy:attachment:create  | policy:attachment:edit                  | policy:attachment:delete  |
| Restriction Policy        | policy:restriction:view                 | policy:restriction:create | policy:restriction:edit                 | policy:restriction:delete |
| Forwarding Policy         | policy:forwarding:view                  | policy:forwarding:create  | policy:forwarding:edit                  | policy:forwarding:delete  |
| Distribution Policy       | policy:distribution:view                | policy:distribution:create| policy:distribution:edit                | policy:distribution:delete|


```sql
-- Update permissions for the users table
UPDATE users
SET permissions = ARRAY[
    -- Users
    'user:view',
    'user:create',
    'user:edit',
    'user:delete',
    'user:security:password:edit',
    'user:security:permissions:view',
    'user:security:permissions:edit',
    'user:security:permissions:template:view',
    'user:security:permissions:template:edit',
    'user:security:2fa:email:edit',
    'user:security:backup_codes:view',
    'user:security:backup_codes:edit',
    'user:security:2fa:sms_phone:edit',
    'user:security:2fa:totp:view',
    'user:security:2fa:totp:edit',
    'organization:view',
    'organization:create',
    'organization:edit',
    'organization:delete',
    'api_keys:view',
    'api_keys:create',
    'api_keys:edit',
    'api_keys:delete',
    'chat:view',
    'chat:edit',

    -- CRM
    'server:view',
    'server:create',
    'server:edit',
    'server:delete',
    'crm:service:view',
    'crm:service:create',
    'crm:service:edit',
    'crm:service:delete',
    'crm:purchase_order:view',
    'crm:purchase_order:create',
    'crm:purchase_order:edit',
    'crm:purchase_order:delete',
    'mailbox:migration:view',
    'mailbox:migration:create',
    'crm:invoice:view',
    'crm:invoice:create',
    'crm:invoice:edit',
    'domain:migration:view',
    'domain:migration:create',
    'support_ticket:view',
    'support_ticket:create',
    'support_ticket:edit',
    'support_admin:view',
    'support_admin:create',
    'support_admin:edit',
    'support_admin:delete',
    'maintenance:create',
    'maintenance:edit',
    'maintenance:delete',

    -- Logs
    'logs:audit:view',
    'logs:mail_flow:view',
    'dashboard:view',
    'logs:login_attempts:view',
    'session:view',
    'session:edit',
    'session:delete',

    -- Mail Flow
    'domain:view',
    'domain:create',
    'domain:edit',
    'domain:delete',
    'policy:filters:view',
    'policy:filters:create',
    'policy:filters:edit',
    'policy:filters:delete',
    'policy:general:view',
    'policy:general:create',
    'policy:general:edit',
    'policy:general:delete',
    'policy:attachment:view',
    'policy:attachment:create',
    'policy:attachment:edit',
    'policy:attachment:delete',
    'department:view',
    'department:create',
    'department:edit',
    'department:delete',
    'mailbox:view',
    'mailbox:create',
    'mailbox:edit',
    'mailbox:delete',
    'disclaimer:view',
    'disclaimer:create',
    'disclaimer:edit',
    'disclaimer:delete',
    'caution:view',
    'caution:create',
    'caution:edit',
    'caution:delete'
];
```

## To update existing users with new permissions, run the following SQL command:

```sql
-- Update permissions for the users table
UPDATE users
SET permissions = permissions || ARRAY[
    'file:view',
    'file:create',
    'file:edit',
    'file:delete'
]

-- Update only one user by adding a WHERE clause
WHERE user_name = 'nikhil';
```
