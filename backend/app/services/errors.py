"""
Errores de negocio.

Los servicios no saben nada de HTTP: cuando una regla del negocio no se cumple
—no hay stock, la orden no existe, ya pasó el plazo de cancelación— lanzan uno
de estos errores, y es la capa de la API la que decide con qué código responder.

Sin esta separación, la lógica de negocio queda atada a FastAPI: no se puede
reutilizar desde un script, ni probar sin levantar la aplicación, ni mover a
otra interfaz (una cola de tareas, una CLI) sin arrastrar el framework web
detrás.

El mapeo a códigos HTTP está en un solo sitio, `app/main.py`, con un manejador
que traduce cualquier `ErrorDeNegocio` a su respuesta.
"""


class ErrorDeNegocio(Exception):
    """Una regla del negocio que no se cumplió. Traducible a una respuesta HTTP."""

    codigo_http = 400

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class RecursoNoEncontrado(ErrorDeNegocio):
    """Lo que se pidió no existe, o el usuario no debería saber que existe."""

    codigo_http = 404


class OperacionNoPermitida(ErrorDeNegocio):
    """La operación es válida en general, pero no en este estado o para este usuario."""

    codigo_http = 400


class AccesoDenegado(ErrorDeNegocio):
    """El usuario está identificado pero esto no le corresponde."""

    codigo_http = 403


class ServicioNoDisponible(ErrorDeNegocio):
    """Una dependencia externa no está configurada o no responde."""

    codigo_http = 503
