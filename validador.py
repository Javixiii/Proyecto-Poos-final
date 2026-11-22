"""Validador: validación y saneamiento de entradas (lista blanca, no lista negra).
Los métodos validar_* devuelven bool, según el diagrama de clases."""

import math
import re
import unicodedata
from datetime import date, datetime

from errores import ErrorValidacion

PRECIO_MAXIMO = 1_000_000_000
_RE_EMAIL = re.compile(r"^[a-z0-9._%+\-]{1,64}@[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}$")
_RE_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ '\-]{0,59}$")
_RE_TELEFONO = re.compile(r"^\+?[0-9]{8,12}$")
_RE_DOCUMENTO = re.compile(r"^[A-Za-z0-9.\-]{5,20}$")


class Validador:

    # ---------- saneamiento ----------
    @staticmethod
    def sanear_texto(valor, max_largo=200) -> str:
        """Normaliza Unicode, elimina caracteres de control y recorta espacios."""
        if not isinstance(valor, str):
            raise ErrorValidacion("tipo no texto", "Debe ingresar un texto.")
        valor = unicodedata.normalize("NFKC", valor)
        valor = "".join(c for c in valor if c.isprintable()).strip()
        if len(valor) > max_largo:
            raise ErrorValidacion("entrada demasiado larga", f"El texto supera los {max_largo} caracteres.")
        return valor

    @staticmethod
    def a_fecha(valor) -> date:
        """Acepta date o texto AAAA-MM-DD. Lanza ErrorValidacion si no es una fecha real."""
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        try:
            return datetime.strptime(Validador.sanear_texto(valor, 10), "%Y-%m-%d").date()
        except ValueError:
            raise ErrorValidacion("fecha inválida", "Fecha inválida (use AAAA-MM-DD).") from None

    # ---------- validaciones (bool) ----------
    @staticmethod
    def validar_email(email: str) -> bool:
        try:
            email = Validador.sanear_texto(email, 254).lower()
        except ErrorValidacion:
            return False
        return "@" in email and bool(_RE_EMAIL.match(email))     # debe contener "@"

    @staticmethod
    def validar_fecha(fecha) -> bool:
        try:
            Validador.a_fecha(fecha)
            return True
        except ErrorValidacion:
            return False

    @staticmethod
    def validar_texto(texto: str, max_largo: int = 100) -> bool:
        try:
            return Validador.sanear_texto(texto, max_largo) != ""
        except ErrorValidacion:
            return False

    @staticmethod
    def validar_precio(precio: float) -> bool:
        if isinstance(precio, bool) or not isinstance(precio, (int, float)):
            return False
        return math.isfinite(precio) and 0 < precio <= PRECIO_MAXIMO

    @staticmethod
    def validar_password(password: str) -> bool:
        """Política para contraseñas nuevas: 8-128 caracteres con mayúscula, minúscula y número."""
        return (isinstance(password, str) and 8 <= len(password) <= 128
                and re.search(r"[a-z]", password) is not None
                and re.search(r"[A-Z]", password) is not None
                and re.search(r"[0-9]", password) is not None)

    # ---------- auxiliares ----------
    @staticmethod
    def validar_nombre(nombre: str) -> bool:
        try:
            return bool(_RE_NOMBRE.match(Validador.sanear_texto(nombre, 60)))
        except ErrorValidacion:
            return False

    @staticmethod
    def validar_telefono(telefono: str) -> bool:
        try:
            return bool(_RE_TELEFONO.match(Validador.sanear_texto(telefono, 15).replace(" ", "")))
        except ErrorValidacion:
            return False

    @staticmethod
    def validar_documento(documento: str) -> bool:
        try:
            return bool(_RE_DOCUMENTO.match(Validador.sanear_texto(documento, 20)))
        except ErrorValidacion:
            return False

    @staticmethod
    def validar_opcion(texto, validas) -> str:
        texto = Validador.sanear_texto(texto, 5)
        if texto not in validas:
            raise ErrorValidacion("opción inválida", "Opción no válida.")
        return texto
