"""BaseDatos: persistencia SQLite. Todas las consultas son parametrizadas (?) y cada
conexión activa las claves foráneas."""

import logging
import sqlite3
from contextlib import contextmanager

import configuracion as cfg
from errores import ErrorPersistencia, ErrorValidacion

log = logging.getLogger("viajes.db")


class BaseDatos:

    def __init__(self, ruta_bd=None):
        self._ruta_bd = ruta_bd or cfg.DB_RUTA
        self._conexion = None

    @property
    def ruta_bd(self):
        return self._ruta_bd

    @property
    def conexion(self):
        return self._conexion

    def conectar(self):
        if self._conexion is None:
            try:
                self._conexion = sqlite3.connect(self._ruta_bd)
                self._conexion.execute("PRAGMA foreign_keys = ON")   # SQLite las ignora si no se activan
            except sqlite3.Error as e:
                self._conexion = None
                log.error("No se pudo abrir la BD: %s", e)
                raise ErrorPersistencia(str(e)) from e
        return self._conexion

    def cerrar(self):
        if self._conexion is not None:
            self._conexion.close()
            self._conexion = None

    def __enter__(self):
        self.conectar()
        return self

    def __exit__(self, *_):
        self.cerrar()

    @contextmanager
    def transaccion(self):
        """Commit si todo sale bien; rollback ante cualquier error. Traduce errores de SQLite."""
        conexion = self.conectar()
        try:
            yield conexion.cursor()
            conexion.commit()
        except sqlite3.IntegrityError as e:
            conexion.rollback()
            log.warning("Violación de integridad: %s", e)
            raise ErrorValidacion(str(e), "El registro ya existe o viola una restricción de datos.") from e
        except sqlite3.Error as e:
            conexion.rollback()
            log.error("Error SQLite: %s", e)
            raise ErrorPersistencia(str(e)) from e
        except Exception:
            conexion.rollback()
            raise

    def guardar(self, consulta, parametros=()):
        """INSERT/UPDATE/DELETE parametrizado. Devuelve el id de la última fila insertada."""
        with self.transaccion() as cur:
            cur.execute(consulta, parametros)
            return cur.lastrowid

    def consultar(self, consulta, parametros=()):
        """SELECT parametrizado. Devuelve una lista de tuplas."""
        try:
            return self.conectar().execute(consulta, parametros).fetchall()
        except sqlite3.Error as e:
            log.error("Error SQLite: %s", e)
            raise ErrorPersistencia(str(e)) from e

    def crear_tablas(self):
        with self.transaccion() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS usuario(
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('Cliente','Administrador')),
                telefono TEXT,
                documento TEXT,
                rol TEXT
            )""")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_email ON usuario(lower(email))")
            c.execute("""
            CREATE TABLE IF NOT EXISTS destino(
                id_destino INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                pais TEXT NOT NULL,
                descripcion TEXT,
                precio_base REAL NOT NULL CHECK(precio_base > 0)
            )""")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_destino ON destino(lower(nombre), lower(pais))")
            c.execute("""
            CREATE TABLE IF NOT EXISTS paquete(
                id_paquete INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL,
                fecha_fin TEXT NOT NULL,
                cupos_disponibles INTEGER NOT NULL CHECK(cupos_disponibles >= 0),
                costo_adicional REAL NOT NULL CHECK(costo_adicional >= 0),
                CHECK(fecha_fin >= fecha_inicio)
            )""")
            c.execute("""
            CREATE TABLE IF NOT EXISTS paquete_destino(
                id_paquete INTEGER NOT NULL,
                id_destino INTEGER NOT NULL,
                PRIMARY KEY(id_paquete, id_destino),
                FOREIGN KEY(id_paquete) REFERENCES paquete(id_paquete) ON DELETE CASCADE,
                FOREIGN KEY(id_destino) REFERENCES destino(id_destino) ON DELETE RESTRICT
            )""")
            c.execute("""
            CREATE TABLE IF NOT EXISTS reserva(
                id_reserva INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_reserva TEXT NOT NULL,
                estado TEXT NOT NULL CHECK(estado IN ('Pendiente','Confirmada','Cancelada')),
                costo_total REAL NOT NULL CHECK(costo_total >= 0),
                id_cliente INTEGER NOT NULL,
                id_paquete INTEGER NOT NULL,
                FOREIGN KEY(id_cliente) REFERENCES usuario(id_usuario),
                FOREIGN KEY(id_paquete) REFERENCES paquete(id_paquete)
            )""")
