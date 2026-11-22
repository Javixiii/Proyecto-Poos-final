from reserva import Reserva
from usuario import Usuario
from errores import ErrorNegocio, ErrorValidacion
from validador import Validador


class Cliente(Usuario):

    TIPO = "Cliente"

    def __init__(self, id_usuario, nombre, email, password_hash, telefono, documento):
        super().__init__(id_usuario, nombre, email, password_hash)
        self._telefono = None
        self._documento = None
        self._reservas = []          # asociación 1 — 0..* con Reserva
        self.telefono = telefono
        self.documento = documento

    @property
    def telefono(self):
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        if not Validador.validar_telefono(valor):
            raise ErrorValidacion("teléfono inválido", "Teléfono inválido (8 a 12 dígitos, opcional +).")
        self._telefono = Validador.sanear_texto(valor, 15).replace(" ", "")

    @property
    def documento(self):
        return self._documento

    @documento.setter
    def documento(self, valor):
        if not Validador.validar_documento(valor):
            raise ErrorValidacion("documento inválido", "Documento inválido (5 a 20 letras, números, punto o guion).")
        self._documento = Validador.sanear_texto(valor, 20)

    def _validar_datos_propios(self) -> bool:
        return Validador.validar_telefono(self._telefono) and Validador.validar_documento(self._documento)

    # ---------------- comportamiento (UML) ----------------
    def registrar(self) -> bool:
        """True si todos los datos del cliente son válidos para registrarlo."""
        return self.validar_datos()

    def realizar_reserva(self, paquete) -> Reserva:
        """Crea (sin persistir) la reserva del cliente para el paquete."""
        if self.id_usuario is None:
            raise ErrorNegocio("cliente sin registrar", "Debe estar registrado para reservar.")
        if not paquete.consultar_disponibilidad():
            raise ErrorNegocio("paquete sin cupos", "El paquete no tiene cupos disponibles.")
        reserva = Reserva(None, None, "Pendiente", paquete.calcular_costo(), self.id_usuario,
                          paquete.id_paquete, paquete)
        return reserva                # GestorReservas la persiste y la agrega al historial

    def consultar_historial(self):
        return list(self._reservas)

    def _reemplazar_historial(self, reservas):
        """Uso interno de GestorReservas: sincroniza el historial con lo guardado en la BD."""
        self._reservas = list(reservas)
