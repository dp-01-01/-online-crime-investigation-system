import os
import sys
import secrets
import sqlite3
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash


# Load environment variables from .env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# =========================
# FLASK APPLICATION
# =========================

app = Flask(__name__)

# If FLASK_SECRET_KEY is not set, a random key is generated.
# Sessions will then reset whenever the app restarts, so set it in production.
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. Add it to your .env file before starting the app."
    )


# =========================
# SESSION SECURITY
# =========================

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Set SESSION_COOKIE_SECURE=true in your environment when deployed with HTTPS.
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
)


# =========================
# DATABASE (SQLite)
# =========================

DATABASE = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "crime_system.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'citizen'
        CHECK (role IN ('admin', 'investigator', 'citizen')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT NOT NULL UNIQUE,
    crime_type TEXT,
    location TEXT,
    incident_date TEXT,
    description TEXT,
    status TEXT DEFAULT 'Open',
    investigator TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS victims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT,
    name TEXT,
    age INTEGER,
    gender TEXT,
    phone TEXT,
    address TEXT,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suspects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT,
    name TEXT,
    age INTEGER,
    gender TEXT,
    phone TEXT,
    address TEXT,
    description TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT,
    evidence_type TEXT,
    description TEXT,
    collected_date TEXT,
    collected_by TEXT,
    location_found TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT,
    investigator TEXT,
    investigation_date TEXT,
    investigation_type TEXT,
    details TEXT,
    findings TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_number TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    crime_type TEXT,
    location TEXT,
    incident_date TEXT,
    description TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    # Rows behave like dictionaries: row["name"] (also works in Jinja: row.name)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """Create all tables if they do not exist yet."""
    connection = get_db_connection()
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def fetch_all(query, params=()):
    connection = get_db_connection()
    try:
        return connection.execute(query, params).fetchall()
    finally:
        connection.close()


def fetch_one(query, params=()):
    connection = get_db_connection()
    try:
        return connection.execute(query, params).fetchone()
    finally:
        connection.close()


def write_db(query, params, error_message):
    """
    Run an INSERT / UPDATE / DELETE.
    Returns None on success, or an error string on failure.
    """
    connection = get_db_connection()
    try:
        connection.execute(query, params)
        connection.commit()
        return None
    except sqlite3.Error as error:
        connection.rollback()
        return f"{error_message}: {error}"
    finally:
        connection.close()


def count_rows(table, where="", params=()):
    # 'table' and 'where' are fixed strings written in this file, never user input.
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return fetch_one(sql, params)[0]


# =========================
# REGISTRATION ROLES
# =========================

REGISTRATION_ROLES = ("citizen", "investigator", "admin")

# =========================
# LOGIN REQUIRED DECORATOR
# =========================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# =========================
# ROLE REQUIRED DECORATOR
# =========================

def role_required(*roles):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") not in roles:
                return "Access Denied: You do not have permission to access this page."

            return function(*args, **kwargs)

        return wrapper

    return decorator


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():

    return render_template("index.html")


# =========================
# LOGIN PAGE
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:

            return render_template(
                "login.html",
                error="Please enter username and password."
            )

        user = fetch_one(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )

        if user and check_password_hash(user["password"], password):

            # Clear any previous session data before establishing this login.
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


# =========================
# REGISTRATION PAGE
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "citizen").strip().lower()

        # Never trust the role sent by the browser; validate it on the server.
        if role not in REGISTRATION_ROLES:
            return render_template(
                "register.html",
                error="Invalid account type selected."
            )

        if not username or not email or not password:
            return render_template(
                "register.html",
                error="Please fill in all required fields."
            )

        if len(password) < 6:
            return render_template(
                "register.html",
                error="Password must contain at least 6 characters."
            )

        # Admin and Officer (stored as investigator) accounts require a
        # private code configured in .env. Citizen registration stays open.
        if role in ("admin", "investigator"):
            configured_staff_code = os.getenv("STAFF_REGISTRATION_CODE")
            submitted_staff_code = request.form.get("staff_code", "").strip()

            if not configured_staff_code:
                return render_template(
                    "register.html",
                    error="Staff registration is currently disabled. Contact the system administrator."
                )

            if not submitted_staff_code or not secrets.compare_digest(
                submitted_staff_code, configured_staff_code
            ):
                return render_template(
                    "register.html",
                    error="Invalid staff registration code."
                )

        existing_user = fetch_one(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        )

        if existing_user:
            return render_template(
                "register.html",
                error="Username or email already exists. Please use a different one."
            )

        error = write_db(
            """
            INSERT INTO users (username, email, password, role)
            VALUES (?, ?, ?, ?)
            """,
            (username, email, generate_password_hash(password), role),
            "Registration failed"
        )

        if error:
            return render_template(
                "register.html",
                error="Registration failed. Please try again."
            )

        return redirect(url_for("login"))

    return render_template("register.html")

# =========================
# DASHBOARD PAGE
# =========================

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",
        total_cases=count_rows("cases"),
        open_cases=count_rows("cases", "status = ?", ("Open",)),
        total_victims=count_rows("victims"),
        total_suspects=count_rows("suspects"),
        total_evidence=count_rows("evidence"),
        total_investigations=count_rows("investigations")
    )


# ==================================================
# CASE MANAGEMENT
# ==================================================

@app.route("/cases")
@role_required("admin", "investigator")
def cases():

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    query = "SELECT * FROM cases WHERE 1=1"
    values = []

    # SEARCH
    if search:

        query += """
            AND (
                case_number LIKE ?
                OR crime_type LIKE ?
                OR location LIKE ?
                OR investigator LIKE ?
            )
        """

        search_value = "%" + search + "%"
        values.extend([search_value] * 4)

    # STATUS FILTER
    if status:

        query += " AND status = ?"
        values.append(status)

    query += " ORDER BY id DESC"

    case_list = fetch_all(query, values)

    return render_template(
        "cases.html",
        cases=case_list,
        search=search,
        status=status
    )


# =========================
# ADD NEW CASE
# =========================

@app.route("/add-case", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_case():

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["crime_type"],
            request.form["location"],
            request.form["incident_date"],
            request.form["description"],
            request.form["status"],
            request.form["investigator"]
        )

        error = write_db(
            """
            INSERT INTO cases
            (
                case_number,
                crime_type,
                location,
                incident_date,
                description,
                status,
                investigator
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
            "Case could not be added"
        )

        if error:
            return error

        return redirect(url_for("cases"))

    return render_template("add_case.html")


# =========================
# EDIT CASE
# =========================

@app.route("/edit-case/<int:case_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_case(case_id):

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["crime_type"],
            request.form["location"],
            request.form["incident_date"],
            request.form["description"],
            request.form["status"],
            request.form["investigator"],
            case_id
        )

        error = write_db(
            """
            UPDATE cases
            SET
                case_number = ?,
                crime_type = ?,
                location = ?,
                incident_date = ?,
                description = ?,
                status = ?,
                investigator = ?
            WHERE id = ?
            """,
            values,
            "Case could not be updated"
        )

        if error:
            return error

        return redirect(url_for("cases"))

    case = fetch_one("SELECT * FROM cases WHERE id = ?", (case_id,))

    if not case:
        return "Case not found"

    return render_template("edit_case.html", case=case)


# =========================
# DELETE CASE
# =========================

@app.route("/delete-case/<int:case_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_case(case_id):

    error = write_db(
        "DELETE FROM cases WHERE id = ?",
        (case_id,),
        "Case could not be deleted"
    )

    if error:
        return error

    return redirect(url_for("cases"))


# ==================================================
# VICTIM MANAGEMENT
# ==================================================

@app.route("/victims")
@role_required("admin", "investigator")
def victims():

    victim_list = fetch_all("SELECT * FROM victims ORDER BY id DESC")

    return render_template("victims.html", victims=victim_list)


# =========================
# ADD NEW VICTIM
# =========================

@app.route("/add-victim", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_victim():

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["name"],
            request.form["age"],
            request.form["gender"],
            request.form["phone"],
            request.form["address"],
            request.form["description"]
        )

        error = write_db(
            """
            INSERT INTO victims
            (
                case_number,
                name,
                age,
                gender,
                phone,
                address,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
            "Victim could not be added"
        )

        if error:
            return error

        return redirect(url_for("victims"))

    return render_template("add_victim.html")


# =========================
# EDIT VICTIM
# =========================

@app.route("/edit-victim/<int:victim_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_victim(victim_id):

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["name"],
            request.form["age"],
            request.form["gender"],
            request.form["phone"],
            request.form["address"],
            request.form["description"],
            victim_id
        )

        error = write_db(
            """
            UPDATE victims
            SET
                case_number = ?,
                name = ?,
                age = ?,
                gender = ?,
                phone = ?,
                address = ?,
                description = ?
            WHERE id = ?
            """,
            values,
            "Victim could not be updated"
        )

        if error:
            return error

        return redirect(url_for("victims"))

    victim = fetch_one("SELECT * FROM victims WHERE id = ?", (victim_id,))

    if not victim:
        return "Victim not found"

    return render_template("edit_victim.html", victim=victim)


# =========================
# DELETE VICTIM
# =========================

@app.route("/delete-victim/<int:victim_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_victim(victim_id):

    error = write_db(
        "DELETE FROM victims WHERE id = ?",
        (victim_id,),
        "Victim could not be deleted"
    )

    if error:
        return error

    return redirect(url_for("victims"))


# ==================================================
# SUSPECT MANAGEMENT
# ==================================================

@app.route("/suspects")
@role_required("admin", "investigator")
def suspects():

    suspect_list = fetch_all("SELECT * FROM suspects ORDER BY id DESC")

    return render_template("suspects.html", suspects=suspect_list)


# =========================
# ADD NEW SUSPECT
# =========================

@app.route("/add-suspect", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_suspect():

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["name"],
            request.form["age"],
            request.form["gender"],
            request.form["phone"],
            request.form["address"],
            request.form["description"],
            request.form["status"]
        )

        error = write_db(
            """
            INSERT INTO suspects
            (
                case_number,
                name,
                age,
                gender,
                phone,
                address,
                description,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
            "Suspect could not be added"
        )

        if error:
            return error

        return redirect(url_for("suspects"))

    return render_template("add_suspect.html")


# =========================
# EDIT SUSPECT
# =========================

@app.route("/edit-suspect/<int:suspect_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_suspect(suspect_id):

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["name"],
            request.form["age"],
            request.form["gender"],
            request.form["phone"],
            request.form["address"],
            request.form["description"],
            request.form["status"],
            suspect_id
        )

        error = write_db(
            """
            UPDATE suspects
            SET
                case_number = ?,
                name = ?,
                age = ?,
                gender = ?,
                phone = ?,
                address = ?,
                description = ?,
                status = ?
            WHERE id = ?
            """,
            values,
            "Suspect could not be updated"
        )

        if error:
            return error

        return redirect(url_for("suspects"))

    suspect = fetch_one("SELECT * FROM suspects WHERE id = ?", (suspect_id,))

    if not suspect:
        return "Suspect not found"

    return render_template("edit_suspect.html", suspect=suspect)


# =========================
# DELETE SUSPECT
# =========================

@app.route("/delete-suspect/<int:suspect_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_suspect(suspect_id):

    error = write_db(
        "DELETE FROM suspects WHERE id = ?",
        (suspect_id,),
        "Suspect could not be deleted"
    )

    if error:
        return error

    return redirect(url_for("suspects"))


# ==================================================
# EVIDENCE MANAGEMENT
# ==================================================

@app.route("/evidence")
@role_required("admin", "investigator")
def evidence():

    evidence_list = fetch_all("SELECT * FROM evidence ORDER BY id DESC")

    return render_template("evidence.html", evidence=evidence_list)


# =========================
# ADD NEW EVIDENCE
# =========================

@app.route("/add-evidence", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_evidence():

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["evidence_type"],
            request.form["description"],
            request.form["collected_date"],
            request.form["collected_by"],
            request.form["location_found"],
            request.form["status"]
        )

        error = write_db(
            """
            INSERT INTO evidence
            (
                case_number,
                evidence_type,
                description,
                collected_date,
                collected_by,
                location_found,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
            "Evidence could not be added"
        )

        if error:
            return error

        return redirect(url_for("evidence"))

    return render_template("add_evidence.html")


# =========================
# EDIT EVIDENCE
# =========================

@app.route("/edit-evidence/<int:evidence_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_evidence(evidence_id):

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["evidence_type"],
            request.form["description"],
            request.form["collected_date"],
            request.form["collected_by"],
            request.form["location_found"],
            request.form["status"],
            evidence_id
        )

        error = write_db(
            """
            UPDATE evidence
            SET
                case_number = ?,
                evidence_type = ?,
                description = ?,
                collected_date = ?,
                collected_by = ?,
                location_found = ?,
                status = ?
            WHERE id = ?
            """,
            values,
            "Evidence could not be updated"
        )

        if error:
            return error

        return redirect(url_for("evidence"))

    evidence_item = fetch_one(
        "SELECT * FROM evidence WHERE id = ?",
        (evidence_id,)
    )

    if not evidence_item:
        return "Evidence not found"

    return render_template("edit_evidence.html", evidence=evidence_item)


# =========================
# DELETE EVIDENCE
# =========================

@app.route("/delete-evidence/<int:evidence_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_evidence(evidence_id):

    error = write_db(
        "DELETE FROM evidence WHERE id = ?",
        (evidence_id,),
        "Evidence could not be deleted"
    )

    if error:
        return error

    return redirect(url_for("evidence"))


# ==================================================
# INVESTIGATION MANAGEMENT
# ==================================================

@app.route("/investigations")
@role_required("admin", "investigator")
def investigations():

    investigation_list = fetch_all(
        "SELECT * FROM investigations ORDER BY id DESC"
    )

    return render_template(
        "investigations.html",
        investigations=investigation_list
    )


# =========================
# ADD NEW INVESTIGATION
# =========================

@app.route("/add-investigation", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_investigation():

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["investigator"],
            request.form["investigation_date"],
            request.form["investigation_type"],
            request.form["details"],
            request.form["findings"],
            request.form["status"]
        )

        error = write_db(
            """
            INSERT INTO investigations
            (
                case_number,
                investigator,
                investigation_date,
                investigation_type,
                details,
                findings,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
            "Investigation could not be added"
        )

        if error:
            return error

        return redirect(url_for("investigations"))

    return render_template("add_investigation.html")


# =========================
# EDIT INVESTIGATION
# =========================

@app.route(
    "/edit-investigation/<int:investigation_id>",
    methods=["GET", "POST"]
)
@role_required("admin", "investigator")
def edit_investigation(investigation_id):

    if request.method == "POST":

        values = (
            request.form["case_number"],
            request.form["investigator"],
            request.form["investigation_date"],
            request.form["investigation_type"],
            request.form["details"],
            request.form["findings"],
            request.form["status"],
            investigation_id
        )

        error = write_db(
            """
            UPDATE investigations
            SET
                case_number = ?,
                investigator = ?,
                investigation_date = ?,
                investigation_type = ?,
                details = ?,
                findings = ?,
                status = ?
            WHERE id = ?
            """,
            values,
            "Investigation could not be updated"
        )

        if error:
            return error

        return redirect(url_for("investigations"))

    investigation = fetch_one(
        "SELECT * FROM investigations WHERE id = ?",
        (investigation_id,)
    )

    if not investigation:
        return "Investigation not found"

    return render_template(
        "edit_investigation.html",
        investigation=investigation
    )


# =========================
# DELETE INVESTIGATION
# =========================

@app.route(
    "/delete-investigation/<int:investigation_id>",
    methods=["POST"]
)
@role_required("admin", "investigator")
def delete_investigation(investigation_id):

    error = write_db(
        "DELETE FROM investigations WHERE id = ?",
        (investigation_id,),
        "Investigation could not be deleted"
    )

    if error:
        return error

    return redirect(url_for("investigations"))


# ==================================================
# CRIME COMPLAINT
# ==================================================

@app.route("/complaint", methods=["GET", "POST"])
@role_required("citizen")
def complaint():

    if request.method == "POST":

        values = (
            request.form["complaint_number"],
            session.get("username"),
            request.form["crime_type"],
            request.form["location"],
            request.form["incident_date"],
            request.form["description"]
        )

        error = write_db(
            """
            INSERT INTO complaints
            (
                complaint_number,
                username,
                crime_type,
                location,
                incident_date,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            values,
            "Complaint could not be submitted"
        )

        if error:
            return error

        return redirect(url_for("complaints"))

    return render_template("complaint.html")


# =========================
# VIEW CITIZEN COMPLAINTS
# =========================

@app.route("/complaints")
@role_required("citizen")
def complaints():

    complaint_list = fetch_all(
        "SELECT * FROM complaints WHERE username = ? ORDER BY id DESC",
        (session.get("username"),)
    )

    return render_template("complaints.html", complaints=complaint_list)


# ==================================================
# ADMIN / INVESTIGATOR
# VIEW ALL COMPLAINTS
# ==================================================

@app.route("/admin/complaints")
@role_required("admin", "investigator")
def admin_complaints():

    complaint_list = fetch_all("SELECT * FROM complaints ORDER BY id DESC")

    return render_template(
        "admin_complaints.html",
        complaints=complaint_list
    )


# =========================
# UPDATE COMPLAINT STATUS
# =========================

@app.route(
    "/admin/update-complaint/<int:complaint_id>",
    methods=["POST"]
)
@role_required("admin", "investigator")
def update_complaint(complaint_id):

    error = write_db(
        "UPDATE complaints SET status = ? WHERE id = ?",
        (request.form["status"], complaint_id),
        "Complaint status could not be updated"
    )

    if error:
        return error

    return redirect(url_for("admin_complaints"))


# ==================================================
# REPORTS
# ==================================================

@app.route("/reports")
@role_required("admin", "investigator")
def reports():

    return render_template(
        "reports.html",
        total_cases=count_rows("cases"),
        open_cases=count_rows("cases", "status = ?", ("Open",)),
        closed_cases=count_rows("cases", "status = ?", ("Closed",)),
        total_victims=count_rows("victims"),
        total_suspects=count_rows("suspects"),
        total_evidence=count_rows("evidence"),
        total_investigations=count_rows("investigations")
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================
# CREATE ADMIN / INVESTIGATOR FROM COMMAND LINE
# =========================
# Usage:
#   python app.py create-user
# Use this command when you want to create an account directly from the terminal.
# Website registration requires STAFF_REGISTRATION_CODE for admin/investigator roles.\n# Keep this CLI command restricted to trusted administrators with local machine access.

def create_user_cli():

    from getpass import getpass

    username = input("Username: ").strip()
    email = input("Email: ").strip()
    role = input("Role (admin / investigator / citizen): ").strip().lower()
    password = getpass("Password (min 6 characters): ")

    if role not in ("admin", "investigator", "citizen"):
        print("Invalid role.")
        return

    if not username or not email or len(password) < 6:
        print("Username, email and a password of 6+ characters are required.")
        return

    error = write_db(
        "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
        (username, email, generate_password_hash(password), role),
        "User could not be created"
    )

    print(error if error else f"User '{username}' created as {role}.")


def list_users_cli():

    rows = fetch_all("SELECT id, username, email, role FROM users ORDER BY id")

    if not rows:
        print("No users found.")
        return

    for row in rows:
        print(f"{row['id']:>3}  {row['username']:<20} {row['role']:<13} {row['email']}")


def set_role_cli():

    # Usage: python app.py set-role <username> <admin|investigator|citizen>
    if len(sys.argv) != 4 or sys.argv[3] not in ("admin", "investigator", "citizen"):
        print("Usage: python app.py set-role <username> <admin|investigator|citizen>")
        return

    username, role = sys.argv[2], sys.argv[3]

    if not fetch_one("SELECT id FROM users WHERE username = ?", (username,)):
        print(f"User '{username}' not found. Run: python app.py list-users")
        return

    error = write_db(
        "UPDATE users SET role = ? WHERE username = ?",
        (role, username),
        "Role could not be changed"
    )

    print(error if error else f"'{username}' is now {role}. Log out and log in again.")


# Create the tables automatically (works with python app.py, gunicorn, WSGI).
init_db()


# =========================
# START FLASK
# =========================

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "create-user":
        create_user_cli()
    elif len(sys.argv) > 1 and sys.argv[1] == "list-users":
        list_users_cli()
    elif len(sys.argv) > 1 and sys.argv[1] == "set-role":
        set_role_cli()
    else:
        app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")