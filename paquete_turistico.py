from datetime import date

from destino import Destino
from errores import ErrorNegocio, ErrorValidacion
from validador import PRECIO_MAXIMO, Validador


class PaqueteTuristico:

    def __init__(self, id_paquete, nombre, fecha_inicio, fecha_fin, cupos_disponibles, costo_adicional):
        self._id_paquete = None
        self._nombre = None
        self._fecha_inicio = None
        self._fecha_fin = None
        self._cupos_disponibles = None
        self._costo_adicional = None
        self._destinos = []          # composición 1..* con Destino
        self.id_paquete = id_paquete
        self.nombre = nombre
        self._fecha_inicio = Validador.a_fecha(fecha_inicio)
        self.fecha_fin = fecha_fin   # valida fecha_fin >= fecha_inicio
        self.cupos_disponibles = cupos_disponibles
        self.costo_adicional = costo_adicional

    @property
    def id_paquete(self):
        return self._id_paquete

    @id_paquete.setter
    def id_paquete(self, valor):
        if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int) or valor < 1):
            raise ErrorValidacion("id_paquete inválido", "El id de paquete no es válido.")
        self._id_paquete = valor

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        if not Validador.validar_texto(valor, 80):
            raise ErrorValidacion("nombre paquete inválido", "El nombre del paquete es obligatorio (máx. 80).")
        self._nombre = Validador.sanear_texto(valor, 80)

    @property
    def fecha_inicio(self):
        return self._fecha_inicio

    @property
    def fecha_fin(self):
        return self._fecha_fin

    @fecha_fin.setter
    def fecha_fin(self, valor):
        fin = Validador.a_fecha(valor)
        if fin < self._fecha_inicio:
            raise ErrorValidacion("fecha_fin < fecha_inicio", "La fecha de término no puede ser anterior al inicio.")
        self._fecha_fin = fin

    @property
    def cupos_disponibles(self):
        return self._cupos_disponibles

    @cupos_disponibles.setter
    def cupos_disponibles(self, valor):
        if isinstance(valor, bool) or not isinstance(valor, int) or not (0 <= valor <= 10_000):
            raise ErrorValidacion("cupos inválidos", "Los cupos deben ser un entero entre 0 y 10.000.")
        self._cupos_disponibles = valor

    @property
    def costo_adicional(self):
        return self._costo_adicional

    @costo_adicional.setter
    def costo_adicional(self, valor):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not (0 <= valor <= PRECIO_MAXIMO):
            raise ErrorValidacion("costo adicional inválido", "El costo adicional debe ser un número mayor o igual a cero.")
        self._costo_adicional = round(float(valor), 2)

    @property
    def destinos(self):
        return list(self._destinos)      # copia: no se modifica la lista desde afuera

    # ---------------- comportamiento (UML) ----------------
    def agregar_destino(self, destino: Destino) -> None:
        if not isinstance(destino, Destino):
            raise ErrorValidacion("no es Destino", "Destino inválido.")
        if any(d.id_destino == destino.id_destino and d.id_destino is not None for d in self._destinos):
            raise ErrorNegocio("destino repetido", "El destino ya está en el paquete.")
        self._destinos.append(destino)

    def quitar_destino(self, destino: Destino) -> None:
        if destino not in self._destinos:
            raise ErrorNegocio("destino no está en el paquete", "El destino no pertenece al paquete.")
        self._destinos.remove(destino)

    def calcular_costo(self) -> float:
        return round(sum(d.precio_base for d in self._destinos) + self._costo_adicional, 2)

    def consultar_disponibilidad(self) -> bool:
        return self._cupos_disponibles > 0 and self._fecha_inicio >= date.today()

    def reducir_cupo(self) -> None:
        if self._cupos_disponibles <= 0:
            raise ErrorNegocio("sin cupos", "El paquete no tiene cupos disponibles.")
        self._cupos_disponibles -= 1

    def liberar_cupo(self) -> None:
        self._cupos_disponibles += 1

    def __str__(self) -> str:
        return (f"{self._nombre} | {self._fecha_inicio} a {self._fecha_fin} | cupos {self._cupos_disponibles} | "
                f"${self.calcular_costo():,.0f}")
