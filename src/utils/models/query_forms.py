"""
This module contains all the query forms for the application
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


from src.utils.base.libraries import BaseModel, Field, List, Optional, Enum, datetime


class AuthRequest(BaseModel):
    """
    Login form for the endpoint
    user_name: User name of the user
    password: Password of the user
    """
    user_name: str = Field(..., title="User Name", description="User name of the user")
    password: str = Field(..., title="Password", description="Password of the user")
    recaptcha_token: str = Field(..., title="Recaptcha Token", description="Recaptcha token for bot prevention")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "user_name": "UserName",
                "password": "Base64-encoded-password",
                "recaptcha_token": "recaptcha-token"
            }
        }


class PasswdReset(BaseModel):
    """
    Reset password form for the endpoint
    """
    user_id: str = Field(..., title="User ID - UUID", description="ID of the user to reset the password for")
    password: str = Field(..., title="Password", description="Password of the user")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                # Example UUID for user_id: uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "user_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "password": "Base64-encoded-password"
            }
        }


class CreateUserForm(BaseModel):
    """
    Create user form for the endpoint
    """
    user_name: str = Field(..., title="User Name", description="User name of the user")
    user_email: str = Field(..., title="User Email", description="Email of the user")
    primary_phone_number_with_country_code: str = Field(..., title="Primary Phone Number with Country Code", description="Primary phone number of the user with country code")
    display_name: str = Field(..., title="Display Name", description="Display name of the user")
    base64_password: str = Field(..., title="Password", description="Password of the user in base64 format")
    activate: bool = Field(..., title="Activate", description="Activate the user - is_active")
    user_details: dict = Field(..., title="User Details", description="User details of the user")
    permissions_template: Optional[dict] = Field({}, title="Permissions Template", description="Permissions templates for the user to be used")
    permissions: List[str] = Field(..., title="Permissions", description="Permissions given to the user")
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization to which the user belongs")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "user_name": "nik",
                "user_email": "nik@example.com",
                "primary_phone_number_with_country_code": "+1234567890",
                "display_name": "Example",
                "base64_password": "Base64-encoded-password",
                "activate": True,
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "permissions_template": {
                    "basic": [
                        "user:view",
                        "user:edit"
                    ],
                    "admin": [
                        "user:create",
                        "user:delete",
                        "user:edit",
                        "user:security:password:edit"
                    ]
                },
                "permissions": [
                    "user:view",
                    "user:edit",
                    "user:create",
                    "user:delete"
                ],
                "user_details": {
                    "first_name": "Neko",
                    "last_name": "Nik",
                    "email": "admin@example.com"
                }
            }
        }


class CreateOrganizationForm(BaseModel):
    """
    Create organization form for the endpoint
    """
    name: str = Field(..., title="Name", description="Name of the organization")
    details: dict = Field(..., title="Details", description="Details of the organization")
    activate: bool = Field(..., title="Activate", description="Activate the organization - is_active")
    email_service_enabled: bool = Field(..., title="Email Service Enabled", description="Enable or disable email service for the organization")
    chat_service_enabled: bool = Field(..., title="Chat Service Enabled", description="Enable or disable chat service for the organization")
    file_service_enabled: bool = Field(..., title="File Service Enabled", description="Enable or disable file service for the organization")
    allocated_quota: float = Field(..., title="Allocated Quota", description="Size of the quota in GigaBytes, max size of the organization - quota_allocated")
    allocated_email_identities: int = Field(..., title="Allocated Email Identities", description="Total email identities allocated for the organization (-1 for unlimited)")
    parent_organization_id: str = Field(..., title="Parent Organization ID", description="ID of the parent organization")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "name": "Neko Nik",
                "details": {
                    "description": "Example Organization",
                    "address": "123 Neko Street, Neko City, Neko Country",
                    "type": "Partner",
                    "branches": [
                        {
                            "name": "Example Branch 1",
                            "address": "123 Neko Street, Neko City, Neko Country"
                        },
                        {
                            "name": "Example Branch 2",
                            "address": "456 Neko Street, Neko City, Neko Country"
                        }
                    ]
                },
                "email_service_enabled": True,
                "chat_service_enabled": True,
                "file_service_enabled": True,
                "activate": True,
                "allocated_quota": 1000,
                "allocated_email_identities": 100,
                "parent_organization_id": "Example-UUID"   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
            }
        }


class ConnectorProperties(BaseModel):
    """
    Connector properties for the hybrid mode
    """
    description: str = Field(..., title="Description", description="Description of the connector")
    fqdn: str = Field(..., title="FQDN", description="Fully qualified domain name of the connector")
    port: int = Field(..., title="Port", description="Port of the connector")
    ipv4: str = Field(..., title="IPv4", description="IPv4 address of the connector")
    ipv6: Optional[str] = Field(None, title="IPv6", description="IPv6 address of the connector, if available")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "description": "Example Hybrid Connector",
                "fqdn": "hybrid.example.com",
                "port": 443,
                "ipv4": "1.1.1.1",
                "ipv6": "2001:db8::1"
            }
        }


class CreateDomainForm(BaseModel):
    """
    Create new domain form for the endpoint
    """
    domain_name: str = Field(..., title="Domain Name", description="Fully qualified domain name")
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization to which the domain belongs")
    activate: bool = Field(..., title="Activate", description="Activate the domain - is_active")
    details: dict = Field(..., title="Details", description="Details of the domain")
    anti_phishing_secret_code: str = Field(..., title="Anti-Phishing Secret Code", description="Secret key for anti-phishing (used in email body directly, to help users identify phishing emails)")
    enable_catch_all: bool = Field(..., title="Enable Catch All", description="Enable catch all for the domain - catch_all_enabled")
    catch_all_forwarding_address: Optional[str] = Field(None, title="Catch All Forwarding Address", description="Forwarding address for the catch all emails, if enabled")
    enable_hybrid_mode: bool = Field(..., title="Enable Hybrid Mode", description="Enable hybrid mode for the domain - hybrid_mode_enabled")
    hybrid_connector_properties: Optional[ConnectorProperties] = Field(None, title="Hybrid Connector Properties", description="Properties of the hybrid connector, if hybrid mode is enabled")
    spam_destination: str = Field(..., title="Spam Destination", description="Spam destination for the domain")
    spam_destination_properties: dict = Field(..., title="Spam Destination Properties", description="Spam destination properties for the domain")
    max_password_age: int = Field(..., title="Max Password Age", description="Max password age for the domain")
    max_password_age_properties: dict = Field(..., title="Max Password Age Properties", description="Max password age properties for the domain")
    caution_id: Optional[str] = Field(None, title="Caution ID", description="ID of the caution message to be associated with the domain")
    disclaimer_id: Optional[str] = Field(None, title="Disclaimer ID", description="ID of the disclaimer to be associated with the domain")
    filter_policy_id: Optional[str] = Field(None, title="Filter Policy ID", description="ID of the filter policy to be associated with the domain")
    attachment_policy_id: Optional[str] = Field(None, title="Attachment Policy ID", description="ID of the attachment policy to be associated with the domain")
    session_timeout: int = Field(..., title="Session Timeout", description="Session timeout for the Mailbox Email Client in minutes")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "domain_name": "example.com",
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "activate": True,
                "details": {
                    "description": "Example Domain",
                    "address": "123 Neko Street, Neko City, Neko Country"
                },
                "anti_phishing_secret_code": "Example - Secret Code",
                "enable_catch_all": True,
                "catch_all_forwarding_address": "nik@example.com",
                "enable_hybrid_mode": True,
                "hybrid_connector_properties": {
                    "description": "Example Hybrid Connector",
                    "fqdn": "hybrid.example.com",
                    "port": 443,
                    "ipv4": "1.1.1.1",
                    "ipv6": "2001:db8::1"
                },
                "spam_destination": "Folder",
                "spam_destination_properties": {
                    "description": "Spam destination properties",
                    "folder_name": "Spam"
                },
                "max_password_age": 90,
                "max_password_age_properties": {
                    "description": "Max password age properties",
                    "send_notification": True,
                    "notification_period": 7,
                    "notify_user": True,
                    "notify_admin": True
                },
                "caution_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Caution')
                "disclaimer_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Disclaimer')
                "filter_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Filter Policy')
                "attachment_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Attachment Policy')
                "session_timeout": 720
            }
        }


class PatchDomainForm(BaseModel):
    """
    Patch domain form for the endpoint
    """
    details: dict = Field(..., title="Details", description="Details of the domain")
    anti_phishing_secret_code: str = Field(..., title="Anti-Phishing Secret Code", description="Secret key for anti-phishing (used in email body directly, to help users identify phishing emails)")
    enable_catch_all: bool = Field(..., title="Enable Catch All", description="Enable catch all for the domain - catch_all_enabled")
    catch_all_forwarding_address: Optional[str] = Field(None, title="Catch All Forwarding Address", description="Forwarding address for the catch all emails, if enabled")
    enable_hybrid_mode: bool = Field(..., title="Enable Hybrid Mode", description="Enable hybrid mode for the domain - hybrid_mode_enabled")
    hybrid_connector_properties: Optional[ConnectorProperties] = Field(None, title="Hybrid Connector Properties", description="Properties of the hybrid connector, if hybrid mode is enabled")
    spam_destination: str = Field(..., title="Spam Destination", description="Spam destination for the domain")
    spam_destination_properties: dict = Field(..., title="Spam Destination Properties", description="Spam destination properties for the domain")
    max_password_age: int = Field(..., title="Max Password Age", description="Max password age for the domain")
    max_password_age_properties: dict = Field(..., title="Max Password Age Properties", description="Max password age properties for the domain")
    caution_id: Optional[str] = Field(None, title="Caution ID", description="ID of the caution message to be associated with the domain")
    disclaimer_id: Optional[str] = Field(None, title="Disclaimer ID", description="ID of the disclaimer to be associated with the domain")
    filter_policy_id: Optional[str] = Field(None, title="Filter Policy ID", description="ID of the filter policy to be associated with the domain")
    attachment_policy_id: Optional[str] = Field(None, title="Attachment Policy ID", description="ID of the attachment policy to be associated with the domain")
    session_timeout: int = Field(..., title="Session Timeout", description="Session timeout for the Mailbox Email Client in minutes")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "details": {
                    "description": "Example Domain",
                    "address": "123 Neko Street, Neko City, Neko Country"
                },
                "anti_phishing_secret_code": "Example - Secret Code",
                "enable_catch_all": True,
                "catch_all_forwarding_address": "nik@example.com",
                "enable_hybrid_mode": True,
                "hybrid_connector_properties": {
                    "description": "Example Hybrid Connector",
                    "fqdn": "hybrid.example.com",
                    "port": 443,
                    "ipv4": "1.1.1.1",
                    "ipv6": "2001:db8::1"
                },
                "spam_destination": "Folder",
                "spam_destination_properties": {
                    "description": "Spam destination properties",
                    "folder_name": "Spam"
                },
                "max_password_age": 90,
                "max_password_age_properties": {
                    "description": "Max password age properties",
                    "send_notification": True,
                    "notification_period": 7,
                    "notify_user": True,
                    "notify_admin": True
                },
                "caution_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Caution')
                "disclaimer_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Disclaimer')
                "filter_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Filter Policy')
                "attachment_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example Attachment Policy')
                "session_timeout": 720
            }
        }


class PolicyRuleType(str, Enum):
    """
    Enum for Policy Rule Types
    """
    ANYONE = "ANYONE"           # Anyone can send email to this group of mailboxes
    GROUP_MEMBER = "GROUP_MEMBER"  # Any group member can send email to this group of mailboxes
    DOMAIN_MEMBER = "DOMAIN_MEMBER"  # Any one in the domain can send email
    SPECIFIC_EMAILS = "SPECIFIC_EMAILS"  # Specific email addresses can send email


class EmailType(str, Enum):
    """
    Enum for Email Types
    """
    NORMAL = "NORMAL"           # Normal Email
    GROUP = "GROUP"             # Group Email (Email Distribution List)
    ALIAS = "ALIAS"             # Alias Email (Email Forwarding)


class MailBoxGroupMembers(BaseModel):
    """
    MailBox group members form for the endpoint
    """
    internal: List[str] = Field(..., title="Internal Members", description="List of internal members of the group mailbox")
    external: List[str] = Field(..., title="External Members", description="List of external members of the group mailbox")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "internal": ["internal@example.com"],
                "external": ["external@example.com"]
            }
        }


class CreateMailBoxForm(BaseModel):
    """
    Create new mailbox form for the endpoint
    """
    email_identity: str = Field(..., title="Email Identity", description="Email identity of the mailbox, e.g., 'user@domain.com'")
    enabled: bool = Field(..., title="Enabled", description="Enable the mailbox - is_active")
    allocate_quota: float = Field(..., title="Allocated Quota", description="Size of the quota in GigaBytes, max size of the organization - quota_allocated")
    general_policy_id: Optional[str] = Field(None, title="General Policy ID", description="ID of the general policy to be associated with the mailbox")
    forwarding_policy_id: Optional[str] = Field(None, title="Forwarding Policy ID", description="ID of the forwarding policy to be associated with the mailbox")
    distribution_policy_id: Optional[str] = Field(None, title="Distribution Policy ID", description="ID of the distribution policy to be associated with the mailbox")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "email_identity": "nik@example.com",
                "enabled": True,
                "allocate_quota": 10,
                "general_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "forwarding_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "distribution_policy_id": "Example-UUID"  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
            }
        }


class UpdateMailBoxInfoForm(BaseModel):
    """
    Update mailbox info form for the endpoint
    """
    general_policy_id: Optional[str] = Field(None, title="General Policy ID", description="ID of the general policy to be associated with the mailbox")
    forwarding_policy_id: Optional[str] = Field(None, title="Forwarding Policy ID", description="ID of the forwarding policy to be associated with the mailbox")
    distribution_policy_id: Optional[str] = Field(None, title="Distribution Policy ID", description="ID of the distribution policy to be associated with the mailbox")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "general_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "forwarding_policy_id": "Example-UUID",  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "distribution_policy_id": "Example-UUID"  # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
            }
        }


class DateRange(BaseModel):
    """
    Date Range model
    """
    from_date: datetime = Field(..., title="From Date", description="From Date")
    to_date: datetime = Field(..., title="To Date", description="To Date")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "from_date": "2021-01-01T00:00:00Z",     # ISO 8601 format
                "to_date": "2021-01-02T00:00:00Z"        # ISO 8601 format
            }
        }


class AuditSearchForm(BaseModel):
    """
    Audit search form for the endpoint
    """
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization to which the domain belongs")
    date_range: DateRange = Field(..., title="Date Range", description="Date range to filter logs")
    user_id: str = Field('', title="User ID", description="ID of the user to filter the audit logs")
    action_type: str = Field('', title="Action Type", description="Action type to search for in the audit logs")
    search_text: str = Field('', title="Search Text", description="Text to search for in the audit logs")
    action: str = Field('', title="Action", description="Action to search for in the audit logs")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "user_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "action_type": "domain_create",
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "date_range": {
                    "from_date": "2023-01-01T00:00:00Z",
                    "to_date": "2023-01-02T00:00:00Z"
                },
                "search_text": "Create Domain",
                "action": "domain_create"   # Nothing but a function name
            }
        }


class CreateServerForm(BaseModel):
    """
    Create new server form for the endpoint
    """
    host_name: str = Field(..., title="Host Name", description="Host name of the server")
    smtp_port: int = Field(..., title="SMTP Port", description="SMTP port of the server")
    server_info: dict = Field(..., title="Server Info", description="Server info of the server")
    is_active: bool = Field(..., title="Is Active", description="Is the server active or not")
    is_monitoring: bool = Field(..., title="Is Monitoring", description="Is the server under monitoring")
    is_mailbox_server: bool = Field(..., title="Is Mailbox Storage Server", description="Is the server used for mailbox storage")
    is_accepting_new_mailboxes: bool = Field(..., title="Is Accepting New Mailboxes", description="Is the server accepting new mailboxes")
    quota_allocated: float = Field(..., title="Allocated Quota", description="Size of the quota in GigaBytes, max size of the organization")
    storage_path: str = Field(..., title="Storage Path", description="Storage path for the server")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "host_name": "mail.example.com",
                "smtp_port": 25,
                "server_info": {
                    "description": "Example Mailbox Server",
                    "os": "Linux - Ubuntu 22.04",
                    "location": "Hetzner Datacenter - Falkenstein DC12",
                    "ipv4": "1.1.1.1",
                    "ipv6": "2001:db8::1"
                },
                "is_active": True,
                "is_monitoring": False,
                "is_mailbox_server": False,
                "is_accepting_new_mailboxes": False,
                "quota_allocated": 1000,    # Size of the quota in GigaBytes
                "storage_path": "/data/vmail"
            }
        }


class CreateDisclaimerForm(BaseModel):
    """
    Create new disclaimer form for the endpoint
    """
    associated_organization_id: str = Field(..., title="Associated Organization ID", description="ID of the organization to which the disclaimer is associated")
    disclaimer_name: str = Field(..., title="Disclaimer Name", description="Name of the disclaimer")
    details: dict = Field(..., title="Details", description="Details of the disclaimer")
    html_content: str = Field(..., title="HTML Content", description="HTML content of the disclaimer")
    text_content: str = Field(..., title="Text Content", description="Text content of the disclaimer")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "associated_organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "disclaimer_name": "Example Disclaimer",
                "details": {
                    "description": "Example Disclaimer",
                    "address": "123 Neko Street, Neko City, Neko Country"
                },
                "html_content": "<p>This is a disclaimer</p>",
                "text_content": "This is a disclaimer"
            }
        }


class CreateDepartmentForm(BaseModel):
    """
    Create new department form for the endpoint
    """
    associated_organization_id: str = Field(..., title="Associated Organization ID", description="ID of the organization to which the department is associated")
    department_name: str = Field(..., title="Department Name", description="Name of the department")
    department_details: dict = Field(..., title="Details", description="Details of the department")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "associated_organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "department_name": "Example Department",
                "department_details": {
                    "description": "Example Department Description",
                    "notes": "This is a test department, and there is no schema for this details",
                    "address": "123 Neko Street, Neko City, Neko Country",
                    "athorized_persons": [
                        {
                            "name": "Example",
                            "email": "nik@example.com",
                            "phone": "+1234567890"
                        }
                    ]
                }
            }
        }


class CreateCautionMessageForm(BaseModel):
    """
    Create new caution message form for the endpoint
    """
    associated_organization_id: str = Field(..., title="Associated Organization ID", description="ID of the organization to which the caution message is associated")
    caution_message_name: str = Field(..., title="Caution Message Title", description="Name of the caution message")
    info: dict = Field(..., title="Info", description="Additional information about the caution message")
    html_content: str = Field(..., title="HTML Content", description="HTML content of the caution message")
    text_content: str = Field(..., title="Text Content", description="Text content of the caution message")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "associated_organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "caution_message_name": "Example Caution",
                "info": {
                    "description": "This is a caution message for Example",
                    "severity": "High",
                    "notes": "This caution message is important and should be acknowledged by all users"
                },
                "html_content": "<p>This is a caution message</p>",
                "text_content": "This is a caution message"
            }
        }


class CreateCRMService(BaseModel):
    """
    Create new CRM service form for the endpoint
    """
    code: str = Field(..., title="Service Code", description="Code of the service")
    name: str = Field(..., title="Service Name", description="Name of the service")
    description: str = Field(..., title="Service Description", description="Description of the service")
    info: dict = Field(..., title="Service Info", description="Additional information about the service")
    activate: bool = Field(..., title="Is Active", description="Is the service active - is_active")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "code": "CRM-SERVICE-001",
                "name": "Example CRM Service",
                "description": "This is a CRM service for Example",
                "info": {
                    "description": "This is a CRM service for Example",
                    "version": "1.0.0",
                    "created_by": "Example",
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-01T00:00:00Z"
                },
                "activate": True
            }
        }


class CreatePurchaseOrder(BaseModel):
    """
    Create new purchase order form for the endpoint
    """
    associated_organization_id: str = Field(..., title="Organization ID", description="ID of the organization to which the purchase order belongs")
    name: str = Field(..., title="Purchase Order Name", description="Name of the purchase order")
    description: str = Field(..., title="Purchase Order Description", description="Description of the purchase order")
    status: str = Field(..., title="Purchase Order Status", description="Status of the purchase order")
    date: datetime = Field(..., title="Purchase Order Date", description="Date of the purchase order")
    total_amount: float = Field(..., title="Total Amount", description="Total amount of the purchase order")
    details: dict = Field(..., title="Details", description="Additional information about the purchase order")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "associated_organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "name": "Example Purchase Order",
                "description": "This is a purchase order for Example",
                "status": "Pending",
                "date": "2023-01-01T00:00:00Z",
                "total_amount": 1000.0,
                "details": {
                    "description": "This is a purchase order for Example",
                    "created_by": "Example",
                    "created_at": "2023-01-01T00:00:00Z"
                }
            }
        }


class CreatePOServiceLink(BaseModel):
    """
    Create new service link for the purchase order
    """
    notes: str = Field(..., title="Notes", description="Notes for the service link")
    details: dict = Field(..., title="Details", description="Additional information about the service link")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "notes": "This is a service link for Example purchase order",
                "details": {
                    "description": "This is a service link for Example purchase order",
                    "created_by": "Example",
                    "created_at": "2023-01-01T00:00:00Z"
                }
            }
        }


class AddAuditLog(BaseModel):
    """
    Add audit log form for the endpoint
    """
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization to which the audit log belongs")
    message: str = Field(..., title="Message", description="Audit log message to be added")
    action_type: str = Field(..., title="Action Type", description="Action performed by the user")
    action_timestamp: str = Field(..., title="Action Timestamp", description="Timestamp of the action in ISO 8601 format with timezone")
    details: dict = Field(..., title="Details", description="Additional information about the action")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "message": "User created successfully",
                "action_type": "user_create",
                "action_timestamp": "2023-01-01T00:00:00Z+05:30",  # ISO 8601 format with timezone
                "details": {
                    "created_by": "nik",
                    "user_name": "nik1",
                    "any_other_info": "This is a test user"
                }
            }
        }


class CreateFiltersPolicyListEntryForm(BaseModel):
    """
    Create new Filters Policy List entry form for the endpoint
    """
    policy_name: str = Field(..., title="List Name", description="Name of the Filters Policy List")
    domain: str = Field(..., title="Domain", description="Domain for which the entry is created")
    is_active: bool = Field(..., title="Is Enabled", description="Is the policy entry enabled - is_active")
    white_entries: List[str] = Field(..., title="White Entries", description="List of white list entries for the Filters Policy List, e.g., ['example.com'] or ['nik@example.com']")
    black_entries: List[str] = Field(..., title="Black Entries", description="List of black list entries for the Filters Policy List, e.g., ['spam.com'] or ['spammer@spam.com']")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "policy_name": "Corporate White List",
                "is_active": True,
                "white_entries": ["nik@example.com", "nik2@example.com"],
                "black_entries": ["spam@spam.com", "spammer@spam.com"]
            }
        }


class CreateGeneralPolicyListEntryForm(BaseModel):
    """
    Create new General Policy List entry form for the endpoint
    """
    policy_name: str = Field(..., title="List Name", description="Name of the general Policy List")
    policy_description: str = Field(..., title="Policy Description", description="Description of the general Policy List")
    domain: str = Field(..., title="Domain", description="Domain for which the entry is created")
    block_all_incoming_emails: bool = Field(..., title="Block All Incoming Emails", description="Block all incoming emails if True")
    block_all_outgoing_emails: bool = Field(..., title="Block All Outgoing Emails", description="Block all outgoing emails if True")
    block_all_incoming_domains: bool = Field(..., title="Block All Incoming Domains", description="Block all incoming domains if True")
    block_all_outgoing_domains: bool = Field(..., title="Block All Outgoing Domains", description="Block all outgoing domains if True")
    incoming_exception_domains: List[str] = Field(..., title="Incoming Exception Domains", description="List of incoming exception domains, e.g., ['example.com', 'another.com']")
    incoming_exception_emails: List[str] = Field(..., title="Incoming Exception Emails", description="List of incoming exception emails, e.g., ['test@test.com', 'test2@test.com']")
    outgoing_exception_domains: List[str] = Field(..., title="Outgoing Exception Domains", description="List of outgoing exception domains, e.g., ['example.com', 'another.com']")
    outgoing_exception_emails: List[str] = Field(..., title="Outgoing Exception Emails", description="List of outgoing exception emails, e.g., ['test@test.com', 'test2@test.com']")
    outgoing_size_limit_mb: float = Field(..., title="Outgoing Size Limit in MegaBytes", description="Size limit for outgoing emails in MegaBytes")
    is_active: bool = Field(..., title="Is Active", description="Is the policy active - is_active")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "policy_name": "Corporate general Policy",
                "policy_description": "This is a corporate general policy for Example",
                "block_all_incoming_emails": False,
                "block_all_outgoing_emails": False,
                "block_all_incoming_domains": False,
                "block_all_outgoing_domains": False,
                "incoming_exception_domains": ["example.com", "another.com"],
                "incoming_exception_emails": ['test@test.com', 'test2@test.com'],
                "outgoing_exception_domains": ["example.com", "another.com"],
                "outgoing_exception_emails": ['test@test.com', 'test2@test.com'],
                "outgoing_size_limit_mb": 7.86,
                "is_active": True
            }
        }


class MailFlowSearchForm(BaseModel):
    """
    Mail flow search form for the endpoint
    """
    domain_name: str = Field(..., title="Domain Name", description="Domain name to filter logs")
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization to which the domain belongs")
    date_range: DateRange = Field(..., title="Date Range", description="Date range to filter logs")
    euid: str = Field("", title="EUID", description="EUID of the user")
    from_email_id: str = Field("", title="From Email ID", description="From email ID to filter logs")
    to_email_ids: list[str] = Field([], title="To Email IDs", description="To email IDs to filter logs")
    subject: str = Field("", title="Subject", description="Subject to filter logs")
    log_type: str = Field("", title="Log Type", description="Type of log to filter")
    log_status: str = Field("", title="Status", description="Status of the log to filter")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "domain_name": "example.com",
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "date_range": {
                    "from_date": "2021-01-01T00:00:00Z",     # ISO 8601 format
                    "to_date": "2021-01-02T00:00:00Z"        # ISO 8601 format
                },
                "euid": "123",
                "from_email_id": "from@example.com",
                "to_email_ids": ["to1@example.com", "to2@yukthi.com"],
                "subject": "Test Subject",
                "log_type": "Cloud",
                "log_status": "success"
            }
        }


class LoginAttemptsSearchForm(BaseModel):
    """
    Login attempts search form for the endpoint
    """
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization to which the login attempts belong")
    date_range: DateRange = Field(..., title="Date Range", description="Date range to filter logs")
    origin_ip_address: str = Field('', title="IP Address", description="IP address to filter the login attempts")
    email_id: str = Field('', title="Email ID", description="Email ID to filter the login attempts")
    domain_name: str = Field('', title="Domain Name", description="Domain name to filter the login attempts")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "date_range": {
                    "from_date": "2021-01-01T00:00:00Z",
                    "to_date": "2021-01-02T00:00:00Z"
                },
                "origin_ip_address": "1.1.1.1",
                "email_id": "test@test.com",
                "domain_name": "example.com"
            }
        }

class CreateRevisedInvoice(BaseModel):
    """
    Create new invoice form for the endpoint (Revised invoice)
    """
    invoice_id: str = Field(..., title="Invoice ID", description="ID of the invoice, to be revised")
    revision_number: int = Field(..., title="Revision Number", description="Revision number of the invoice")
    revision_date: datetime = Field(..., title="Revision Date", description="Date of the invoice revision")
    basic_details: dict = Field(..., title="Basic Details", description="Basic details of the invoice")
    invoice_details: dict = Field(..., title="Invoice Details", description="Details of the invoice, acutal invoice details")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-001",
                "revision_number": 1,
                "revision_date": "2023-01-01T00:00:00Z",
                "basic_details": {
                    "description": "Example Invoice Revision",
                    "amount": 1200.0,
                    "currency": "USD"
                },
                "invoice_details": {
                    "invoice_id": "INV-001",
                    "template_type": "standard-v1",
                    "gst_number": "GST-123456789",
                    "invoice_date": "2023-01-01T00:00:00Z",
                    "tax_details": {
                        "tax_rate": 18.0,
                        "tax_amount": 216.0,
                        "total_amount": 1416.0
                    },
                    "description": "Revised invoice for Example",
                    "items": [
                        {"description": "Service A", "amount": 600.0, "quantity": 1},
                        {"description": "Service B", "amount": 600.0, "quantity": 1}
                    ],
                    "total_amount": 1200.0
                }
            }
        }


class CreateInvoice(BaseModel):
    """
    Create new invoice form for the endpoint (First time creation)
    """
    invoice_id: str = Field(..., title="Invoice ID", description="ID of the invoice")
    invoice_date: datetime = Field(..., title="Invoice Date", description="Date of the invoice")
    due_date: datetime = Field(..., title="Due Date", description="Due date of the invoice")
    is_paid: bool = Field(..., title="Is Paid", description="Is the invoice paid - is_paid")
    alerts: dict = Field(..., title="Alerts", description="Alerts for the invoice")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "invoice_id": "2025-26/001",
                "invoice_date": "2023-01-01T00:00:00Z",
                "due_date": "2023-01-15T00:00:00Z",
                "is_paid": False,
                "alerts": {
                    "send_notification": True,
                    "notification_period": 7,
                    "notify_users": ["email-ids-here"]
                }
            }
        }


class CreateAttachmentPolicy(BaseModel):
    """
    Create a new attachment policy form for the endpoint
    """
    policy_name: str = Field(..., title="Attachment Policy Name", description="Name of the attachment policy")
    policy_description: str = Field(..., title="Attachment Policy Description", description="Description of the attachment policy")
    domain_name: str = Field(..., title="Domain Name", description="Domain name for which the attachment policy is created")
    blocked_file_types: List[str] = Field(..., title="Blocked File Types", description="List of blocked file types/extensions, e.g., ['exe', 'bat']")
    allowed_file_types: List[str] = Field(..., title="Allowed File Types", description="List of allowed file types/extensions, e.g., ['pdf', 'docx']")
    max_attachment_size_mb: float = Field(..., title="Max Attachment Size in MegaBytes", description="Maximum allowed attachment size in MegaBytes")
    is_active: bool = Field(..., title="Is Active", description="Is the attachment policy active - is_active")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "domain_name": "example.com",
                "policy_name": "Example Attachment Policy",
                "policy_description": "This is an attachment policy for Example",
                "blocked_file_types": ["exe", "bat", "cmd"],
                "allowed_file_types": ["pdf", "docx", "xlsx", "png", "jpg"],
                "max_attachment_size_mb": 25.0,
                "is_active": True
            }
        }


class CreateSupportTicketForm(BaseModel):
    """
    Create new support ticket form for the endpoint
    """
    title: str = Field(..., title="Ticket Title", description="Title of the support ticket")
    description: str = Field(..., title="Ticket Description", description="Description of the support ticket")
    details: dict = Field(..., title="Details", description="Additional details about the support ticket")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "title": "Example Support Ticket",
                "description": "This is a support ticket for Example",
                "details": {
                    "priority": "High",
                    "created_by": "Some Display Name",
                    "category": "Technical Issue",
                    "sub_category": "Email Delivery Problem",
                    "attachments": [
                        {
                            "file_name": "screenshot1.png",
                            "file_size_mb": 2.5,
                            "file_type": "png",
                            "uploaded_at": "2023-01-01T00:00:00Z",
                            "file_id": "file-1234567890"
                        }
                    ],
                    "additional_info": "Any key value pairs as needed, no schema enforced"
                }
            }
        }


class AdminFilterSupportTicketsForm(BaseModel):
    """
    Admin filter support tickets form for the endpoint
    """
    organization_id: Optional[str] = Field(None, title="Organization ID", description="ID of the organization to which the support tickets belong")
    ticket_id: Optional[int] = Field(None, title="Ticket ID", description="ID of the support ticket to filter")
    ticket_status: Optional[str] = Field(None, title="Ticket Status", description="Status of the support tickets to filter")
    title_search: Optional[str] = Field(None, title="Title Search", description="Search text in the title of the support tickets")
    created_by: Optional[str] = Field(None, title="Created By", description="User who created the support tickets")
    assigned_to: Optional[str] = Field(None, title="Assigned To", description="User to whom the support tickets are assigned")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "ticket_status": "IN_PROGRESS",
                "ticket_id": 123,
                "title_search": "Email Delivery",
                "created_by": "user-1234567890",
                "assigned_to": "admin-0987654321"
            }
        }


class CreateAPIKeyForm(BaseModel):
    """
    Create new API key form for the endpoint
    """
    key_name: str = Field(..., title="Key Name", description="Name of the API key")
    details: dict = Field(..., title="Key Description", description="Description of the API key")
    permissions: List[str] = Field(..., title="Permissions", description="List of permissions associated with the API key")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "key_name": "Example API Key",
                "details": {
                    "description": "This is an API key for Example",
                    "created_by": "Example",
                    "Other info": "Any other info can be added here"
                },
                "permissions": ["read_users", "write_users", "read_domains"]
            }
        }


class CreateRestrictionPolicyForm(BaseModel):
    """
    Create restriction policy form for the endpoint
    """
    policy_name: str = Field(..., title="Policy Name", description="Name of the restriction policy")
    policy_description: str = Field(..., title="Policy Description", description="Description of the restriction policy")
    ip_restrictions: List[str] = Field(..., title="IP Restrictions", description="List of IP addresses or CIDR ranges to be restricted")
    geo_restrictions: List[str] = Field(..., title="Geo Restrictions", description="List of country codes to be restricted")
    is_active: bool = Field(..., title="Is Active", description="Is the restriction policy active - is_active")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "policy_name": "Example Restriction Policy",
                "policy_description": "This is a restriction policy for Example",
                "ip_restrictions": ["192.168.1.1", "10.0.0.0/24"],
                "geo_restrictions": ["CN", "RU"],
                "is_active": True
            }
        }


class CreateDistributionPolicyForm(BaseModel):
    """
    Create distribution policy form for the endpoint
    """
    policy_name: str = Field(..., title="Policy Name", description="Name of the distribution policy")
    policy_description: str = Field(..., title="Policy Description", description="Description of the distribution policy")
    domain_name: str = Field(..., title="Domain Name", description="Domain name for which the distribution policy is created")
    is_active: bool = Field(..., title="Is Active", description="Is the distribution policy active - is_active")
    rule_type: PolicyRuleType = Field(..., title="Rule Type", description="Type of distribution rule")
    specific_emails: List[str] = Field([], title="Specific Emails", description="List of specific email IDs for distribution, if rule_type is SPECIFIC_EMAILS")
    internal_members: List[str] = Field([], title="Internal Members", description="List of internal member email IDs for distribution, if rule_type is INTERNAL_MEMBERS")
    external_members: List[str] = Field([], title="External Members", description="List of external member email IDs for distribution, if rule_type is EXTERNAL_MEMBERS")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "domain_name": "example.com",
                "policy_name": "Example Distribution Policy",
                "policy_description": "This is a distribution policy for Example",
                "is_active": True,
                "rule_type": PolicyRuleType.SPECIFIC_EMAILS,
                "specific_emails": ["some@email.com"],
                "internal_members": ["internal@email.com"],
                "external_members": ["external@email.com"]
            }
        }


class CreateForwardingPolicyForm(BaseModel):
    """
    Create forwarding policy form for the endpoint
    """
    policy_name: str = Field(..., title="Policy Name", description="Name of the forwarding policy")
    policy_description: str = Field(..., title="Policy Description", description="Description of the forwarding policy")
    domain_name: str = Field(..., title="Domain Name", description="Domain name for which the forwarding policy is created")
    is_active: bool = Field(..., title="Is Active", description="Is the forwarding policy active - is_active")
    subject_contains: List[str] = Field([], title="Subject Contains", description="List of keywords that the email subject should contain for forwarding")
    from_emails: List[str] = Field([], title="From Emails", description="List of email IDs that the email should be from for forwarding")
    forward_to_emails: List[str] = Field(..., title="Forward To Emails", description="List of email IDs to which the email should be forwarded")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "domain_name": "example.com",
                "policy_name": "Example Forwarding Policy",
                "policy_description": "This is a forwarding policy for Example",
                "is_active": True,
                "subject_contains": ["Important", "Urgent"],
                "from_emails": ["internal@email.com", "external@email.com", "any@email.com"],
                "forward_to_emails": ["forwardto@email.com"]
            }
        }


class IMAPSyncCreateForm(BaseModel):
    """
    Create new IMAP Sync Job form for the endpoint
    """
    to_email_prefix: str = Field(..., title="To Email Prefix", description="Prefix of the email ID to be synced")
    to_email_domain: str = Field(..., title="To Email Domain", description="Domain of the email ID to be synced")
    imap_server: str = Field(..., title="IMAP Server", description="IMAP server address")
    imap_username: str = Field(..., title="IMAP Username", description="Username for IMAP server authentication")
    imap_password: str = Field(..., title="IMAP Password", description="Password for IMAP server authentication")
    imap_port: Optional[int] = Field(None, title="IMAP Port", description="Port number for IMAP server connection, default is 993 for SSL")
    sync_specific_folder: Optional[str] = Field(None, title="Sync Specific Folder", description="Name of the specific folder to sync, if not provided all folders will be synced")
    date_range_from: Optional[datetime] = Field(None, title="Date Range From", description="Start date only for syncing emails, in ISO 8601 format")
    date_range_to: Optional[datetime] = Field(None, title="Date Range To", description="End date only for syncing emails, in ISO 8601 format")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "to_email_prefix": "test",
                "to_email_domain": "example.com",
                "imap_server": "imap.example.com",
                "imap_username": "example_imap_user",
                "imap_password": "securepassword123",
                "imap_port": 993,
                "sync_specific_folder": "INBOX",
                "date_range_from": "2023-01-01T00:00:00Z",
                "date_range_to": "2023-01-31T23:59:59Z"
            }
        }


class ChatServiceConfigUpdateForm(BaseModel):
    """
    Update Chat Service related configurations form for the endpoint
    """
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization for which the chat service configurations are to be updated")
    enable_file_sharing: bool = Field(..., title="Enable File Sharing", description="Enable or disable file sharing in chat")
    file_size_limit_mb: int = Field(..., title="File Size Limit (MB)", description="Maximum file size allowed for sharing in chat, in MB")
    enable_group_chat: bool = Field(..., title="Enable Group Chat", description="Enable or disable group chat")
    enable_direct_chat: bool = Field(..., title="Enable Direct Chat", description="Enable or disable direct (one-on-one) chat")
    quota_allocated: float = Field(..., title="Quota Allocated", description="Allocated quota for the chat service")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "enable_file_sharing": True,
                "file_size_limit_mb": 100,
                "enable_group_chat": True,
                "enable_direct_chat": True,
                "quota_allocated": 500.0
            }
        }


class FileServiceConfigUpdateForm(BaseModel):
    """
    Update File Service related configurations form for the endpoint
    """
    organization_id: str = Field(..., title="Organization ID", description="ID of the organization for which the file service configurations are to be updated")
    enable_file_sharing: bool = Field(..., title="Enable File Sharing", description="Enable or disable file sharing in the file service")
    enable_file_versioning: bool = Field(..., title="Enable File Versioning", description="Enable or disable file versioning in the file service")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "organization_id": "Example-UUID",   # uuid.uuid5(uuid.NAMESPACE_DNS, 'Example')
                "enable_file_sharing": True,
                "enable_file_versioning": True
            }
        }


class FilesUserCreateForm(BaseModel):
    """
    Create new Files user form for the endpoint
    """
    email_identity: str = Field(..., title="Email Identity", description="Email identity for the Files user")
    quota_allocated: float = Field(..., title="Quota Allocated", description="Quota allocated for the Files user")
    domain_name: str = Field(..., title="Domain Name", description="Domain name for the Files user")
    enable_user: bool = Field(..., title="Enable User", description="Enable or disable the Files user")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "email_identity": "john.doe@example.com",
                "quota_allocated": 100.0,
                "domain_name": "example.com",
                "enable_user": True
            }
        }


class CreateIdentity(BaseModel):
    """
    Create new identity form for the endpoint
    """
    email_prefix: str = Field(..., title="Email Prefix", description="Prefix of the email ID for the identity")
    email_domain: str = Field(..., title="Email Domain", description="Domain of the email ID for the identity")
    first_name: str = Field(..., title="First Name", description="First name of the identity")
    last_name: str = Field('', title="Last Name", description="Last name of the identity")
    primary_phone_number: str = Field(..., title="Primary Phone Number", description="Primary phone number for the identity")
    secondary_email: str = Field('', title="Secondary Email", description="Secondary email ID for the identity")
    base64_password: str = Field(..., title="Password", description="Base64 encoded password for the identity")
    restriction_policy_id: Optional[str] = Field(None, title="Restriction Policy ID", description="ID of the restriction policy to be applied to the identity")
    department_id: Optional[str] = Field(None, title="Department ID", description="ID of the department to which the identity belongs")
    is_enabled: bool = Field(..., title="Is Enabled", description="Is the identity enabled - is_enabled")
    is_app_2fa_enabled: bool = Field(..., title="Is App 2FA Enabled", description="Is app-based two-factor authentication enabled for the identity")
    is_sms_2fa_enabled: bool = Field(..., title="Is SMS 2FA Enabled", description="Is SMS-based two-factor authentication enabled for the identity")
    is_email_2fa_enabled: bool = Field(..., title="Is Email 2FA Enabled", description="Is email-based two-factor authentication enabled for the identity")

    class Config:
        """
        Configuration for the model
        """
        json_schema_extra = {
            "example": {
                "email_prefix": "john.doe",
                "email_domain": "example.com",
                "first_name": "John",
                "last_name": "Doe",
                "primary_phone_number": "+1234567890",
                "secondary_email": "john.doe.secondary@example.com",
                "base64_password": "Base64EncodedPassword==",
                "restriction_policy_id": 1,
                "is_enabled": True,
                "is_app_2fa_enabled": True,
                "is_sms_2fa_enabled": False,
                "is_email_2fa_enabled": True
            }
        }
