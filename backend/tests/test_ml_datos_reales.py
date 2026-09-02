"""
Pruebas de la carga de datos reales para el entrenamiento.

Existen por un fallo concreto: la versión anterior leía las transacciones
abriendo `backend/sanchez_ecommerce.db` por ruta de archivo. En producción la
base es PostgreSQL en Neon, ese archivo no existe, y la función devolvía None
en silencio: el "aprendizaje con datos reales" nunca llegó a ocurrir en el
servidor y nada lo delataba. Estas pruebas fijan el comportamiento para que no
vuelva a pasar.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.security import hash_password
from app.models.fraud_log import FraudLog
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from ml import dataset


async def _sembrar(motor, fraudes: int, legitimos: int, sin_revisar: int = 0):
    """Deja en la base pedidos evaluados, etiquetados o no."""
    async with motor.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fabrica = async_sessionmaker(bind=motor, expire_on_commit=False)

    async with fabrica() as sesion:
        usuario = User(
            email="cliente@ejemplo.com",
            hashed_password=hash_password("clave-de-prueba"),
            full_name="Cliente de Prueba",
            role=UserRole.CLIENTE,
        )
        sesion.add(usuario)
        await sesion.flush()

        casos = (
            [(True, True)] * fraudes
            + [(False, True)] * legitimos
            + [(False, False)] * sin_revisar
        )

        for indice, (es_fraude, revisado) in enumerate(casos):
            monto = 3000.0 + indice if es_fraude else 200.0 + indice
            orden = Order(
                user_id=usuario.id,
                total_amount=monto,
                status=OrderStatus.COMPLETED,
                shipping_address="Av. España 1234",
                shipping_city="Trujillo",
            )
            sesion.add(orden)
            await sesion.flush()

            sesion.add(
                FraudLog(
                    order_id=orden.id,
                    fraud_score=0.9 if es_fraude else 0.1,
                    decision="BLOCKED" if es_fraude else "APPROVED",
                    risk_level="HIGH" if es_fraude else "LOW",
                    detection_time_ms=1.0,
                    feature_vector={
                        "total_amount": monto,
                        "high_risk_items_count": 3 if es_fraude else 0,
                        "checkout_duration_seconds": 15.0 if es_fraude else 240.0,
                        "is_new_shipping_address": 1 if es_fraude else 0,
                    },
                    is_actual_fraud=es_fraude,
                    reviewed_at=datetime.now(timezone.utc) if revisado else None,
                )
            )

        await sesion.commit()


@pytest.fixture
def base_con(monkeypatch, tmp_path):
    """
    Devuelve una función que siembra una base temporal y la deja como si fuera
    la de la aplicación, que es de donde `ml.dataset` lee.
    """

    def preparar(fraudes: int, legitimos: int, sin_revisar: int = 0):
        motor = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'datos.db'}")
        asyncio.run(_sembrar(motor, fraudes, legitimos, sin_revisar))

        # `ml.dataset` importa el motor y la fábrica de sesiones en el momento
        # de usarlos, así que sustituirlos en el módulo basta.
        monkeypatch.setattr("app.core.database.engine", motor)
        monkeypatch.setattr(
            "app.core.database.AsyncSessionLocal",
            async_sessionmaker(bind=motor, expire_on_commit=False),
        )

    return preparar


def test_lee_los_pedidos_etiquetados_de_la_base(base_con):
    """
    La prueba que faltaba: que el entrenamiento pueda de verdad leer lo que la
    tienda acumuló, contra la base que la aplicación usa —sea SQLite o
    PostgreSQL— y no contra un archivo con un nombre fijo.
    """
    base_con(fraudes=40, legitimos=180)

    df, motivo = dataset.cargar_datos_reales()

    assert df is not None, motivo
    assert len(df) == 220
    assert int(df[dataset.ETIQUETA].sum()) == 40
    assert set(dataset.FEATURES).issubset(df.columns)
    # Y los valores llegan enteros, no vacíos.
    assert df["checkout_duration_seconds"].gt(0).all()


def test_los_pedidos_sin_revisar_no_entran(base_con):
    """
    Un pedido que nadie miró no es un ejemplo de entrenamiento: no se sabe qué
    pasó con él. Antes entraban todos como si fueran legítimos.
    """
    base_con(fraudes=40, legitimos=180, sin_revisar=500)

    df, motivo = dataset.cargar_datos_reales()

    assert df is not None, motivo
    assert len(df) == 220


def test_con_pocos_pedidos_no_se_entrena_y_se_explica(base_con):
    base_con(fraudes=5, legitimos=20)

    df, motivo = dataset.cargar_datos_reales()

    assert df is None
    assert str(dataset.MINIMO_TOTAL) in motivo


def test_sin_casos_de_una_clase_no_se_entrena(base_con):
    """
    Doscientos pedidos legítimos y tres fraudes no enseñan a distinguir nada, y
    entrenar con ellos degradaría el modelo que ya está sirviendo.
    """
    base_con(fraudes=3, legitimos=250)

    df, motivo = dataset.cargar_datos_reales()

    assert df is None
    assert "clase" in motivo


def test_sin_nada_etiquetado_lo_dice_con_claridad(base_con):
    base_con(fraudes=0, legitimos=0, sin_revisar=10)

    df, motivo = dataset.cargar_datos_reales()

    assert df is None
    assert "etiquetado" in motivo


def test_cargar_datos_cae_en_los_sinteticos_y_lo_avisa(base_con, capsys):
    """
    Mientras la tienda no acumule historial, el entrenamiento sigue funcionando
    con el conjunto sintético —pero dejándolo dicho, que es lo que antes no
    ocurría.
    """
    base_con(fraudes=2, legitimos=5)

    datos = dataset.cargar_datos(preferir_reales=True)

    assert datos.origen == "sintetico"
    assert "sintético" in capsys.readouterr().out


def test_con_datos_suficientes_prefiere_los_de_la_tienda(base_con):
    base_con(fraudes=60, legitimos=200)

    datos = dataset.cargar_datos(preferir_reales=True)

    assert datos.origen == "tienda"
    assert len(datos.df) == 260
    assert "260" in datos.detalle
