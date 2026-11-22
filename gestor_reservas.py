"""GestorReservas: crea, cancela y consulta reservas. Cupos y reserva se guardan en UNA transacción."""

import logging

from cliente import Cliente
from reserva import Reserva
from errores import ErrorNegocio, ErrorNoEncontrado, ErrorPermiso, ErrorValidacion
from gestor_paquetes import GestorPaquetes

log = logging.getLogger("viajes.reservas")
_COLS = "id_reserva, fecha_reserva, estado, costo_total, id_cliente, id_paquete"


class GestorReservas:

    def __init__(self, base_datos, gestor_paquetes=None):
        self._db = base_datos
        self._paquetes = gestor_paquetes or GestorPaquetes(base_datos)

    def crear_reserva(self, cliente: Cliente, paquete) -> Reserva:
        if not isinstance(cliente, Cliente):
            raise ErrorPermiso("solo clientes reservan", "Solo un cliente puede realizar reservas.")
        paquete = self._paquetes.obtener_paquete(paquete.id_paquete)   # estado real, no el copiado en memoria
        reserva = cliente.realizar_reserva(paquete)                     # valida cupos y calcula el costo
        reserva.confirmar()
        with self._db.transaccion() as cur:
            # Descuento atómico: si otro cliente tomó el último cupo, rowcount = 0 y se revierte todo.
            cur.execute("""UPDATE paquete SET cupos_disponibles = cupos_disponibles - 1
                           WHERE id_paquete = ? AND cupos_disponibles > 0""", (paquete.id_paquete,))
            if cur.rowcount != 1:
                raise ErrorNegocio("sin cupos al reservar", "El paquete ya no tiene cupos disponibles.")
            cur.execute("""INSERT INTO reserva(fecha_reserva, estado, costo_total, id_cliente, id_paquete)
                           VALUES (?,?,?,?,?)""",
                        (reserva.fecha_reserva.isoformat(), reserva.estado, reserva.costo_total,
                         cliente.id_usuario, paquete.id_paquete))
            reserva.id_reserva = cur.lastrowid
        paquete.reducir_cupo()
        cliente._reemplazar_historial(self.obtener_historial(cliente))
        log.info("Reserva creada id=%s cliente=%s", reserva.id_reserva, cliente.id_usuario)
        return reserva

    def cancelar_reserva(self, id_reserva: int, cliente: Cliente = None) -> bool:
        """Si se indica `cliente`, la reserva debe ser suya (un cliente no cancela reservas ajenas)."""
        filas = self._db.consultar(f"SELECT {_COLS} FROM reserva WHERE id_reserva = ?", (id_reserva,))
        if not filas:
            raise ErrorNoEncontrado(f"reserva {id_reserva}", "La reserva no existe.")
        reserva = Reserva(*filas[0])
        if cliente is not None and reserva.id_cliente != cliente.id_usuario:
            raise ErrorPermiso(f"reserva {id_reserva} ajena", "La reserva no existe.")   # no revela que existe
        reserva.cancelar()
        with self._db.transaccion() as cur:
            cur.execute("UPDATE reserva SET estado = ? WHERE id_reserva = ? AND estado <> 'Cancelada'",
                        (reserva.estado, id_reserva))
            if cur.rowcount != 1:
                raise ErrorNegocio("cancelación concurrente", "La reserva ya está cancelada.")
            cur.execute("UPDATE paquete SET cupos_disponibles = cupos_disponibles + 1 WHERE id_paquete = ?",
                        (reserva.id_paquete,))
        if cliente is not None:
            cliente._reemplazar_historial(self.obtener_historial(cliente))
        log.info("Reserva cancelada id=%s", id_reserva)
        return True

    def obtener_historial(self, cliente: Cliente):
        if cliente.id_usuario is None:
            raise ErrorValidacion("cliente sin id", "El cliente no está registrado.")
        filas = self._db.consultar(
            f"SELECT {_COLS} FROM reserva WHERE id_cliente = ? ORDER BY id_reserva DESC", (cliente.id_usuario,))
        return [Reserva(*f) for f in filas]
