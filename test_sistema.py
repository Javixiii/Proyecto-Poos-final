"""Pruebas de Viajes Aventura.  Ejecutar desde la raíz:  python -m unittest discover -s tests -t ."""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


from base_datos import BaseDatos
from administrador import Administrador
from cliente import Cliente
from destino import Destino
from paquete_turistico import PaqueteTuristico
from reserva import Reserva
from main import Aplicacion
import seguridad
from errores import *
from gestor_destinos import GestorDestinos
from gestor_paquetes import GestorPaquetes
from gestor_reservas import GestorReservas
from seguridad import HashContraseña
from servicio_autenticacion import ServicioAutenticacion
from validador import Validador

FUTURO = (date.today() + timedelta(days=30)).isoformat()
FUTURO2 = (date.today() + timedelta(days=40)).isoformat()


class Base(unittest.TestCase):
    def setUp(self):
        fd, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db = BaseDatos(self.ruta)
        self.db.crear_tablas()
        self.auth = ServicioAutenticacion(self.db)
        self.gd, self.gp = GestorDestinos(self.db), GestorPaquetes(self.db)
        self.gr = GestorReservas(self.db, self.gp)

    def tearDown(self):
        self.db.cerrar()
        os.unlink(self.ruta)

    def cliente(self, email="ana@correo.cl", clave="Clave1234"):
        c = Cliente(None, "Ana", email, None, "987654321", "12345678-5")
        self.auth.registrar_usuario(c, clave)
        return c

    def destino(self, nombre="Torres del Paine", precio=100000):
        d = Destino(None, nombre, "Chile", "Trekking", precio)
        self.gd.registrar_destino(d)
        return d

    def paquete(self, destinos=None, cupos=2, adicional=50000):
        p = PaqueteTuristico(None, "Patagonia", FUTURO, FUTURO2, cupos, adicional)
        for d in destinos or [self.destino()]:
            p.agregar_destino(d)
        self.gp.crear_paquete(p)
        return p


class TestSeguridadYUsuario(Base):
    def test_password_hash_es_objeto_y_no_str(self):
        c = self.cliente()
        self.assertIsInstance(c.password_hash, HashContraseña)
        self.assertNotIsInstance(c.password_hash, str)
        self.assertNotIn("Clave1234", repr(c.password_hash))
        self.assertTrue(c.verificar_password("Clave1234"))
        self.assertFalse(c.verificar_password("clave1234"))

    def test_hash_con_salt_distinto_y_constantes(self):
        a, b = HashContraseña.desde_password("Clave1234"), HashContraseña.desde_password("Clave1234")
        self.assertNotEqual(a, b)
        self.assertEqual(a.iteraciones, seguridad.ITERACIONES)
        self.assertTrue(a.valor.startswith(seguridad.PREFIJO + "$"))
        with self.assertRaises(AttributeError):
            a.valor = "x"

    def test_formato_anomalo_no_verifica(self):
        h = HashContraseña.desde_password("Clave1234").valor
        self.assertFalse(seguridad.verificar_password("Clave1234", "texto plano"))
        self.assertFalse(seguridad.verificar_password("Clave1234", h[:-3] + "AAA"))

    def test_password_no_queda_en_texto_plano_en_bd(self):
        self.cliente()
        with sqlite3.connect(self.ruta) as c:
            (guardado,) = c.execute("SELECT password_hash FROM usuario").fetchone()
        self.assertTrue(guardado.startswith("pbkdf2_sha256$"))
        self.assertNotIn("Clave1234", guardado)

    def test_email_exige_arroba(self):
        for malo in ("ana.correo.cl", "anacorreo", "", None, "a@b", "@x.cl"):
            with self.assertRaises(ErrorValidacion):
                Cliente(None, "Ana", malo, None, "987654321", "12345678-5")
        self.assertFalse(Validador.validar_email("sin-arroba.cl"))
        self.assertTrue(Validador.validar_email("ok@correo.cl"))
        c = self.cliente()
        with self.assertRaises(ErrorValidacion):
            c.email = "sin-arroba.cl"
        self.assertEqual(c.email, "ana@correo.cl")

    def test_login_ok_y_fallos(self):
        self.cliente()
        u = self.auth.iniciar_sesion("ANA@correo.cl", "Clave1234")
        self.assertIsInstance(u, Cliente)
        for email, clave in (("ana@correo.cl", "mala"), ("nadie@correo.cl", "Clave1234")):
            with self.assertRaises(ErrorAutenticacion) as ctx:
                self.auth.iniciar_sesion(email, clave)
            self.assertEqual(ctx.exception.mensaje_usuario, "Credenciales inválidas.")   # mismo mensaje

    def test_login_email_sin_arroba_rechazado(self):
        with self.assertRaises(ErrorValidacion):
            self.auth.iniciar_sesion("sinarroba", "Clave1234")

    def test_bloqueo_tras_3_intentos(self):
        self.cliente()
        t = [0]
        self.auth._reloj = lambda: t[0]
        for _ in range(3):
            with self.assertRaises(ErrorAutenticacion):
                self.auth.iniciar_sesion("ana@correo.cl", "mala")
        with self.assertRaises(ErrorBloqueo):
            self.auth.iniciar_sesion("ana@correo.cl", "Clave1234")
        t[0] = 1000
        self.assertIsNotNone(self.auth.iniciar_sesion("ana@correo.cl", "Clave1234"))

    def test_registro_password_debil_y_duplicado(self):
        c = Cliente(None, "Ana", "ana@correo.cl", None, "987654321", "12345678-5")
        with self.assertRaises(ErrorValidacion):
            self.auth.registrar_usuario(c, "corta")
        self.auth.registrar_usuario(c, "Clave1234")
        with self.assertRaises(ErrorValidacion):
            self.auth.registrar_usuario(Cliente(None, "Otra", "ANA@correo.cl", None, "987654321", "87654321-4"), "Clave1234")

    def test_cambiar_password(self):
        c = self.cliente()
        self.assertFalse(self.auth.cambiar_password(c, "incorrecta", "Nueva12345"))
        with self.assertRaises(ErrorValidacion):
            self.auth.cambiar_password(c, "Clave1234", "debil")
        self.assertTrue(self.auth.cambiar_password(c, "Clave1234", "Nueva12345"))
        self.assertIsNotNone(self.auth.iniciar_sesion("ana@correo.cl", "Nueva12345"))
        with self.assertRaises(ErrorAutenticacion):
            self.auth.iniciar_sesion("ana@correo.cl", "Clave1234")

    def test_admin_inicial_solo_una_vez(self):
        a = Administrador(None, "Root", "root@viajes.cl", None, "Administrador general")
        self.assertTrue(self.auth.crear_administrador_inicial(a, "Admin12345"))
        with self.assertRaises(ErrorPermiso):
            self.auth.crear_administrador_inicial(Administrador(None, "Otro", "otro@viajes.cl", None, "x"), "Admin12345")
        self.assertIsInstance(self.auth.iniciar_sesion("root@viajes.cl", "Admin12345"), Administrador)

    def test_inyeccion_sql_en_login(self):
        with self.assertRaises(ErrorValidacion):
            self.auth.iniciar_sesion("' OR 1=1 --@x.cl", "x")
        self.assertEqual(self.db.consultar("SELECT COUNT(*) FROM usuario")[0][0], 0)


class TestDominio(Base):
    def test_property_validan_y_protegen(self):
        d = Destino(None, "Cusco", "Perú", "", 80000)
        for campo, malo in (("nombre", ""), ("pais", "  "), ("precio_base", -1), ("precio_base", True), ("precio_base", float("nan"))):
            with self.assertRaises(ErrorValidacion):
                setattr(d, campo, malo)
        with self.assertRaises(AttributeError):                 # propiedad de solo lectura
            Reserva(1, None, "Pendiente", 1, 1, 1).fecha_reserva = date.today()

    def test_modificar_es_todo_o_nada(self):
        d = Destino(None, "Cusco", "Perú", "", 80000)
        with self.assertRaises(ErrorValidacion):
            d.modificar({"nombre": "Lima", "precio_base": -5})
        self.assertEqual(d.nombre, "Cusco")
        with self.assertRaises(ErrorValidacion):
            d.modificar({"id_destino": 9})
        d.modificar({"nombre": "Lima", "precio_base": 90000})
        self.assertEqual((d.nombre, d.precio_base), ("Lima", 90000))

    def test_paquete_costo_y_cupos(self):
        d1, d2 = self.destino("A", 100), self.destino("B", 200)
        p = PaqueteTuristico(None, "Mix", FUTURO, FUTURO2, 1, 50)
        p.agregar_destino(d1)
        p.agregar_destino(d2)
        self.assertEqual(p.calcular_costo(), 350)
        with self.assertRaises(ErrorNegocio):
            p.agregar_destino(d1)
        p.quitar_destino(d2)
        self.assertEqual(p.calcular_costo(), 150)
        p.reducir_cupo()
        self.assertFalse(p.consultar_disponibilidad())
        with self.assertRaises(ErrorNegocio):
            p.reducir_cupo()
        p.liberar_cupo()
        self.assertTrue(p.consultar_disponibilidad())

    def test_fechas_invalidas(self):
        with self.assertRaises(ErrorValidacion):
            PaqueteTuristico(None, "X", FUTURO2, FUTURO, 1, 0)
        with self.assertRaises(ErrorValidacion):
            PaqueteTuristico(None, "X", "2026-02-30", FUTURO, 1, 0)

    def test_reserva_estados(self):
        r = Reserva(None, None, "Pendiente", 10, 1, 1)
        r.confirmar()
        with self.assertRaises(ErrorNegocio):
            r.confirmar()
        r.cancelar()
        with self.assertRaises(ErrorNegocio):
            r.cancelar()


class TestPersistenciaCRUD(Base):
    def test_crud_destinos(self):
        d = self.destino()
        self.assertIsNotNone(d.id_destino)
        self.gd.modificar_destino(d.id_destino, {"precio_base": 123456, "descripcion": "Nuevo"})
        self.assertEqual(self.gd.obtener_destino(d.id_destino).precio_base, 123456)
        self.assertEqual(len(self.gd.listar_destinos()), 1)
        self.gd.eliminar_destino(d.id_destino)
        self.assertEqual(self.gd.listar_destinos(), [])
        with self.assertRaises(ErrorNoEncontrado):
            self.gd.eliminar_destino(d.id_destino)

    def test_destino_duplicado(self):
        self.destino()
        with self.assertRaises(ErrorValidacion):
            self.destino()

    def test_no_se_elimina_destino_en_uso(self):
        p = self.paquete()
        with self.assertRaises(ErrorNegocio):
            self.gd.eliminar_destino(p.destinos[0].id_destino)

    def test_paquete_se_guarda_con_destinos(self):
        d1, d2 = self.destino("A", 100000), self.destino("B", 200000)
        p = self.paquete([d1, d2], adicional=10000)
        leido = self.gp.obtener_paquete(p.id_paquete)
        self.assertEqual({d.nombre for d in leido.destinos}, {"A", "B"})
        self.assertEqual(leido.calcular_costo(), 310000)
        self.assertEqual(len(self.gp.buscar_disponibles()), 1)

    def test_paquete_sin_destinos_o_fecha_pasada(self):
        with self.assertRaises(ErrorNegocio):
            self.gp.crear_paquete(PaqueteTuristico(None, "Vacío", FUTURO, FUTURO2, 1, 0))
        p = PaqueteTuristico(None, "Viejo", "2020-01-01", "2020-01-10", 1, 0)
        p.agregar_destino(self.destino())
        with self.assertRaises(ErrorValidacion):
            self.gp.crear_paquete(p)

    def test_paquete_con_destino_inexistente_no_guarda_nada(self):
        p = PaqueteTuristico(None, "Fantasma", FUTURO, FUTURO2, 1, 0)
        p.agregar_destino(Destino(999, "Nada", "Chile", "", 10))
        with self.assertRaises(ErrorNoEncontrado):
            self.gp.crear_paquete(p)
        self.assertEqual(self.gp.listar_paquetes(), [])


class TestReservas(Base):
    def test_reservar_descuenta_cupo_y_guarda_historial(self):
        c, p = self.cliente(), self.paquete(cupos=2, adicional=50000)
        r = self.gr.crear_reserva(c, p)
        self.assertEqual((r.estado, r.costo_total), ("Confirmada", 150000))
        self.assertEqual(self.gp.obtener_paquete(p.id_paquete).cupos_disponibles, 1)
        self.assertEqual([x.id_reserva for x in self.gr.obtener_historial(c)], [r.id_reserva])
        self.assertEqual(len(c.consultar_historial()), 1)

    def test_sin_cupos(self):
        c, p = self.cliente(), self.paquete(cupos=1)
        self.gr.crear_reserva(c, p)
        with self.assertRaises(ErrorNegocio):
            self.gr.crear_reserva(c, p)
        self.assertEqual(len(self.gr.obtener_historial(c)), 1)

    def test_cancelar_libera_cupo_una_sola_vez(self):
        c, p = self.cliente(), self.paquete(cupos=1)
        r = self.gr.crear_reserva(c, p)
        self.assertTrue(self.gr.cancelar_reserva(r.id_reserva, c))
        self.assertEqual(self.gp.obtener_paquete(p.id_paquete).cupos_disponibles, 1)
        with self.assertRaises(ErrorNegocio):
            self.gr.cancelar_reserva(r.id_reserva, c)
        self.assertEqual(self.gp.obtener_paquete(p.id_paquete).cupos_disponibles, 1)

    def test_cliente_no_cancela_reserva_ajena(self):
        a, b, p = self.cliente(), self.cliente("beto@correo.cl"), self.paquete(cupos=2)
        r = self.gr.crear_reserva(a, p)
        with self.assertRaises(ErrorPermiso):
            self.gr.cancelar_reserva(r.id_reserva, b)
        self.assertEqual(self.gr.obtener_historial(a)[0].estado, "Confirmada")
        self.assertEqual(self.gr.obtener_historial(b), [])

    def test_admin_no_reserva(self):
        a = Administrador(None, "Root", "root@viajes.cl", None, "Administrador general")
        with self.assertRaises(ErrorPermiso):
            self.gr.crear_reserva(a, self.paquete())

    def test_reserva_inexistente(self):
        with self.assertRaises(ErrorNoEncontrado):
            self.gr.cancelar_reserva(999)


class TestConsola(Base):
    """Flujo completo por consola con entradas simuladas (sin tocar el teclado)."""

    def ejecutar(self, entradas, claves):
        salida, ent, cla = [], iter(entradas), iter(claves)
        app = Aplicacion(entrada=lambda _="": next(ent), secreta=lambda _="": next(cla), salida=salida.append, db=self.db)
        app.ejecutar()
        return "\n".join(salida)

    def test_flujo_admin_y_cliente(self):
        entradas = [
            "Root", "root@viajes.cl",                                   # admin inicial
            "1", "root@viajes.cl",                                      # login admin
            "1", "Torres del Paine", "Chile", "Trekking", "100000",     # registrar destino
            "5", "Patagonia", FUTURO, FUTURO2, "5", "50000", "1",       # crear paquete
            "0", "2", "Ana", "ana@correo.cl", "987654321", "12345678-5",  # registrarse
            "1", "ana@correo.cl",                                       # login cliente
            "2", "1", "s",                                              # reservar
            "3", "0", "3"]                                              # historial, salir
        claves = ["Admin12345", "Admin12345", "Admin12345", "Clave1234", "Clave1234", "Clave1234"]
        out = self.ejecutar(entradas, claves)
        for esperado in ("Administrador creado", "Destino registrado con ID 1", "Paquete creado con ID 1",
                         "Registro exitoso", "Reserva #1 confirmada", "Total: $150,000", "Hasta luego"):
            self.assertIn(esperado, out)
        self.assertEqual(self.gp.obtener_paquete(1).cupos_disponibles, 4)

    def test_cliente_no_ve_menu_admin(self):
        from main import exigir_rol
        c = self.cliente()
        with self.assertRaises(ErrorPermiso):
            exigir_rol(c, Administrador)


if __name__ == "__main__":
    unittest.main()
