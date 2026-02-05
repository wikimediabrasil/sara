# S.A.R.A.

> **S.A.R.A.** is an acronym for the Results and Learning Evaluation System (or _Sistema de Avaliação de Resultados e Aprendizados_ in Portuguese) and it is a software meant for recording and evaluating activities quantitative and qualitative metrics.

---

## Table of Contents
- [About the Project](#about-the-project)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Database Setup](#database-setup)
- [Running the Project](#running-the-project)
- [Tests](#tests)
- [Internationalization (i18n)](#internationalization-i18n)
- [Code Style & Quality](#code-style--quality)
- [Deployment](#deployment)
- [Common Commands](#common-commands)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---
## About the Project

- This is a Django-based web application for managing reports of activities, registering the metrics and learnings, and providing aggregated metrics reports.
- Can be used and adapted by any organization, Wikimedia affiliate or user group.
- It offers multilingual support and robust fallback logic for translated fields.

---

## Tech Stack

- **Python**: 3.9.2
- **Django**: 4.2.27
- **Database**: MariaDB / SQLite
- **Frontend**: Django Templates
- **Other**:
  - django
  - pandas
  - whitenoise
  - xlsxwriter
  - django-admin-logs
  - django_select2
  - requests
  - xhtml2pdf
  - pdfkit
  - social-auth-app-django
  - django-modeltranslation

---

## Project Structure

```
├───agenda
│   ├───management
│   │   └───commands
│   ├───migrations
│   ├───templates
│   │   └───agenda
│   └───templatetags
├───bug
│   ├───migrations
│   └───templates
│       └───bug
├───locale
├───metrics
│   ├───migrations
│   ├───templates
│   │   └───metrics
│   └───templatetags
├───report
│   ├───migrations
│   └───templates
│       └───report
├───sara
│   ├───asgi.py
│   ├───settings.py
│   ├───settings_local.py
│   ├───urls.py
│   ├───wsgi.py
├───static
│   ├───css
│   ├───images
│   └───js
├───strategy
│   └───migrations
├───templates
├───users
│   ├───migrations
│   └───templates
│       └───users
└───utils
```

---

## Getting Started

### Prerequisites

Make sure you have installed:

- Python >= 3.9.2
- pip
- Virtualenv (recommended)
- Database server (if not using SQLite)

---

### Installation

Clone the repository:

```bash
git clone https://github.com/wikimediabrasil/sara.git
cd sara
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

### CONFIGURATION

Create a `settings_local.py` file based on `settings_local_example.py`:

#### Core Paths & Django Settings
- `SECRET_KEY` — Django secret key
- `DEBUG` — Debug mode flag
- `ALLOWED_HOSTS` — Allowed hostnames/domains

#### External URLs
- `POA_URL` — Plan of Activities URL
- `STRATEGY_URL` — Strategy Plan URL

#### Feature Flags
- `SARA_MAINTENANCE_MODE` — Enables maintenance mode, when you need 
- `ENABLE_BUG_APP` — Enables bug reporting feature
- `ENABLE_AGENDA_APP` — Enables public agenda feature

#### Reporting Configuration
- `REPORT_TIMESPANS` — Time aggregation configuration for reports
  - `trimester`
  - `semester`
  - `year`

- Each timespan defines:
  - `periods` — Date ranges as `((month, day), (month, day))`
  - `total` — Full date range
  - `labels` — Human-readable labels

#### Internationalization (i18n)
- `LANGUAGES` — Supported languages
- `MODELTRANSLATION_DEFAULT_LANGUAGE` — Default translation language
- `MODELTRANSLATION_FALLBACK_LANGUAGES` — Fallback languages

#### MediaWiki / OAuth
All the instructions about requesting the OAuth consumer on Wikimedia is available [here](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose). 
- `SOCIAL_AUTH_MEDIAWIKI_KEY` — OAuth key
- `SOCIAL_AUTH_MEDIAWIKI_SECRET` — OAuth secret
- `SOCIAL_AUTH_MEDIAWIKI_URL` — MediaWiki OAuth endpoint
- `SOCIAL_AUTH_MEDIAWIKI_CALLBACK` — OAuth callback URL
- `SEND_USER_AGENT` — Enables custom User-Agent
- `USER_AGENT` — Custom User-Agent string

#### Email Configuration
- `EMAIL_BACKEND` — Django email backend
- `EMAIL_HOST` — SMTP host
- `EMAIL_PORT` — SMTP port
- `DEFAULT_FROM_EMAIL` — Default sender address
- `EMAIL_HOST_USER` — SMTP username
- `EMAIL_HOST_PASSWORD` — SMTP password
- `EMAIL_USE_TLS` — TLS enable flag
- `EMAIL_USE_SSL` — SSL enable flag
- `EMAIL_COORDINATOR` — Coordinator contact email

#### Database & Filesystem

- `HOME` — User home directory
- `replica_path` — Toolforge replica config path

#### SSH Tunnel (Local Toolforge)

- `tunnel` — SSH tunnel for Toolforge MySQL access

#### Database Configuration

- `DATABASES` — Django database configuration
  - MySQL via SSH tunnel (local)
  - MySQL via `replica.my.cnf` (production)
  - SQLite3 fallback (local)

- `config` — ConfigParser instance for `replica.my.cnf`


### Database Setup

Apply migrations:

```bash
python manage.py migrate
```

Create a superuser:

```bash
python manage.py createsuperuser
```

## Running the Project

Start the development server:

```bash
python manage.py runserver
```

Access the application at:

- http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

---

## Tests

Run the full test suite:

```bash
python manage.py test
```

Run a specific app:

```bash
python manage.py test apps.users
```

---

## Internationalization (i18n)

This project supports multiple languages.

Create message files:

```bash
python manage.py makemessages -l pt_BR
```

Compile translations:

```bash
python manage.py compilemessages
```

Language fallback logic is implemented at the application level (see relevant utility functions).

---

## Code Style & Quality

Recommended tools:

- **Black** – code formatting
- **isort** – import sorting
- **ruff** – linting

```bash
black .
isort .
ruff check .
```

---

## Deployment

High-level deployment steps:

1. Set `DEBUG=False`
2. Configure `ALLOWED_HOSTS`
3. Collect static files:

```bash
python manage.py collectstatic
```

4. Apply migrations
5. Configure WSGI/ASGI (uWSGI)
6. Set up a reverse proxy (Nginx)

---

## Common Commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py shell
python manage.py createsuperuser
python manage.py collectstatic
```

---

## Troubleshooting

**Problem:** Migrations out of sync

```bash
python manage.py makemigrations --check
```

**Problem:** Duplicate rows in queries
- Check joins
- Use `Subquery`, `Exists`, or `distinct()` carefully

**Problem:** Wrong language field selected
- Verify `LANGUAGE_CODE`
- Check fallback configuration

---

## Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

Follow existing code style and include tests.

---

## License

## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details.
