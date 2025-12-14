CREATE DATABASE IF NOT EXISTS students_db;
USE students_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    program VARCHAR(100) NOT NULL,
    year_level INT NOT NULL
);

-- Insert 20+ sample students
INSERT INTO students (student_id, first_name, last_name, email, program, year_level) VALUES
('2021-0001', 'Juan', 'Dela Cruz', 'juan@university.edu', 'Computer Science', 3),
('2021-0002', 'Maria', 'Santos', 'maria@university.edu', 'Information Technology', 2),
('2021-0003', 'Pedro', 'Gomez', 'pedro@university.edu', 'Computer Engineering', 4),
('2021-0004', 'Ana', 'Reyes', 'ana@university.edu', 'Data Science', 1),
('2021-0005', 'Luis', 'Aquino', 'luis@university.edu', 'Cybersecurity', 3),
('2021-0006', 'Sofia', 'Lim', 'sofia@university.edu', 'Software Engineering', 2),
('2021-0007', 'Carlos', 'Tan', 'carlos@university.edu', 'AI & Machine Learning', 4),
('2021-0008', 'Isabel', 'Ong', 'isabel@university.edu', 'Computer Science', 1),
('2021-0009', 'Miguel', 'Chua', 'miguel@university.edu', 'Information Systems', 3),
('2021-0010', 'Elena', 'Wong', 'elena@university.edu', 'IT Management', 2),
('2021-0011', 'Rafael', 'Sy', 'rafael@university.edu', 'Computer Science', 4),
('2021-0012', 'Carmen', 'Yu', 'carmen@university.edu', 'Data Analytics', 1),
('2021-0013', 'Diego', 'Cheng', 'diego@university.edu', 'Cybersecurity', 3),
('2021-0014', 'Lucia', 'Huang', 'lucia@university.edu', 'Software Engineering', 2),
('2021-0015', 'Gabriel', 'Lin', 'gabriel@university.edu', 'Computer Engineering', 4),
('2021-0016', 'Teresa', 'Chen', 'teresa@university.edu', 'AI', 1),
('2021-0017', 'Francisco', 'Lo', 'francisco@university.edu', 'IT', 3),
('2021-0018', 'Rosa', 'Ng', 'rosa@university.edu', 'Computer Science', 2),
('2021-0019', 'Antonio', 'Ko', 'antonio@university.edu', 'Data Science', 4),
('2021-0020', 'Luna', 'Fei', 'luna@university.edu', 'Information Technology', 1),
('2021-0021', 'Victor', 'Ma', 'victor@university.edu', 'Cybersecurity', 3);