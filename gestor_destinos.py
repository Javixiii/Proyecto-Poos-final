"""GestorDestinos: CRUD de destinos turísticos (consultas parametrizadas)."""

import logging

from destino import Destino
from errores import ErrorNegocio, ErrorNoEncontrado, ErrorValidacion

log = logging.getLogger("viajes.destinos")
_COLS = "id_destino, nombre, pais, descripcion, precio_base"


class GestorDestinos:

    def __init__(self, base_datos):
        self._db = base_datos

    def registrar_destino(self, destino: Destino) -> None:
        if not isinstance(destino, Destino):
            raise ErrorValidacion("no es Destino", "Destino inválido.")
        destino.id_destino = self._db.guardar(
            "INSERT INTO destino(nombre, pais, descripcion, precio_base) VALUES (?,?,?,?)",
            (destino.nombre, destino.pais, destino.descripcion, destino.precio_base))
        log.info("Destino registrado id=%s", destino.id_destino)

    def obtener_destino(self, id_destino: int) -> Destino:
        filas = self._db.consultar(f"SELECT {_COLS} FROM destino WHERE id_destino = ?", (id_destino,))
        if not filas:
            raise ErrorNoEncontrado(f"destino {id_destino}", "El destino no existe.")
        return Destino(*filas[0])

    def modificar_destino(self, id_destino: int, datos: dict) -> None:
        destino = self.obtener_destino(id_destino)
        destino.modificar(datos)                       # valida antes de tocar la BD
        self._db.guardar(
            "UPDATE destino SET nombre=?, pais=?, descripcion=?, precio_base=? WHERE id_destino=?",
            (destino.nombre, destino.pais, destino.descripcion, destino.precio_base, id_destino))
        log.info("Destino modificado id=%s", id_destino)

    def eliminar_destino(self, id_destino: int) -> None:
        self.obtener_destino(id_destino)               # lanza ErrorNoEncontrado si no existe
        en_uso = self._db.consultar("SELECT 1 FROM paquete_destino WHERE id_destino = ? LIMIT 1", (id_destino,))
        if en_uso:
            raise ErrorNegocio(f"destino {id_destino} en uso", "No se puede eliminar: el destino forma parte de un paquete.")
        self._db.guardar("DELETE FROM destino WHERE id_destino = ?", (id_destino,))
        log.info("Destino eliminado id=%s", id_destino)

    def listar_destinos(self):
        return [Destino(*f) for f in self._db.consultar(f"SELECT {_COLS} FROM destino ORDER BY nombre")]
