import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# IMPORTAMOS TU SCRIPT DE VALIDACIÓN
from validar_pdf import validar_recibo_cfe

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
    telegram    = data.get('telegram') or None   

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

        query = "SELECT Id, Nombres, Contrasena, Rol FROM Usuario WHERE Correo = %s"
        cursor.execute(query, (correo,))
        usuario = cursor.fetchone()

        if usuario and check_password_hash(usuario['Contrasena'], contrasena):
            return jsonify({
                "status": "success",
                "userId": usuario['Id'],
                "nombre": usuario['Nombres'],
                "rol": usuario['Rol']
            }), 200
        else:
            return jsonify({"status": "error", "message": "Credenciales inválidas"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

# ==========================================
# ENDPOINT DE SUBIDA Y VALIDACIÓN
# ==========================================
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
        
        # 1. Guardamos el archivo físicamente para poder analizarlo
        file.save(filepath)

        # 2. VALIDAMOS EL ARCHIVO CON TU SCRIPT
        es_valido, mensaje_validacion = validar_recibo_cfe(filepath)

        if not es_valido:
            # Si el PDF no es de CFE, lo borramos del servidor y detenemos todo
            os.remove(filepath)
            return jsonify({"status": "error", "message": mensaje_validacion}), 400

        # 3. Si pasa la validación, lo guardamos en la base de datos
        conn   = get_db_connection()
        cursor = conn.cursor()
        fecha_subida = datetime.now().strftime('%Y-%m-%d')

        query = """
            INSERT INTO Recibos (UsuarioId, Url, FechaSubida, Estado) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, filepath, fecha_subida, 'Subido y Validado'))
        recibo_id = cursor.lastrowid
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Archivo subido y validado correctamente",
            "file": {
                "id":   recibo_id,
                "name": filename,
                "date": fecha_subida
            }
        }), 201

    except Exception as e:
        # Por si el PDF está corrupto y el script explota
        if os.path.exists(filepath): os.remove(filepath)
        return jsonify({"status": "error", "message": f"Error al procesar el archivo: {str(e)}"}), 500
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
                "estado": r['Estado'],
                "url": f"http://127.0.0.1:5000/api/uploads/{filename_part}" # Agregamos la URL para poder verlo
            })

        return jsonify({"status": "success", "archivos": archivos_formateados}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

# RUTA PARA VER LOS PDF
@app.route('/api/uploads/<path:filename>', methods=['GET'])
def serve_pdf(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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

# ==========================================
# HELPERS Y ENDPOINTS DE ADMINISTRADOR
# ==========================================
def verificar_admin(admin_id):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Rol FROM Usuario WHERE Id = %s", (admin_id,))
        user = cursor.fetchone()
        return user is not None and user['Rol'] == 2
    except Exception:
        return False
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

@app.route('/api/admin/usuarios', methods=['GET'])
def admin_get_usuarios():
    admin_id = request.args.get('adminId')
    if not admin_id or not verificar_admin(int(admin_id)):
        return jsonify({"status": "error", "message": "Acceso denegado"}), 403

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT Id, Nombres, Apellidos, Correo, Telefono, FechaRegistro "
            "FROM Usuario WHERE Rol = 1 ORDER BY Id"
        )
        usuarios = cursor.fetchall()
        for u in usuarios:
            if u['FechaRegistro']:
                u['FechaRegistro'] = u['FechaRegistro'].strftime('%Y-%m-%d')
        return jsonify({"status": "success", "usuarios": usuarios, "total": len(usuarios)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

@app.route('/api/admin/usuarios/<int:user_id>', methods=['DELETE'])
def admin_delete_usuario(user_id):
    data     = request.json or {}
    admin_id = data.get('adminId')
    if not admin_id or not verificar_admin(int(admin_id)):
        return jsonify({"status": "error", "message": "Acceso denegado"}), 403

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtenemos archivos físicos del usuario para borrarlos del disco
        cursor.execute("SELECT Url FROM Recibos WHERE UsuarioId = %s", (user_id,))
        recibos = cursor.fetchall()

        cursor2 = conn.cursor()
        # Borramos en orden para respetar las FK
        cursor2.execute(
            "DELETE p FROM Prediccion p "
            "JOIN Recibos r ON p.ReciboId = r.Id WHERE r.UsuarioId = %s", (user_id,)
        )
        cursor2.execute("DELETE FROM Recibos      WHERE UsuarioId = %s", (user_id,))
        cursor2.execute("DELETE FROM Analisis      WHERE UsuarioId = %s", (user_id,))
        cursor2.execute("DELETE FROM Notificacion  WHERE UsuarioId = %s", (user_id,))
        cursor2.execute("DELETE FROM Errores       WHERE UsuarioId = %s", (user_id,))
        cursor2.execute("DELETE FROM Usuario       WHERE Id = %s AND Rol = 1", (user_id,))
        conn.commit()

        if cursor2.rowcount == 0:
            return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        # Borrar archivos físicos
        for r in recibos:
            if r['Url'] and os.path.exists(r['Url']):
                os.remove(r['Url'])

        return jsonify({"status": "success", "message": "Usuario eliminado"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor'  in locals(): cursor.close()
        if 'cursor2' in locals(): cursor2.close()
        if 'conn'    in locals(): conn.close()

@app.route('/api/admin/tickets', methods=['GET'])
def admin_get_tickets():
    admin_id = request.args.get('adminId')
    if not admin_id or not verificar_admin(int(admin_id)):
        return jsonify({"status": "error", "message": "Acceso denegado"}), 403

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.Id, u.Correo, e.Titulo, e.Mensaje, e.FechaReporte, e.Estatus
            FROM Errores e
            JOIN Usuario u ON e.UsuarioId = u.Id
            ORDER BY e.Id
        """)
        tickets = cursor.fetchall()
        for t in tickets:
            if t['FechaReporte']:
                t['FechaReporte'] = t['FechaReporte'].strftime('%Y-%m-%d')
        return jsonify({"status": "success", "tickets": tickets, "total": len(tickets)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

@app.route('/api/admin/tickets/<int:ticket_id>', methods=['DELETE'])
def admin_delete_ticket(ticket_id):
    data     = request.json or {}
    admin_id = data.get('adminId')
    if not admin_id or not verificar_admin(int(admin_id)):
        return jsonify({"status": "error", "message": "Acceso denegado"}), 403

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Errores WHERE Id = %s", (ticket_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"status": "error", "message": "Ticket no encontrado"}), 404
        return jsonify({"status": "success", "message": "Ticket eliminado"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn'   in locals(): conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)