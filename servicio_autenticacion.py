"""ServicioAutenticacion: registro, login y cambio de contraseña (hash PBKDF2 con salt)."""

import logging
import time

from administrador import Administrador
from cliente import Cliente
import configuracion as cfg
from errores import (ErrorAutenticacion, ErrorBloqueo, ErrorPermiso, ErrorValidacion)
from seguridad import HashContraseña, verificacion_ficticia, verificar_password
from validador import Validador

log = logging.getLogger("viajes.auth")
_COLS = "id_usuario, nombre, email, password_hash, tipo, telefono, documento, rol"


class ServicioAutenticacion:

    def __init__(self, base_datos, reloj=time.monotonic):
        self._db = base_datos
        self._reloj = reloj
        self._fallos = {}   # email -> (intentos, bloqueado_hasta)

    # ---- hash (UML: hashear_password / verificar_password) ----
    def hashear_password(self, password: str) -> HashContraseña:
        return HashContraseña.desde_password(password)

    def verificar_password(self, password: str, hash_guardado) -> bool:
        return verificar_password(password, hash_guardado)

    # ---- registro ----
    def registrar_usuario(self, cliente: Cliente, password: str) -> bool:
        """Registro público de un cliente. Valida datos y política de contraseña antes de guardar."""
        if not isinstance(cliente, Cliente):
            raise ErrorPermiso("solo se registran clientes", "Tipo de usuario no permitido.")
        if not cliente.registrar():
            raise ErrorValidacion("datos de cliente inválidos", "Los datos del cliente no son válidos.")
        if not Validador.validar_password(password):
            raise ErrorValidacion("password débil",
                                  "La contraseña debe tener 8-128 caracteres con mayúscula, minúscula y número.")
        cliente.password_hash = self.hashear_password(password)
        self._insertar(cliente)
        return True

    def crear_administrador_inicial(self, admin: Administrador, password: str) -> bool:
        """Solo si todavía no existe ningún usuario (configuración inicial)."""
        if self._db.consultar("SELECT COUNT(*) FROM usuario")[0][0] > 0:
            raise ErrorPermiso("ya existen usuarios; setup inicial bloqueado", "La configuración inicial ya se realizó.")
        if not Validador.validar_password(password):
            raise ErrorValidacion("password débil",
                                  "La contraseña debe tener 8-128 caracteres con mayúscula, minúscula y número.")
        admin.password_hash = self.hashear_password(password)
        self._insertar(admin)
        return True

    def _insertar(self, u):
        es_cliente = isinstance(u, Cliente)
        u.id_usuario = self._db.guardar(
            """INSERT INTO usuario(nombre, email, password_hash, tipo, telefono, documento, rol)
               VALUES (?,?,?,?,?,?,?)""",
            (u.nombre, u.email, u.password_hash.valor, u.TIPO,
             u.telefono if es_cliente else None, u.documento if es_cliente else None,
             None if es_cliente else u.rol))
        log.info("Usuario registrado id=%s tipo=%s", u.id_usuario, u.TIPO)

    # ---- login ----
    def iniciar_sesion(self, email: str, password: str):
        if not Validador.validar_email(email):
            raise ErrorValidacion("email inválido", "El correo no tiene un formato válido o no contiene '@'.")
        if not isinstance(password, str) or not password or len(password) > 128:
            raise ErrorValidacion("password vacía", "Debe ingresar su contraseña.")
        email = Validador.sanear_texto(email, 254).lower()
        self._revisar_bloqueo(email)
        usuario = self._buscar_por_email(email)
        if usuario is None:
            verificacion_ficticia(password)                # mismo costo que un login real
            self._registrar_fallo(email)
            raise ErrorAutenticacion("email inexistente")
        if not usuario.autenticar(email, password):
            self._registrar_fallo(email)
            raise ErrorAutenticacion("password incorrecta")
        self._fallos.pop(email, None)
        log.info("Login correcto usuario=%s tipo=%s", usuario.id_usuario, usuario.TIPO)
        return usuario

    def _buscar_por_email(self, email):
        filas = self._db.consultar(f"SELECT {_COLS} FROM usuario WHERE lower(email) = lower(?)", (email,))
        if not filas:
            return None
        id_, nombre, mail, hash_, tipo, telefono, documento, rol = filas[0]
        if tipo == "Administrador":
            return Administrador(id_, nombre, mail, hash_, rol)
        return Cliente(id_, nombre, mail, hash_, telefono, documento)

    def _revisar_bloqueo(self, email):
        _, hasta = self._fallos.get(email, (0, 0))
        if hasta and self._reloj() < hasta:
            raise ErrorBloqueo("cuenta temporalmente bloqueada")
        if hasta:
            self._fallos.pop(email, None)

    def _registrar_fallo(self, email):
        intentos, _ = self._fallos.get(email, (0, 0))
        intentos += 1
        hasta = self._reloj() + cfg.BLOQUEO_LOGIN_SEG if intentos >= cfg.MAX_INTENTOS_LOGIN else 0
        self._fallos[email] = (intentos, hasta)
        log.warning("Login fallido intento=%s", intentos)    # sin email ni clave en el log

    # ---- cambio de contraseña ----
    def cambiar_password(self, usuario, actual: str, nueva: str) -> bool:
        if not usuario.cambiar_password(actual, nueva):
            return False
        self._db.guardar("UPDATE usuario SET password_hash = ? WHERE id_usuario = ?",
                         (usuario.password_hash.valor, usuario.id_usuario))
        log.info("Contraseña cambiada usuario=%s", usuario.id_usuario)
        return True
