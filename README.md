# cse_final_3# Student Management REST API

A secure Flask API for managing university students with JWT auth, XML/JSON output, and search.

## 🛠️ Installation

1. Create DB: Run `students_db.sql` in MySQL
2. Update `config.py` with your MySQL credentials
3. Setup venv:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt