"""GestorPaquetes: creación y consulta de paquetes turísticos (con sus destinos)."""

import logging
from datetime import date

from destino import Destino
from paquete_turistico import PaqueteTuristico
from errores import ErrorNegocio, ErrorNoEncontrado, ErrorValidacion

log = logging.getLogger("viajes.paquetes")
_SQL = """SELECT p.id_paquete, p.nombre, p.fecha_inicio, p.fecha_fin, p.cupos_disponibles, p.costo_adicional,
                 d.id_destino, d.nombre, d.pais, d.descripcion, d.precio_base
          FROM paquete p
          LEFT JOIN paquete_destino pd ON pd.id_paquete = p.id_paquete
          LEFT JOIN destino d ON d.id_destino = pd.id_destino"""


class GestorPaquetes:

    def __init__(self, base_datos):
        self._db = base_datos

    def crear_paquete(self, paquete: PaqueteTuristico) -> None:
        if not isinstance(paquete, PaqueteTuristico):
            raise ErrorValidacion("no es paquete", "Paquete inválido.")
        if not paquete.destinos:
            raise ErrorNegocio("paquete sin destinos", "El paquete debe incluir al menos un destino.")
        if paquete.fecha_inicio < date.today():
            raise ErrorValidacion("fecha_inicio pasada", "La fecha de inicio no puede estar en el pasado.")
        with self._db.transaccion() as cur:            # paquete + destinos: todo o nada
            for d in paquete.destinos:
                cur.execute("SELECT 1 FROM destino WHERE id_destino = ?", (d.id_destino,))
                if cur.fetchone() is None:
                    raise ErrorNoEncontrado(f"destino {d.id_destino}", "Uno de los destinos no existe.")
            cur.execute("""INSERT INTO paquete(nombre, fecha_inicio, fecha_fin, cupos_disponibles, costo_adicional)
                           VALUES (?,?,?,?,?)""",
                        (paquete.nombre, paquete.fecha_inicio.isoformat(), paquete.fecha_fin.isoformat(),
                         paquete.cupos_disponibles, paquete.costo_adicional))
            paquete.id_paquete = cur.lastrowid
            for d in paquete.destinos:
                cur.execute("INSERT INTO paquete_destino(id_paquete, id_destino) VALUES (?,?)",
                            (paquete.id_paquete, d.id_destino))
        log.info("Paquete creado id=%s", paquete.id_paquete)

    def _cargar(self, where="", parametros=()):
        filas = self._db.consultar(f"{_SQL} {where} ORDER BY p.fecha_inicio, p.id_paquete", parametros)
        paquetes = {}
        for f in filas:
            if f[0] not in paquetes:
                paquetes[f[0]] = PaqueteTuristico(*f[:6])
            if f[6] is not None:
                paquetes[f[0]].agregar_destino(Destino(*f[6:]))
        return list(paquetes.values())

    def obtener_paquete(self, id_paquete: int) -> PaqueteTuristico:
        res = self._cargar("WHERE p.id_paquete = ?", (id_paquete,))
        if not res:
            raise ErrorNoEncontrado(f"paquete {id_paquete}", "El paquete no existe.")
        return res[0]

    def listar_paquetes(self):
        return self._cargar()

    def buscar_disponibles(self):
        return self._cargar("WHERE p.cupos_disponibles > 0 AND p.fecha_inicio >= ?", (date.today().isoformat(),))
