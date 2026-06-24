# Enterprise Employee Management System (EMS)

A comprehensive, containerized Enterprise Employee Management System (EMS) built with a modular Python Flask backend, SQLAlchemy ORM, SQLite/PostgreSQL, and a modern Glassmorphism frontend using Bootstrap 5 and Chart.js.

---

## Features

- **Authentication & RBAC**: Session-based login for web templates and JWT for REST APIs. Supported roles: *Super Admin*, *HR Manager*, *Team Lead*, and *Employee*.
- **Daily Timecards & Attendance**: Check-in, check-out, automatic working hours, and overtime calculations.
- **Leave Operations**: Allowances balances, manager approvals panel, and automatic timesheet logging.
- **Monthly Payroll**: Basic salary, HRA, PF deductions, tax withholding math, and automatic payslip PDF generation.
- **Document Cabinet**: Resume, certificates, offer letters upload, download, and file screenings.
- **AI Console**: Natural language directory search (NLP), resume screening score summaries, dashboard chat assistant, and predictive employee attrition risk insights.
- **Disbursement Reports**: Multi-format exports (CSV, Excel, PDF) for directory listings, leaves logs, timecards, and payroll registries.
- **Audit Trails**: Security tracking logs of administrator modifications and user logins.

---

## Initial Seed User Logins

Seed the database to access these preconfigured accounts:

| Role | Email / Username | Password |
|---|---|---|
| **Super Admin** | `admin@enterprise.com` | `Admin@123` |
| **HR Manager** | `hr@enterprise.com` | `Hr@123` |
| **Team Lead** | `lead@enterprise.com` | `Lead@123` |
| **Employee** | `emp@enterprise.com` | `Emp@123` |

---

## Installation & Setup

### Option 1: Running Locally (Development Mode)

#### 1. Setup Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS / Linux
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Initialize & Seed Database
```bash
# This will initialize tables in 'database/ems.db' and seed mock records
python manage.py seed
```

#### 4. Run Development Server
```bash
python app.py
```
*The portal will be available at `http://localhost:5000`.*

---

### Option 2: Running with Docker Compose (Production Ready)

Ensure you have Docker and Docker Compose installed.

```bash
# Spin up PostgreSQL database, Flask application, and Nginx proxy containers
docker-compose up --build -d
```
*The system will automatically map Nginx through port 80. Open your browser and navigate to `http://localhost`.*

To seed the PostgreSQL database inside the running container:
```bash
docker-compose exec web python manage.py seed
```

---

## Database Management Commands

Local SQLite databases can be managed via CLI helpers in `manage.py`:

- **Seed Database**:
  ```bash
  python manage.py seed
  ```
- **Backup Database**:
  ```bash
  python manage.py backup
  ```
  *Saves a copy of the database to `database_backup.db`.*
- **Restore Database**:
  ```bash
  python manage.py restore
  ```
  *Overwrites current database with `database_backup.db`.*

---

## Running Automated Tests

Run the isolated test suite verifying APIs, JWT, attendance calculations, and salary structures:

```bash
python -m unittest discover -s tests
```
