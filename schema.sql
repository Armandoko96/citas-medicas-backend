-- Esquema de Base de Datos para MariaDB
-- Proyecto Final: Sistema de Citas Médicas
-- Alumno: Luis Armando Ojeda Rodríguez

CREATE DATABASE IF NOT EXISTS citas_medicas;
USE citas_medicas;

-- Tabla de Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(200) NOT NULL,
    rol VARCHAR(20) DEFAULT 'paciente',
    tipo_plan VARCHAR(20) DEFAULT 'Seguro Básico',
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL
);

-- Tabla de Catálogo de Doctores
CREATE TABLE IF NOT EXISTS doctores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    especialidad VARCHAR(100) NOT NULL,
    consultorio VARCHAR(20) NOT NULL,
    costo DOUBLE NOT NULL,
    disponible BOOLEAN DEFAULT TRUE
);

-- Tabla de Citas Médicas Agendadas
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
);

-- Inserción de Datos Iniciales (Usuarios de Prueba)
-- Contraseñas hasheadas con pbkdf2/scrypt de Python (admin123 y paciente123)
INSERT INTO usuarios (usuario, password, rol, tipo_plan, nombre, email) VALUES 
('admin', 'scrypt:32768:8:1$iC2rKkPEXBw1FpxL$367a731efc1b2c45d65825ee5cb6ebc4cb185c7f8a70c06db1f26f6345ecb3a2be10c3bcf6d3b36eeea206bbf5d8f6153724c96dd931a78ee9efc6ea211f42d5', 'admin', 'Seguro Premium', 'Administrador', 'laorbusiness@gmail.com'),
('paciente', 'scrypt:32768:8:1$n6bWdDqJ4H2c59sN$c79efcdb7ee8868ec1db2bc035987a0c7104be66a012ab63ab1c1b1df4e432acff81db19992bb18ff2b9cba35db20bbbf3d95efc5d4ef6fae109df7fbbf1ccca', 'paciente', 'Seguro Básico', 'Luis Armando Ojeda Rodríguez', 'laorbusiness@gmail.com')
ON DUPLICATE KEY UPDATE usuario=usuario;

-- Inserción de Doctores Semilla para el Catálogo
INSERT INTO doctores (nombre, especialidad, consultorio, costo, disponible) VALUES 
('Dr. Aldo Uriarte', 'Medicina General', '101', 450.0, TRUE),
('Dra. Laura Gómez', 'Pediatría', '105', 600.0, TRUE),
('Dr. Carlos Sánchez', 'Cardiología', '202', 850.0, TRUE),
('Dra. Sofía Martínez', 'Dermatología', '109', 700.0, TRUE),
('Dr. Juan Manuel Pérez', 'Odontología', '103', 500.0, TRUE);
