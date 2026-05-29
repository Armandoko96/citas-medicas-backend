import os
import re
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# Inicializar Flask y habilitar CORS
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey123_estudiante')

# Permitir orígenes dinámicos para CORS (local y producción)
frontend_url = os.environ.get('FRONTEND_URL')
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if frontend_url:
    allowed_origins.append(frontend_url.strip())

CORS(app, supports_credentials=True, origins=allowed_origins)

# Configurar cookies seguras para sesiones cross-domain en producción
if frontend_url:
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True
    )

# Intentar cargar variables desde .env si existe
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key.strip()] = val.strip()

# Configuración de la base de datos
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_name = os.environ.get('DB_NAME', 'citas_medicas')

# Seleccionar motor de base de datos
if db_user and db_host:
    import pymysql
    db_type = "MariaDB/MySQL"
    placeholder = "%s"
else:
    import sqlite3
    db_type = "SQLite local"
    placeholder = "?"

db_path = os.path.join(os.path.dirname(__file__), 'citas.db')
print(f"--> Conectando a la base de datos: {db_type}")

def get_db_connection():
    if db_user and db_host:
        return pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
    else:
        conn = sqlite3.connect(db_path)
        return conn

# ----------------- INICIALIZACIÓN DE TABLAR (SQL DIRECTO) -----------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    if db_user and db_host:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(200) NOT NULL,
            rol VARCHAR(20) DEFAULT 'paciente',
            tipo_plan VARCHAR(20) DEFAULT 'Seguro Básico',
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctores (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            especialidad VARCHAR(100) NOT NULL,
            consultorio VARCHAR(20) NOT NULL,
            costo DOUBLE NOT NULL,
            disponible BOOLEAN DEFAULT TRUE
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS citas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT NOT NULL,
            doctor_id INT NOT NULL,
            fecha VARCHAR(50) NOT NULL,
            motivo VARCHAR(200) NOT NULL,
            urgente BOOLEAN DEFAULT FALSE,
            atendida BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES doctores(id) ON DELETE CASCADE
        )
        """)
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT DEFAULT 'paciente',
            tipo_plan TEXT DEFAULT 'Seguro Básico',
            nombre TEXT NOT NULL,
            email TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            consultorio TEXT NOT NULL,
            costo REAL NOT NULL,
            disponible INTEGER DEFAULT 1
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            motivo TEXT NOT NULL,
            urgente INTEGER DEFAULT 0,
            atendida INTEGER DEFAULT 0,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES doctores(id) ON DELETE CASCADE
        )
        """)
    conn.commit()
    cursor.close()
    conn.close()

# Inicializar tablas
try:
    init_db()
except Exception as e:
    print(f"Error al inicializar base de datos: {e}")

# ----------------- SEMILLA DE DATOS (SEED) -----------------
def seed_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        admin_pass = generate_password_hash('admin123')
        cursor.execute(
            f"INSERT INTO usuarios (usuario, password, rol, tipo_plan, nombre, email) VALUES ({placeholder}, {placeholder}, 'admin', 'Seguro Premium', 'Administrador', 'laorbusiness@gmail.com')",
            ('admin', admin_pass)
        )
        paciente_pass = generate_password_hash('paciente123')
        cursor.execute(
            f"INSERT INTO usuarios (usuario, password, rol, tipo_plan, nombre, email) VALUES ({placeholder}, {placeholder}, 'paciente', 'Seguro Básico', 'Luis Armando Ojeda Rodríguez', 'laorbusiness@gmail.com')",
            ('paciente', paciente_pass)
        )
        conn.commit()
        print("--> Usuarios semilla creados correctamente (admin y paciente).")

    cursor.execute("SELECT COUNT(*) FROM doctores")
    if cursor.fetchone()[0] == 0:
        doctores = [
            ("Dr. Aldo Uriarte", "Medicina General", "101", 450.0),
            ("Dra. Laura Gómez", "Pediatría", "105", 600.0),
            ("Dr. Carlos Sánchez", "Cardiología", "202", 850.0),
            ("Dra. Sofía Martínez", "Dermatología", "109", 700.0),
            ("Dr. Juan Manuel Pérez", "Odontología", "103", 500.0)
        ]
        for d in doctores:
            cursor.execute(
                f"INSERT INTO doctores (nombre, especialidad, consultorio, costo, disponible) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 1)",
                d
            )
        conn.commit()
        print("--> Doctores semilla agregados al catálogo.")
        
    cursor.close()
    conn.close()

# Ejecutar semilla
try:
    seed_data()
except Exception as e:
    print(f"Error al sembrar datos: {e}")

# ----------------- RUTAS DE LA API -----------------

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    usuario_req = data.get('usuario', '').strip()
    password_req = data.get('password', '').strip()

    if not usuario_req or not password_req:
        return jsonify({"error": "Por favor ingresa usuario y contraseña."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id, usuario, password, rol, tipo_plan, nombre, email FROM usuarios WHERE usuario = {placeholder}",
        (usuario_req,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not check_password_hash(user[2], password_req):
        return jsonify({"error": "Usuario o contraseña incorrectos."}), 401

    # Guardar en sesión
    session['user_id'] = user[0]
    session['usuario'] = user[1]
    session['rol'] = user[3]
    session['tipo_plan'] = user[4]
    session['nombre'] = user[5]
    session['email'] = user[6]

    return jsonify({
        "mensaje": "Inicio de sesión exitoso",
        "usuario": {
            "id": user[0],
            "usuario": user[1],
            "rol": user[3],
            "tipo_plan": user[4],
            "nombre": user[5],
            "email": user[6]
        }
    }), 200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"mensaje": "Sesión cerrada correctamente"}), 200

@app.route('/api/auth/session', methods=['GET'])
def get_session():
    if 'user_id' in session:
        return jsonify({
            "autenticado": True,
            "usuario": {
                "id": session['user_id'],
                "usuario": session['usuario'],
                "rol": session['rol'],
                "tipo_plan": session['tipo_plan'],
                "nombre": session['nombre'],
                "email": session.get('email')
            }
        }), 200
    return jsonify({"autenticado": False, "usuario": None}), 200

@app.route('/api/auth/plan', methods=['POST'])
def cambiar_plan():
    if 'user_id' not in session:
        return jsonify({"error": "No has iniciado sesión."}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT tipo_plan FROM usuarios WHERE id = {placeholder}", (session['user_id'],))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        return jsonify({"error": "Usuario no encontrado."}), 404
    
    nuevo_plan = 'Seguro Premium' if user[0] == 'Seguro Básico' else 'Seguro Básico'
    cursor.execute(
        f"UPDATE usuarios SET tipo_plan = {placeholder} WHERE id = {placeholder}",
        (nuevo_plan, session['user_id'])
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    session['tipo_plan'] = nuevo_plan
    
    return jsonify({
        "mensaje": "Plan actualizado correctamente",
        "tipo_plan": nuevo_plan
    }), 200

@app.route('/api/doctores', methods=['GET'])
def get_doctores():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, especialidad, consultorio, costo, disponible FROM doctores")
    doctores = cursor.fetchall()
    cursor.close()
    conn.close()

    resultado = []
    for d in doctores:
        resultado.append({
            "id": d[0],
            "nombre": d[1],
            "especialidad": d[2],
            "consultorio": d[3],
            "costo": d[4],
            "disponible": bool(d[5])
        })
    return jsonify(resultado), 200

@app.route('/api/doctores', methods=['POST'])
def add_doctor():
    if 'user_id' not in session or session.get('rol') != 'admin':
        return jsonify({"error": "Acceso denegado. Se requiere cuenta de administrador."}), 403

    data = request.json
    nombre = data.get('nombre', '').strip()
    especialidad = data.get('especialidad', '').strip()
    consultorio = data.get('consultorio', '').strip()
    costo = data.get('costo')

    if not nombre or not especialidad or not consultorio or costo is None:
        return jsonify({"error": "Todos los campos son obligatorios."}), 400

    try:
        costo_float = float(costo)
        if costo_float <= 0:
            return jsonify({"error": "El costo debe ser un valor positivo."}), 400
    except ValueError:
        return jsonify({"error": "El costo debe ser un número válido."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO doctores (nombre, especialidad, consultorio, costo, disponible) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, 1)",
        (nombre, especialidad, consultorio, costo_float)
    )
    conn.commit()
    doc_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({"mensaje": "Doctor agregado al catálogo correctamente.", "id": doc_id}), 201

@app.route('/api/doctores/<int:id>', methods=['DELETE'])
def delete_doctor(id):
    if 'user_id' not in session or session.get('rol') != 'admin':
        return jsonify({"error": "Acceso denegado."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM doctores WHERE id = {placeholder}", (id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "Doctor no encontrado."}), 404

    cursor.execute(f"DELETE FROM doctores WHERE id = {placeholder}", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "Doctor eliminado correctamente."}), 200

@app.route('/api/citas', methods=['GET'])
def get_citas():
    if 'user_id' not in session:
        return jsonify({"error": "No has iniciado sesión."}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session.get('rol') == 'admin':
        cursor.execute("""
            SELECT c.id, c.usuario_id, u.nombre, c.doctor_id, d.nombre, d.especialidad, d.consultorio, d.costo, c.fecha, c.motivo, c.urgente, c.atendida
            FROM citas c
            JOIN usuarios u ON c.usuario_id = u.id
            JOIN doctores d ON c.doctor_id = d.id
        """)
    else:
        cursor.execute(f"""
            SELECT c.id, c.usuario_id, u.nombre, c.doctor_id, d.nombre, d.especialidad, d.consultorio, d.costo, c.fecha, c.motivo, c.urgente, c.atendida
            FROM citas c
            JOIN usuarios u ON c.usuario_id = u.id
            JOIN doctores d ON c.doctor_id = d.id
            WHERE c.usuario_id = {placeholder}
        """, (session['user_id'],))
        
    citas = cursor.fetchall()
    cursor.close()
    conn.close()

    resultado = []
    for c in citas:
        resultado.append({
            "id": c[0],
            "usuario_id": c[1],
            "paciente_nombre": c[2],
            "doctor_id": c[3],
            "doctor_nombre": c[4],
            "especialidad": c[5],
            "consultorio": c[6],
            "costo": c[7],
            "fecha": c[8],
            "motivo": c[9],
            "urgente": bool(c[10]),
            "atendida": bool(c[11])
        })
    return jsonify(resultado), 200

@app.route('/api/citas', methods=['POST'])
def add_cita():
    if 'user_id' not in session:
        return jsonify({"error": "Inicie sesión para agendar una cita."}), 401

    data = request.json
    doctor_id = data.get('doctor_id')
    fecha = data.get('fecha', '').strip()
    motivo = data.get('motivo', '').strip()
    urgente = bool(data.get('urgente', False))

    if not doctor_id or not fecha or not motivo:
        return jsonify({"error": "Debe rellenar la fecha, el motivo y seleccionar un médico."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT nombre FROM doctores WHERE id = {placeholder}", (doctor_id,))
    doctor = cursor.fetchone()
    if not doctor:
        cursor.close()
        conn.close()
        return jsonify({"error": "El médico seleccionado no existe en el catálogo."}), 404

    cursor.execute(
        f"INSERT INTO citas (usuario_id, doctor_id, fecha, motivo, urgente, atendida) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 0)",
        (session['user_id'], doctor_id, fecha, motivo, 1 if urgente else 0)
    )
    conn.commit()
    cita_id = cursor.lastrowid
    cursor.close()
    conn.close()

    # Obtener el correo al que se enviará la confirmación
    destinatario_real = data.get('email', '').strip()
    if not destinatario_real:
        destinatario_real = session.get('email')
    if not destinatario_real:
        destinatario_real = os.environ.get('MAIL_TO', 'laorbusiness@gmail.com')

    # Disparar envío del correo de confirmación
    try:
        from email_service import enviar_correo_confirmacion
        enviar_correo_confirmacion(
            paciente_email=destinatario_real,
            paciente_nombre=session['nombre'],
            doctor_nombre=doctor[0],
            fecha=fecha,
            motivo=motivo,
            urgente=urgente
        )
    except Exception as mail_err:
        print(f"Error al enviar correo: {mail_err}")

    return jsonify({
        "mensaje": "Cita agendada correctamente. Se ha enviado un correo de confirmación.",
        "cita": {
            "id": cita_id,
            "doctor_nombre": doctor[0],
            "fecha": fecha,
            "motivo": motivo,
            "urgente": urgente
        }
    }), 201

@app.route('/api/citas/<int:id>/atender', methods=['PUT', 'POST'])
def atender_cita(id):
    if 'user_id' not in session or session.get('rol') != 'admin':
        return jsonify({"error": "Acceso denegado. Se requiere cuenta de administrador."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM citas WHERE id = {placeholder}", (id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"error": "La cita no existe."}), 404

    cursor.execute(f"UPDATE citas SET atendida = 1 WHERE id = {placeholder}", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "La cita ha sido marcada como atendida."}), 200

@app.route('/api/citas/<int:id>', methods=['DELETE'])
def delete_cita(id):
    if 'user_id' not in session:
        return jsonify({"error": "Inicie sesión."}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT usuario_id FROM citas WHERE id = {placeholder}", (id,))
    cita = cursor.fetchone()
    if not cita:
        cursor.close()
        conn.close()
        return jsonify({"error": "La cita no existe."}), 404

    # Validar que el paciente sea dueño de su cita o sea un admin
    if session.get('rol') != 'admin' and cita[0] != session['user_id']:
        cursor.close()
        conn.close()
        return jsonify({"error": "No tiene permisos para cancelar esta cita."}), 403

    cursor.execute(f"DELETE FROM citas WHERE id = {placeholder}", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "La cita ha sido cancelada correctamente."}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
