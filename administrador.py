from usuario import Usuario
from errores import ErrorValidacion
from validador import Validador


class Administrador(Usuario):

    TIPO = "Administrador"

    def __init__(self, id_usuario, nombre, email, password_hash, rol):
        super().__init__(id_usuario, nombre, email, password_hash)
        self._rol = None
        self.rol = rol

    @property
    def rol(self):
        return self._rol

    @rol.setter
    def rol(self, valor):
        if not Validador.validar_texto(valor, 40):
            raise ErrorValidacion("rol vacío", "El rol no puede estar vacío.")
        self._rol = Validador.sanear_texto(valor, 40)

    def _validar_datos_propios(self) -> bool:
        return Validador.validar_texto(self._rol, 40)

    def gestionar_destinos(self):
        print("Gestionando destinos")

    def gestionar_paquetes(self):
        print("Gestionando paquetes")
