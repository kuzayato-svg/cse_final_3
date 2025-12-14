from flask import Flask, request, jsonify, make_response, render_template_string, session, redirect, url_for
from flask_mysqldb import MySQL
import jwt
import datetime
from functools import wraps
import xml.dom.minidom
from xml.etree.ElementTree import Element, SubElement, tostring
import hashlib
import os

app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = os.environ.get('SECRET_KEY', 'student-api-secret-key')
mysql = MySQL(app)

# === RESPONSE FORMATTER (API ONLY) ===
def format_response(data, fmt='json'):
    if fmt.lower() == 'xml':
        root = Element('response')
        if isinstance(data, list):
            for item in data:
                elem = SubElement(root, 'student')
                for key, val in item.items():
                    SubElement(elem, key).text = str(val)
        else:
            for key, val in data.items():
                SubElement(root, key).text = str(val)
        rough = tostring(root, 'utf-8')
        reparsed = xml.dom.minidom.parseString(rough)
        xml_str = reparsed.toprettyxml(indent="  ")
        resp = make_response(xml_str)
        resp.headers['Content-Type'] = 'application/xml'
        return resp
    else:
        return jsonify(data)

# === JWT AUTH DECORATOR ===
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if request.headers.get('x-access-token'):
            token = request.headers['x-access-token']
        elif 'token' in session:
            token = session['token']

        if not token:
            if request.args.get('format') in ['json', 'xml']:
                return format_response({'error': 'Token missing'}, request.args.get('format')), 401
            else:
                return redirect(url_for('login'))

        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            if request.args.get('format') in ['json', 'xml']:
                return format_response({'error': 'Invalid token'}, request.args.get('format')), 401
            else:
                session.pop('token', None)
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# === REGISTER ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Register • Student Portal</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f7ff; margin: 0; padding: 0; }
                .container { max-width: 500px; margin: 60px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
                h2 { text-align: center; color: #1E3A8A; margin-bottom: 25px; }
                input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #1E3A8A; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
                button:hover { background: #1a3070; }
                a { display: block; text-align: center; margin-top: 15px; color: #1E3A8A; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🎓 Register</h2>
                <form method="POST">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Create Account</button>
                </form>
                <a href="/login">← Already have an account?</a>
            </div>
        </body>
        </html>
        ''')

    username = request.form['username']
    password = request.form['password']
    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('login'))
    except:
        cur.close()
        return '<h3 style="text-align:center;color:red">Error: Username already exists</h3><a href="/register" style="display:block;text-align:center">Try again</a>', 400

# === LOGIN ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login • Student Portal</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f7ff; margin: 0; padding: 0; }
                .container { max-width: 500px; margin: 60px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
                h2 { text-align: center; color: #1E3A8A; margin-bottom: 25px; }
                input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #1E3A8A; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
                button:hover { background: #1a3070; }
                a { display: block; text-align: center; margin-top: 15px; color: #1E3A8A; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🎓 Login</h2>
                <form method="POST">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Sign In</button>
                </form>
                <a href="/register">← Don't have an account?</a>
            </div>
        </body>
        </html>
        ''')

    username = request.form['username']
    password = request.form['password']
    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed))
    user = cur.fetchone()
    cur.close()

    if user:
        token = jwt.encode({'user': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
        session['token'] = token
        return redirect(url_for('list_students'))
    else:
        return '<h3 style="text-align:center;color:red">Invalid credentials</h3><a href="/login" style="display:block;text-align:center">Try again</a>', 401

# === LOGOUT ===
@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))

# === CREATE STUDENT ===
@app.route('/students/new', methods=['GET', 'POST'])
@token_required
def create_student():
    if request.method == 'GET':
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Student</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f7ff; padding: 20px; }
                .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
                h2 { color: #1E3A8A; margin-bottom: 20px; }
                input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }
                button { padding: 10px 20px; background: #1E3A8A; color: white; border: none; border-radius: 5px; cursor: pointer; }
                a { color: #1E3A8A; text-decoration: none; margin-top: 10px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>➕ Add New Student</h2>
                <form method="POST">
                    <input name="student_id" placeholder="Student ID (e.g., 2021-0001)" required>
                    <input name="first_name" placeholder="First Name" required>
                    <input name="last_name" placeholder="Last Name" required>
                    <input name="email" type="email" placeholder="Email" required>
                    <input name="program" placeholder="Program" required>
                    <input name="year_level" type="number" min="1" max="4" placeholder="Year Level (1-4)" required>
                    <button type="submit">Add Student</button>
                </form>
                <a href="/students">← Cancel</a>
            </div>
        </body>
        </html>
        ''')

    cur = mysql.connection.cursor()
    try:
        year = int(request.form['year_level'])
        if year < 1 or year > 4:
            raise ValueError
        cur.execute("""
            INSERT INTO students (student_id, first_name, last_name, email, program, year_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            request.form['student_id'],
            request.form['first_name'],
            request.form['last_name'],
            request.form['email'],
            request.form['program'],
            year
        ))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('list_students'))
    except Exception as e:
        print(e)
        cur.close()
        return '<h3 style="color:red">Error adding student. Check for duplicate ID/email.</h3><a href="/students/new">Try again</a>', 400

# === READ ALL + SEARCH ===
@app.route('/students', methods=['GET'])
@token_required
def list_students():
    search = request.args.get('search', '')
    fmt = request.args.get('format', 'html')

    cur = mysql.connection.cursor()
    if search:
        cur.execute("""
            SELECT * FROM students
            WHERE first_name LIKE %s OR last_name LIKE %s OR email LIKE %s OR program LIKE %s
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM students")
    rows = cur.fetchall()
    cur.close()

    students = []
    for row in rows:
        students.append({
            'id': row[0],
            'student_id': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'email': row[4],
            'program': row[5],
            'year_level': row[6]
        })

    if fmt in ['json', 'xml']:
        return format_response(students, fmt)

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Students • Student Portal</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f5f7ff; padding: 20px; }
            .container { max-width: 900px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
            h2 { color: #1E3A8A; }
            .controls { margin: 15px 0; text-align: center; }
            .controls a { margin: 0 10px; color: #1E3A8A; text-decoration: none; }
            form.inline { display: inline; }
            form.inline button {
                background: none;
                border: none;
                color: #1E3A8A;
                text-decoration: underline;
                cursor: pointer;
                font-size: 14px;
                padding: 0;
                margin: 0 10px 0 0;
            }
            form { text-align: center; margin: 20px 0; }
            input[type="text"] { padding: 8px; width: 300px; border: 1px solid #ccc; border-radius: 5px; }
            button { padding: 8px 16px; background: #1E3A8A; color: white; border: none; border-radius: 5px; cursor: pointer; }
            ul { list-style: none; padding: 0; }
            li { padding: 15px; margin: 10px 0; background: #f9fbff; border-left: 4px solid #1E3A8A; }
            .nav { margin-top: 20px; text-align: center; }
            .nav a { margin: 0 10px; color: #1E3A8A; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🎓 Student List</h2>
            <div class="controls">
                <a href="/students?format=json">[JSON]</a>
                <a href="/students?format=xml">[XML]</a>
            </div>
            <form method="GET">
                <input type="text" name="search" placeholder="Search by name/email/program" value="{{search}}">
                <button type="submit">Search</button>
            </form>
            <p><a href="/students/new" style="color:#1E3A8A">➕ Add New Student</a></p>
            <ul>
            {% for s in students %}
                <li>
                    <strong>{{s.student_id}}</strong>: {{s.first_name}} {{s.last_name}}<br>
                    {{s.program}}, Year {{s.year_level}} • {{s.email}}<br>
                    <a href="/students/{{s.id}}">View</a> |
                    <a href="/students/{{s.id}}/edit">Edit</a> |
                    <form class="inline" method="POST" action="/students/{{s.id}}/delete" onsubmit="return confirm('Delete this student?')">
                        <button type="submit">Delete</button>
                    </form>
                </li>
            {% endfor %}
            </ul>
            <div class="nav">
                <a href="/">Home</a> | <a href="/logout">Logout</a>
            </div>
        </div>
    </body>
    </html>
    ''', students=students, search=search)

# === VIEW STUDENT ===
@app.route('/students/<int:id>', methods=['GET'])
@token_required
def view_student(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id = %s", (id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return '<h3>Student not found</h3><a href="/students">Back</a>', 404

    student = {
        'id': row[0],
        'student_id': row[1],
        'first_name': row[2],
        'last_name': row[3],
        'email': row[4],
        'program': row[5],
        'year_level': row[6]
    }

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Student Details</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f5f7ff; padding: 20px; }
            .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
            h2 { color: #1E3A8A; }
            p { margin: 10px 0; }
            a { display: inline-block; margin: 5px 10px 0 0; padding: 8px 16px; background: #1E3A8A; color: white; text-decoration: none; border-radius: 5px; }
            form.inline { display: inline; }
            form.inline button {
                padding: 8px 16px; background: #d32f2f; color: white; border: none; border-radius: 5px; cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🎓 {{student.first_name}} {{student.last_name}}</h2>
            <p><strong>ID:</strong> {{student.student_id}}</p>
            <p><strong>Email:</strong> {{student.email}}</p>
            <p><strong>Program:</strong> {{student.program}}</p>
            <p><strong>Year:</strong> {{student.year_level}}</p>
            <a href="/students/{{student.id}}/edit">✏️ Edit</a>
            <form class="inline" method="POST" action="/students/{{student.id}}/delete" onsubmit="return confirm('Are you sure?')">
                <button type="submit">🗑️ Delete</button>
            </form>
            <a href="/students">← Back</a>
        </div>
    </body>
    </html>
    ''', student=student)

# === EDIT STUDENT ===
@app.route('/students/<int:id>/edit', methods=['GET', 'POST'])
@token_required
def edit_student(id):
    if request.method == 'GET':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students WHERE id = %s", (id,))
        row = cur.fetchone()
        cur.close()
        if not row:
            return '<h3>Not found</h3><a href="/students">Back</a>', 404
        s = {
            'id': row[0],
            'student_id': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'email': row[4],
            'program': row[5],
            'year_level': row[6]
        }
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edit Student</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f7ff; padding: 20px; }
                .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
                h2 { color: #1E3A8A; margin-bottom: 20px; }
                input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }
                button { padding: 10px 20px; background: #1E3A8A; color: white; border: none; border-radius: 5px; cursor: pointer; }
                a { color: #1E3A8A; text-decoration: none; margin-top: 10px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✏️ Edit Student</h2>
                <form method="POST" action="/students/{{s.id}}/update">
                    <input name="student_id" value="{{s.student_id}}" required>
                    <input name="first_name" value="{{s.first_name}}" required>
                    <input name="last_name" value="{{s.last_name}}" required>
                    <input name="email" type="email" value="{{s.email}}" required>
                    <input name="program" value="{{s.program}}" required>
                    <input name="year_level" type="number" min="1" max="4" value="{{s.year_level}}" required>
                    <button type="submit">Save Changes</button>
                </form>
                <a href="/students/{{s.id}}">← Cancel</a>
            </div>
        </body>
        </html>
        ''', s=s)

    cur = mysql.connection.cursor()
    try:
        year = int(request.form['year_level'])
        if year < 1 or year > 4:
            raise ValueError
        cur.execute("""
            UPDATE students SET student_id=%s, first_name=%s, last_name=%s, email=%s, program=%s, year_level=%s
            WHERE id=%s
        """, (
            request.form['student_id'],
            request.form['first_name'],
            request.form['last_name'],
            request.form['email'],
            request.form['program'],
            year,
            id
        ))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('view_student', id=id))
    except:
        cur.close()
        return '<h3>Error updating student</h3><a href="/students/{{id}}/edit">Try again</a>', 400

# === DELETE STUDENT (WORKING) ===
@app.route('/students/<int:id>/delete', methods=['POST'])
@token_required
def delete_student(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id = %s", (id,))
    if not cur.fetchone():
        cur.close()
        return '<h3>Student not found</h3><a href="/students">Back</a>', 404
    cur.execute("DELETE FROM students WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('list_students'))

# === UPDATE ROUTE ===
@app.route('/students/<int:id>/update', methods=['POST'])
@token_required
def update_student_route(id):
    return edit_student(id)

# === HOME ===
@app.route('/')
def index():
    if 'token' in session:
        return redirect(url_for('list_students'))
    else:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Student Portal</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f5f7ff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .box { text-align: center; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 0 30px rgba(0,0,0,0.15); }
                h1 { color: #1E3A8A; margin-bottom: 30px; }
                .btn { display: block; width: 200px; margin: 12px auto; padding: 12px; background: #1E3A8A; color: white; text-decoration: none; border-radius: 8px; }
                .btn:hover { background: #1a3070; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🎓 Student Management Portal</h1>
                <a href="/login" class="btn">Login</a>
                <a href="/register" class="btn">Register</a>
            </div>
        </body>
        </html>
        ''')

if __name__ == '__main__':
    app.run(debug=True)