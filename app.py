from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from functools import wraps
import os


# Load environment variables from .env
load_dotenv()


# =========================
# FLASK APPLICATION
# =========================

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")


# =========================
# SESSION SECURITY
# =========================

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Keep False for local HTTP development.
# Change to True when deployed with HTTPS.
app.config["SESSION_COOKIE_SECURE"] = False


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
# DATABASE CONNECTION
# =========================

def get_db_connection():

    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


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

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT *
            FROM users
            WHERE username = %s
        """

        cursor.execute(query, (username,))

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

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
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Public registration is always for citizens.
        # Do not trust the role sent by the browser.
        role = "citizen"

        # Basic validation

        if not username or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all fields."
            )

        if len(password) < 6:

            return render_template(
                "register.html",
                error="Password must contain at least 6 characters."
            )

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            # Check whether username or email already exists

            check_query = """
                SELECT id
                FROM users
                WHERE username = %s
                   OR email = %s
            """

            cursor.execute(
                check_query,
                (username, email)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                return render_template(
                    "register.html",
                    error="Username or email already exists. Please use a different one."
                )

            # Insert new citizen account

            query = """
                INSERT INTO users
                (
                    username,
                    email,
                    password,
                    role
                )
                VALUES (%s, %s, %s, %s)
            """

            values = (
                username,
                email,
                hashed_password,
                role
            )

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error:

            connection.rollback()

            return render_template(
                "register.html",
                error="Registration failed. Please try again."
            )

        finally:

            cursor.close()
            connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")
# =========================
# DASHBOARD PAGE
# =========================

@app.route("/dashboard")
@login_required
def dashboard():

    connection = get_db_connection()
    cursor = connection.cursor()

    # Total cases
    cursor.execute("SELECT COUNT(*) FROM cases")
    total_cases = cursor.fetchone()[0]

    # Open cases
    cursor.execute(
        "SELECT COUNT(*) FROM cases WHERE status = %s",
        ("Open",)
    )
    open_cases = cursor.fetchone()[0]

    # Total victims
    cursor.execute("SELECT COUNT(*) FROM victims")
    total_victims = cursor.fetchone()[0]

    # Total suspects
    cursor.execute("SELECT COUNT(*) FROM suspects")
    total_suspects = cursor.fetchone()[0]

    # Total evidence
    cursor.execute("SELECT COUNT(*) FROM evidence")
    total_evidence = cursor.fetchone()[0]

    # Total investigations
    cursor.execute("SELECT COUNT(*) FROM investigations")
    total_investigations = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return render_template(
        "dashboard.html",
        total_cases=total_cases,
        open_cases=open_cases,
        total_victims=total_victims,
        total_suspects=total_suspects,
        total_evidence=total_evidence,
        total_investigations=total_investigations
    )


# ==================================================
# CASE MANAGEMENT
# ==================================================

@app.route("/cases")
@role_required("admin", "investigator")
def cases():

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM cases
        WHERE 1=1
    """

    values = []

    # SEARCH
    if search:

        query += """
            AND (
                case_number LIKE %s
                OR crime_type LIKE %s
                OR location LIKE %s
                OR investigator LIKE %s
            )
        """

        search_value = "%" + search + "%"

        values.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    # STATUS FILTER
    if status:

        query += """
            AND status = %s
        """

        values.append(status)

    query += """
        ORDER BY id DESC
    """

    cursor.execute(query, values)

    cases = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "cases.html",
        cases=cases,
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

        case_number = request.form["case_number"]
        crime_type = request.form["crime_type"]
        location = request.form["location"]
        incident_date = request.form["incident_date"]
        description = request.form["description"]
        status = request.form["status"]
        investigator = request.form["investigator"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            case_number,
            crime_type,
            location,
            incident_date,
            description,
            status,
            investigator
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Case could not be added: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("cases"))

    return render_template("add_case.html")


# =========================
# EDIT CASE
# =========================

@app.route("/edit-case/<int:case_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_case(case_id):

    connection = get_db_connection()

    if request.method == "POST":

        cursor = connection.cursor()

        case_number = request.form["case_number"]
        crime_type = request.form["crime_type"]
        location = request.form["location"]
        incident_date = request.form["incident_date"]
        description = request.form["description"]
        status = request.form["status"]
        investigator = request.form["investigator"]

        query = """
            UPDATE cases
            SET
                case_number = %s,
                crime_type = %s,
                location = %s,
                incident_date = %s,
                description = %s,
                status = %s,
                investigator = %s
            WHERE id = %s
        """

        values = (
            case_number,
            crime_type,
            location,
            incident_date,
            description,
            status,
            investigator,
            case_id
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Case could not be updated: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("cases"))

    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM cases
        WHERE id = %s
    """

    cursor.execute(query, (case_id,))

    case = cursor.fetchone()

    cursor.close()
    connection.close()

    if not case:

        return "Case not found"

    return render_template(
        "edit_case.html",
        case=case
    )


# =========================
# DELETE CASE
# =========================

@app.route("/delete-case/<int:case_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_case(case_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        DELETE FROM cases
        WHERE id = %s
    """

    try:

        cursor.execute(query, (case_id,))

        connection.commit()

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return f"Case could not be deleted: {error}"

    cursor.close()
    connection.close()

    return redirect(url_for("cases"))


# ==================================================
# VICTIM MANAGEMENT
# ==================================================

@app.route("/victims")
@role_required("admin", "investigator")
def victims():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM victims
        ORDER BY id DESC
    """

    cursor.execute(query)

    victims = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "victims.html",
        victims=victims
    )


# =========================
# ADD NEW VICTIM
# =========================

@app.route("/add-victim", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_victim():

    if request.method == "POST":

        case_number = request.form["case_number"]
        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        address = request.form["address"]
        description = request.form["description"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            case_number,
            name,
            age,
            gender,
            phone,
            address,
            description
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Victim could not be added: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("victims"))

    return render_template("add_victim.html")


# =========================
# EDIT VICTIM
# =========================

@app.route("/edit-victim/<int:victim_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_victim(victim_id):

    connection = get_db_connection()

    if request.method == "POST":

        cursor = connection.cursor()

        case_number = request.form["case_number"]
        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        address = request.form["address"]
        description = request.form["description"]

        query = """
            UPDATE victims
            SET
                case_number = %s,
                name = %s,
                age = %s,
                gender = %s,
                phone = %s,
                address = %s,
                description = %s
            WHERE id = %s
        """

        values = (
            case_number,
            name,
            age,
            gender,
            phone,
            address,
            description,
            victim_id
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Victim could not be updated: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("victims"))

    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM victims
        WHERE id = %s
    """

    cursor.execute(query, (victim_id,))

    victim = cursor.fetchone()

    cursor.close()
    connection.close()

    if not victim:

        return "Victim not found"

    return render_template(
        "edit_victim.html",
        victim=victim
    )


# =========================
# DELETE VICTIM
# =========================

@app.route("/delete-victim/<int:victim_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_victim(victim_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        DELETE FROM victims
        WHERE id = %s
    """

    try:

        cursor.execute(query, (victim_id,))

        connection.commit()

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return f"Victim could not be deleted: {error}"

    cursor.close()
    connection.close()

    return redirect(url_for("victims"))


# ==================================================
# SUSPECT MANAGEMENT
# ==================================================

@app.route("/suspects")
@role_required("admin", "investigator")
def suspects():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM suspects
        ORDER BY id DESC
    """

    cursor.execute(query)

    suspects = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "suspects.html",
        suspects=suspects
    )


# =========================
# ADD NEW SUSPECT
# =========================

@app.route("/add-suspect", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_suspect():

    if request.method == "POST":

        case_number = request.form["case_number"]
        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        address = request.form["address"]
        description = request.form["description"]
        status = request.form["status"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            case_number,
            name,
            age,
            gender,
            phone,
            address,
            description,
            status
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Suspect could not be added: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("suspects"))

    return render_template("add_suspect.html")


# =========================
# EDIT SUSPECT
# =========================

@app.route("/edit-suspect/<int:suspect_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_suspect(suspect_id):

    connection = get_db_connection()

    if request.method == "POST":

        cursor = connection.cursor()

        case_number = request.form["case_number"]
        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        address = request.form["address"]
        description = request.form["description"]
        status = request.form["status"]

        query = """
            UPDATE suspects
            SET
                case_number = %s,
                name = %s,
                age = %s,
                gender = %s,
                phone = %s,
                address = %s,
                description = %s,
                status = %s
            WHERE id = %s
        """

        values = (
            case_number,
            name,
            age,
            gender,
            phone,
            address,
            description,
            status,
            suspect_id
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Suspect could not be updated: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("suspects"))

    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM suspects
        WHERE id = %s
    """

    cursor.execute(query, (suspect_id,))

    suspect = cursor.fetchone()

    cursor.close()
    connection.close()

    if not suspect:

        return "Suspect not found"

    return render_template(
        "edit_suspect.html",
        suspect=suspect
    )

@app.route("/delete-suspect/<int:suspect_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_suspect(suspect_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        DELETE FROM suspects
        WHERE id = %s
    """

    try:

        cursor.execute(query, (suspect_id,))

        connection.commit()

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return f"Suspect could not be deleted: {error}"

    cursor.close()
    connection.close()

    return redirect(url_for("suspects"))


# ==================================================
# EVIDENCE MANAGEMENT
# ==================================================

@app.route("/evidence")
@role_required("admin", "investigator")
def evidence():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM evidence
        ORDER BY id DESC
    """

    cursor.execute(query)

    evidence = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "evidence.html",
        evidence=evidence
    )


# =========================
# ADD NEW EVIDENCE
# =========================

@app.route("/add-evidence", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_evidence():

    if request.method == "POST":

        case_number = request.form["case_number"]
        evidence_type = request.form["evidence_type"]
        description = request.form["description"]
        collected_date = request.form["collected_date"]
        collected_by = request.form["collected_by"]
        location_found = request.form["location_found"]
        status = request.form["status"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            case_number,
            evidence_type,
            description,
            collected_date,
            collected_by,
            location_found,
            status
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Evidence could not be added: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("evidence"))

    return render_template("add_evidence.html")


@app.route("/edit-evidence/<int:evidence_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_evidence(evidence_id):

    connection = get_db_connection()

    if request.method == "POST":

        cursor = connection.cursor()

        case_number = request.form["case_number"]
        evidence_type = request.form["evidence_type"]
        description = request.form["description"]
        collected_date = request.form["collected_date"]
        collected_by = request.form["collected_by"]
        location_found = request.form["location_found"]
        status = request.form["status"]

        query = """
            UPDATE evidence
            SET
                case_number = %s,
                evidence_type = %s,
                description = %s,
                collected_date = %s,
                collected_by = %s,
                location_found = %s,
                status = %s
            WHERE id = %s
        """

        values = (
            case_number,
            evidence_type,
            description,
            collected_date,
            collected_by,
            location_found,
            status,
            evidence_id
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Evidence could not be updated: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("evidence"))

    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM evidence
        WHERE id = %s
    """

    cursor.execute(query, (evidence_id,))

    evidence_item = cursor.fetchone()

    cursor.close()
    connection.close()

    if not evidence_item:

        return "Evidence not found"

    return render_template(
        "edit_evidence.html",
        evidence=evidence_item
    )

@app.route("/delete-evidence/<int:evidence_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_evidence(evidence_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        DELETE FROM evidence
        WHERE id = %s
    """

    try:

        cursor.execute(query, (evidence_id,))

        connection.commit()

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return f"Evidence could not be deleted: {error}"

    cursor.close()
    connection.close()

    return redirect(url_for("evidence"))

# ==================================================
# INVESTIGATION MANAGEMENT
# ==================================================

@app.route("/investigations")
@role_required("admin", "investigator")
def investigations():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM investigations
        ORDER BY id DESC
    """

    cursor.execute(query)

    investigations = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "investigations.html",
        investigations=investigations
    )


# =========================
# ADD NEW INVESTIGATION
# =========================

@app.route("/add-investigation", methods=["GET", "POST"])
@role_required("admin", "investigator")
def add_investigation():

    if request.method == "POST":

        case_number = request.form["case_number"]
        investigator = request.form["investigator"]
        investigation_date = request.form["investigation_date"]
        investigation_type = request.form["investigation_type"]
        details = request.form["details"]
        findings = request.form["findings"]
        status = request.form["status"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            case_number,
            investigator,
            investigation_date,
            investigation_type,
            details,
            findings,
            status
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Investigation could not be added: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("investigations"))

    return render_template("add_investigation.html")


@app.route("/edit-investigation/<int:investigation_id>", methods=["GET", "POST"])
@role_required("admin", "investigator")
def edit_investigation(investigation_id):

    connection = get_db_connection()

    if request.method == "POST":

        cursor = connection.cursor()

        case_number = request.form["case_number"]
        investigator = request.form["investigator"]
        investigation_date = request.form["investigation_date"]
        investigation_type = request.form["investigation_type"]
        details = request.form["details"]
        findings = request.form["findings"]
        status = request.form["status"]

        query = """
            UPDATE investigations
            SET
                case_number = %s,
                investigator = %s,
                investigation_date = %s,
                investigation_type = %s,
                details = %s,
                findings = %s,
                status = %s
            WHERE id = %s
        """

        values = (
            case_number,
            investigator,
            investigation_date,
            investigation_type,
            details,
            findings,
            status,
            investigation_id
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Investigation could not be updated: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("investigations"))

    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM investigations
        WHERE id = %s
    """

    cursor.execute(query, (investigation_id,))

    investigation = cursor.fetchone()

    cursor.close()
    connection.close()

    if not investigation:

        return "Investigation not found"

    return render_template(
        "edit_investigation.html",
        investigation=investigation
    )

@app.route("/delete-investigation/<int:investigation_id>", methods=["POST"])
@role_required("admin", "investigator")
def delete_investigation(investigation_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        DELETE FROM investigations
        WHERE id = %s
    """

    try:

        cursor.execute(query, (investigation_id,))

        connection.commit()

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return f"Investigation could not be deleted: {error}"

    cursor.close()
    connection.close()

    return redirect(url_for("investigations"))


# ==================================================
# CRIME COMPLAINT
# ==================================================

@app.route("/complaint", methods=["GET", "POST"])
@role_required("citizen")
def complaint():

    if request.method == "POST":

        complaint_number = request.form["complaint_number"]
        crime_type = request.form["crime_type"]
        location = request.form["location"]
        incident_date = request.form["incident_date"]
        description = request.form["description"]

        username = session.get("username")

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO complaints
            (
                complaint_number,
                username,
                crime_type,
                location,
                incident_date,
                description
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            complaint_number,
            username,
            crime_type,
            location,
            incident_date,
            description
        )

        try:

            cursor.execute(query, values)

            connection.commit()

        except mysql.connector.Error as error:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Complaint could not be submitted: {error}"

        cursor.close()
        connection.close()

        return redirect(url_for("complaints"))

    return render_template("complaint.html")


# =========================
# VIEW CITIZEN COMPLAINTS
# =========================

@app.route("/complaints")
@role_required("citizen")
def complaints():

    username = session.get("username")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM complaints
        WHERE username = %s
        ORDER BY id DESC
    """

    cursor.execute(query, (username,))

    complaints = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "complaints.html",
        complaints=complaints
    )


# ==================================================
# ADMIN / INVESTIGATOR
# VIEW ALL COMPLAINTS
# ==================================================

@app.route("/admin/complaints")
@role_required("admin", "investigator")
def admin_complaints():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM complaints
        ORDER BY id DESC
    """

    cursor.execute(query)

    complaints = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_complaints.html",
        complaints=complaints
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

    status = request.form["status"]

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        UPDATE complaints
        SET status = %s
        WHERE id = %s
    """

    values = (
        status,
        complaint_id
    )

    try:

        cursor.execute(query, values)

        connection.commit()

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return f"Complaint status could not be updated: {error}"

    cursor.close()
    connection.close()

    return redirect(url_for("admin_complaints"))


# ==================================================
# REPORTS
# ==================================================

@app.route("/reports")
@role_required("admin", "investigator")
def reports():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Total Cases
    cursor.execute(
        "SELECT COUNT(*) AS total FROM cases"
    )

    total_cases = cursor.fetchone()["total"]

    # Open Cases
    cursor.execute(
        "SELECT COUNT(*) AS total FROM cases WHERE status = 'Open'"
    )

    open_cases = cursor.fetchone()["total"]

    # Closed Cases
    cursor.execute(
        "SELECT COUNT(*) AS total FROM cases WHERE status = 'Closed'"
    )

    closed_cases = cursor.fetchone()["total"]

    # Total Victims
    cursor.execute(
        "SELECT COUNT(*) AS total FROM victims"
    )

    total_victims = cursor.fetchone()["total"]

    # Total Suspects
    cursor.execute(
        "SELECT COUNT(*) AS total FROM suspects"
    )

    total_suspects = cursor.fetchone()["total"]

    # Total Evidence
    cursor.execute(
        "SELECT COUNT(*) AS total FROM evidence"
    )

    total_evidence = cursor.fetchone()["total"]

    # Total Investigations
    cursor.execute(
        "SELECT COUNT(*) AS total FROM investigations"
    )

    total_investigations = cursor.fetchone()["total"]

    cursor.close()
    connection.close()

    return render_template(
        "reports.html",
        total_cases=total_cases,
        open_cases=open_cases,
        closed_cases=closed_cases,
        total_victims=total_victims,
        total_suspects=total_suspects,
        total_evidence=total_evidence,
        total_investigations=total_investigations
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================
# START FLASK
# =========================

if __name__ == "__main__":

    app.run(debug=True)