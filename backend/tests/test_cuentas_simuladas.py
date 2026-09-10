"""
Pruebas del reparto de cuentas del historial simulado.

El número de cuentas dejó de ser algo que emergía del reparto de compras y pasó
a elegirse: «¿cuántos clientes tiene la tienda?» se responde mejor con un número
que se decidió que con uno que salió. Lo que se comprueba aquí es que ese número
se cumpla exacto, que los administradores sean personal y no compradores, y que
ninguna cuenta quede sin un solo pedido —una cuenta sin pedidos no se distingue
de un registro abandonado y ensucia el listado del panel.
"""

import numpy as np
import pytest

from app.models.user import UserRole
from app.scripts.simular_historial import DOMINIO_SIMULADO, _crear_clientes


@pytest.fixture(autouse=True)
def _sin_bcrypt(monkeypatch):
    """
    Sustituye el hasheo de contraseñas mientras corren estas pruebas.

    bcrypt tarda a propósito —es su razón de ser— y aquí se crean quinientas
    cuentas por prueba: sin esto, este archivo solo tarda más de siete minutos.
    Lo que se comprueba es el reparto de cuentas y de compras, no el hash, así
    que sustituirlo no debilita nada. La política de contraseñas tiene sus
    propias pruebas en `test_politica_de_contrasenas.py`.
    """
    monkeypatch.setattr(
        "app.scripts.simular_historial.hash_password", lambda clave: f"hash:{clave}"
    )


class _SesionFalsa:
    """Recoge lo que el script añadiría a la base, sin tocar ninguna."""

    def __init__(self):
        self.agregados = []

    def add(self, fila):
        self.agregados.append(fila)

    async def flush(self):
        return None


async def _repartir(compras=1000, cuentas=500, administradores=5, semilla=2026):
    sesion = _SesionFalsa()
    reparto, admins = await _crear_clientes(
        sesion, compras, np.random.default_rng(semilla), cuentas, administradores
    )
    return sesion, reparto, admins


@pytest.mark.asyncio
async def test_crea_exactamente_las_cuentas_pedidas():
    sesion, _, admins = await _repartir()

    assert len(sesion.agregados) == 500
    assert len(admins) == 5


@pytest.mark.asyncio
async def test_cinco_son_administradores_y_el_resto_clientes():
    sesion, _, _ = await _repartir()

    roles = [c.role for c in sesion.agregados]
    assert roles.count(UserRole.ADMIN) == 5
    assert roles.count(UserRole.CLIENTE) == 495


@pytest.mark.asyncio
async def test_los_administradores_no_compran():
    """
    Son personal de la tienda. Un administrador con un pedido que acabó en
    contracargo es un artefacto raro de explicar y no aporta nada a lo que el
    historial viene a enseñar.
    """
    _, reparto, admins = await _repartir()

    correos_admin = {a.email for a in admins}
    assert not correos_admin & {c.email for c in reparto}
    assert all(c.role == UserRole.CLIENTE for c in reparto)


@pytest.mark.asyncio
async def test_el_reparto_cubre_todas_las_compras():
    _, reparto, _ = await _repartir(compras=1000)

    assert len(reparto) == 1000


@pytest.mark.asyncio
async def test_ningun_cliente_se_queda_sin_pedido():
    sesion, reparto, admins = await _repartir()

    compradores = {c.email for c in sesion.agregados if c.role == UserRole.CLIENTE}
    assert {c.email for c in reparto} == compradores


@pytest.mark.asyncio
async def test_las_compras_no_se_reparten_a_partes_iguales():
    """
    La mayoría compra una vez y unos pocos son habituales. Un reparto plano
    daría una tienda donde todo el mundo compra exactamente lo mismo, que no
    existe.
    """
    _, reparto, _ = await _repartir()

    from collections import Counter

    veces = Counter(c.email for c in reparto)
    assert min(veces.values()) == 1
    assert max(veces.values()) > 3


@pytest.mark.asyncio
async def test_todas_las_cuentas_llevan_el_dominio_reservado():
    """
    Es lo que permite a `--limpiar` retirarlas sin rozar una cuenta real, y lo
    que hace evidente en el panel que no son clientes de verdad.
    """
    sesion, _, _ = await _repartir()

    assert all(c.email.endswith(f"@{DOMINIO_SIMULADO}") for c in sesion.agregados)
    assert len({c.email for c in sesion.agregados}) == 500


@pytest.mark.asyncio
async def test_no_caben_mas_compradores_que_compras():
    """Cada comprador estrena con un pedido, así que el reparto tiene tope."""
    with pytest.raises(ValueError):
        await _repartir(compras=100, cuentas=500)


@pytest.mark.asyncio
async def test_no_pueden_ser_todos_administradores():
    with pytest.raises(ValueError):
        await _repartir(cuentas=5, administradores=5)
