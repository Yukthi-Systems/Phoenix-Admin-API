"""
This file contains Global constants
Also storing all the env and config variables here
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


import os

# environment Constants (Fetching from docker-compose)
POSTGRES_DB_USERNAME = os.environ.get("POSTGRES_DB_USERNAME", "<POSTGRES_DB_USERNAME>")
POSTGRES_DB_PASSWORD = os.environ.get("POSTGRES_DB_PASSWORD", "<POSTGRES_DB_PASSWORD>")
POSTGRES_DB_HOST = os.environ.get("POSTGRES_DB_HOST", "<POSTGRES_DB_HOST>")
POSTGRES_DB_PORT = os.environ.get("POSTGRES_DB_PORT", "<POSTGRES_DB_PORT>")
POSTGRES_DB_DATABASE = os.environ.get("POSTGRES_DB_DATABASE", "<POSTGRES_DB_DATABASE>")
POSTGRES_POOL_SIZE = int(os.environ.get("POSTGRES_POOL_SIZE", "10"))
POSTGRES_DB_URI = os.environ.get(
    "POSTGRES_DB_URI",
    "postgresql://<POSTGRES_DB_USERNAME>:<POSTGRES_DB_PASSWORD>@<POSTGRES_DB_HOST>:<POSTGRES_DB_PORT>/<POSTGRES_DB_DATABASE>"
)

# MemCache DB Constants
MEMCACHED_DB_HOST = os.environ.get("MEMCACHED_DB_HOST", "<MEMCACHED_DB_HOST>")
MEMCACHED_DB_PORT = os.environ.get("MEMCACHED_DB_PORT", "<MEMCACHED_DB_PORT>")
MEMCACHED_DB_POOL_SIZE = int(os.environ.get("MEMCACHED_DB_POOL_SIZE", "10"))
MAX_AGE_OF_CACHE = int(os.environ.get("MAX_AGE_OF_CACHE", str(3 * 60 * 60)))

# Logging Constants
LOG_LEVEL = int(os.environ.get("LOG_LEVEL", "20"))
LOG_FILE_PATH = os.environ.get("LOG_FILE_PATH", "<LOG_FILE_PATH>")

# RabbitMQ Constants
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "<RABBITMQ_HOST>")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "5672"))
RABBITMQ_VIRTUAL_HOST = os.environ.get("RABBITMQ_VIRTUAL_HOST", "<RABBITMQ_VIRTUAL_HOST>")
RABBITMQ_USERNAME = os.environ.get("RABBITMQ_USERNAME", "<RABBITMQ_USERNAME>")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "<RABBITMQ_PASSWORD>")
RABBITMQ_EXCHANGE = os.environ.get("RABBITMQ_EXCHANGE", "<RABBITMQ_EXCHANGE>")
RABBITMQ_AUDIT_LOGS_QUEUE = os.environ.get("RABBITMQ_AUDIT_LOGS_QUEUE", "<RABBITMQ_AUDIT_LOGS_QUEUE>")
RABBITMQ_NOTIFICATIONS_QUEUE = os.environ.get("RABBITMQ_NOTIFICATIONS_QUEUE", "<RABBITMQ_NOTIFICATIONS_QUEUE>")
RABBITMQ_MAILBOX_MANAGER_QUEUE = os.environ.get("RABBITMQ_MAILBOX_MANAGER_QUEUE", "<RABBITMQ_MAILBOX_MANAGER_QUEUE>")

# ClickHouse Constants
CLICK_HOUSE_HOST = os.environ.get("CLICK_HOUSE_HOST", "<CLICK_HOUSE_HOST>")
CLICK_HOUSE_PORT = int(os.environ.get("CLICK_HOUSE_PORT", "8123"))
CLICK_HOUSE_USERNAME = os.environ.get("CLICK_HOUSE_USERNAME", "<CLICK_HOUSE_USERNAME>")
CLICK_HOUSE_PASSWORD = os.environ.get("CLICK_HOUSE_PASSWORD", "<CLICK_HOUSE_PASSWORD>")
CLICK_HOUSE_AUDIT_LOGS_TABLE = os.environ.get("CLICK_HOUSE_AUDIT_LOGS_TABLE", "<CLICK_HOUSE_AUDIT_LOGS_TABLE>")
CLICK_HOUSE_MAIL_FLOW_LOGS_TABLE = os.environ.get("CLICK_HOUSE_MAIL_FLOW_LOGS_TABLE", "<CLICK_HOUSE_MAIL_FLOW_LOGS_TABLE>")

# Archive S3 details
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "<S3_BUCKET_NAME>")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "<S3_ACCESS_KEY>")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "<S3_SECRET_KEY>")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "<S3_ENDPOINT>")

# QuestDB Constants
QUEST_DB_HOST = os.environ.get("QUEST_DB_HOST", "<QUEST_DB_HOST>")
QUEST_DB_PORT = int(os.environ.get("QUEST_DB_PORT", "9000"))
QUEST_DB_USER = os.environ.get("QUEST_DB_USER", "<QUEST_DB_USER>")
QUEST_DB_PASSWORD = os.environ.get("QUEST_DB_PASSWORD", "<QUEST_DB_PASSWORD>")

# Centrifugo Real-time Messaging System Constants
CENTRIFUGO_SECRET_KEY = os.environ.get("CENTRIFUGO_SECRET_KEY", "<CENTRIFUGO_SECRET_KEY>")
CENTRIFUGO_ALGORITHM = os.environ.get("CENTRIFUGO_ALGORITHM", "HS256")
CENTRIFUGO_API_URL = os.getenv("CENTRIFUGO_API_URL", "<CENTRIFUGO_API_URL>")

# O-Tel Health URL
OTEL_HEALTH_URL = os.getenv("OTEL_HEALTH_URL", "<OTEL_HEALTH_URL>")

# Auth API Constants
SSO_API_BASE_URL = os.getenv("SSO_API_BASE_URL", "<SSO_API_BASE_URL>")
SSO_API_KEY = os.getenv("SSO_API_KEY", "<SSO_API_KEY>")
GOOGLE_RECAPTCHA_API_KEY = os.getenv("GOOGLE_RECAPTCHA_API_KEY", "<GOOGLE_RECAPTCHA_API_KEY>")
GOOGLE_RECAPTCHA_PROJECT_ID = os.getenv("GOOGLE_RECAPTCHA_PROJECT_ID", "<GOOGLE_RECAPTCHA_PROJECT_ID>")
GOOGLE_RECAPTCHA_SITE_KEY = os.getenv("GOOGLE_RECAPTCHA_SITE_KEY", "<GOOGLE_RECAPTCHA_SITE_KEY>")
GOOGLE_RECAPTCHA_PLD_URL = os.getenv("GOOGLE_RECAPTCHA_PLD_URL", "<GOOGLE_RECAPTCHA_PLD_URL>")
GOOGLE_RECAPTCHA_PLD_API_KEY = os.getenv("GOOGLE_RECAPTCHA_PLD_API_KEY", "<GOOGLE_RECAPTCHA_PLD_API_KEY>")

# DNS Lookup API Constants
DNS_LOOKUP_API_URL = os.getenv("DNS_LOOKUP_API_URL", "<DNS_LOOKUP_API_URL>")
DNS_LOOKUP_API_KEY = os.getenv("DNS_LOOKUP_API_KEY", "<DNS_LOOKUP_API_KEY>")

# Server Manager API
SERVER_MANAGER_API_KEY = os.getenv("SERVER_MANAGER_API_KEY", "<SERVER_MANAGER_API_KEY>")
SERVER_MANAGER_API_MAPS = dict(
    item.split(":")
    for item in str(
        os.getenv(
            "SERVER_MANAGER_API_MAPS",
            "server1:<HOSTNAME1>,server2:<HOSTNAME2>"
        )
    ).split(",")
)

DKIM_API_URL = os.getenv("DKIM_API_URL", "<DKIM_API_URL>")
DKIM_API_KEY = os.getenv("DKIM_API_AUTH_TOKEN", "<DKIM_API_AUTH_TOKEN>")

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "<INTERNAL_API_KEY>")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "<COOKIE_DOMAIN>")
ALLOWED_ORIGINS = str(
    os.getenv(
        "ALLOWED_ORIGINS",
        "https://example1.com,https://example2.com,http://localhost:5173"
    )
).split(",")

IMAP_ADMIN_PASSWORD = os.getenv("IMAP_ADMIN_PASSWORD", "<IMAP_ADMIN_PASSWORD>")
IMAP_HOST_NAME = os.getenv("IMAP_HOST_NAME", "<IMAP_HOST_NAME>")
MX_SERVER_DOMAIN = os.getenv("MX_SERVER_DOMAIN", "<MX_SERVER_DOMAIN>")
DEFAULT_SERVER_ID = os.getenv("DEFAULT_SERVER_ID", "<DEFAULT_SERVER_ID>")

# AI API Constants
AI_API_URL = os.getenv("AI_API_URL", "<AI_API_URL>")
AI_API_KEY = os.getenv("AI_API_KEY", "<AI_API_KEY>")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "<OPENAI_API_KEY>")

DEEP_INFRA_API_KEY = os.getenv("DEEP_INFRA_API_KEY", "<DEEP_INFRA_API_KEY>")
DEEP_INFRA_API_URL = os.getenv("DEEP_INFRA_API_URL", "<DEEP_INFRA_API_URL>")

# SYSTEM PROMPT Constants
SYSTEM_PROMPT = """You are a very helpful and knowledgeable help desk assistant. Use the provided context to answer the user's question.
- If the context fully answers the question, provide a clear and concise response. Make it easy to follow.
- If information is missing from the context or the context is not relevant, do not fabricate answers.
- If the context is partially helpful, use it but acknowledge any gaps and provide the best possible answer.
- If the context does not contain enough information, say so politely and suggest what the user can do next (e.g., escalate to support, check documentation, or rephrase the query).
- Never invent details or make assumptions beyond the provided context.
- Use a polite, professional, and supportive tone.
- If any links or references are mentioned in the context, ensure they are included in your response.
- If relevant, present steps or instructions as a numbered list for clarity.

Format your answer as follows:
- Direct answer first (short and clear).
- Supporting details (if needed, from the context).
- Next steps or escalation (if the answer is incomplete)."""

SYSTEM_PROMPT_FOR_STYLING = """You are an expert email header and footer designer. Your task is to create visually appealing and professional email headers and footers using HTML and inline CSS styles. Follow these guidelines:
- Ensure the design is responsive and looks good on both desktop and mobile devices.
- Do not change the content provided by the user. Only format it.
- Provide only the HTML code in your response without any additional explanations or text."""
