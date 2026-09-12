# Online Crime Investigation System

A web-based application for managing crime cases, complaints, victims, suspects, evidence, and investigations.

## Technologies Used

- HTML
- CSS
- Bootstrap
- JavaScript
- Python
- Flask
- MySQL
- Git and GitHub

## Main Features

- User Registration and Login
- Role-Based Access
- Dashboard
- Crime Case Management
- Victim Management
- Suspect Management
- Evidence Management
- Investigation Management
- Crime Complaint Management
- Case Search and Filtering
- Case Reports
- Complaint Status Tracking

## User Roles

### Admin

- Manage cases
- Manage victims
- Manage suspects
- Manage evidence
- Manage investigations
- Manage complaints
- View reports

### Investigator

- Manage cases
- Manage victims
- Manage suspects
- Manage evidence
- Manage investigations
- Manage complaints
- View reports

### Citizen

- Report crimes
- View submitted complaints
- Track complaint status

## Database

The application uses MySQL with the following tables:

- users
- cases
- victims
- suspects
- evidence
- investigations
- complaints

## How to Run

1. Clone the repository.
2. Create a Python virtual environment.
3. Install the required packages.
4. Configure the `.env` file.
5. Create the MySQL database.
6. Run the Flask application.

```bash
python app.py