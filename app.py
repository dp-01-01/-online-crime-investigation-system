from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import os


load_dotenv()

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login():
    return "Login page coming soon..."


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


if __name__ == "__main__":
    app.run(debug=True)