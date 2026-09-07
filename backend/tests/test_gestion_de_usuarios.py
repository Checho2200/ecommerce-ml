"""
Pruebas de la gestión de cuentas desde el panel.

La parte que de verdad hay que sujetar no es crear usuarios: es que no se
pueda dejar la tienda sin nadie capaz de administrarla. Ese error no da un
mensaje al hacerlo —el clic funciona—; se descubre al día siguiente, cuando
nadie puede entrar al panel y hay que ir a la base de datos a mano.

Son dos situaciones distintas y por eso hay dos guardas: quitarse el rol uno
mismo, que es lo que pasa por descuido, y quitárselo al último administrador
que queda, que es lo que pasa cuando dos personas creen que la otra sigue
teniendo acceso.
"""

from app.models.user import UserRole
from tests.conftest import CONTRASENA, cabeceras_de, crear_usuario

CLAVE_NUEVA = "clave-larga-de-alta"


async def _admin(cliente, sesion, email="admin@ejemplo.com"):
    usuario = await crear_usuario(sesion, email=email, rol=UserRole.ADMIN)
    return usuario, await cabeceras_de(cliente, email)


# ── Alta de cuentas ──────────────────────────────────────────────────────────


async def test_un_administrador_puede_crear_otro_administrador(cliente, sesion):
    _, cabeceras = await _admin(cliente, sesion)

    respuesta = await cliente.post(
        "/api/v1/users",
        json={
            "email": "segundo.admin@ejemplo.com",
            "password": CLAVE_NUEVA,
            "full_name": "Segundo Administrador",
            "role": "ADMIN",
        },
        headers=cabeceras,
    )

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["role"] == "ADMIN"
    assert cuerpo["is_active"] is True
    assert "hashed_password" not in cuerpo

    # Y la cuenta nueva sirve para entrar de verdad, no solo para figurar.
    acceso = await cliente.post(
        "/api/v1/auth/login",
        json={"email": "segundo.admin@ejemplo.com", "password": CLAVE_NUEVA},
    )
    assert acceso.status_code == 200, acceso.text


async def test_no_se_puede_crear_una_cuenta_con_un_correo_ya_usado(cliente, sesion):
    _, cabeceras = await _admin(cliente, sesion)
    await crear_usuario(sesion, email="repetido@ejemplo.com")

    respuesta = await cliente.post(
        "/api/v1/users",
        json={
            "email": "repetido@ejemplo.com",
            "password": CLAVE_NUEVA,
            "full_name": "Otra Persona",
        },
        headers=cabeceras,
    )

    assert respuesta.status_code == 409


async def test_la_politica_de_contrasenas_rige_tambien_en_el_alta_del_panel(cliente, sesion):
    # Una cuenta creada a mano no merece una clave más floja que una registrada
    # por su dueño: al contrario, suele ser la de un administrador.
    _, cabeceras = await _admin(cliente, sesion)

    respuesta = await cliente.post(
        "/api/v1/users",
        json={
            "email": "floja@ejemplo.com",
            "password": "123",
            "full_name": "Clave Floja",
            "role": "ADMIN",
        },
        headers=cabeceras,
    )

    assert respuesta.status_code == 422


async def test_un_cliente_no_puede_listar_ni_crear_cuentas(cliente, sesion):
    await crear_usuario(sesion, email="cliente@ejemplo.com")
    cabeceras = await cabeceras_de(cliente, "cliente@ejemplo.com")

    assert (await cliente.get("/api/v1/users", headers=cabeceras)).status_code == 403
    creacion = await cliente.post(
        "/api/v1/users",
        json={
            "email": "intruso@ejemplo.com",
            "password": CLAVE_NUEVA,
            "full_name": "Intento De Escalada",
            "role": "ADMIN",
        },
        headers=cabeceras,
    )
    assert creacion.status_code == 403


# ── Las guardas ──────────────────────────────────────────────────────────────


async def test_un_administrador_no_puede_quitarse_el_rol_a_si_mismo(cliente, sesion):
    admin, cabeceras = await _admin(cliente, sesion)
    # Hay otro administrador, así que no es la guarda del último: es la de no
    # cerrarse la puerta desde dentro.
    await crear_usuario(sesion, email="otro.admin@ejemplo.com", rol=UserRole.ADMIN)

    respuesta = await cliente.patch(
        f"/api/v1/users/{admin.id}", json={"role": "CLIENTE"}, headers=cabeceras
    )

    assert respuesta.status_code == 400
    assert "ti mismo" in respuesta.json()["detail"]


async def test_un_administrador_no_puede_desactivarse_a_si_mismo(cliente, sesion):
    admin, cabeceras = await _admin(cliente, sesion)
    await crear_usuario(sesion, email="otro.admin@ejemplo.com", rol=UserRole.ADMIN)

    respuesta = await cliente.patch(
        f"/api/v1/users/{admin.id}", json={"is_active": False}, headers=cabeceras
    )

    assert respuesta.status_code == 400


async def test_no_se_deja_a_la_tienda_sin_ningun_administrador(cliente, sesion):
    _, cabeceras = await _admin(cliente, sesion)
    # El segundo administrador es el único al que el primero podría degradar.
    otro = await crear_usuario(sesion, email="otro.admin@ejemplo.com", rol=UserRole.ADMIN)

    # Se degrada al segundo: quedaría uno, así que se permite.
    primera = await cliente.patch(
        f"/api/v1/users/{otro.id}", json={"role": "CLIENTE"}, headers=cabeceras
    )
    assert primera.status_code == 200, primera.text

    # Y ahora el que queda intenta degradarse: lo para la guarda del último.
    yo = (await cliente.get("/api/v1/auth/me", headers=cabeceras)).json()
    segunda = await cliente.patch(
        f"/api/v1/users/{yo['id']}", json={"role": "CLIENTE"}, headers=cabeceras
    )
    assert segunda.status_code == 400


async def test_degradar_a_otro_administrador_si_queda_alguien_funciona(cliente, sesion):
    _, cabeceras = await _admin(cliente, sesion)
    otro = await crear_usuario(sesion, email="otro.admin@ejemplo.com", rol=UserRole.ADMIN)

    respuesta = await cliente.patch(
        f"/api/v1/users/{otro.id}", json={"role": "CLIENTE"}, headers=cabeceras
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["role"] == "CLIENTE"


async def test_una_cuenta_desactivada_ya_no_puede_entrar(cliente, sesion):
    _, cabeceras = await _admin(cliente, sesion)
    persona = await crear_usuario(sesion, email="baja@ejemplo.com")

    baja = await cliente.patch(
        f"/api/v1/users/{persona.id}", json={"is_active": False}, headers=cabeceras
    )
    assert baja.status_code == 200

    acceso = await cliente.post(
        "/api/v1/auth/login", json={"email": "baja@ejemplo.com", "password": CONTRASENA}
    )
    assert acceso.status_code in (401, 403), acceso.text


# ── El listado ───────────────────────────────────────────────────────────────


async def test_el_listado_busca_y_cuenta_los_administradores_activos(cliente, sesion):
    _, cabeceras = await _admin(cliente, sesion)
    await crear_usuario(sesion, email="ana.perez@ejemplo.com")
    await crear_usuario(sesion, email="otro.admin@ejemplo.com", rol=UserRole.ADMIN)

    todos = (await cliente.get("/api/v1/users", headers=cabeceras)).json()
    assert todos["total"] == 3
    # El panel lo usa para avisar antes de degradar al último que queda.
    assert todos["active_admins"] == 2
    # Los administradores salen primero: es lo que se viene a buscar.
    assert todos["items"][0]["role"] == "ADMIN"

    buscados = (
        await cliente.get("/api/v1/users?search=ana.perez", headers=cabeceras)
    ).json()
    assert buscados["total"] == 1
    assert buscados["items"][0]["email"] == "ana.perez@ejemplo.com"

    solo_admins = (
        await cliente.get("/api/v1/users?role=ADMIN", headers=cabeceras)
    ).json()
    assert solo_admins["total"] == 2
