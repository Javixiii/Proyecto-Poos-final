from abc import ABC, abstractmethod

from errores import ErrorValidacion
from seguridad import HashContraseña, es_hash
from validador import Validador


class Usuario(ABC):
    TIPO = None  # lo define cada subclase: "Cliente" / "Administrador"

    def __init__(self, id_usuario, nombre, email, password_hash):
        self._id_usuario = None
        self._nombre = None
        self._email = None
        self._password_hash = None
        # Las asignaciones pasan por los setters (validan antes de guardar)
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.email = email
        self.password_hash = password_hash

    # ---------------- id_usuario ----------------
    @property
    def id_usuario(self):
        return self._id_usuario

    @id_usuario.setter
    def id_usuario(self, valor):
        # None hasta que la BD asigna el id
        if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int) or valor < 1):
            raise ErrorValidacion("id_usuario inválido", "El id de usuario no es válido.")
        self._id_usuario = valor

    # ---------------- nombre ----------------
    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        if not Validador.validar_nombre(valor):
            raise ErrorValidacion("nombre inválido", "El nombre solo admite letras, espacios, ' y -.")
        self._nombre = Validador.sanear_texto(valor, 60)

    # ---------------- email (debe contener "@") ----------------
    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valor):
        if not isinstance(valor, str) or "@" not in valor:
            raise ErrorValidacion("email sin '@'", "El correo debe contener '@'.")
        if not Validador.validar_email(valor):
            raise ErrorValidacion("email inválido", "El correo no tiene un formato válido.")
        self._email = Validador.sanear_texto(valor, 254).lower()

    # ---------------- password_hash (objeto HashContraseña, no str) ----------------
    @property
    def password_hash(self):
        return self._password_hash

    @password_hash.setter
    def password_hash(self, valor):
        """Acepta: None (usuario aún sin registrar), un HashContraseña, el texto ya hasheado
        (leído desde SQLite) o una contraseña en texto plano, que se transforma con
        PBKDF2-HMAC-SHA256 + salt. Lo que queda guardado es siempre un HashContraseña."""
        if valor is None or isinstance(valor, HashContraseña):
            self._password_hash = valor
        elif es_hash(valor):
            self._password_hash = HashContraseña.desde_almacenado(valor)
        else:
            self._password_hash = HashContraseña.desde_password(valor)

    # ---------------- comportamiento (UML) ----------------
    def verificar_password(self, password) -> bool:
        return self._password_hash is not None and self._password_hash.verificar(password)

    def autenticar(self, email: str, password: str) -> bool:
        try:
            email = Validador.sanear_texto(email, 254).lower()
        except ErrorValidacion:
            return False
        return self._email == email and self.verificar_password(password)

    def validar_datos(self) -> bool:
        return (Validador.validar_nombre(self._nombre) and Validador.validar_email(self._email)
                and self._validar_datos_propios())

    def cambiar_password(self, actual: str, nueva: str) -> bool:
        """False si la contraseña actual no coincide. Lanza ErrorValidacion si la nueva es débil."""
        if not self.verificar_password(actual):
            return False
        if not Validador.validar_password(nueva):
            raise ErrorValidacion("password nueva débil",
                                  "La contraseña debe tener 8-128 caracteres con mayúscula, minúscula y número.")
        self._password_hash = HashContraseña.desde_password(nueva)
        return True

    @abstractmethod
    def _validar_datos_propios(self) -> bool:
        """Validación de los atributos específicos de cada subclase."""
