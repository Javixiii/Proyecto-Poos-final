"""Jerarquía de excepciones. Cada una separa:
  - mensaje_usuario: texto seguro que sí se muestra en pantalla.
  - detalle técnico (str(e)): solo se escribe en el log, nunca en pantalla."""


class ErrorViajes(Exception):
    mensaje_usuario = "Ocurrió un error inesperado. La operación no se realizó."

    def __init__(self, detalle="", mensaje_usuario=None):
        super().__init__(detalle or self.mensaje_usuario)
        if mensaje_usuario:
            self.mensaje_usuario = mensaje_usuario


class ErrorValidacion(ErrorViajes):
    mensaje_usuario = "Dato inválido."


class ErrorAutenticacion(ErrorViajes):
    mensaje_usuario = "Credenciales inválidas."


class ErrorBloqueo(ErrorAutenticacion):
    mensaje_usuario = "Demasiados intentos fallidos. Intente nuevamente más tarde."


class ErrorPermiso(ErrorViajes):
    mensaje_usuario = "Su rol no tiene permiso para realizar esta acción."


class ErrorNoEncontrado(ErrorViajes):
    mensaje_usuario = "El registro solicitado no existe."


class ErrorNegocio(ErrorViajes):
    """Regla de negocio incumplida (sin cupos, destino en uso, reserva ya cancelada...)."""
    mensaje_usuario = "La operación no es posible en el estado actual."


class ErrorPersistencia(ErrorViajes):
    mensaje_usuario = "No fue posible acceder a la base de datos."
