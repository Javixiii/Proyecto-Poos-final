from datetime import date

from errores import ErrorNegocio, ErrorValidacion
from validador import Validador


class Reserva:

    ESTADOS = ("Pendiente", "Confirmada", "Cancelada")

    def __init__(self, id_reserva, fecha_reserva, estado, costo_total, id_cliente, id_paquete, paquete=None):
        self._id_reserva = id_reserva
        self._fecha_reserva = Validador.a_fecha(fecha_reserva) if fecha_reserva else date.today()
        self._estado = None
        self._costo_total = None
        self._id_cliente = id_cliente      # asociación: Cliente 1 — 0..* Reserva
        self._id_paquete = id_paquete      # asociación: Reserva 0..* — 1 PaqueteTuristico
        self._paquete = paquete
        self.estado = estado
        self.costo_total = costo_total

    @property
    def id_reserva(self):
        return self._id_reserva

    @id_reserva.setter
    def id_reserva(self, valor):
        self._id_reserva = valor           # la BD lo asigna una sola vez

    @property
    def fecha_reserva(self):
        return self._fecha_reserva

    @property
    def estado(self):
        return self._estado

    @estado.setter
    def estado(self, valor):
        if valor not in self.ESTADOS:
            raise ErrorValidacion("estado inválido", "Estado de reserva inválido.")
        self._estado = valor

    @property
    def costo_total(self):
        return self._costo_total

    @costo_total.setter
    def costo_total(self, valor):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor < 0:
            raise ErrorValidacion("costo inválido", "El costo total no es válido.")
        self._costo_total = round(float(valor), 2)

    @property
    def id_cliente(self):
        return self._id_cliente

    @property
    def id_paquete(self):
        return self._id_paquete

    @property
    def paquete(self):
        return self._paquete

    # ---------------- comportamiento (UML) ----------------
    def confirmar(self) -> None:
        if self._estado != "Pendiente":
            raise ErrorNegocio(f"confirmar desde {self._estado}", "Solo se puede confirmar una reserva pendiente.")
        self._estado = "Confirmada"

    def cancelar(self) -> None:
        if self._estado == "Cancelada":
            raise ErrorNegocio("ya cancelada", "La reserva ya está cancelada.")
        self._estado = "Cancelada"

    def calcular_total(self) -> float:
        """Con el paquete cargado recalcula; si no, devuelve el costo guardado al reservar."""
        return self._paquete.calcular_costo() if self._paquete is not None else self._costo_total

    def __str__(self) -> str:
        return f"Reserva #{self._id_reserva} | {self._fecha_reserva} | {self._estado} | ${self._costo_total:,.0f}"
