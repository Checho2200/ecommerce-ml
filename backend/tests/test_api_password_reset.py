"""
Pruebas de la recuperación de contraseña.

El enlace que se envía por correo es, mientras vive, tan bueno como la
contraseña: por eso se comprueba que caduque su uso, que no sirva dos veces y
que un token de sesión normal no valga para cambiarla.
"""

from app.core.security import (
    create_access_token,
    create_password_reset_token,
    verify_password,
)
from app.services import email_service
from tests.conftest import CONTRASENA, crear_usuario

NUEVA = "otra-clave-distinta"


async def test_pedir_el_enlace_responde_igual_exista_o_no_la_cuenta(cliente, sesion):
    """
    Contestar "ese correo no existe" convertiría el endpoint en un buscador de
    clientes registrados, así que la respuesta es siempre la misma.
    """
    await crear_usuario(sesion, email="existe@ejemplo.com")

    con_cuenta = await cliente.post(
        "/api/v1/auth/forgot-password", json={"email": "existe@ejemplo.com"}
    )
    sin_cuenta = await cliente.post(
        "/api/v1/auth/forgot-password", json={"email": "nadie@ejemplo.com"}
    )

    assert con_cuenta.status_code == sin_cuenta.status_code == 202
    assert con_cuenta.json() == sin_cuenta.json()


async def test_el_correo_lleva_un_enlace_al_frontend(cliente, sesion, monkeypatch):
    await crear_usuario(sesion, email="existe@ejemplo.com")

    enviados = []
    monkeypatch.setattr(
        email_service,
        "enviar_enlace_de_recuperacion",
        lambda destinatario, nombre, enlace: enviados.append(enlace),
    )

    await cliente.post(
        "/api/v1/auth/forgot-password", json={"email": "existe@ejemplo.com"}
    )

    assert len(enviados) == 1
    assert "/reset-password?token=" in enviados[0]


async def test_a_una_cuenta_inexistente_no_se_le_manda_nada(cliente, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        email_service,
        "enviar_enlace_de_recuperacion",
        lambda *args: enviados.append(args),
    )

    await cliente.post(
        "/api/v1/auth/forgot-password", json={"email": "nadie@ejemplo.com"}
    )

    assert enviados == []


async def test_el_token_valido_cambia_la_contrasena(cliente, sesion):
    usuario = await crear_usuario(sesion, email="persona@ejemplo.com")
    token = create_password_reset_token(usuario.id, usuario.hashed_password)

    respuesta = await cliente.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NUEVA}
    )

    assert respuesta.status_code == 200, respuesta.text

    await sesion.refresh(usuario)
    assert verify_password(NUEVA, usuario.hashed_password)
    assert not verify_password(CONTRASENA, usuario.hashed_password)


async def test_con_la_contrasena_nueva_se_entra_y_con_la_vieja_no(cliente, sesion):
    usuario = await crear_usuario(sesion, email="persona@ejemplo.com")
    token = create_password_reset_token(usuario.id, usuario.hashed_password)

    await cliente.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NUEVA}
    )

    con_la_nueva = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "persona@ejemplo.com", "password": NUEVA},
    )
    con_la_vieja = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "persona@ejemplo.com", "password": CONTRASENA},
    )

    assert con_la_nueva.status_code == 200
    assert con_la_vieja.status_code == 401


async def test_el_enlace_no_sirve_dos_veces(cliente, sesion):
    """
    El token lleva la huella de la contraseña vigente cuando se pidió; al
    cambiarla, esa huella deja de cuadrar y el enlace queda gastado.
    """
    usuario = await crear_usuario(sesion, email="persona@ejemplo.com")
    token = create_password_reset_token(usuario.id, usuario.hashed_password)

    primero = await cliente.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NUEVA}
    )
    segundo = await cliente.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "tercera-clave"},
    )

    assert primero.status_code == 200
    assert segundo.status_code == 400

    await sesion.refresh(usuario)
    assert verify_password(NUEVA, usuario.hashed_password)


async def test_un_token_inventado_no_cambia_nada(cliente, sesion):
    usuario = await crear_usuario(sesion, email="persona@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/auth/reset-password",
        json={"token": "esto-no-es-un-jwt", "new_password": NUEVA},
    )

    assert respuesta.status_code == 400
    await sesion.refresh(usuario)
    assert verify_password(CONTRASENA, usuario.hashed_password)


async def test_un_token_de_sesion_no_vale_para_cambiar_la_contrasena(cliente, sesion):
    """
    Un JWT de sesión está firmado con la misma clave, así que sin comprobar el
    propósito serviría para reescribir la contraseña de su propio dueño —y
    cualquier token robado dejaría de ser temporal para volverse permanente.
    """
    usuario = await crear_usuario(sesion, email="persona@ejemplo.com")
    token_de_sesion = create_access_token({"sub": usuario.id, "role": usuario.role})

    respuesta = await cliente.post(
        "/api/v1/auth/reset-password",
        json={"token": token_de_sesion, "new_password": NUEVA},
    )

    assert respuesta.status_code == 400
    await sesion.refresh(usuario)
    assert verify_password(CONTRASENA, usuario.hashed_password)


async def test_una_cuenta_desactivada_no_puede_recuperar(cliente, sesion):
    usuario = await crear_usuario(sesion, email="baja@ejemplo.com")
    token = create_password_reset_token(usuario.id, usuario.hashed_password)
    usuario.is_active = False
    await sesion.commit()

    respuesta = await cliente.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NUEVA}
    )

    assert respuesta.status_code == 400


async def test_la_contrasena_nueva_tiene_un_minimo(cliente, sesion):
    usuario = await crear_usuario(sesion, email="persona@ejemplo.com")
    token = create_password_reset_token(usuario.id, usuario.hashed_password)

    respuesta = await cliente.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "123"}
    )

    assert respuesta.status_code == 422
