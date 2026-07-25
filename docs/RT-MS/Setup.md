# Real Time - Messaging System (RT-MS) - Centrifugal

Setup Centrifugal in a server to enable real time messaging system for the application

root@RT-MS:~# cat config.json 
```json
{
    "client": {
        "token": {
            "hmac_secret_key": "HMAC_SECRET_KEY"
        },
        "allowed_origins": ["*"]
    },
    "admin": {
        "enabled": true,
        "password": "ADMIN_PASSWORD",
        "secret": "ADMIN_SECRET"
    },
    "http_api": {
        "key": "HTTP_API_KEY"
    },
    "http_server" : {
        "address": "127.0.0.1",
        "port": "8086"
    },
    "log": {
        "level": "info",
        "file": "/var/log/centrifugo/logs.log"
    },
    "engine": {
        "type": "memory"
    },
    "health": {
        "enabled": true
    },
    "swagger": {
        "enabled": true
    },
    "channel": {
        "without_namespace": {
            "presence": true,
            "history_size": 30,
            "history_ttl": "12h"
        },
        "namespaces": [
            {
                "name": "notifications",
                "presence": true,
                "history_size": 100,
                "history_ttl": "84h"
            }
        ]
    }
}
```


# Channels and its namespaces

Example `notifications:530b2473-b224-5f54-9185-89189ee72df8` where `notifications` is the namespace and `530b2473-b224-5f54-9185-89189ee72df8` is the organization ID. The organization ID is unique across the system and is used to identify the specific organization for which the notifications are being sent.

- `notifications` - This is the default namespace for all clients. It is used for general and important messages that need to be broadcasted to all connected clients.
    - Includes things like system notifications, announcements, and server down time alerts etc.
    - Note: The channel names are organization IDs, so they are unique across the system.
    - Includes things like audit logs, user specific notifications, etc.
    - Like "xyz user deleted abc user", "quota has been updated for xyz email", etc.


# Installation and Configuration


Some useful commands and configurations to setup Centrifugo in a server to enable real time messaging system for the application are listed below.


```sh
root@RT-MS:/etc/centrifugo# ufw status
Status: active

To                         Action      From
--                         ------      ----
80/tcp                     ALLOW       Anywhere                  
443/tcp                    ALLOW       Anywhere                  
22/tcp                     ALLOW       Anywhere                  
80/tcp (v6)                ALLOW       Anywhere (v6)             
443/tcp (v6)               ALLOW       Anywhere (v6)             
22/tcp (v6)                ALLOW       Anywhere (v6)             

root@RT-MS:/etc/centrifugo# 
```

nano /etc/security/limits.conf
```
*                soft    nofile          65535
*                hard    nofile          1048576
```

nano /etc/pam.d/common-session and nano /etc/pam.d/common-session-noninteractive
```
session required        pam_limits.so
```

ulimit -n 65535


nano /etc/systemd/system/centrifugo.service
```toml
[Unit]
Description=Centrifugo Real-time Messaging Server
After=network.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/bin/centrifugo --config=/etc/centrifugo/config.json
WorkingDirectory=/etc/centrifugo
Restart=on-failure
LimitNOFILE=65535
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable --now centrifugo

systemctl show --property=LimitNOFILE centrifugo
journalctl -u centrifugo -f

systemctl start centrifugo
systemctl status centrifugo
systemctl restart centrifugo
