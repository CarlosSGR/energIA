from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
CORS(app)

db_config = {
    'host': 'localhost',
    'user': 'root',         
    'password': 'Sydgad-Sinput012', 
    'database': 'ControlRecibos'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ==========================================
# ENDPOINT: REGISTRO DE USUARIO
# ==========================================
@app.route('/api/registro', methods=['POST'])
def registro():
    data = request.json
    nombres = data.get('nombres')
    apellidos = data.get('apellidos')
    correo = data.get('correo')
    contrasena = data.get('contrasena')

    # Concatenación para coincidir con tu esquema de BD
    nombre_completo = f"{nombres} {apellidos}".strip()
    
    # Hash de seguridad para la contraseña
    contrasena_hash = generate_password_hash(contrasena)
    fecha_registro = datetime.now().strftime('%Y-%m-%d')
    rol_default = 1 # Asume que el ID 1 existe en la tabla Rol

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO Usuario (Rol, `Nombre(s)`, Correo, Contrasena, FechaRegistro) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (rol_default, nombre_completo, correo, contrasena_hash, fecha_registro))
        conn.commit()
        
        return jsonify({"status": "success", "message": "Usuario registrado correctamente"}), 201

    except mysql.connector.IntegrityError as err:
        # 1062: Error de duplicado (ej. correo ya registrado)
        if err.errno == 1062:
            return jsonify({"status": "error", "message": "El correo ya está registrado"}), 409
        # 1452: Error de llave foránea (ej. el Rol 1 no existe)
        elif err.errno == 1452:
            return jsonify({"status": "error", "message": "Error interno: El Rol por defecto no existe en la base de datos"}), 500
        else:
            return jsonify({"status": "error", "message": f"Error de integridad: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# ==========================================
# ENDPOINT: LOGIN DE USUARIO
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    correo = data.get('correo')
    contrasena = data.get('contrasena')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT Id, `Nombre(s)`, Contrasena FROM Usuario WHERE Correo = %s"
        cursor.execute(query, (correo,))
        usuario = cursor.fetchone()
        
        # Se verifica si el usuario existe y si el hash coincide con la contraseña ingresada
        if usuario and check_password_hash(usuario['Contrasena'], contrasena):
            return jsonify({
                "status": "success", 
                "userId": usuario['Id'],
                "nombre": usuario['Nombre(s)']
            }), 200
        else:
            return jsonify({"status": "error", "message": "Credenciales inválidas"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)