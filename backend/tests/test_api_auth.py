"""
Pruebas de registro, inicio de sesión y perfil.

Cubren la puerta de entrada de la aplicación: quién puede crear una cuenta,
quién consigue un token y qué pasa con las credenciales equivocadas.
"""

from app.core.rate_limit import limiter
from tests.conftest import CONTRASENA, cabeceras_de, crear_usuario

NUEVO = {
    "email": "nueva@ejemplo.com",
    "password": "clave-larga-1",
    "full_name": "Cuenta Nueva",
    "phone": "900111222",
}


async def test_una_cuenta_nueva_se_registra_como_cliente(cliente):
    respuesta = await cliente.post("/api/v1/auth/register", json=NUEVO)

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["email"] == NUEVO["email"]
    # Nadie se registra como administrador desde fuera.
    assert cuerpo["role"] == "CLIENTE"
    assert "hashed_password" not in cuerpo


async def test_no_se_puede_registrar_dos_veces_el_mismo_correo(cliente, sesion):
    await crear_usuario(sesion, email=NUEVO["email"])

    respuesta = await cliente.post("/api/v1/auth/register", json=NUEVO)

    assert respuesta.status_code == 409


async def test_el_login_correcto_devuelve_un_token(cliente, sesion):
    await crear_usuario(sesion, email="persona@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "persona@ejemplo.com", "password": CONTRASENA},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]


async def test_la_contrasena_equivocada_no_entra(cliente, sesion):
    await crear_usuario(sesion, email="persona@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "persona@ejemplo.com", "password": "otra-cosa"},
    )

    assert respuesta.status_code == 401


async def test_una_cuenta_desactivada_no_entra(cliente, sesion):
    usuario = await crear_usuario(sesion, email="baja@ejemplo.com")
    usuario.is_active = False
    await sesion.commit()

    respuesta = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "baja@ejemplo.com", "password": CONTRASENA},
    )

    assert respuesta.status_code == 403


async def test_el_perfil_exige_token(cliente):
    respuesta = await cliente.get("/api/v1/auth/me")

    assert respuesta.status_code in (401, 403)


async def test_el_perfil_devuelve_al_usuario_del_token(cliente, sesion):
    await crear_usuario(sesion, email="persona@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "persona@ejemplo.com")

    respuesta = await cliente.get("/api/v1/auth/me", headers=cabeceras)

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == "persona@ejemplo.com"


async def test_el_login_corta_los_intentos_repetidos(cliente, sesion):
    """
    El tope por IP es lo que impide probar contraseñas a ciegas. Se enciende
    solo aquí porque el resto de pruebas hace muchos logins seguidos.
    """
    await crear_usuario(sesion, email="persona@ejemplo.com")
    limiter.reset()
    limiter.enabled = True

    try:
        codigos = []
        for _ in range(12):
            respuesta = await cliente.post(
                "/api/v1/auth/login",
                json={"email": "persona@ejemplo.com", "password": "equivocada"},
            )
            codigos.append(respuesta.status_code)
    finally:
        limiter.enabled = False
        limiter.reset()

    assert 429 in codigos, f"nunca se cortó: {codigos}"


async def test_el_perfil_se_puede_actualizar(cliente, sesion):
    await crear_usuario(sesion, email="persona@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "persona@ejemplo.com")

    respuesta = await cliente.patch(
        "/api/v1/auth/me",
        json={"full_name": "Nombre Corregido", "phone": "944555666"},
        headers=cabeceras,
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["full_name"] == "Nombre Corregido"

    # Y el cambio queda guardado, no solo en la respuesta.
    de_nuevo = await cliente.get("/api/v1/auth/me", headers=cabeceras)
    assert de_nuevo.json()["phone"] == "944555666"


async def test_el_perfil_no_deja_cambiarse_el_rol(cliente, sesion):
    await crear_usuario(sesion, email="persona@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "persona@ejemplo.com")

    await cliente.patch(
        "/api/v1/auth/me",
        json={"full_name": "Persona", "role": "ADMIN"},
        headers=cabeceras,
    )

    respuesta = await cliente.get("/api/v1/auth/me", headers=cabeceras)
    assert respuesta.json()["role"] == "CLIENTE"
