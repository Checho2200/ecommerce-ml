"""
Hace compras ficticias contra la tienda, para tener evidencia de que funciona.

    python -m app.scripts.simular_compras                # 30 compras
    python -m app.scripts.simular_compras --cuantas 60

Cada compra entra por el mismo endpoint que usaría un cliente real
(`POST /api/v1/orders`), así que recorre el camino completo: descuento de
stock, evaluación del modelo, decisión, registro con su explicación y aporte de
cada variable. Después quedan visibles en el panel de administración, que es lo
que sirve para capturar pantallas y demostrar el sistema.

No hace falta levantar el servidor: la aplicación se ejecuta en memoria.

Las compras son inventadas y el script solo corre contra SQLite —la base de
desarrollo— salvo que se autorice a mano. Una tienda con pedidos ficticios
mezclados con los de verdad no sirve ni para vender ni para medir.

Necesita `httpx`, que está en requirements-dev.txt.
"""

import argparse
import asyncio
import random
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.product import Product
from app.models.user import User, UserRole

CLAVE_DEL_CLIENTE = "compras-de-prueba-2026"
CORREO_DEL_CLIENTE = "cliente.simulado@ejemplo.com"

DIRECCIONES = [
    "Av. España 1234, Trujillo",
    "Jr. Pizarro 456, Trujillo",
    "Av. Larco 789, Víctor Larco",
    "Calle Los Robles 321, Trujillo",
    "Av. América Norte 1010, Trujillo",
]

settings = get_settings()


def _perfil_de_compra(rng: random.Random) -> dict:
    """
    Devuelve cómo se comporta esta compra.

    Se mezclan tres perfiles para que las decisiones del modelo salgan
    repartidas y el panel muestre los tres estados, no treinta aprobaciones
    seguidas.
    """
    sorteo = rng.random()

    if sorteo < 0.65:
        # Compra corriente: barata, sin prisa, a una dirección de siempre.
        return {
            "perfil": "corriente",
            "articulos": rng.randint(1, 2),
            "cantidad_maxima": 1,
            "caros": False,
            "segundos": rng.uniform(120, 600),
            "direccion": DIRECCIONES[0],
        }

    if sorteo < 0.85:
        # Compra grande pero normal: alguien armando su equipo, con calma.
        return {
            "perfil": "equipo completo",
            "articulos": rng.randint(2, 4),
            "cantidad_maxima": 2,
            "caros": True,
            "segundos": rng.uniform(180, 900),
            "direccion": rng.choice(DIRECCIONES[:2]),
        }

    # Perfil de riesgo: caro, concentrado en componentes de reventa fácil,
    # resuelto en segundos y a una dirección estrenada.
    return {
        "perfil": "sospechosa",
        "articulos": rng.randint(2, 3),
        "cantidad_maxima": 3,
        "caros": True,
        "segundos": rng.uniform(6, 45),
        "direccion": rng.choice(DIRECCIONES[2:]),
    }


async def _preparar_cliente() -> None:
    """Crea el cliente ficticio si no existe."""
    async with AsyncSessionLocal() as sesion:
        resultado = await sesion.execute(
            select(User).where(User.email == CORREO_DEL_CLIENTE)
        )
        if resultado.scalar_one_or_none():
            return

        sesion.add(
            User(
                email=CORREO_DEL_CLIENTE,
                hashed_password=hash_password(CLAVE_DEL_CLIENTE),
                full_name="Cliente Simulado (pruebas)",
                phone="900000000",
                role=UserRole.CLIENTE,
            )
        )
        await sesion.commit()
        print(f"Cliente ficticio creado: {CORREO_DEL_CLIENTE}")


async def _catalogo() -> tuple[list, list]:
    """Productos disponibles, separados entre caros y del montón."""
    async with AsyncSessionLocal() as sesion:
        resultado = await sesion.execute(
            select(Product).where(Product.is_active == True, Product.stock > 0)  # noqa: E712
        )
        productos = [
            {"id": p.id, "nombre": p.name, "precio": p.price, "stock": p.stock}
            for p in resultado.scalars().all()
        ]

    if not productos:
        raise RuntimeError(
            "No hay productos con stock. Ejecuta primero `python -m app.seed` "
            "para llenar el catálogo de desarrollo."
        )

    caros = [p for p in productos if p["precio"] >= 900] or productos
    baratos = [p for p in productos if p["precio"] < 900] or productos
    return caros, baratos


async def comprar(cuantas: int, semilla: int) -> list[dict]:
    from httpx import ASGITransport, AsyncClient

    from app.core.rate_limit import limiter
    from app.main import app

    await _preparar_cliente()
    caros, baratos = await _catalogo()

    rng = random.Random(semilla)
    compras = []

    # El tope de intentos por IP está pensado para personas, no para un script
    # que hace treinta compras seguidas desde la misma máquina.
    limiter.enabled = False
    try:
        transporte = ASGITransport(app=app)
        async with AsyncClient(transport=transporte, base_url="http://simulacion") as http:
            acceso = await http.post(
                "/api/v1/auth/login",
                json={"email": CORREO_DEL_CLIENTE, "password": CLAVE_DEL_CLIENTE},
            )
            acceso.raise_for_status()
            cabeceras = {"Authorization": f"Bearer {acceso.json()['access_token']}"}

            for numero in range(1, cuantas + 1):
                perfil = _perfil_de_compra(rng)
                fuente = caros if perfil["caros"] else baratos
                elegidos = rng.sample(fuente, min(perfil["articulos"], len(fuente)))

                items = [
                    {
                        "product_id": producto["id"],
                        "quantity": rng.randint(1, max(1, min(perfil["cantidad_maxima"], producto["stock"]))),
                    }
                    for producto in elegidos
                ]

                respuesta = await http.post(
                    "/api/v1/orders",
                    json={
                        "items": items,
                        "shipping_address": perfil["direccion"],
                        "shipping_city": "Trujillo",
                        "checkout_duration_seconds": round(perfil["segundos"], 1),
                    },
                    headers=cabeceras,
                )

                if respuesta.status_code != 201:
                    print(f"  Compra {numero}: rechazada por la API ({respuesta.status_code})")
                    continue

                orden = respuesta.json()
                compras.append(
                    {
                        "numero": numero,
                        "perfil": perfil["perfil"],
                        "monto": orden["total_amount"],
                        "segundos": round(perfil["segundos"], 1),
                        "direccion": perfil["direccion"],
                        "puntaje": orden["fraud_score"],
                        "decision": orden["fraud_decision"],
                        "estado": orden["status"],
                        "explicacion": orden["fraud_explanation"],
                    }
                )
    finally:
        limiter.enabled = True

    return compras


def _informe(compras: list[dict]) -> str:
    """Deja la evidencia por escrito, para adjuntarla al documento."""
    conteo = Counter(c["decision"] for c in compras)
    lineas = [
        "# Compras simuladas en la tienda\n",
        f"{len(compras)} compras hechas contra la API real de la tienda "
        "(`POST /api/v1/orders`), con el mismo recorrido que haría un cliente: "
        "descuento de stock, evaluación del modelo, decisión y registro.\n",
        f"- Aprobadas: **{conteo.get('APPROVED', 0)}**",
        f"- A revisión manual: **{conteo.get('REVIEW', 0)}**",
        f"- Bloqueadas: **{conteo.get('BLOCKED', 0)}**\n",
        "| # | Perfil | Monto | Checkout | Puntaje | Decisión | Estado del pedido |",
        "| ---: | :--- | ---: | ---: | ---: | :---: | :--- |",
    ]

    for compra in compras:
        duracion = compra["segundos"]
        duracion_texto = f"{duracion:.0f} s" if duracion < 60 else f"{duracion / 60:.1f} min"
        lineas.append(
            f"| {compra['numero']} | {compra['perfil']} | "
            f"S/ {compra['monto']:,.2f} | {duracion_texto} | "
            f"{compra['puntaje']:.0%} | {compra['decision']} | {compra['estado']} |"
        )

    ejemplos = [c for c in compras if c["decision"] != "APPROVED"][:3]
    if ejemplos:
        lineas.append("\n## Explicaciones que quedaron registradas\n")
        for compra in ejemplos:
            lineas.append(
                f"**Compra {compra['numero']}** (S/ {compra['monto']:,.2f}, "
                f"{compra['decision']}):\n\n> {compra['explicacion']}\n"
            )

    lineas.append(
        "\n*Compras generadas por `app/scripts/simular_compras.py`. Son "
        "ficticias: sirven para demostrar el funcionamiento del sistema, no "
        "como datos de venta.*\n"
    )
    return "\n".join(lineas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hace compras ficticias en la tienda.")
    parser.add_argument("--cuantas", type=int, default=30)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument(
        "--acepto-datos-simulados-en-esta-base",
        action="store_true",
        help="Necesario para correr contra una base que no sea SQLite.",
    )
    argumentos = parser.parse_args()

    if not settings.DATABASE_URL.startswith("sqlite") and not argumentos.acepto_datos_simulados_en_esta_base:
        print(
            "ABORTADO: la base configurada no es SQLite.\n\n"
            "Estas compras son inventadas y descuentan stock de verdad. En la\n"
            "tienda desplegada ensuciarían el inventario y las métricas. Si es\n"
            "una base de pruebas, repite con --acepto-datos-simulados-en-esta-base."
        )
        return 1

    compras = asyncio.run(comprar(argumentos.cuantas, argumentos.semilla))
    if not compras:
        print("No se registró ninguna compra.")
        return 1

    conteo = Counter(c["decision"] for c in compras)
    print(f"\n{len(compras)} compras registradas:")
    for decision in ("APPROVED", "REVIEW", "BLOCKED"):
        print(f"  {decision:<9} {conteo.get(decision, 0)}")

    destino = Path(__file__).resolve().parents[2] / "ml" / "informes"
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / "compras_simuladas_en_la_tienda.md"
    archivo.write_text(_informe(compras), encoding="utf-8")
    print(f"\nEvidencia guardada en {archivo}")

    asyncio.run(engine.dispose())
    return 0


if __name__ == "__main__":
    sys.exit(main())
