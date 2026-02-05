import configparser
import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _
from sshtunnel import SSHTunnelForwarder

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "<your_secret_key>"
DEBUG = True  # or False, if in development
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "<your_host_address>"]

POA_URL = "<your_plan_of_activities_url>"
STRATEGY_URL = "<your_strategy_plan_url>"

SARA_MAINTENANCE_MODE = False  # or True, if you need to freeze SARA to generate reports
ENABLE_BUG_APP = True  # or False, if you do not want users creating bug reports
ENABLE_AGENDA_APP = (
    True  # or False, if you do not want to create or share a public agenda
)

# You can change the dates as you please.
REPORT_TIMESPANS = {
    "trimester": {
        "periods": [
            ((1, 1), (3, 31)),
            ((4, 1), (6, 30)),
            ((7, 1), (9, 30)),
            ((10, 1), (12, 31)),
        ],
        "total": ((1, 1), (12, 31)),
        "labels": ["Q1", "Q2", "Q3", "Q4"],
    },
    "semester": {
        "periods": [
            ((1, 1), (6, 30)),
            ((7, 1), (12, 31)),
        ],
        "total": ((1, 1), (12, 31)),
        "labels": ["S1", "S2"],
    },
    "year": {
        "periods": [((1, 1), (12, 31))],
        "total": ((1, 1), (12, 31)),
        "labels": ["Year"],
    },
}

LANGUAGES = [
    ("en", _("English")),
    ("pt", _("Portuguese")),
]

MODELTRANSLATION_DEFAULT_LANGUAGE = "en"
MODELTRANSLATION_FALLBACK_LANGUAGES = ("en", "pt-br", "es")

SOCIAL_AUTH_MEDIAWIKI_KEY = "<social_auth_mediawiki_key>"
SOCIAL_AUTH_MEDIAWIKI_SECRET = "<social_auth_mediawiki_secret>"
SOCIAL_AUTH_MEDIAWIKI_URL = "https://meta.wikimedia.org/w/index.php"
SOCIAL_AUTH_MEDIAWIKI_CALLBACK = "<your_host_address>/oauth/complete/mediawiki/"
SEND_USER_AGENT = True
USER_AGENT = "<your_user_agent>"

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
DEFAULT_FROM_EMAIL = "<sender>"
EMAIL_HOST_USER = "<host_email>"
EMAIL_HOST_PASSWORD = "<host_password>"
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_COORDINATOR = "<coordinator_email>"

# Database
HOME = os.environ.get("HOME") or ""
replica_path = HOME + "/replica.my.cnf"

# Toolforge database connection for local development
tunnel = SSHTunnelForwarder(
    ("login.toolforge.org", 22),
    ssh_username="<your_ssh_username>",
    ssh_private_key="~/.ssh/id_rsa",
    remote_bind_address=("tools.db.svc.wikimedia.cloud", 3306),
    local_bind_address=("localhost", 3307),
)

tunnel.start()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "<your_toolforge_tool_user>__<your_toolforge_tool_database>",
        "USER": "<your_toolforge_tool_user>",
        "PASSWORD": "<your_toolforge_tool_password>",
        "HOST": "localhost",
        "PORT": tunnel.local_bind_port,
    }
}

# Toolforge database connection for production
if os.path.exists(replica_path):
    config = configparser.ConfigParser()
    config.read(replica_path)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "<your_toolforge_tool_user>__<your_toolforge_tool_database>",
            "USER": config["client"]["user"],
            "PASSWORD": config["client"]["password"],
            "HOST": "tools.db.svc.wikimedia.cloud",
            "PORT": "",
        }
    }
# Local database in SQLite3 for local development
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "<local_database_name>.sqlite3",
        }
    }

    print("replica.my.cnf file not found")
