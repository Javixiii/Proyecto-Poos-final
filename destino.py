from errores import ErrorValidacion
from validador import Validador


class Destino:

    CAMPOS_MODIFICABLES = ("nombre", "pais", "descripcion", "precio_base")

    def __init__(self, id_destino, nombre, pais, descripcion, precio_base):
        self._id_destino = None
        self._nombre = None
        self._pais = None
        self._descripcion = None
        self._precio_base = None
        self.id_destino = id_destino
        self.nombre = nombre
        self.pais = pais
        self.descripcion = descripcion
        self.precio_base = precio_base

    @property
    def id_destino(self):
        return self._id_destino

    @id_destino.setter
    def id_destino(self, valor):
        if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int) or valor < 1):
            raise ErrorValidacion("id_destino inválido", "El id de destino no es válido.")
        self._id_destino = valor

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        if not Validador.validar_texto(valor, 80):
            raise ErrorValidacion("nombre destino inválido", "El nombre del destino es obligatorio (máx. 80).")
        self._nombre = Validador.sanear_texto(valor, 80)

    @property
    def pais(self):
        return self._pais

    @pais.setter
    def pais(self, valor):
        if not Validador.validar_texto(valor, 60):
            raise ErrorValidacion("país inválido", "El país es obligatorio (máx. 60).")
        self._pais = Validador.sanear_texto(valor, 60)

    @property
    def descripcion(self):
        return self._descripcion

    @descripcion.setter
    def descripcion(self, valor):
        self._descripcion = Validador.sanear_texto(valor, 300)   # puede ir vacía

    @property
    def precio_base(self):
        return self._precio_base

    @precio_base.setter
    def precio_base(self, valor):
        if not Validador.validar_precio(valor):
            raise ErrorValidacion("precio inválido", "El precio debe ser un número mayor que cero.")
        self._precio_base = round(float(valor), 2)

    def modificar(self, datos: dict) -> None:
        """Actualiza solo campos permitidos. Si algo es inválido no cambia nada (todo o nada)."""
        if not isinstance(datos, dict) or not datos:
            raise ErrorValidacion("datos vacíos", "No hay datos para modificar.")
        extra = set(datos) - set(self.CAMPOS_MODIFICABLES)
        if extra:
            raise ErrorValidacion(f"campos no permitidos: {sorted(extra)}", "Hay campos que no se pueden modificar.")
        respaldo = (self._nombre, self._pais, self._descripcion, self._precio_base)
        try:
            for campo, valor in datos.items():
                setattr(self, campo, valor)
        except ErrorValidacion:
            self._nombre, self._pais, self._descripcion, self._precio_base = respaldo
            raise

    def __str__(self) -> str:
        return f"{self._nombre} ({self._pais}) - ${self._precio_base:,.0f}"
