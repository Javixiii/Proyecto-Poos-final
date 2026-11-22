"""Punto de entrada de Viajes Aventura.  Ejecutar:  python main.py"""
from datetime import date, timedelta
import getpass
import logging

from base_datos import BaseDatos
from administrador import Administrador
from cliente import Cliente
from destino import Destino
from paquete_turistico import PaqueteTuristico
import configuracion as cfg
from errores import ErrorPermiso, ErrorValidacion, ErrorViajes
from gestor_destinos import GestorDestinos
from gestor_paquetes import GestorPaquetes
from gestor_reservas import GestorReservas
from servicio_autenticacion import ServicioAutenticacion
from validador import Validador

log = logging.getLogger("viajes.main")

def configurar_logging():
    """Los detalles técnicos van al archivo de log; la consola solo muestra mensajes seguros."""
    logging.basicConfig(filename=cfg.LOG_RUTA, level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

def exigir_rol(usuario, clase):
    """Control de acceso por rol: se comprueba el tipo real del objeto, no un dato escrito por el usuario."""
    if not isinstance(usuario, clase):
        log.warning("Acceso denegado usuario=%s accion=%s", usuario.id_usuario, clase.__name__)
        raise ErrorPermiso(f"{usuario.TIPO} sin acceso de {clase.__name__}")

DESTINOS_POR_DEFECTO = [
    ("Torres del Paine", "Chile", "Trekking y glaciares en la Patagonia chilena", 180000),
    ("San Pedro de Atacama", "Chile", "Desierto, salares y geiseres del Tatio", 150000),
    ("Isla de Pascua", "Chile", "Moáis, cultura Rapa Nui y playas", 320000),
    ("Valparaíso y Viña del Mar", "Chile", "Puerto patrimonial, cerros y ciudad jardín", 70000),
    ("Machu Picchu", "Perú", "Ciudadela inca y Valle Sagrado", 280000),
    ("Salar de Uyuni", "Bolivia", "El mayor salar del mundo y lagunas de colores", 210000),
    ("Cataratas del Iguazú", "Argentina", "Cascadas en plena selva subtropical", 240000),
    ("Buenos Aires", "Argentina", "Tango, gastronomía y arquitectura", 160000),
    ("Cartagena de Indias", "Colombia", "Ciudad amurallada y playas del Caribe", 260000),
    ("Río de Janeiro", "Brasil", "Cristo Redentor, Pan de Azúcar y Copacabana", 300000),
]

PAQUETES_POR_DEFECTO = [
    ("Patagonia Esencial", 30, 6, 12, 90000, ["Torres del Paine"]),
    ("Desierto de Atacama", 35, 5, 10, 60000, ["San Pedro de Atacama"]),
    ("Rapa Nui Aventura", 45, 7, 8, 150000, ["Isla de Pascua"]),
    ("Chile Clásico", 20, 8, 15, 70000, ["Valparaíso y Viña del Mar", "San Pedro de Atacama", "Torres del Paine"]),
    ("Perú Mágico", 50, 8, 10, 120000, ["Machu Picchu"]),
    ("Ruta del Altiplano", 55, 7, 9, 100000, ["San Pedro de Atacama", "Salar de Uyuni"]),
    ("Triple Frontera", 60, 6, 12, 80000, ["Cataratas del Iguazú", "Buenos Aires"]),
    ("Capitales del Cono Sur", 65, 7, 14, 70000, ["Buenos Aires", "Valparaíso y Viña del Mar"]),
    ("Caribe Colombiano", 75, 6, 10, 110000, ["Cartagena de Indias"]),
    ("Sudamérica Épica", 90, 14, 6, 250000,
     ["Machu Picchu", "Salar de Uyuni", "Cataratas del Iguazú", "Río de Janeiro"]),
]

class Aplicacion:

    def __init__(self, entrada=input, secreta=getpass.getpass, salida=print, db=None):
        self.entrada, self.secreta, self.salida = entrada, secreta, salida
        self.db = db or BaseDatos()
        self.auth = ServicioAutenticacion(self.db)
        self.destinos = GestorDestinos(self.db)
        self.paquetes = GestorPaquetes(self.db)
        self.reservas = GestorReservas(self.db, self.paquetes)

    # ---------------- utilidades ----------------
    def _seguro(self, accion):
        """Ejecuta una acción sin que ningún error detenga el sistema ni exponga detalles técnicos."""
        try:
            return accion()
        except EOFError:
            raise
        except ErrorViajes as e:
            log.warning("%s: %s", type(e).__name__, e)
            self.salida(f"  ✗ {e.mensaje_usuario}")
        except Exception:
            log.exception("Error no controlado")
            self.salida("  ✗ Ocurrió un error inesperado. La operación no se realizó.")
        return None

    def _numero(self, texto, etiqueta="ID"):
        texto = Validador.sanear_texto(texto, 10)
        if not texto.isdigit() or not (1 <= int(texto) <= 2_000_000_000):
            raise ErrorValidacion(f"{etiqueta} inválido", f"{etiqueta} inválido: ingrese un número entero positivo.")
        return int(texto)

    def _decimal(self, texto, etiqueta):
        texto = Validador.sanear_texto(texto, 15).replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            raise ErrorValidacion(f"{etiqueta} no numérico", f"{etiqueta} debe ser un número.") from None
    def cargar_datos_por_defecto(self):
        """Si no hay destinos ni paquetes, carga los 10 destinos y 10 paquetes por defecto.
        Si ya existen datos no hace nada (no duplica ni pisa lo que el administrador creó)."""
        if self.destinos.listar_destinos() or self.paquetes.listar_paquetes():
            return
        for nombre, pais, descripcion, precio in DESTINOS_POR_DEFECTO:
            self.destinos.registrar_destino(Destino(None, nombre, pais, descripcion, precio))
        por_nombre = {d.nombre: d for d in self.destinos.listar_destinos()}
        for nombre, desde, duracion, cupos, adicional, nombres in PAQUETES_POR_DEFECTO:
            inicio = date.today() + timedelta(days=desde)       # siempre en el futuro
            paquete = PaqueteTuristico(None, nombre, inicio, inicio + timedelta(days=duracion), cupos, adicional)
            for n in nombres:
                paquete.agregar_destino(por_nombre[n])
            self.paquetes.crear_paquete(paquete)
            
    # ---------------- configuración inicial y registro ----------------
    def configuracion_inicial(self):
        self.salida("\nNo hay usuarios registrados. Cree la cuenta del administrador inicial.")
        while True:
            def crear():
                admin = Administrador(None, self.entrada("Nombre: "), self.entrada("Correo: "), None, "Administrador general")
                clave = self.secreta("Contraseña (mín. 8, mayúscula, minúscula y número): ")
                if clave != self.secreta("Repita la contraseña: "):
                    raise ErrorViajes("confirmación distinta", "Las contraseñas no coinciden.")
                return self.auth.crear_administrador_inicial(admin, clave)
            if self._seguro(crear):
                self.salida("  ✓ Administrador creado.")
                return

    def registrarse(self):
        cliente = Cliente(None, self.entrada("Nombre: "), self.entrada("Correo: "), None,
                          self.entrada("Teléfono: "), self.entrada("Documento (RUT/pasaporte): "))
        clave = self.secreta("Contraseña (mín. 8, mayúscula, minúscula y número): ")
        if clave != self.secreta("Repita la contraseña: "):
            raise ErrorViajes("confirmación distinta", "Las contraseñas no coinciden.")
        self.auth.registrar_usuario(cliente, clave)
        self.salida("  ✓ Registro exitoso. Ya puede iniciar sesión.")

    # ---------------- flujo principal ----------------
    def ejecutar(self):
        self.salida("=" * 40 + "\n VIAJES AVENTURA\n" + "=" * 40)
        self._seguro(self.db.crear_tablas)
        self._seguro(self.cargar_datos_por_defecto)
        if self._seguro(lambda: self.db.consultar("SELECT COUNT(*) FROM usuario")[0][0]) == 0:
            self.configuracion_inicial()
        while True:
            self.salida("\n1) Iniciar sesión\n2) Registrarse como cliente\n3) Salir")
            op = self._seguro(lambda: Validador.validar_opcion(self.entrada("Opción: "), {"1", "2", "3"}))
            if op == "3":
                self.salida("Hasta luego.")
                self.db.cerrar()
                return
            if op == "2":
                self._seguro(self.registrarse)
            elif op == "1":
                usuario = self._seguro(self.login)
                if usuario:
                    self.menu_usuario(usuario)

    def login(self):
        usuario = self.auth.iniciar_sesion(self.entrada("Correo: "), self.secreta("Contraseña: "))
        self.salida(f"\n  ✓ Bienvenido/a {usuario.nombre} ({usuario.TIPO})")
        return usuario

    def menu_usuario(self, usuario):
        es_admin = isinstance(usuario, Administrador)
        while True:
            if es_admin:
                opciones = {"1": ("Registrar destino", self.registrar_destino),
                            "2": ("Modificar destino", self.modificar_destino),
                            "3": ("Eliminar destino", self.eliminar_destino),
                            "4": ("Listar destinos", self.listar_destinos),
                            "5": ("Crear paquete turístico", self.crear_paquete),
                            "6": ("Listar todos los paquetes", self.listar_paquetes)}
            else:
                opciones = {"1": ("Ver paquetes disponibles", self.ver_disponibles),
                            "2": ("Reservar un paquete", self.reservar),
                            "3": ("Mi historial de reservas", self.ver_historial),
                            "4": ("Cancelar una reserva", self.cancelar_reserva)}
            opciones["8"] = ("Cambiar contraseña", self.cambiar_password)
            opciones["0"] = ("Cerrar sesión", None)
            self.salida(f"\n--- MENÚ {usuario.TIPO.upper()} ---")
            for k, (texto, _) in opciones.items():
                self.salida(f"{k}) {texto}")
            op = self._seguro(lambda: Validador.validar_opcion(self.entrada("Opción: "), set(opciones)))
            if op == "0":
                self.salida("Sesión cerrada.")
                return
            if op:
                self._seguro(lambda: opciones[op][1](usuario))

    # ---------------- administrador: destinos ----------------
    def registrar_destino(self, usuario):
        exigir_rol(usuario, Administrador)
        d = Destino(None, self.entrada("Nombre: "), self.entrada("País: "), self.entrada("Descripción: "),
                    self._decimal(self.entrada("Precio base: "), "El precio"))
        self.destinos.registrar_destino(d)
        self.salida(f"  ✓ Destino registrado con ID {d.id_destino}.")

    def modificar_destino(self, usuario):
        exigir_rol(usuario, Administrador)
        id_ = self._numero(self.entrada("ID del destino: "))
        actual = self.destinos.obtener_destino(id_)
        self.salida(f"  Actual: {actual}   (deje vacío lo que no quiera cambiar)")
        datos = {}
        for campo, etiqueta in (("nombre", "Nombre"), ("pais", "País"), ("descripcion", "Descripción"), ("precio_base", "Precio base")):
            texto = self.entrada(f"{etiqueta}: ").strip()
            if texto:
                datos[campo] = self._decimal(texto, "El precio") if campo == "precio_base" else texto
        if not datos:
            self.salida("  (sin cambios)")
            return
        self.destinos.modificar_destino(id_, datos)
        self.salida("  ✓ Destino modificado.")

    def eliminar_destino(self, usuario):
        exigir_rol(usuario, Administrador)
        id_ = self._numero(self.entrada("ID del destino a eliminar: "))
        if self.entrada(f"¿Eliminar el destino {id_}? (s/n): ").strip().lower() != "s":
            self.salida("  (cancelado)")
            return
        self.destinos.eliminar_destino(id_)
        self.salida("  ✓ Destino eliminado.")

    def listar_destinos(self, usuario):
        exigir_rol(usuario, Administrador)
        lista = self.destinos.listar_destinos()
        self.salida("\n--- DESTINOS ---")
        for d in lista:
            self.salida(f"  #{d.id_destino} {d} | {d.descripcion}")
        if not lista:
            self.salida("  (vacío)")

    # ---------------- administrador: paquetes ----------------
    def crear_paquete(self, usuario):
        exigir_rol(usuario, Administrador)
        p = PaqueteTuristico(None, self.entrada("Nombre del paquete: "), self.entrada("Fecha inicio (AAAA-MM-DD): "),
                             self.entrada("Fecha fin (AAAA-MM-DD): "),
                             self._numero(self.entrada("Cupos: "), "Cupos"),
                             self._decimal(self.entrada("Costo adicional: "), "El costo adicional"))
        ids = [self._numero(t, "ID de destino") for t in self.entrada("IDs de destinos separados por coma: ").split(",")]
        for id_ in ids:
            p.agregar_destino(self.destinos.obtener_destino(id_))
        self.paquetes.crear_paquete(p)
        self.salida(f"  ✓ Paquete creado con ID {p.id_paquete}. Costo total: ${p.calcular_costo():,.0f}")

    def _mostrar_paquetes(self, lista):
        if not lista:
            self.salida("  (sin paquetes)")
        for p in lista:
            self.salida(f"  #{p.id_paquete} {p}")
            self.salida("      Destinos: " + "; ".join(str(d) for d in p.destinos))

    def listar_paquetes(self, usuario):
        exigir_rol(usuario, Administrador)
        self.salida("\n--- TODOS LOS PAQUETES ---")
        self._mostrar_paquetes(self.paquetes.listar_paquetes())

    # ---------------- cliente ----------------
    def ver_disponibles(self, usuario):
        exigir_rol(usuario, Cliente)
        self.salida("\n--- PAQUETES DISPONIBLES ---")
        self._mostrar_paquetes(self.paquetes.buscar_disponibles())

    def reservar(self, usuario):
        exigir_rol(usuario, Cliente)
        self.ver_disponibles(usuario)
        paquete = self.paquetes.obtener_paquete(self._numero(self.entrada("ID del paquete a reservar: ")))
        if self.entrada(f"Total a pagar ${paquete.calcular_costo():,.0f}. ¿Confirmar? (s/n): ").strip().lower() != "s":
            self.salida("  (cancelado)")
            return
        r = self.reservas.crear_reserva(usuario, paquete)
        self.salida(f"  ✓ Reserva #{r.id_reserva} confirmada. Total: ${r.costo_total:,.0f}")

    def ver_historial(self, usuario):
        exigir_rol(usuario, Cliente)
        self.salida("\n--- MI HISTORIAL ---")
        historial = self.reservas.obtener_historial(usuario)
        for r in historial:
            self.salida(f"  {r} | paquete #{r.id_paquete}")
        if not historial:
            self.salida("  (sin reservas)")

    def cancelar_reserva(self, usuario):
        exigir_rol(usuario, Cliente)
        id_ = self._numero(self.entrada("ID de la reserva a cancelar: "))
        self.reservas.cancelar_reserva(id_, usuario)
        self.salida("  ✓ Reserva cancelada.")

    # ---------------- común ----------------
    def cambiar_password(self, usuario):
        actual = self.secreta("Contraseña actual: ")
        nueva = self.secreta("Nueva contraseña: ")
        if nueva != self.secreta("Repita la nueva contraseña: "):
            raise ErrorViajes("confirmación distinta", "Las contraseñas no coinciden.")
        if self.auth.cambiar_password(usuario, actual, nueva):
            self.salida("  ✓ Contraseña actualizada.")
        else:
            self.salida("  ✗ La contraseña actual no es correcta.")


def ejecutar():
    configurar_logging()
    try:
        Aplicacion().ejecutar()
    except (KeyboardInterrupt, EOFError):
        print("\nSistema cerrado por el usuario.")


if __name__ == "__main__":
    ejecutar()
