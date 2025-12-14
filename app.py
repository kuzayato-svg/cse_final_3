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

# === RESPONSE FORMATTER (JSON/XML) ===
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
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        elif 'token' in session:
            token = session['token']

        if not token:
            if request.args.get('format') in ['json', 'xml']:
                return format_response({'message': 'Token is missing!'}, request.args.get('format')), 401
            else:
                return redirect(url_for('login'))

        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            if request.args.get('format') in ['json', 'xml']:
                return format_response({'message': 'Token is invalid!'}, request.args.get('format')), 401
            else:
                session.pop('token', None)
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# === REGISTER (HTML + JSON) ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template_string('''
        <h2>Register</h2>
        <form method="POST">
            <p><input type="text" name="username" placeholder="Username" required></p>
            <p><input type="password" name="password" placeholder="Password" required></p>
            <p><button type="submit">Register</button></p>
            <a href="/login">Already have an account?</a>
        </form>
        ''')

    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return '<h3>Error: Username and password required</h3><a href="/register">Try again</a>', 400

    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
        mysql.connection.commit()
        cur.close()
        return '<h3>Registered successfully!</h3><a href="/login">Login now</a>'
    except Exception as e:
        cur.close()
        if "Duplicate entry" in str(e):
            return '<h3>Username already exists</h3><a href="/register">Try again</a>', 400
        return '<h3>Registration failed</h3><a href="/register">Try again</a>', 500

# === LOGIN (HTML + JSON) ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string('''
        <h2>Login</h2>
        <form method="POST">
            <p><input type="text" name="username" placeholder="Username" required></p>
            <p><input type="password" name="password" placeholder="Password" required></p>
            <p><button type="submit">Login</button></p>
            <a href="/register">Don't have an account?</a>
        </form>
        ''')

    username = request.form.get('username')
    password = request.form.get('password')
    hashed = hashlib.sha256(password.encode()).hexdigest()

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed))
    user = cur.fetchone()
    cur.close()

    if not user:
        return '<h3>Invalid credentials</h3><a href="/login">Try again</a>', 401

    token = jwt.encode({
        'user': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    session['token'] = token
    return redirect(url_for('list_students'))

# === LOGOUT ===
@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))

# === CREATE STUDENT (HTML FORM) ===
@app.route('/students/new', methods=['GET', 'POST'])
@token_required
def create_student():
    if request.method == 'GET':
        return render_template_string('''
        <h2>Add New Student</h2>
        <form method="POST">
            <p><input name="student_id" placeholder="Student ID (e.g., 2021-0001)" required></p>
            <p><input name="first_name" placeholder="First Name" required></p>
            <p><input name="last_name" placeholder="Last Name" required></p>
            <p><input name="email" type="email" placeholder="Email" required></p>
            <p><input name="program" placeholder="Program (e.g., Computer Science)" required></p>
            <p><input name="year_level" type="number" min="1" max="4" placeholder="Year Level (1-4)" required></p>
            <p><button type="submit">Add Student</button></p>
            <a href="/students">Cancel</a>
        </form>
        ''')

    data = {
        'student_id': request.form['student_id'],
        'first_name': request.form['first_name'],
        'last_name': request.form['last_name'],
        'email': request.form['email'],
        'program': request.form['program'],
        'year_level': request.form['year_level']
    }

    try:
        year = int(data['year_level'])
        if year < 1 or year > 4:
            return '<h3>Error: Year level must be 1–4</h3><a href="/students/new">Try again</a>', 400
    except:
        return '<h3>Error: Year level must be a number</h3><a href="/students/new">Try again</a>', 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO students (student_id, first_name, last_name, email, program, year_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data['student_id'], data['first_name'], data['last_name'], data['email'], data['program'], year))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('list_students'))
    except Exception as e:
        cur.close()
        return f'<h3>Error: {str(e)}</h3><a href="/students/new">Try again</a>', 400

# === READ ALL + SEARCH (supports ?format=json/xml) ===
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

    html = '''
    <h2>Students</h2>
    <p><a href="/students?format=json">JSON</a> | <a href="/students?format=xml">XML</a></p>
    <form method="GET">
        <input type="text" name="search" placeholder="Search by name/email/program" value="{{search}}">
        <button type="submit">Search</button>
    </form>
    <p><a href="/students/new">Add New Student</a></p>
    <ul>
    {% for s in students %}
        <li>
            {{s.student_id}}: {{s.first_name}} {{s.last_name}} ({{s.program}}, Year {{s.year_level}})
            | <a href="/students/{{s.id}}">View</a>
            | <a href="/students/{{s.id}}?format=json">JSON</a>
            | <a href="/students/{{s.id}}?format=xml">XML</a>
            | <a href="/students/{{s.id}}/edit">Edit</a>
            | <a href="/students/{{s.id}}/delete" onclick="return confirm('Delete?')">Delete</a>
        </li>
    {% endfor %}
    </ul>
    <p><a href="/">Home</a> | <a href="/logout">Logout</a></p>
    '''
    return render_template_string(html, students=students, search=search)

# === VIEW / UPDATE / DELETE ===
@app.route('/students/<int:id>', methods=['GET', 'POST', 'DELETE'])
@token_required
def student_detail(id):
    if request.method == 'POST' and 'delete' in request.form:
        request.method = 'DELETE'

    fmt = request.args.get('format', 'html')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id = %s", (id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        if fmt in ['json', 'xml']:
            return format_response({'error': 'Student not found'}, fmt), 404
        else:
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

    if request.method == 'GET':
        if fmt in ['json', 'xml']:
            cur.close()
            return format_response(student, fmt)
        else:
            html = '''
            <h2>{{student.first_name}} {{student.last_name}}</h2>
            <p><strong>Student ID:</strong> {{student.student_id}}</p>
            <p><strong>Email:</strong> {{student.email}}</p>
            <p><strong>Program:</strong> {{student.program}}</p>
            <p><strong>Year Level:</strong> {{student.year_level}}</p>
            <p>
                <a href="/students/{{student.id}}/edit">Edit</a> |
                <form method="POST" style="display:inline" onsubmit="return confirm('Delete?')">
                    <input type="hidden" name="delete" value="1">
                    <button type="submit">Delete</button>
                </form> |
                <a href="/students">Back to list</a>
            </p>
            '''
            cur.close()
            return render_template_string(html, student=student)

    # Handle Update
    elif request.method == 'POST':
        if 'delete' not in request.form:
            data = {
                'student_id': request.form['student_id'],
                'first_name': request.form['first_name'],
                'last_name': request.form['last_name'],
                'email': request.form['email'],
                'program': request.form['program'],
                'year_level': request.form['year_level']
            }
            try:
                year = int(data['year_level'])
                if year < 1 or year > 4:
                    return '<h3>Error: Year level must be 1–4</h3><a href="/students/{{id}}/edit">Try again</a>', 400
            except:
                return '<h3>Error: Year level must be a number</h3><a href="/students/{{id}}/edit">Try again</a>', 400

            cur.execute("""
                UPDATE students
                SET student_id=%s, first_name=%s, last_name=%s, email=%s, program=%s, year_level=%s
                WHERE id=%s
            """, (data['student_id'], data['first_name'], data['last_name'], data['email'], data['program'], year, id))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('student_detail', id=id))

    # Handle DELETE
    if request.method == 'DELETE':
        cur.execute("DELETE FROM students WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        if fmt in ['json', 'xml']:
            return format_response({'message': 'Deleted'}, fmt)
        else:
            return redirect(url_for('list_students'))

# === EDIT FORM ===
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
        html = '''
        <h2>Edit Student</h2>
        <form method="POST" action="/students/{{s.id}}">
            <p><input name="student_id" value="{{s.student_id}}" required></p>
            <p><input name="first_name" value="{{s.first_name}}" required></p>
            <p><input name="last_name" value="{{s.last_name}}" required></p>
            <p><input name="email" type="email" value="{{s.email}}" required></p>
            <p><input name="program" value="{{s.program}}" required></p>
            <p><input name="year_level" type="number" min="1" max="4" value="{{s.year_level}}" required></p>
            <p><button type="submit">Save Changes</button></p>
            <a href="/students/{{s.id}}">Cancel</a>
        </form>
        '''
        return render_template_string(html, s=s)

# === HOME ===
@app.route('/')
def index():
    if 'token' in session:
        return '<h2>Welcome!</h2><p><a href="/students">View Students</a></p><p><a href="/logout">Logout</a></p>'
    else:
        return '<h2>Student Management App</h2><p><a href="/login">Login</a> or <a href="/register">Register</a></p>'

if __name__ == '__main__':
    app.run(debug=True)