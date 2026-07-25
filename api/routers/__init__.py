"""
All Routers are imported here and are exposed to the main app file
"""

"""
Copyright (C) 2026 Yukthi Systems Private Limited

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3
as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
version 3 along with this program. If not, see
<https://www.gnu.org/licenses/>.
"""


from .distribution_policies import router as distribution_policy_router
from .restriction_policy import router as restriction_policy_router
from .forwarding_policies import router as forwarding_policy_router
from .attachment_policy import router as attachment_policy_router
from .email_identities import router as email_identity_router
from .filters_policy import router as filters_policy_router
from .general_policy import router as general_policy_router
from .organization import router as organization_router
from .backup_codes import router as backup_code_router
from .maintenance import router as maintenance_router
from .disclaimer import router as disclaimer_router
from .department import router as department_router
from .phone_auth import router as phone_auth_router
from .email_auth import router as email_auth_router
from .files_conf import router as files_conf_router
from .ticketing import router as ticketing_router
from .dashboard import router as dashboard_router
from .imap_sync import router as imap_sync_router
from .caution import router as caution_router
from .mailbox import router as mailbox_router
from .servers import router as server_router
from .chat_conf import router as chat_router
from .domain import router as domain_router
from .logs import router as logs_router
from .totp import router as totp_router
from .user import router as user_router
from .crm import router as crm_router
from .api import router as api_router


__version__ = "v3.5.1-phoenix-release"


__annotations__ = {
    "version": __version__,
    "user_router": "User Login and session management related endpoints",
    "organization_router": "Organization related endpoints",
    "domain_router": "Domain related endpoints",
    "mailbox_router": "Mailbox related endpoints",
    "logs_router": "Logs related endpoints",
    "server_router": "MailBox Server related endpoints",
    "disclaimer_router": "Disclaimer related endpoints",
    "department_router": "Department related endpoints",
    "caution_router": "Caution Message related endpoints",
    "crm_router": "CRM related endpoints",
    "totp_router": "Time Based One Time Password (TOTP) related endpoints",
    "backup_code_router": "Backup Code related endpoints",
    "phone_auth_router": "2FA Phone Authentication related endpoints",
    "email_auth_router": "2FA Email Authentication related endpoints",
    "filters_policy_router": "Filters Policy List management related endpoints",
    "general_policy_router": "General Policy List management related endpoints",
    "dashboard_router": "Dashboard related endpoints for metrics and logs",
    "attachment_policy_router": "Attachment Policy List management related endpoints",
    "maintenance_router": "Maintenance and Tickets related endpoints",
    "ticketing_router": "Ticketing related endpoints",
    "distribution_policy_router": "Distribution Policy List management related endpoints",
    "forwarding_policy_router": "Forwarding Policy List management related endpoints",
    "restriction_policy_router": "Restriction Policy List management related endpoints",
    "api_router": "API related endpoints",
    "imap_sync_router": "IMAP Sync related endpoints",
    "chat_router": "Chat related endpoints",
    "email_identity_router": "Email Identity related endpoints",
    "files_conf_router": "Files Configuration related endpoints"
}


__all__ = [
    "user_router",
    "organization_router",
    "domain_router",
    "mailbox_router",
    "logs_router",
    "server_router",
    "disclaimer_router",
    "department_router",
    "caution_router",
    "crm_router",
    "totp_router",
    "backup_code_router",
    "phone_auth_router",
    "email_auth_router",
    "filters_policy_router",
    "general_policy_router",
    "dashboard_router",
    "attachment_policy_router",
    "maintenance_router",
    "ticketing_router",
    "restriction_policy_router",
    "distribution_policy_router",
    "forwarding_policy_router",
    "api_router",
    "imap_sync_router",
    "chat_router",
    "email_identity_router",
    "files_conf_router"
]
