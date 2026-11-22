"""Hash de contraseñas con PBKDF2-HMAC-SHA256 y salt individual (solo librería estándar).

Formato almacenado:  pbkdf2_sha256$<iteraciones>$<salt_b64>$<hash_b64>

`HashContraseña` es un objeto de valor: representa el hash (no un str cualquiera),
nunca expone la contraseña original y se compara en tiempo constante.
"""

import base64
import hashlib
import hmac
import secrets

PREFIJO = "pbkdf2_sha256"
ITERACIONES = 600_000   # recomendación OWASP 2023 para PBKDF2-HMAC-SHA256
LARGO_SALT = 16         # 128 bits, único por contraseña
LARGO_HASH = 32         # 256 bits (salida de SHA-256)
MAX_ITERACIONES = 10_000_000


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def es_hash(valor) -> bool:
    """True si `valor` ya es un HashContraseña o un texto con el formato almacenado."""
    if isinstance(valor, HashContraseña):
        return True
    return isinstance(valor, str) and valor.startswith(PREFIJO + "$") and valor.count("$") == 3


class HashContraseña:
    """Hash PBKDF2-HMAC-SHA256 inmutable (iteraciones + salt + derivado)."""

    __slots__ = ("_iteraciones", "_salt", "_derivado")

    def __init__(self, iteraciones: int, salt: bytes, derivado: bytes):
        if not isinstance(iteraciones, int) or not (1 <= iteraciones <= MAX_ITERACIONES):
            raise ValueError("Iteraciones fuera de rango.")
        if not isinstance(salt, bytes) or not salt or not isinstance(derivado, bytes) or not derivado:
            raise ValueError("Salt o hash inválido.")
        object.__setattr__(self, "_iteraciones", iteraciones)
        object.__setattr__(self, "_salt", salt)
        object.__setattr__(self, "_derivado", derivado)

    # ---- Construcción ----
    @classmethod
    def desde_password(cls, password: str, iteraciones: int = None) -> "HashContraseña":
        """Calcula el hash de una contraseña en texto, con un salt aleatorio nuevo."""
        if not isinstance(password, str) or not password:
            raise ValueError("La contraseña no puede estar vacía.")
        iteraciones = iteraciones or ITERACIONES
        salt = secrets.token_bytes(LARGO_SALT)
        derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iteraciones, LARGO_HASH)
        return cls(iteraciones, salt, derivado)

    @classmethod
    def desde_almacenado(cls, texto: str) -> "HashContraseña":
        """Reconstruye el hash desde el texto guardado en la base de datos."""
        if not es_hash(texto):
            raise ValueError("Formato de hash inválido.")
        try:
            _, iteraciones, salt_b64, hash_b64 = texto.split("$")
            return cls(int(iteraciones), base64.b64decode(salt_b64, validate=True),
                       base64.b64decode(hash_b64, validate=True))
        except (ValueError, TypeError) as e:
            raise ValueError("Formato de hash inválido.") from e

    # ---- Uso ----
    def verificar(self, password: str) -> bool:
        """Comparación en tiempo constante (hmac.compare_digest)."""
        if not isinstance(password, str):
            return False
        calculado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), self._salt,
                                        self._iteraciones, len(self._derivado))
        return hmac.compare_digest(calculado, self._derivado)

    @property
    def iteraciones(self) -> int:
        return self._iteraciones

    @property
    def valor(self) -> str:
        """Texto para persistir en la base de datos."""
        return f"{PREFIJO}${self._iteraciones}${_b64(self._salt)}${_b64(self._derivado)}"

    # ---- Protocolo de objeto ----
    def __setattr__(self, nombre, valor):
        raise AttributeError("HashContraseña es inmutable.")

    def __eq__(self, otro):
        if not isinstance(otro, HashContraseña):
            return NotImplemented
        return (self._iteraciones == otro._iteraciones
                and hmac.compare_digest(self._salt, otro._salt)
                and hmac.compare_digest(self._derivado, otro._derivado))

    def __hash__(self):
        return hash((self._iteraciones, self._salt, self._derivado))

    def __str__(self):
        return self.valor

    def __repr__(self):                      # nunca imprime salt ni hash en logs o consola
        return f"HashContraseña({PREFIJO}, iteraciones={self._iteraciones}, ***)"


# ---- Funciones de compatibilidad (misma API que antes) ----
def hashear_password(password: str, iteraciones: int = None) -> str:
    return HashContraseña.desde_password(password, iteraciones).valor


def verificar_password(password: str, almacenado) -> bool:
    """Acepta un HashContraseña o su texto. Devuelve False ante cualquier formato anómalo."""
    try:
        h = almacenado if isinstance(almacenado, HashContraseña) else HashContraseña.desde_almacenado(almacenado)
        return h.verificar(password)
    except (ValueError, TypeError):
        return False


_HASH_FICTICIO = None


def verificacion_ficticia(password: str) -> None:
    """Consume el mismo tiempo que una verificación real cuando el correo no existe,
    para que la diferencia de tiempos no revele qué correos están registrados."""
    global _HASH_FICTICIO
    if _HASH_FICTICIO is None:
        _HASH_FICTICIO = HashContraseña.desde_password(secrets.token_urlsafe(16))
    _HASH_FICTICIO.verificar(password)
