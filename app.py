from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os


# Load environment variables from .env
load_dotenv()

app = Flask(__name__)


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

        username = request.form["username"]
        password = request.form["password"]

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

            return redirect(url_for("dashboard"))

        return "Invalid username or password"

    return render_template("login.html")


# =========================
# REGISTRATION PAGE
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            query = """
                INSERT INTO users
                (username, email, password, role)
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

        except mysql.connector.Error as error:

            connection.rollback()

            return f"Registration failed: {error}"

        finally:

            cursor.close()
            connection.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================
# DASHBOARD PAGE
# =========================

@app.route("/dashboard")
def dashboard():

    return render_template("dashboard.html")


# =========================
# CASE MANAGEMENT
# =========================

@app.route("/cases")
def cases():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM cases
        ORDER BY id DESC
    """

    cursor.execute(query)

    cases = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "cases.html",
        cases=cases
    )


# =========================
# ADD NEW CASE
# =========================

@app.route("/add-case", methods=["GET", "POST"])
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
# VICTIM MANAGEMENT
# =========================

@app.route("/victims")
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
# SUSPECT MANAGEMENT
# =========================

@app.route("/suspects")
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
# EVIDENCE MANAGEMENT
# =========================

@app.route("/evidence")
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


# =========================
# INVESTIGATION MANAGEMENT
# =========================

@app.route("/investigations")
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


# =========================
# REPORTS
# =========================

@app.route("/reports")
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
# START FLASK
# =========================

if __name__ == "__main__":

    app.run(debug=True)