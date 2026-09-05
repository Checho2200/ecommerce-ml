"""
Pruebas de la política de contraseñas.

Además de lo que se rechaza, aquí se fija por escrito lo que NO se hace: no se
exige mezclar símbolos y no se le pide nada al login. Esa segunda parte importa
tanto como la primera —endurecer el login dejaría fuera a quien ya tiene una
contraseña anterior, sin darle forma de cambiarla— y es fácil de romper sin
darse cuenta al tocar los schemas.
"""

import pytest

from app.core import passwords
from app.core.passwords import ContrasenaDebil
from app.models.user import UserRole

from tests.conftest import crear_usuario


BUENA = "peregrino-tostado-49"


@pytest.mark.parametrize(
    "clave, motivo",
    [
        ("corta12", "menos de ocho caracteres"),
        ("admin123", "está en cualquier diccionario de ataque"),
        ("aaaaaaaaaa", "un solo carácter repetido"),
        ("  espacios  ", "empieza y termina con espacio"),
    ],
)
def test_se_rechaza_lo_que_un_atacante_prueba_primero(clave, motivo):
    with pytest.raises(ContrasenaDebil):
        passwords.validar(clave), motivo


def test_la_contrasena_no_puede_ser_el_propio_correo():
    with pytest.raises(ContrasenaDebil):
        passwords.validar("jefferson2026", "jefferson@gruposts.com.pe")


def test_una_frase_larga_se_acepta_aunque_no_tenga_simbolos():
    """
    Una contraseña larga y en minúsculas es más fuerte que "Passw0rd!", y la
    política tiene que reflejarlo: exigir símbolos produce claves peores.
    """
    assert passwords.validar("caballo correcto grapa") == "caballo correcto grapa"
    assert passwords.fuerza("caballo correcto grapa") >= 3
    assert passwords.fuerza("admin123") == 0


@pytest.mark.asyncio
async def test_el_registro_explica_que_le_falta_a_la_contrasena(cliente):
    respuesta = await cliente.post(
        "/api/v1/auth/register",
        json={
            "email": "nuevo@ejemplo.com",
            "password": "admin123",
            "full_name": "Persona Nueva",
        },
    )

    assert respuesta.status_code == 422
    detalle = str(respuesta.json()["detail"])
    assert "atacante" in detalle, "el mensaje debe decir qué corregir, no solo 'inválida'"


@pytest.mark.asyncio
async def test_el_registro_acepta_una_contrasena_que_cumple(cliente):
    respuesta = await cliente.post(
        "/api/v1/auth/register",
        json={"email": "nuevo@ejemplo.com", "password": BUENA, "full_name": "Persona Nueva"},
    )
    assert respuesta.status_code == 201


@pytest.mark.asyncio
async def test_el_login_no_aplica_la_politica_nueva(cliente, sesion):
    """
    Una cuenta creada antes de la política tiene una contraseña de seis
    caracteres. Si el login la validara, esa persona no podría entrar —ni
    siquiera para cambiarla— y quedaría encerrada fuera de su propia cuenta.
    """
    await crear_usuario(
        sesion, email="antiguo@ejemplo.com", rol=UserRole.CLIENTE, contrasena="viejo1"
    )

    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "antiguo@ejemplo.com", "password": "viejo1"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]
