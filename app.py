
from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('patients.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            token TEXT PRIMARY KEY,
            name TEXT,
            age INTEGER,
            symptoms TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/save_patient', methods=['POST'])
def save_patient():
    data = request.json
    token = data['token']
    name = data['name']
    age = data['age']
    symptoms = data['symptoms']

    conn = sqlite3.connect('patients.db')
    c = conn.cursor()
    c.execute("SELECT * FROM patients WHERE token = ?", (token,))
    existing = c.fetchone()

    if existing:
        c.execute("UPDATE patients SET name = ?, age = ?, symptoms = ? WHERE token = ?", (name, age, symptoms, token))
        message = "Existing patient updated"
    else:
        c.execute("INSERT INTO patients (token, name, age, symptoms) VALUES (?, ?, ?, ?)", (token, name, age, symptoms))
        message = "New patient added"

    conn.commit()
    conn.close()
    return jsonify({"message": message}), 200

@app.route('/get_patient/<token>', methods=['GET'])
def get_patient(token):
    conn = sqlite3.connect('patients.db')
    c = conn.cursor()
    c.execute("SELECT name, age, symptoms FROM patients WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()

    if row:
        return jsonify({"name": row[0], "age": row[1], "symptoms": row[2]}), 200
    else:
        return jsonify({"error": "Token not found"}), 404

@app.route('/')
def home():
    return "Pregnancy Bot Backend Running"

if __name__ == '__main__':
    app.run(debug=True)
