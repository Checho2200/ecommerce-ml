"""
Etiqueta pedidos ya evaluados para poder demostrar el ciclo de reentrenamiento.

    python -m app.scripts.simular_revisiones            # sobre la base local
    python -m app.scripts.simular_revisiones --deshacer # quita lo simulado

PARA QUÉ SIRVE. El modelo aprende de los pedidos que un administrador revisa y
etiqueta. Mientras la tienda no tenga clientes de verdad no hay ninguno, así
que la rama de "entrenar con datos reales" no se puede mostrar funcionando.
Este script rellena ese hueco: recorre las evaluaciones sin revisar y les pone
una etiqueta plausible, como si alguien las hubiera revisado.

PARA QUÉ NO SIRVE. Las etiquetas son inventadas. Cualquier métrica calculada
sobre ellas mide el simulador, no la tienda, y presentarla como resultado real
sería falsear la tesis. Por eso:

- solo corre contra una base SQLite (la de desarrollo), salvo que se pida lo
  contrario a mano y por escrito;
- cada registro que toca queda marcado en `admin_notes` con MARCA, así que se
  distingue siempre de una revisión de verdad y se puede deshacer;
- las etiquetas llevan ruido a propósito: si fueran una función exacta de las
  variables, el modelo alcanzaría un acierto perfecto y eso —además de falso—
  el propio entrenamiento lo rechaza por sospechoso.
"""

import argparse
import asyncio
import random
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.models.fraud_log import FraudLog

MARCA = "[REVISIÓN SIMULADA — dato de demostración, no es una revisión real]"

# Probabilidad de que el simulador se equivoque a propósito. Sin este ruido las
# etiquetas serían una regla determinista sobre las mismas variables que ve el
# modelo, y entrenar con ellas daría un 100 % de acierto que no significa nada.
RUIDO = 0.12

settings = get_settings()


def _etiqueta_plausible(vector: dict, rng: random.Random) -> bool:
    """
    Decide si ese pedido "resultó" fraudulento.

    La regla imita el perfil que describe el dominio —pedido caro, concentrado
    en componentes de reventa fácil, checkout resuelto en segundos y dirección
    estrenada— y luego voltea la respuesta de vez en cuando.
    """
    monto = float(vector.get("total_amount", 0) or 0)
    riesgo = int(vector.get("high_risk_items_count", 0) or 0)
    duracion = float(vector.get("checkout_duration_seconds", 999) or 999)
    direccion_nueva = int(vector.get("is_new_shipping_address", 0) or 0)

    señales = (
        (monto > 1500)
        + (riesgo >= 2)
        + (duracion < 60)
        + (direccion_nueva == 1)
    )
    es_fraude = señales >= 3

    if rng.random() < RUIDO:
        es_fraude = not es_fraude

    return es_fraude


async def simular(semilla: int = 42) -> int:
    rng = random.Random(semilla)
    ahora = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as sesion:
        resultado = await sesion.execute(
            select(FraudLog).where(FraudLog.reviewed_at.is_(None))
        )
        pendientes = resultado.scalars().all()

        if not pendientes:
            print("No hay evaluaciones sin revisar; no hay nada que simular.")
            return 0

        fraudes = 0
        for log in pendientes:
            es_fraude = _etiqueta_plausible(log.feature_vector or {}, rng)
            log.is_actual_fraud = es_fraude
            log.reviewed_at = ahora
            log.admin_notes = MARCA
            fraudes += int(es_fraude)

        await sesion.commit()

    print(
        f"Etiquetados {len(pendientes)} pedidos: {fraudes} como fraude y "
        f"{len(pendientes) - fraudes} como legítimos."
    )
    print(f"Todos quedaron marcados en admin_notes con: {MARCA}")
    return len(pendientes)


async def deshacer() -> int:
    """Devuelve a "sin revisar" todo lo que este script haya tocado."""
    async with AsyncSessionLocal() as sesion:
        resultado = await sesion.execute(
            select(FraudLog).where(FraudLog.admin_notes == MARCA)
        )
        simulados = resultado.scalars().all()

        for log in simulados:
            log.is_actual_fraud = False
            log.reviewed_at = None
            log.admin_notes = None

        await sesion.commit()

    print(f"Se deshicieron {len(simulados)} revisiones simuladas.")
    return len(simulados)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simula revisiones para demostrar el reentrenamiento."
    )
    parser.add_argument(
        "--deshacer",
        action="store_true",
        help="Quita las etiquetas que puso este script.",
    )
    parser.add_argument(
        "--acepto-datos-simulados-en-esta-base",
        action="store_true",
        help=(
            "Necesario para correr contra una base que no sea SQLite. "
            "Solo tiene sentido en una base de pruebas."
        ),
    )
    parser.add_argument("--semilla", type=int, default=42)
    argumentos = parser.parse_args()

    es_local = settings.DATABASE_URL.startswith("sqlite")
    if not es_local and not argumentos.acepto_datos_simulados_en_esta_base:
        print(
            "ABORTADO: la base configurada no es SQLite.\n\n"
            "Este script inventa etiquetas, y meterlas en la base de producción\n"
            "contaminaría los datos con los que se mide y se reentrena el\n"
            "modelo. Si de verdad es una base de pruebas, vuelve a ejecutarlo\n"
            "con --acepto-datos-simulados-en-esta-base."
        )
        return 1

    print(f"⚠️  {MARCA}")
    if argumentos.deshacer:
        asyncio.run(deshacer())
    else:
        asyncio.run(simular(argumentos.semilla))

    asyncio.run(engine.dispose())
    return 0


if __name__ == "__main__":
    sys.exit(main())
