"""
All the models used in the API are defined here
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


from .generic import All_Exceptions, UserSession
from .query_forms import (
    CreateGeneralPolicyListEntryForm,
    CreateFiltersPolicyListEntryForm,
    AdminFilterSupportTicketsForm,
    CreateDistributionPolicyForm,
    FileServiceConfigUpdateForm,
    ChatServiceConfigUpdateForm,
    CreateRestrictionPolicyForm,
    CreateForwardingPolicyForm,
    CreateCautionMessageForm,
    CreateSupportTicketForm,
    LoginAttemptsSearchForm,
    CreateAttachmentPolicy,
    CreateOrganizationForm,
    UpdateMailBoxInfoForm,
    CreateRevisedInvoice,
    CreateDisclaimerForm,
    CreateDepartmentForm,
    FilesUserCreateForm,
    ConnectorProperties,
    CreatePOServiceLink,
    CreatePurchaseOrder,
    IMAPSyncCreateForm,
    MailFlowSearchForm,
    CreateMailBoxForm,
    CreateDomainForm,
    CreateServerForm,
    CreateCRMService,
    CreateAPIKeyForm,
    AuditSearchForm,
    PatchDomainForm,
    CreateIdentity,
    CreateUserForm,
    CreateInvoice,
    PasswdReset,
    AuthRequest,
    AddAuditLog
)


__version__ = "v1.9.2-phoenix-release"


__annotations__ = {
    "version": __version__,
    "All_Exceptions": "Class for handling wrong input exceptions",
    "AuthRequest": "Login form for the endpoint",
    "CreateUserForm": "Create user form for the endpoint",
    "CreateOrganizationForm": "Create organization form for the endpoint",
    "CreateDomainForm": "Create domain form for the endpoint",
    "PasswdReset": "Password reset form for the endpoint",
    "CreateMailBoxForm": "Create mailbox form for the endpoint",
    "CreateServerForm": "Create server form for the endpoint",
    "ConnectorProperties": "Connector properties form for the endpoint",
    "AuditSearchForm": "Audit search form for the endpoint",
    "CreateDisclaimerForm": "Create disclaimer form for the endpoint",
    "CreateDepartmentForm": "Create department form for the endpoint",
    "UserSession": "User session model for API, used to store user session details in cache",
    "CreateCautionMessageForm": "Create caution message form for the endpoint",
    "CreateCRMService": "Create CRM service form for the endpoint",
    "CreatePurchaseOrder": "Create purchase order form for the endpoint",
    "CreatePOServiceLink": "Create purchase order service link form for the endpoint",
    "AddAuditLog": "Add audit log form for the endpoint",
    "CreateFiltersPolicyListEntryForm": "Create Filters Policy list entry form for the endpoint",
    "CreateGeneralPolicyListEntryForm": "Create general Policy list entry form for the endpoint",
    "MailFlowSearchForm": "Mail flow search form for the endpoint",
    "UpdateMailBoxInfoForm": "Update mailbox information form for the endpoint",
    "PatchDomainForm": "Patch domain form for the endpoint",
    "LoginAttemptsSearchForm": "Login attempts search form for the endpoint",
    "CreateRevisedInvoice": "Create revised invoice form for the endpoint",
    "CreateInvoice": "Create invoice form for the endpoint",
    "CreateAttachmentPolicy": "Create attachment policy form for the endpoint",
    "CreateSupportTicketForm": "Create support ticket form for the endpoint",
    "AdminFilterSupportTicketsForm": "Admin filter support tickets form for the endpoint",
    "CreateAPIKeyForm": "Create API key form for the endpoint",
    "CreateRestrictionPolicyForm": "Create restriction policy form for the endpoint",
    "CreateDistributionPolicyForm": "Create distribution policy form for the endpoint",
    "CreateForwardingPolicyForm": "Create forwarding policy form for the endpoint",
    "IMAPSyncCreateForm": "Create IMAP Sync Job form for the endpoint",
    "ChatServiceConfigUpdateForm": "Chat Service related configurations update form for the endpoint",
    "CreateIdentity": "Create Identity form for the endpoint",
    "FileServiceConfigUpdateForm": "File Service related configurations update form for the endpoint",
    "FilesUserCreateForm": "Create Files user form for the endpoint"
}


__all__ = [
    "All_Exceptions",
    "AuthRequest",
    "CreateUserForm",
    "CreateOrganizationForm",
    "CreateDomainForm",
    "ConnectorProperties",
    "CreateMailBoxForm",
    "CreateServerForm",
    "AuditSearchForm",
    "PasswdReset",
    "CreateDisclaimerForm",
    "CreateDepartmentForm",
    "UserSession",
    "CreateCautionMessageForm",
    "CreateCRMService",
    "CreatePurchaseOrder",
    "AddAuditLog",
    "CreatePOServiceLink",
    "CreateFiltersPolicyListEntryForm",
    "CreateGeneralPolicyListEntryForm",
    "MailFlowSearchForm",
    "UpdateMailBoxInfoForm",
    "PatchDomainForm",
    "LoginAttemptsSearchForm",
    "CreateRevisedInvoice",
    "CreateInvoice",
    "CreateAttachmentPolicy",
    "CreateSupportTicketForm",
    "AdminFilterSupportTicketsForm",
    "CreateAPIKeyForm",
    "CreateRestrictionPolicyForm",
    "CreateDistributionPolicyForm",
    "CreateForwardingPolicyForm",
    "IMAPSyncCreateForm",
    "ChatServiceConfigUpdateForm",
    "CreateIdentity",
    "FileServiceConfigUpdateForm",
    "FilesUserCreateForm"
]
