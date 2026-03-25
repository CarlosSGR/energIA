# EnergIA - Smart Energy Solutions ⚡🤖

**EnergIA** es una plataforma web responsiva diseñada para ayudar a los usuarios a gestionar su consumo eléctrico. El sistema permite cargar recibos de luz, analizar datos mediante inteligencia artificial y obtener predicciones de consumo, facilitando el control del gasto energético en el hogar.

## 📋 Tabla de Contenidos
- [Objetivos del Proyecto](#-objetivos-del-proyecto)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [Equipo de Desarrollo](#-equipo-de-desarrollo)
- [Configuración de la Base de Datos](#-configuración-de-la-base-de-datos)

## 🎯 Objetivos del Proyecto
* **Gestión Eficiente:** Registro y control de consumos históricos de energía.
* **Predicción con IA:** Estimación de consumos y costos futuros basados en los recibos subidos.
* **Automatización:** Notificaciones sobre fechas de corte y pago.
* **Análisis:** Generación de recomendaciones personalizadas para el ahorro de energía.

## 🛠 Tecnologías Utilizadas
* **Backend:** Node.js & Java (procesamiento y validación).
* **IA & Automatización:** OpenAI API & n8n.
* **Base de Datos:** MySQL (XAMPP).
* **Diseño & Gestión:** Figma & Jira.
* **Documentación:** LaTeX.

## 👥 Equipo de Desarrollo
* **Alejandro Guzmán Lozano** - Líder del Proyecto
* **Ivana Alexandra Palomo Saldivar** - Análisis de Requerimientos
* **Victor Manuel de León Perez** - Análisis de Requerimientos
* **Carlos Sebastian Gonzalez Ramirez** - Desarrollador
* **Sandra Haydé Mar Segura** - Tester
* **Luis Alejandro Urbina Gómez** - Diseñador UI/UX

## 🗄️ Configuración de la Base de Datos (MySQL Workbench)

Para configurar el entorno de base de datos, copia y ejecuta el siguiente script en tu instancia de MySQL:

```sql
-- 1. Crear la base de datos
CREATE DATABASE ControlRecibos;
USE ControlRecibos;

-- 2. Tabla: Rol
CREATE TABLE Rol (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    Nombre VARCHAR(50) NOT NULL
);

-- 3. Tabla: Usuario
CREATE TABLE Usuario (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    Rol INT NOT NULL,
    Nombres VARCHAR(50) NOT NULL,
    Apellidos VARCHAR(50) NOT NULL,
    Correo VARCHAR(100) UNIQUE NOT NULL,
    Contrasena VARCHAR(255) NOT NULL,
    FechaRegistro DATE,
    TelegramChatId VARCHAR(20) DEFAULT NULL,
    Telefono VARCHAR(20),
    AceptaNotificaciones BOOLEAN DEFAULT 0,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (Rol) REFERENCES Rol(Id)
);

-- 4. Tabla: Recibos
CREATE TABLE Recibos (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    UsuarioId INT NOT NULL,
    Url VARCHAR(255),
    FechaSubida DATE,
    Estado VARCHAR(50),
    Consumo INT,
    Costo FLOAT,
    FechaInicio DATE,
    FechaFin DATE,
    FechaCorte DATE,
    FechaPago DATE,
    CONSTRAINT fk_recibos_usuario FOREIGN KEY (UsuarioId) REFERENCES Usuario(Id)
);

-- 5. Tabla: Predicción
CREATE TABLE Prediccion (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    ReciboId INT NOT NULL,
    ConsumoEstimado INT,
    CostoEstimado FLOAT,
    FechaGenerada DATE,
    FechaPredicha DATE,
    LecturaAnterior INT,
    LecturaActual INT,
    CONSTRAINT fk_prediccion_recibo FOREIGN KEY (ReciboId) REFERENCES Recibos(Id)
);

-- 6. Tabla: Errores
CREATE TABLE Errores (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    UsuarioId INT NOT NULL,
    Titulo VARCHAR(100),
    Mensaje VARCHAR(255),
    FechaReporte DATE,
    Estatus VARCHAR(50),
    CONSTRAINT fk_errores_usuario FOREIGN KEY (UsuarioId) REFERENCES Usuario(Id)
);

-- 7. Tabla: Notificación
CREATE TABLE Notificacion (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    UsuarioId INT NOT NULL,
    Tipo VARCHAR(50),
    FechaProgramada DATE,
    Estado VARCHAR(50),
    Cuerpo VARCHAR(255),
    HoraEnvio DATETIME,
    CONSTRAINT fk_notificacion_usuario FOREIGN KEY (UsuarioId) REFERENCES Usuario(Id)
);

-- 8. Tabla: Análisis
CREATE TABLE Analisis (
    Id INT PRIMARY KEY AUTO_INCREMENT,
    UsuarioId INT NOT NULL,
    FechaGeneracion DATETIME,
    PeriodoAnalizado VARCHAR(100),
    ConsumoTotal FLOAT,
    GastoTotal FLOAT,
    Comparativa VARCHAR(255),
    Recomendacion VARCHAR(255),
    CONSTRAINT fk_analisis_usuario FOREIGN KEY (UsuarioId) REFERENCES Usuario(Id)
);

-- Insertar datos iniciales
INSERT INTO Rol (Id, Nombre) VALUES (1, 'Usuario Estándar');
