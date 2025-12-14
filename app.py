from flask import Flask, jsonify, request, make_response
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
mysql = MySQL(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'student-api-secret-key')

# === JWT AUTH DECORATOR ===
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

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

# === REGISTER ===
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'User registered!'}), 201
    except Exception as e:
        if "Duplicate entry" in str(e):
            return jsonify({'error': 'Username already exists'}), 400
        return jsonify({'error': 'Registration failed'}), 500

# === LOGIN ===
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed))
    user = cur.fetchone()
    cur.close()

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})

# === CREATE STUDENT ===
@app.route('/students', methods=['POST'])
@token_required
def create_student():
    data = request.get_json()
    required = ['student_id', 'first_name', 'last_name', 'email', 'program', 'year_level']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        year = int(data['year_level'])
        if year < 1 or year > 4:
            return jsonify({'error': 'Year level must be between 1 and 4'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Year level must be an integer'}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO students (student_id, first_name, last_name, email, program, year_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data['student_id'], data['first_name'], data['last_name'], data['email'], data['program'], year))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Student added!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# === READ ALL + SEARCH ===
@app.route('/students', methods=['GET'])
@token_required
def get_students():
    fmt = request.args.get('format', 'json')
    search = request.args.get('search', None)

    cur = mysql.connection.cursor()
    if search:
        query = """
            SELECT * FROM students
            WHERE first_name LIKE %s OR last_name LIKE %s OR email LIKE %s OR program LIKE %s
        """
        like = f"%{search}%"
        cur.execute(query, (like, like, like, like))
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
    return format_response(students, fmt)

# === READ ONE ===
@app.route('/students/<int:id>', methods=['GET'])
@token_required
def get_student(id):
    fmt = request.args.get('format', 'json')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id = %s", (id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return jsonify({'error': 'Student not found'}), 404
    student = {
        'id': row[0],
        'student_id': row[1],
        'first_name': row[2],
        'last_name': row[3],
        'email': row[4],
        'program': row[5],
        'year_level': row[6]
    }
    return format_response(student, fmt)

# === UPDATE ===
@app.route('/students/<int:id>', methods=['PUT'])
@token_required
def update_student(id):
    data = request.get_json()
    required = ['student_id', 'first_name', 'last_name', 'email', 'program', 'year_level']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400
    try:
        year = int(data['year_level'])
        if year < 1 or year > 4:
            return jsonify({'error': 'Year level must be 1-4'}), 400
    except:
        return jsonify({'error': 'Year level must be integer'}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id = %s", (id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Not found'}), 404

    cur.execute("""
        UPDATE students
        SET student_id=%s, first_name=%s, last_name=%s, email=%s, program=%s, year_level=%s
        WHERE id=%s
    """, (data['student_id'], data['first_name'], data['last_name'], data['email'], data['program'], year, id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Student updated!'})

# === DELETE ===
@app.route('/students/<int:id>', methods=['DELETE'])
@token_required
def delete_student(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE id = %s", (id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Not found'}), 404
    cur.execute("DELETE FROM students WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Student deleted!'})

# === HEALTH CHECK ===
@app.route('/')
def index():
    return jsonify({"msg": "Student Management REST API"})

if __name__ == '__main__':
    app.run(debug=True)