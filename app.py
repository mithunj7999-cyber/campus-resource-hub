from flask import Flask, render_template, request, redirect, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import re
import uuid

app = Flask(__name__)
app.secret_key = "campus_secret_key_123"

# Upload folder config
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "txt", "png", "jpg", "jpeg"}

# Check allowed file
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Database initialization
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        stored_filename TEXT UNIQUE NOT NULL,
        uploaded_by TEXT NOT NULL,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# Password strength checker
def is_strong_password(password):

    if len(password) < 8:
        return False

    if not re.search("[A-Z]", password):
        return False

    if not re.search("[a-z]", password):
        return False

    if not re.search("[0-9]", password):
        return False

    if not re.search("[@#$%^&+=!]", password):
        return False

    return True


# Home route
@app.route("/")
def home():

    if "username" not in session:
        return redirect("/login")

    return render_template("dashboard.html")



# Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if not is_strong_password(password):
            return "Weak password. Use uppercase, lowercase, number, special character."

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )

            conn.commit()
            conn.close()

            return redirect("/login")

        except:
            return "Username already exists"

    return render_template("signup.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT password FROM users WHERE username = ?",
            (username,)
        )

        result = cursor.fetchone()
        conn.close()

        if result:

            stored_password = result[0]

            if check_password_hash(stored_password, password):

                session["username"] = username
                return redirect("/")

            else:
                return "Wrong password"

        else:
            return "User not found"

    return render_template("login.html")


# Logout
@app.route("/logout")
def logout():

    session.pop("username", None)
    return redirect("/")


# Upload route
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":

        title = request.form.get("title")
        subject = request.form.get("subject")
        file = request.files.get("file")

        # Validation
        if not title or not subject:
            return "Title and Subject required"

        if not file or file.filename == "":
            return "No file selected"

        if not allowed_file(file.filename):
            return "File type not allowed"

        # Create unique filename
        original_filename = file.filename
        unique_id = str(uuid.uuid4())
        stored_filename = unique_id + "_" + original_filename

        # Save file
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
        file.save(file_path)

        # Save to database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO notes 
            (title, subject, original_filename, stored_filename, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            subject,
            original_filename,
            stored_filename,
            session["username"]
        ))

        conn.commit()
        conn.close()

        return "File uploaded successfully"


    return render_template("upload.html")


# Download
@app.route("/download/<filename>")
def download(filename):

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


# View notes
@app.route("/view")
def view():

    if "username" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, subject, original_filename, stored_filename, uploaded_by, upload_time 
        FROM notes 
        ORDER BY upload_time DESC
    """)

    notes = cursor.fetchall()

    conn.close()

    return render_template("view.html", notes=notes)


# Search
@app.route("/search")
def search():

    if "username" not in session:
        return redirect("/login")

    query = request.args.get("query")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, subject, original_filename, stored_filename, uploaded_by, upload_time
        FROM notes
        WHERE title LIKE ? OR subject LIKE ?
        ORDER BY upload_time DESC
    """, ('%' + query + '%', '%' + query + '%'))

    notes = cursor.fetchall()

    conn.close()

    return render_template("view.html", notes=notes)


# Run app
if __name__ == "__main__":

    # Create uploads folder if not exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    init_db()

    app.run(debug=True)
