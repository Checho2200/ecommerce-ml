"""
Pruebas del modo ensayo del generador de historial.

Existe porque probar una configuración costaba trece minutos: había que crear
miles de cuentas con hasheo real y escribir otros tantos pedidos para descubrir,
al final, que los umbrales daban un número que no servía. El ensayo genera y
mide exactamente igual pero sin escribir, así que la pregunta «¿qué va a
producir esto?» se responde en segundos.

Lo que se comprueba aquí es lo único que puede invalidarlo: que de verdad no
escriba, y que el código que genera sea el mismo en los dos modos —si el ensayo
midiera algo distinto de lo que luego se guarda, sería peor que no tenerlo.
"""

import numpy as np
import pytest

from app.models.user import UserRole
from app.scripts.simular_historial import SesionDeEnsayo, _crear_clientes


class _SesionFalsa:
    def __init__(self):
        self.agregados = []

    def add(self, fila):
        self.agregados.append(fila)

    async def flush(self):
        return None

    async def commit(self):
        return None

    def dime_algo(self):
        """Una lectura cualquiera, para comprobar que la envoltura la deja pasar."""
        return "leído"


def test_la_sesion_de_ensayo_no_deja_pasar_las_escrituras():
    sesion = _SesionFalsa()
    envuelta = SesionDeEnsayo(sesion)

    envuelta.add("un pedido")
    envuelta.add("otro pedido")

    assert sesion.agregados == []
    assert envuelta.escrituras == 2


@pytest.mark.asyncio
async def test_la_sesion_de_ensayo_no_confirma():
    sesion = _SesionFalsa()
    envuelta = SesionDeEnsayo(sesion)

    await envuelta.flush()
    await envuelta.commit()

    assert sesion.agregados == []


def test_la_sesion_de_ensayo_sí_deja_pasar_las_lecturas():
    """
    La generación necesita leer el catálogo de la base. Si la envoltura cortara
    también las lecturas, el ensayo no podría armar un solo carrito.
    """
    envuelta = SesionDeEnsayo(_SesionFalsa())

    assert envuelta.dime_algo() == "leído"


@pytest.mark.asyncio
async def test_el_ensayo_reparte_las_compras_igual_que_la_corrida_real():
    """
    Mismo reparto con la misma semilla, ensayo o no. Es lo que hace que el
    ensayo sirva para predecir: si el tráfico no fuera el mismo, sus números no
    dirían nada de la corrida que viene después.
    """
    def cuentas(ensayo: bool):
        sesion = _SesionFalsa()
        return sesion, _crear_clientes(
            sesion, 300, np.random.default_rng(2026), 150, 5, ensayo
        )

    sesion_ensayo, corutina_ensayo = cuentas(True)
    reparto_ensayo, admins_ensayo = await corutina_ensayo
    sesion_real, corutina_real = cuentas(False)
    reparto_real, admins_real = await corutina_real

    assert [c.email for c in reparto_ensayo] == [c.email for c in reparto_real]
    assert [a.email for a in admins_ensayo] == [a.email for a in admins_real]


@pytest.mark.asyncio
async def test_el_ensayo_no_gasta_tiempo_en_hashear():
    """
    Es de donde sale casi toda la diferencia de tiempo: bcrypt tarda a
    propósito, y en un ensayo esas contraseñas se tiran sin usarse.
    """
    sesion = _SesionFalsa()
    reparto, _ = await _crear_clientes(
        sesion, 60, np.random.default_rng(1), 30, 2, True
    )

    assert all(c.hashed_password == "(ensayo)" for c in sesion.agregados)
    assert reparto


@pytest.mark.asyncio
async def test_las_cuentas_tienen_identificador_antes_de_guardarse():
    """
    Sin esto, `usuario.id` es None hasta el `flush()` y el conjunto que evita
    refechar una cuenta ya fechada se llena de `None`: la primera compra entra
    y todas las demás creen que su cliente ya tiene fecha de alta. En la corrida
    real no se veía porque el `flush()` ocurre antes del bucle; el ensayo, que
    no lo hace, lo dejó a la vista.
    """
    sesion = _SesionFalsa()
    await _crear_clientes(sesion, 60, np.random.default_rng(1), 30, 2, True)

    identificadores = [c.id for c in sesion.agregados]
    assert all(identificadores)
    assert len(set(identificadores)) == len(identificadores)


@pytest.mark.asyncio
async def test_los_administradores_siguen_sin_comprar_en_el_ensayo():
    sesion = _SesionFalsa()
    reparto, admins = await _crear_clientes(
        sesion, 200, np.random.default_rng(7), 100, 5, True
    )

    assert len(admins) == 5
    assert not {a.email for a in admins} & {c.email for c in reparto}
    assert all(c.role == UserRole.CLIENTE for c in reparto)
