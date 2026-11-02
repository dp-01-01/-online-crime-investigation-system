# Online Crime Investigation System

A web-based application for managing crime cases, complaints, victims, suspects, evidence, investigations, and reports.

This project is developed for educational and demonstration purposes using Flask and SQLite.

## Technologies Used

- HTML
- CSS
- Bootstrap
- JavaScript
- Python
- Flask
- SQLite
- Git
- GitHub

## Main Features

- User Registration and Login
- Secure Password Hashing
- Role-Based Access Control
- Citizen Registration
- Dashboard with Live Statistics
- Crime Case Management
- Case Search and Filtering
- Victim Management
- Suspect Management
- Evidence Management
- Investigation Management
- Crime Complaint Management
- Complaint Status Tracking
- Case Reports
- Report Charts and Statistics
- Secure Session Configuration
- Admin and Investigator Management Access

## User Roles

### Admin

- Manage cases
- Manage victims
- Manage suspects
- Manage evidence
- Manage investigations
- Manage complaints
- View reports
- Access management modules

### Investigator

- Manage cases
- Manage victims
- Manage suspects
- Manage evidence
- Manage investigations
- Manage complaints
- View reports

### Citizen

- Create an account
- Login securely
- Report crimes
- View submitted complaints
- Track complaint status

> Public registration creates Citizen accounts only. Admin and Investigator accounts should be created through an authorized administrative process.

## Database

The application uses SQLite (a single file, `crime_system.db`, created automatically on first run) with the following tables:

- users
- cases
- victims
- suspects
- evidence
- investigations
- complaints

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):

```text
FLASK_SECRET_KEY=your-long-random-secret
```

Create the first Admin account (public registration only creates Citizens):

```bash
python app.py create-user
```

Run the app:

```bash
python app.py
```

Open http://127.0.0.1:5000

## Optional Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_PATH` | Custom location of the SQLite file |
| `SESSION_COOKIE_SECURE` | Set to `true` when served over HTTPS |
| `FLASK_DEBUG` | Set to `true` for debug mode (local only) |

## Project Structure

```text
online-crime-investigation-system/
│
├── app.py
├── README.md
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
│
├── static/
│   └── css/
│       └── style.css
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── cases.html
│   ├── add_case.html
│   ├── edit_case.html
│   ├── victims.html
│   ├── add_victim.html
│   ├── edit_victim.html
│   ├── suspects.html
│   ├── add_suspect.html
│   ├── edit_suspect.html
│   ├── evidence.html
│   ├── add_evidence.html
│   ├── edit_evidence.html
│   ├── investigations.html
│   ├── add_investigation.html
│   ├── edit_investigation.html
│   ├── complaints.html
│   ├── complaint.html
│   ├── admin_complaints.html
│   └── reports.html
│
├── crime_system.db   (created automatically)
└── venv/