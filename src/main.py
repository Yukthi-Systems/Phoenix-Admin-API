"""
Basic functions required for the project are defined here
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


from .utils.base.libraries import (
    Annotated,
    requests,
    logging,
    Depends,
    Request,
    secrets,
    string,
    orjson,
    status,
    Config,
    boto3,
    pika,
    time,
    jwt,
    re
)
from .utils.base.constants import (
    RABBITMQ_MAILBOX_MANAGER_QUEUE,
    RABBITMQ_NOTIFICATIONS_QUEUE,
    GOOGLE_RECAPTCHA_PLD_API_KEY,
    GOOGLE_RECAPTCHA_PROJECT_ID,
    GOOGLE_RECAPTCHA_SITE_KEY,
    RABBITMQ_AUDIT_LOGS_QUEUE,
    GOOGLE_RECAPTCHA_API_KEY,
    GOOGLE_RECAPTCHA_PLD_URL,
    SERVER_MANAGER_API_KEY,
    RABBITMQ_VIRTUAL_HOST,
    CENTRIFUGO_SECRET_KEY,
    CENTRIFUGO_ALGORITHM,
    IMAP_ADMIN_PASSWORD,
    CENTRIFUGO_API_URL,
    DNS_LOOKUP_API_URL,
    DNS_LOOKUP_API_KEY,
    RABBITMQ_USERNAME,
    RABBITMQ_PASSWORD,
    RABBITMQ_EXCHANGE,
    MX_SERVER_DOMAIN,
    SSO_API_BASE_URL,
    MAX_AGE_OF_CACHE,
    OTEL_HEALTH_URL,
    IMAP_HOST_NAME,
    S3_BUCKET_NAME,
    S3_ACCESS_KEY,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    S3_SECRET_KEY,
    SSO_API_KEY,
    DKIM_API_KEY,
    DKIM_API_URL,
    S3_ENDPOINT,
    AI_API_KEY,
    AI_API_URL
)
from .database import MemcachedDep, get_organization_details, get_basic_user_details_by_id
from .utils.models import All_Exceptions, UserSession


def has_required_permissions(user_permissions: list[str], required_permissions: list[str]) -> bool:
    """
    Returns True if the user has all required permissions to access a resource.
    """
    return all(p in user_permissions for p in required_permissions)


async def validate_permissions(
    current_user_permissions: list[str],
    basic_permissions: list[str],
    organization_level_permissions: list[str],
    current_user_organization_id: str,
    accessed_organization_id: str,
    user_id: str,
    db
) -> None:
    """
    Validate if the user has the required permissions for the operation
    """
    # Basic permission checks
    if not has_required_permissions(user_permissions=current_user_permissions, required_permissions=basic_permissions):
        raise All_Exceptions(
            message="You do not have basic permissions to access this resource, please contact your administrator",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Check if the user is of proper organization
    if user_id:
        await get_basic_user_details_by_id(db_session=db, user_id=user_id, organization_id=accessed_organization_id)
        # It will raise an exception if the user is not found or does not belong to the organization

    # Organization level permission checks
    if current_user_organization_id != accessed_organization_id:
        if not has_required_permissions(user_permissions=current_user_permissions, required_permissions=organization_level_permissions):
            raise All_Exceptions(
                message="You do not have permission to access this organization",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Check if the user is a parent organization
        organization_details = await get_organization_details(db_session=db, organization_id=accessed_organization_id)
        if current_user_organization_id not in organization_details["hierarchy_path"]:
            raise All_Exceptions(
                message="You do not have permission to access this organization, since you are not a parent organization",
                status_code=status.HTTP_403_FORBIDDEN
            )


async def get_current_user_session_details(request: Request, CacheDB: MemcachedDep) -> UserSession:
    """
    Get current user session details from the cache
    """
    session_id = request.cookies.get("SESSION_ID")
    if not session_id:
        raise All_Exceptions(message="Session ID not found", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        raise All_Exceptions(message="CSRF token not found", status_code=status.HTTP_406_NOT_ACCEPTABLE)

    user_data_bytes = await CacheDB.get(session_id.encode("utf-8"))
    if not user_data_bytes:
        raise All_Exceptions(message="Session expired", status_code=status.HTTP_401_UNAUTHORIZED)

    user_data = orjson.loads(user_data_bytes)
    if user_data["csrf_token"] != csrf_token:
        raise All_Exceptions(message="CSRF token mismatch", status_code=status.HTTP_401_UNAUTHORIZED)

    # Ensure the user is authenticated
    if not user_data.get("authenticated", False):
        raise All_Exceptions(message="User is not authenticated", status_code=status.HTTP_401_UNAUTHORIZED)

    return UserSession(
        user_id=user_data["user_id"],
        display_name=user_data["display_name"],
        primary_phone=user_data["primary_phone"],
        user_email=user_data["user_email"],
        user_name=user_data["user_name"],
        organization_id=user_data["organization_id"],
        permissions=user_data["permissions"],
        organization_name=user_data["organization_name"],
        parent_organization_id=user_data["parent_organization_id"],
        organization_hierarchy_path=user_data["organization_hierarchy_path"],
        csrf_token=user_data["csrf_token"]
    )


CurrentUser = Annotated[UserSession, Depends(get_current_user_session_details)]


def _send_message_to_rabbitmq(message: dict, routing_key: str, headers: dict = None) -> None:
    """
    Send message to RabbitMQ
    :param message: The message to be sent to RabbitMQ
    :param routing_key: The routing key for the RabbitMQ exchange
    :param headers: Optional headers for the message
    :return: None
    """
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VIRTUAL_HOST,
                credentials=pika.PlainCredentials(username=RABBITMQ_USERNAME, password=RABBITMQ_PASSWORD)
            )
        )
        channel = connection.channel()
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=routing_key,
            body=orjson.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make the message persistent
                headers=headers
            )
        )
        connection.close()
        logging.debug(f"Message sent to RabbitMQ: {message}, routing_key: {routing_key}")

    except Exception as e:
        logging.error(f"Error while sending message to RabbitMQ: {e}", exc_info=True)
        raise All_Exceptions(message="Failed to send message to RabbitMQ", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


def rmq_audit_logs(message: dict, organization_id: str, user_id: str) -> None:
    """
    Send audit logs to RabbitMQ
    :param message: The message to be sent to RabbitMQ
    :param organization_id: The organization ID
    :param user_id: The user ID
    :return: None
    """
    message["organization_id"] = organization_id
    message["user_id"] = user_id

    _send_message_to_rabbitmq(
        message=message,
        routing_key=RABBITMQ_AUDIT_LOGS_QUEUE,
        headers={
            "organization_id": organization_id,
            "user_id": user_id,
            "type": "audit"
        }
    )


def send_notification(notification_type: str, to: str, template_name: str, variables: dict) -> None:
    """
    Send notification to RabbitMQ
    :param notification_type: The type of notification (e.g., "email", "sms", "push")
    :param to: The recipient of the notification
    :param template_name: The name of the template to be used for the notification
    :param variables: The variables to be used in the template
    :return: None
    """
    _send_message_to_rabbitmq(
        message={
            "to": to,
            "template": template_name,
            "variables": variables
        },
        routing_key=RABBITMQ_NOTIFICATIONS_QUEUE,
        headers={"type": notification_type}
    )


def put_s3_file(file_name: str, file_content: bytes, file_type: str, organization_id: str) -> None:
    """
    Upload a file to S3
    """
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(retries={'max_attempts': 3, 'mode': 'standard'}, connect_timeout=10, read_timeout=10)
    )

    try:
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=f"{organization_id}/{file_name}",
            Body=file_content,
            ContentType=file_type
        )
        logging.debug(f"File {file_name} uploaded successfully to S3 bucket {S3_BUCKET_NAME}")

    except Exception as e:
        logging.error(f"Error while uploading file to S3: {e}", exc_info=True)
        raise All_Exceptions(message="Failed to upload file", status_code=status.HTTP_410_GONE)


def get_s3_file(file_name: str, organization_id: str) -> bytes:
    """
    Get a file from S3
    :param file_name: The name of the file to be downloaded
    :param organization_id: The organization ID
    :return: The file content as bytes
    """
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(retries={'max_attempts': 3, 'mode': 'standard'}, connect_timeout=10, read_timeout=10)
    )

    try:
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=f"{organization_id}/{file_name}")
        return response['Body'].read()

    except s3.exceptions.NoSuchKey:
        raise All_Exceptions(message="File not found", status_code=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        logging.error(f"Error while downloading file: {e}", exc_info=True)
        raise All_Exceptions(message="Failed to download file", status_code=status.HTTP_410_GONE)


def delete_s3_file(file_name: str, organization_id: str) -> None:
    """
    Delete a file from S3
    :param file_name: The name of the file to be deleted
    :param organization_id: The organization ID
    :return: None
    """
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(retries={'max_attempts': 3, 'mode': 'standard'}, connect_timeout=10, read_timeout=10)
    )

    try:
        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=f"{organization_id}/{file_name}")

    except s3.exceptions.NoSuchKey:
        raise All_Exceptions(message="File not found", status_code=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        logging.error(f"Error while downloading file: {e}", exc_info=True)
        raise All_Exceptions(message="Failed to download file", status_code=status.HTTP_410_GONE)


def assign_new_mailbox_server(email_id: str) -> None:
    """
    Assign a new mailbox server for the given email ID AI will handle the logic
    :param email_id: The email ID for which the mailbox server needs to be assigned
    :return: None
    """
    _send_message_to_rabbitmq(
        message={
            "email": email_id
        },
        routing_key=RABBITMQ_MAILBOX_MANAGER_QUEUE,
        headers={"type": "new_email"}
    )


def rabbit_status_check() -> bool:
    """
    Check the status of RabbitMQ and log the result
    :return: True if RabbitMQ is up, raises an exception otherwise
    """
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VIRTUAL_HOST,
                credentials=pika.PlainCredentials(username=RABBITMQ_USERNAME, password=RABBITMQ_PASSWORD)
            )
        )
        connection.close()
        logging.debug("RabbitMQ is up and running")
        return True

    except Exception as e:
        logging.error(f"RabbitMQ is down: {e}", exc_info=True)
        return False


def start_new_migration(migration_id: str, email_id: str, source_server_id: str, target_server_id: str) -> None:
    """
    Start a new mailbox migration
    :param migration_id: The ID of the migration to be started
    :return: None
    """
    _send_message_to_rabbitmq(
        message={
            "migration_id": migration_id,
            "email": email_id,
            "source_server_id": source_server_id,
            "target_server_id": target_server_id
        },
        routing_key=RABBITMQ_MAILBOX_MANAGER_QUEUE,
        headers={"type": "start_migration"}
    )


def generate_notifications_jwt_token(organization_id: str, user_id: str) -> str:
    """
    Generate a JWT token for notifications.
    :param organization_id: The ID of the organization.
    :param user_id: The ID of the user.
    :return: A JWT token.
    """
    jwt_token = jwt.encode(
        payload={
            "sub": user_id,
            "exp": int(time.time()) + MAX_AGE_OF_CACHE,
            "channels": [f"notifications:{organization_id}"]
        },
        key=CENTRIFUGO_SECRET_KEY,
        algorithm=CENTRIFUGO_ALGORITHM
    )
    logging.debug(f"Generated JWT token for user {user_id} in organization {organization_id}: {jwt_token}")

    return jwt_token


def notifications_centrifugo_health_check() -> bool:
    """
    Check the health of the Centrifugo service.
    :return: True if the service is healthy, False otherwise.
    """
    try:
        resp = requests.get(url=f"{CENTRIFUGO_API_URL}/health", timeout=5)
        resp.raise_for_status()
        return True

    except Exception as e:
        logging.error(f"Centrifugo service health check failed: {e}", exc_info=True)
        return False


def otel_health_check() -> bool:
    """
    Check the health of the O-Tel service
    """
    try:
        response = requests.get(url=OTEL_HEALTH_URL, timeout=5)
        response.raise_for_status()
        if response.json().get("status") != "ok":
            logging.error("O-Tel service health check returned non-ok status")
            return False

        return True

    except Exception as e:
        logging.error(f"O-Tel service health check failed: {e}", exc_info=True)
        return False


def delete_email_on_server(email_prefix: str, domain_name: str, server_id: str) -> None:
    """
    Delete an email from the server
    :param email_prefix: The prefix of the email to be deleted
    :param domain_name: The domain of the email to be deleted
    :param server_id: The ID of the server from which the email should be deleted
    :return: None
    """
    _send_message_to_rabbitmq(
        message={
            "email_prefix": email_prefix,
            "domain_name": domain_name,
            "server_id": server_id
        },
        routing_key=RABBITMQ_MAILBOX_MANAGER_QUEUE,
        headers={"type": "delete_email"}
    )


def retrieve_help_context(user_query: str) -> str:
    """
    Retrieve help context based on the user query.
    This function is a placeholder and should be implemented to fetch relevant help context.
    :param user_query: The user's query for which help context is needed
    :return: A string containing the help context
    """
    try:
        url = f"{AI_API_URL}/generator/retrieve"
        headers = {
            "accept": "application/json",
            "X-Gen-API-Key": AI_API_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "question": user_query
        }
        response = requests.post(url=url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        if response.json().get("context"):
            return response.json()["context"]
        else:
            logging.warning(f"No context found for the query: {user_query}")
            raise All_Exceptions(
                message="No context found for the provided query",
                status_code=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logging.error(f"Error while retrieving help context: {e}", exc_info=True)
        raise All_Exceptions(
            message="Failed to retrieve help context",
            status_code=status.HTTP_412_PRECONDITION_FAILED
        )


def get_mail_queue_for_server(server_host_name: str) -> list[dict]:
    """
    Get the Mail Queue from a specific MailBox Server
    :param server_host_name: The host name of the MailBox Server
    :return: A list of mail queue items
    """
    url = f"http://{server_host_name}:8386/postfix/mailq-cache"
    headers = {
        "X-API-Key": SERVER_MANAGER_API_KEY
    }

    try:
        response = requests.get(url=url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        logging.error(f"Error while fetching mail queue for server {server_host_name}: {e}", exc_info=True)
        return []


def fetch_dns_records(domain: str):
    """
    Fetch DNS records for a specific domain.
    :param domain: The domain for which to fetch DNS records
    :return: A dictionary containing the DNS records
    """
    domain = domain.lower().strip()
    root_name = f"@ or {domain}" if len(domain.split(".")) == 2 else f"{domain.split('.')[0]}"

    url = f"{DKIM_API_URL}/v1/{domain}"
    headers = {
        "Accept": "application/json",
        "Auth-Token": DKIM_API_KEY
    }
    try:
        response = requests.get(url=url, headers=headers, timeout=5)
        response.raise_for_status()
        result = response.json()

        if not result.get("keys_exist"):
            logging.warning(f"No DKIM keys exist for the domain: {domain}")
            return []

        return [
            {
                "type": "MX",
                "name": root_name,
                "priority": 0,
                "value": f"mx0000.{MX_SERVER_DOMAIN}"
            },
            {
                "type": "MX",
                "name": root_name,
                "priority": 5,
                "value": f"mx1.{MX_SERVER_DOMAIN}"
            },
            {
                "type": "MX",
                "name": root_name,
                "priority": 5,
                "value": f"mx2.{MX_SERVER_DOMAIN}"
            },
            {
                "type": "MX",
                "name": root_name,
                "priority": 10,
                "value": f"mx1000.{MX_SERVER_DOMAIN}"
            },
            {
                "type": "TXT",
                "name": root_name,
                "priority": None,
                "value": f"v=spf1 a:smtp.spf1.{MX_SERVER_DOMAIN} ~all"
            },
            {
                "type": "CNAME",
                "name": "mailsvc._domainkey",
                "priority": None,
                "value": result.get("domain_cname")
            }
        ]

    except Exception as e:
        logging.error(f"Error while fetching DNS records for domain {domain}: {e}", exc_info=True)
        return []


def new_domain_creation(domain_name: str) -> None:
    """
    Start a new mailbox migration
    :param domain_name: The name of the domain to be created
    :return: None
    """
    _send_message_to_rabbitmq(
        message={
            "domain_name": domain_name
        },
        routing_key=RABBITMQ_MAILBOX_MANAGER_QUEUE,
        headers={"type": "new_domain"}
    )


def delete_domain_process(domain_name: str) -> None:
    """
    Start a domain deletion
    :param domain_name: The name of the domain to be deleted
    :return: None
    """
    _send_message_to_rabbitmq(
        message={
            "domain_name": domain_name.lower().strip()
        },
        routing_key=RABBITMQ_MAILBOX_MANAGER_QUEUE,
        headers={"type": "delete_domain"}
    )


def clear_email_client_session_cache(email_id: str, ip_address: str) -> None:
    """
    Clear email client session cache for a specific email ID and IP address
    :param email_id: The email ID for which the session cache needs to be cleared
    :param ip_address: The IP address from which the request is made
    :return: None
    """
    try:
        response = requests.delete(
            f"{SSO_API_BASE_URL}/internal/mail-service/clear",
            headers={
                "X-API-KEY": SSO_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": email_id,
                "ip_addr": ip_address,
                "domain": email_id.split("@")[-1]
            }
        )
        response.raise_for_status()

    except Exception as e:
        logging.error(f"Error while clearing email client session cache for {email_id}: {e}", exc_info=True)


def perform_action_on_postfix_server(server_host_name: str, action: str, message_id: str = '') -> None:
    """
    Perform an action on the Postfix server
    :param server_host_name: The host name of the Postfix server
    :param action: The action to be performed (e.g., "flush", "delete")
    :param message_id: The message ID for delete action
    :return: None
    """
    url = f"http://{server_host_name}:8386/postfix/mailq/{action}"
    headers = {
        "X-API-Key": SERVER_MANAGER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url=url,
            headers=headers,
            json=message_id if message_id else "",
            timeout=5
        )
        logging.debug(f"Performed action {action} on server {server_host_name} successfully")
        response.raise_for_status()

    except Exception as e:
        logging.error(f"Error while performing action {action} on server {server_host_name}: {e}", exc_info=True)


def validate_recaptcha(token: str) -> bool:
    """
    Validate Google Recaptcha token
    :param token: The recaptcha token to be validated
    :return: True if the token is valid, False otherwise
    """
    url = f"https://recaptchaenterprise.googleapis.com/v1/projects/{GOOGLE_RECAPTCHA_PROJECT_ID}/assessments?key={GOOGLE_RECAPTCHA_API_KEY}"
    payload = {
        "event": {
            "token": token,
            "siteKey": GOOGLE_RECAPTCHA_SITE_KEY,
        }
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        result = response.json()

        logging.debug(f"Recaptcha validation status code: {response.status_code}")

        response.raise_for_status()
        if "tokenProperties" in result:
            token_properties = result["tokenProperties"]
            if token_properties.get("valid"):
                logging.debug("Recaptcha token is valid")
                return True

        logging.warning(f"Recaptcha token is invalid: {result}")
        return False

    except Exception as e:
        logging.error(f"Error validating recaptcha token: {e}", exc_info=True)
        return False


def start_imap_sync(
    job_id: str,
    host1: str,
    user1: str,
    password1: str,
    user2: str,
    port1: int | None,
    folder: str | None,
    from_date: str | None,
    to_date: str | None
) -> None:
    """
    Start a domain deletion
    :param domain_name: The name of the domain to be deleted
    :return: None
    """
    # TODO: Find out which server the email belongs to and then provide host2, password2, port2 etc.

    data = {
        "host1": host1,
        "user1": user1,
        "password1": password1,
        "host2": IMAP_HOST_NAME,
        "user2": f"{user2}*admin",
        "password2": IMAP_ADMIN_PASSWORD
    }

    if port1:
        data["port1"] = port1
        data["port2"] = 993

    if folder:
        data["folder"] = folder

    if from_date and to_date:
        data["from_date"] = from_date
        data["to_date"] = to_date

    _send_message_to_rabbitmq(
        message={
            "job_id": job_id,
            "params": data
        },
        routing_key=RABBITMQ_MAILBOX_MANAGER_QUEUE,
        headers={"type": "imap_sync"}
    )


def get_pflogsum_report_for_server(server_host_name: str, which_data: str) -> str:
    """
    Get the Postfix Logs Summary from a specific MailBox Server
    :param server_host_name: The host name of the MailBox Server
    :param which_data: The data to be fetched (e.g., "today", "yesterday")
    :return: The pflogsumm report as a string
    """
    url = f"http://{server_host_name}:8386/postfix/pflogsumm/{which_data}"
    headers = {
        "X-API-Key": SERVER_MANAGER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            url=url,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()

        return response.json().get("report", "")

    except Exception as e:
        logging.error(f"Error while performing action {which_data} on server {server_host_name}: {e}", exc_info=True)

    return ""


def get_first_line(raw: str) -> str:
    # Get the first non-empty line
    for line in raw.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def get_grand_totals(raw: str) -> dict:
    lines = raw.splitlines()
    in_section = False

    totals = {
        "messages": {},
        "traffic": {},
        "counts": {}
    }

    for line in lines:
        line = line.strip()

        if line == "Grand Totals":
            in_section = True
            continue

        if in_section and line.startswith("Per-Hour"):
            break

        if not in_section or not line or set(line) == {"-"}:
            continue

        # Messages section
        m = re.match(r"(\d+)\s+([a-z ]+?)(?:\s+\((\d+)%\))?$", line)
        if m:
            value = int(m.group(1))
            key = m.group(2).strip().replace(" ", "_")
            percent = m.group(3)

            if percent is not None:
                totals["messages"][key] = {
                    "count": value,
                    "percent": int(percent)
                }
            else:
                totals["messages"][key] = value
            continue

        # Bytes
        m = re.match(r"(\S+)\s+bytes\s+(received|delivered)", line)
        if m:
            totals["traffic"][f"bytes_{m.group(2)}"] = m.group(1)
            continue

        # Counts
        m = re.match(r"(\d+)\s+(.+)", line)
        if m:
            key = m.group(2).strip().replace(" ", "_").replace("/", "_")
            totals["counts"][key] = int(m.group(1))

    return totals


def parse_top_section(raw: str, header: str, limit=20):
    lines = raw.splitlines()
    results = []
    in_section = False

    for line in lines:
        if line.strip() == header:
            in_section = True
            continue

        if in_section:
            if not line.strip():
                break

            m = re.match(r"\s*(\d+)\s+(.+)", line)
            if m:
                results.append({
                    "count": int(m.group(1)),
                    "value": m.group(2).strip()
                })

        if len(results) == limit:
            break

    return results


def parse_msg_received_section(raw: str, limit=20):
    lines = raw.splitlines()
    results = []
    in_section = False

    for line in lines:
        if line.strip() == "Host/Domain Summary: Messages Received":
            in_section = True
            continue

        if in_section:
            if not line.strip():
                break
            
            m = re.match(r"\s*(\d+)\s+(\S+)\s+(.+)", line)
            if m:
                results.append({
                    "message_count": int(m.group(1)),
                    "bytes": m.group(2),
                    "host_domain": m.group(3).strip()
                })

        if len(results) == limit:
            break

    return results


def parse_hierarchical_section(raw: str, section_name: str):
    if f"{section_name}: none" in raw:
        return None

    lines = raw.splitlines()
    in_section = False
    data = {}

    current_context = None
    current_reason = None

    for line in lines:
        line = line.rstrip()

        # Section start
        if line == section_name:
            in_section = True
            continue

        if not in_section:
            continue

        # Section end
        if not line.strip():
            break

        # Separator
        if set(line.strip()) == {"-"}:
            continue

        # Context (e.g. RCPT)
        m = re.match(r"\s{2,}([A-Z][A-Z0-9_-]+)$", line)
        if m:
            current_context = m.group(1)
            data.setdefault(current_context, {})
            current_reason = None
            continue

        # Reason + total
        m = re.match(r"\s{4,}(.+?)\s+\(total:\s*(\d+)\)", line)
        if m:
            if current_context is None:
                # Safety: skip malformed block
                continue

            current_reason = m.group(1).strip()
            data[current_context][current_reason] = {
                "total": int(m.group(2)),
                "sources": []
            }
            continue

        # Source entries
        m = re.match(r"\s{6,}(\d+)\s+(.+)", line)
        if m and current_context and current_reason:
            data[current_context][current_reason]["sources"].append({
                "count": int(m.group(1)),
                "value": m.group(2).strip()
            })

    return data or None


def parse_warning_error_section(raw: str, section_name: str):
    if f"{section_name}: none" in raw:
        return None

    lines = raw.splitlines()
    in_section = False
    data = {}

    current_module = None

    for line in lines:
        line = line.rstrip()

        if line == section_name:
            in_section = True
            continue

        if in_section:
            if set(line.strip()) == {"-"}:
                continue

            if not line.strip():
                break

            # Module header
            m = re.match(r"\s{2}(.+?)\s+\(total:\s*(\d+)\)", line)
            if m:
                current_module = m.group(1)
                data[current_module] = {
                    "total": int(m.group(2)),
                    "entries": []
                }
                continue

            # Entry
            m = re.match(r"\s{5,}(\d+)\s+(.+)", line)
            if m and current_module:
                data[current_module]["entries"].append({
                    "count": int(m.group(1)),
                    "message": m.group(2).strip()
                })

    return data or None


def parse_pflogsum_report(raw_report: str) -> dict:
    """
    Parse the pflogsumm report and extract grand totals.
    :param raw_report: The raw pflogsumm report as a string
    :return: A dictionary containing the grand totals
    """
    try:
        heading = get_first_line(raw_report)
        grand_totals = get_grand_totals(raw_report)
        host_domain_summary_received = parse_msg_received_section(raw_report)
        senders_by_message_count = parse_top_section(raw_report, "Senders by message count")
        recipients_by_message_count = parse_top_section(raw_report, "Recipients by message count")
        message_reject_detail = parse_hierarchical_section(raw_report, "message reject detail")
        message_deferral_detail = parse_hierarchical_section(raw_report, "message deferral detail")
        message_reject_warning_detail = parse_hierarchical_section(raw_report, "message reject warning detail")
        message_hold_detail = parse_hierarchical_section(raw_report, "message hold detail")
        message_discard_detail = parse_hierarchical_section(raw_report, "message discard detail")
        smtp_delivery_failures = parse_warning_error_section(raw_report, "smtp delivery failures")
        fatal_errors = parse_warning_error_section(raw_report, "Fatal Errors")
        panics_response = parse_warning_error_section(raw_report, "Panics")
        warnings_response = parse_warning_error_section(raw_report, "Warnings")
        master_daemon_messages = parse_warning_error_section(raw_report, "Master daemon messages")

        return {
            "heading": heading,
            "grand_totals": grand_totals,
            "host_domain_summary_received": host_domain_summary_received,
            "senders_by_message_count": senders_by_message_count,
            "recipients_by_message_count": recipients_by_message_count,
            "message_deferral_detail": message_deferral_detail,
            "message_reject_detail": message_reject_detail,
            "message_reject_warning_detail": message_reject_warning_detail,
            "message_hold_detail": message_hold_detail,
            "message_discard_detail": message_discard_detail,
            "smtp_delivery_failures": smtp_delivery_failures,
            "fatal_errors": fatal_errors,
            "panics": panics_response,
            "warnings": warnings_response,
            "master_daemon_messages": master_daemon_messages
        }

    except Exception as e:
        logging.error(f"Error while parsing pflogsumm report: {e}", exc_info=True)
        return {}


def get_procs_list_for_server(server_host_name: str) -> list[dict]:
    """
    Get the process list from a specific MailBox Server
    :param server_host_name: The host name of the MailBox Server
    :return: A list of process items
    """
    url = f"http://{server_host_name}:8386/system/processes"
    headers = {
        "X-API-Key": SERVER_MANAGER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            url=url,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logging.error(f"Error while fetching process list for server {server_host_name}: {e}", exc_info=True)

    return []


def check_password_breach(user_name: str, password: str) -> bool:
    """
    Check if the given password has been breached using the Google reCaptcha Enterprise API
    :param user_name: The user name for which the password breach needs to be checked
    :param password: The password to be checked for breach
    :return: True if the password is breached, False otherwise
    """
    url = f"{GOOGLE_RECAPTCHA_PLD_URL}/createAssessment"
    payload = {
        "username": user_name,
        "password": password
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-API-Key": GOOGLE_RECAPTCHA_PLD_API_KEY
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=3)
        result = response.json()

        response.raise_for_status()
        if "leakedStatus" in result:
            leaked_status = result["leakedStatus"]
            if leaked_status == "LEAKED":
                return True
            elif leaked_status == "NO_STATUS":
                # Only case where we can be sure that the password is not breached
                return False

        return True

    except Exception as e:
        logging.error(f"Error validating recaptcha token: {e}", exc_info=True)
        return True


def generate_dns_txt_verification_key() -> str:
    """
    Generate a random DNS TXT verification key.
    :return: A random DNS TXT verification key as a string
    """
    alphabet = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(alphabet) for _ in range(32)
    )


async def validate_dns_txt_verification_key(domain_name: str, txt_record: str) -> bool:
    """
    Validate the DNS TXT verification key for a specific domain.
    :param domain_name: The domain name for which the TXT record needs to be validated
    :param txt_record: The TXT record to be validated
    :return: True if the TXT record is valid, False otherwise
    """
    url = f"{DNS_LOOKUP_API_URL}/api/dns/txt-verify"
    headers = {
        "x-api-key": DNS_LOOKUP_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "domain": domain_name,
        "expected": txt_record
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=3)
        result = response.json()
        logging.debug(f"DNS TXT verification response for domain {domain_name}: {result}")

        if "success" in result:
            return result["success"]

        return False

    except Exception as e:
        logging.error(f"Error while validating DNS TXT record for domain {domain_name}: {e}", exc_info=True)
        return False
