import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
CORS(app)

db_config = {
    'host': 'localhost',
    'user': 'root',         
    'password': 'Sydgad-Sinput012', 
    'database': 'ControlRecibos'
}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/api/registro', methods=['POST'])
def registro():
    data = request.json
    nombres     = data.get('nombres')
    apellidos   = data.get('apellidos')
    correo      = data.get('correo')
    telefono    = data.get('telefono')
    contrasena  = data.get('contrasena')
    telegram    = data.get('telegram') or None   # None si viene vacío

    acepta_notificaciones = 1 if data.get('notificaciones') else 0
    contrasena_hash = generate_password_hash(contrasena)
    fecha_registro  = datetime.now().strftime('%Y-%m-%d')
    rol_default     = 1

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO Usuario 
                (Rol, Nombres, Apellidos, Correo, Contrasena, FechaRegistro, Telefono, AceptaNotificaciones, TelegramChatId) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            rol_default, nombres, apellidos, correo,
            contrasena_hash, fecha_registro, telefono,
            acepta_notificaciones, telegram
        ))
        conn.commit()

        return jsonify({"status": "success", "message": "Usuario registrado correctamente"}), 201

    except mysql.connector.IntegrityError as err:
        if err.errno == 1062:
            return jsonify({"status": "error", "message": "El correo ya está registrado"}), 409
        elif err.errno == 1452:
            return jsonify({"status": "error", "message": "Error interno: El Rol por defecto no existe en la base de datos"}), 500
        else:
            return jsonify({"status": "error", "message": f"Error de integridad: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data      = request.json
    correo    = data.get('correo')
    contrasena = data.get('contrasena')

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT Id, Nombres, Contrasena FROM Usuario WHERE Correo = %s"
        cursor.execute(query, (correo,))
        usuario = cursor.fetchone()

        if usuario and check_password_hash(usuario['Contrasena'], contrasena):
            return jsonify({
                "status": "success",
                "userId": usuario['Id'],
                "nombre": usuario['Nombres']
            }), 200
        else:
            return jsonify({"status": "error", "message": "Credenciales inválidas"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No se envió ningún archivo"}), 400

    file    = request.files['file']
    user_id = request.form.get('userId')

    if file.filename == '':
        return jsonify({"status": "error", "message": "Archivo no seleccionado"}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"status": "error", "message": "Solo se permiten archivos PDF"}), 400

    try:
        filename        = secure_filename(file.filename)
        timestamp       = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{user_id}_{timestamp}_{filename}"

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        conn   = get_db_connection()
        cursor = conn.cursor()
        fecha_subida = datetime.now().strftime('%Y-%m-%d')

        query = """
            INSERT INTO Recibos (UsuarioId, Url, FechaSubida, Estado) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, filepath, fecha_subida, 'Pendiente'))
        recibo_id = cursor.lastrowid
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Archivo subido correctamente",
            "file": {
                "id":   recibo_id,
                "name": filename,
                "date": fecha_subida
            }
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

@app.route('/api/recibos/<int:user_id>', methods=['GET'])
def obtener_recibos(user_id):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT Id, Url, FechaSubida, Estado FROM Recibos WHERE UsuarioId = %s ORDER BY FechaSubida DESC"
        cursor.execute(query, (user_id,))
        recibos = cursor.fetchall()

        archivos_formateados = []
        for r in recibos:
            filename_part  = os.path.basename(r['Url'])
            partes         = filename_part.split('_', 2)
            nombre_original = partes[2] if len(partes) > 2 else filename_part

            archivos_formateados.append({
                "id":     r['Id'],
                "name":   nombre_original,
                "date":   r['FechaSubida'].strftime('%Y-%m-%d'),
                "estado": r['Estado']
            })

        return jsonify({"status": "success", "archivos": archivos_formateados}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

@app.route('/api/recibos/<int:recibo_id>', methods=['DELETE'])
def eliminar_recibo(recibo_id):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT Url FROM Recibos WHERE Id = %s", (recibo_id,))
        recibo = cursor.fetchone()

        if recibo:
            filepath = recibo['Url']
            if os.path.exists(filepath):
                os.remove(filepath)

            cursor.execute("DELETE FROM Recibos WHERE Id = %s", (recibo_id,))
            conn.commit()

            return jsonify({"status": "success", "message": "Recibo eliminado correctamente"}), 200
        else:
            return jsonify({"status": "error", "message": "Recibo no encontrado"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)