"""
Demostración guiada del sistema: cuatro compras que enseñan lo que decide el modelo.

    python -m app.scripts.demostracion

A diferencia de `simular_compras.py`, que hace compras al azar para llenar el
panel, este script hace **cuatro compras concretas y siempre las mismas**. Cada
una está construida para terminar en un desenlace distinto, porque para
sustentar la tesis no basta con que el modelo funcione: hay que poder enseñar
que funciona, y enseñarlo dos veces seguidas con el mismo resultado.

Las cuatro:

    1. APROBADA Y PAGADA      Clienta con cuenta antigua, compra barata, sin
                              prisa. El modelo aprueba, el cobro pasa y el
                              pedido queda COMPLETED.

    2. RETENIDA POR EL MODELO Cuenta recién abierta, dirección estrenada, monto
                              medio. El modelo manda a revisar; el cobro pasa y
                              el pedido queda FRAUD_REVIEW: cobrado, pero
                              parado antes de salir del almacén.

    3. BLOQUEADA              Cuenta nueva, dirección nueva, componente caro de
                              reventa fácil, checkout resuelto en segundos. El
                              modelo bloquea: el pedido nace REJECTED, nunca
                              llega al formulario de pago y el inventario vuelve
                              en el acto.

    4. COBRO RECHAZADO        El modelo aprueba, pero la tarjeta no pasa. El
                              pedido queda CANCELLED y el stock vuelve. Es el
                              caso que separa «el modelo dijo que no» de «el
                              banco dijo que no», que son cosas distintas.

Nada de esto está escrito a mano. Las compras entran por el mismo endpoint que
usaría un cliente (`POST /api/v1/orders`), las evalúa el modelo entrenado que
haya cargado, y el cobro entra por el endpoint de pago con las mismas tarjetas
que reconoce la tienda. Los puntajes que salgan son los que salgan.

Deja el informe en `ml/informes/demostracion_del_modelo.md`, listo para
adjuntar.

No hace falta levantar el servidor: la aplicación se ejecuta en memoria.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.product import Category, Product
from app.models.user import User, UserRole
from app.services.pago_simulado import TARJETAS_DE_PRUEBA

CLAVE = "demostracion-2026"

settings = get_settings()


def _tarjeta(que_hace: str) -> str:
    """
    Una tarjeta de las que reconoce la tienda, buscada por su desenlace.

    Se leen del propio servicio de pago en lugar de copiarlas aquí: si algún día
    cambian los números, este script sigue funcionando en vez de quedarse
    demostrando con tarjetas que ya no existen.
    """
    for numero, (decision, _marca, _codigo) in TARJETAS_DE_PRUEBA.items():
        if decision.startswith(que_hace):
            return numero
    raise RuntimeError(f"No hay ninguna tarjeta de prueba que termine en «{que_hace}»")


# ─────────────────────────────────────────────────────────────────────────────
# Los cuatro casos
# ─────────────────────────────────────────────────────────────────────────────
CASOS = [
    {
        "clave": "aprobada",
        "titulo": "Compra normal, aprobada y pagada",
        "correo": "rosa.medina@ejemplo.com",
        "nombre": "Rosa Medina Vargas",
        "antiguedad_dias": 120,
        "producto": "barato",
        "direccion": "Av. España 1234, Trujillo",
        "segundos": 150.0,
        "tarjeta": "aprobada",
        "esperado": "COMPLETED",
        "por_que": (
            "Una clienta de hace cuatro meses comprando algo barato y tomándose su "
            "tiempo. Es el perfil que el modelo tiene que dejar pasar sin fricción: "
            "si a esta compra le pusiera una traba, la tienda perdería clientes "
            "legítimos y el sistema no serviría."
        ),
    },
    {
        "clave": "retenida",
        "titulo": "Compra retenida por el modelo",
        "correo": "kevin.salas@ejemplo.com",
        "nombre": "Kevin Salas Ortiz",
        "antiguedad_dias": 1,
        "producto": "medio",
        "direccion": "Jr. Los Cedros 880, Trujillo",
        "segundos": 60.0,
        "tarjeta": "aprobada",
        # El titular de la tarjeta NO coincide con el dueño de la cuenta, que es
        # la marca clásica del fraude con tarjeta robada y la señal que el
        # revisor tiene delante gracias a que la retención ocurre tras el cobro.
        "titular_de_la_tarjeta": "M. ANGELA TORRES P",
        "esperado": "FRAUD_REVIEW",
        "por_que": (
            "Cuenta abierta ayer, dirección estrenada y un monto que ya duele. No "
            "hay nada concluyente, y por eso no se bloquea: se cobra y se para "
            "antes de enviar. Al revisor le queda delante el dato que no existía "
            "hasta que se pagó —el titular de la tarjeta— y aquí no coincide con "
            "el dueño de la cuenta."
        ),
    },
    {
        "clave": "bloqueada",
        "titulo": "Compra bloqueada antes de cobrar",
        "correo": "luis.paredes@ejemplo.com",
        "nombre": "Luis Paredes Ruiz",
        "antiguedad_dias": 0,
        "producto": "alto_riesgo",
        "direccion": "Calle Las Gardenias 45, Trujillo",
        "segundos": 22.0,
        "tarjeta": None,  # No llega a pagarse.
        "esperado": "REJECTED",
        "por_que": (
            "Cuenta creada hace un momento, dirección nueva, componente caro de "
            "reventa inmediata y checkout resuelto en veintidós segundos. Las "
            "cinco variables apuntan al mismo sitio. El pedido nace rechazado: no "
            "se le pide la tarjeta a nadie y el inventario vuelve en el acto."
        ),
    },
    {
        "clave": "cobro_rechazado",
        "titulo": "Aprobada por el modelo, rechazada por el banco",
        "correo": "rosa.medina@ejemplo.com",
        "nombre": "Rosa Medina Vargas",
        "antiguedad_dias": 120,
        "producto": "barato",
        "direccion": "Av. España 1234, Trujillo",
        "segundos": 150.0,
        "tarjeta": "rechazada",
        "esperado": "CANCELLED",
        "por_que": (
            "La misma clienta y la misma compra del primer caso, con una tarjeta "
            "sin fondos. El modelo la aprueba —no hay nada sospechoso— y el cobro "
            "no prospera. El pedido se cancela y el stock vuelve a la tienda. Sirve "
            "para separar dos cosas que se confunden: que el sistema antifraude "
            "diga que no, y que el banco diga que no."
        ),
    },
]


async def _preparar_compradores() -> None:
    """
    Crea las cuentas de la demostración, cada una con su antigüedad.

    La antigüedad de la cuenta es una de las cinco variables del modelo y la que
    más pesa, así que no se puede dejar al azar: se fija hacia atrás en el
    tiempo. Una cuenta de cuatro meses y una abierta hace un minuto tienen que
    ser distintas de verdad, no de mentira.
    """
    async with AsyncSessionLocal() as sesion:
        for caso in CASOS:
            existente = (
                await sesion.execute(select(User).where(User.email == caso["correo"]))
            ).scalar_one_or_none()

            nacimiento = datetime.now(timezone.utc) - timedelta(
                days=caso["antiguedad_dias"]
            )

            if existente:
                existente.created_at = nacimiento
                continue

            sesion.add(
                User(
                    email=caso["correo"],
                    hashed_password=hash_password(CLAVE),
                    full_name=caso["nombre"],
                    phone="900000000",
                    role=UserRole.CLIENTE,
                    created_at=nacimiento,
                )
            )
        await sesion.commit()


async def _elegir_productos() -> dict:
    """
    Un producto para cada caso, sacado del catálogo real.

    No se nombran a mano: se buscan por lo que tienen que ser, así que el script
    funciona con el catálogo que haya delante.
    """
    async with AsyncSessionLocal() as sesion:
        resultado = await sesion.execute(
            select(Product, Category)
            .join(Category, Product.category_id == Category.id)
            .where(Product.is_active == True, Product.stock > 0)  # noqa: E712
        )
        filas = [
            {
                "id": p.id,
                "nombre": p.name,
                "precio": float(c.is_high_risk and p.price or p.price),
                "alto_riesgo": bool(c.is_high_risk),
                "stock": p.stock,
            }
            for p, c in resultado.all()
        ]

    if not filas:
        raise RuntimeError(
            "No hay productos con stock. Ejecuta antes `python -m app.seed`."
        )

    por_precio = sorted(filas, key=lambda f: f["precio"])
    caros_de_riesgo = [f for f in por_precio if f["alto_riesgo"] and f["precio"] >= 1200]
    medios = [f for f in por_precio if 400 <= f["precio"] <= 900 and not f["alto_riesgo"]]

    if not caros_de_riesgo:
        raise RuntimeError(
            "No hay ningún producto caro en una categoría de alto riesgo. Sin eso "
            "no se puede demostrar el bloqueo."
        )

    return {
        "barato": por_precio[0],
        "medio": (medios or por_precio)[len(medios) // 2 if medios else 0],
        "alto_riesgo": caros_de_riesgo[-1],
    }


async def _stock_de(producto_id: str) -> int:
    async with AsyncSessionLocal() as sesion:
        return (await sesion.get(Product, producto_id)).stock


async def demostrar() -> list[dict]:
    from httpx import ASGITransport, AsyncClient

    from app.core.rate_limit import limiter
    from app.main import app

    await _preparar_compradores()
    productos = await _elegir_productos()

    resultados = []

    # El tope por IP está pensado para personas, no para un script que hace
    # cuatro compras seguidas desde la misma máquina.
    limiter.enabled = False
    try:
        transporte = ASGITransport(app=app)
        async with AsyncClient(transport=transporte, base_url="http://demostracion") as http:
            for caso in CASOS:
                producto = productos[caso["producto"]]
                stock_antes = await _stock_de(producto["id"])

                acceso = await http.post(
                    "/api/v1/auth/login",
                    json={"email": caso["correo"], "password": CLAVE},
                )
                acceso.raise_for_status()
                cabeceras = {"Authorization": f"Bearer {acceso.json()['access_token']}"}

                respuesta = await http.post(
                    "/api/v1/orders",
                    json={
                        "items": [{"product_id": producto["id"], "quantity": 1}],
                        "shipping_address": caso["direccion"],
                        "shipping_city": "Trujillo",
                        "checkout_duration_seconds": caso["segundos"],
                    },
                    headers=cabeceras,
                )
                respuesta.raise_for_status()
                orden = respuesta.json()

                cobro = None
                if caso["tarjeta"] and orden["status"] == "PENDING":
                    pago = await http.post(
                        f"/api/v1/orders/{orden['id']}/pago-simulado",
                        json={
                            "numero": _tarjeta(caso["tarjeta"]),
                            "mes": 12,
                            "anio": datetime.now(timezone.utc).year + 2,
                            "cvv": "123",
                            "titular": caso.get("titular_de_la_tarjeta", caso["nombre"]),
                        },
                        headers=cabeceras,
                    )
                    pago.raise_for_status()
                    cobro = pago.json()

                final = await http.get(
                    f"/api/v1/orders/{orden['id']}", headers=cabeceras
                )
                final.raise_for_status()
                orden_final = final.json()

                resultados.append(
                    {
                        **caso,
                        "producto": producto["nombre"],
                        "alto_riesgo": producto["alto_riesgo"],
                        "monto": orden["total_amount"],
                        "puntaje": orden["fraud_score"],
                        "decision": orden["fraud_decision"],
                        "explicacion": orden["fraud_explanation"],
                        "estado_inicial": orden["status"],
                        "estado_final": orden_final["status"],
                        "cobro": cobro,
                        "referencia": orden_final.get("payment_id"),
                        "tarjeta_guardada": orden_final.get("card_last_four"),
                        "titular_guardado": orden_final.get("card_holder"),
                        "stock_antes": stock_antes,
                        "stock_despues": await _stock_de(producto["id"]),
                    }
                )
    finally:
        limiter.enabled = True

    return resultados


def _informe(resultados: list[dict]) -> str:
    lineas = [
        "# El modelo decidiendo: cuatro compras\n",
        "Cuatro compras hechas contra la API real de la tienda "
        "(`POST /api/v1/orders`), con el recorrido completo: reserva de "
        "inventario, evaluación del modelo LightGBM, decisión, cobro y estado "
        "final del pedido. Ninguno de los puntajes de abajo está escrito a mano; "
        "son los que devolvió el modelo cargado en ese momento.\n",
        "| Caso | Monto | Antigüedad | Dirección | Checkout | Puntaje | Decisión | Estado final |",
        "| :--- | ---: | ---: | :--- | ---: | ---: | :---: | :--- |",
    ]

    for r in resultados:
        lineas.append(
            f"| {r['titulo']} | S/ {r['monto']:,.2f} | "
            f"{r['antiguedad_dias']} d | {'nueva' if r['clave'] != 'cobro_rechazado' else 'conocida'} | "
            f"{r['segundos']:.0f} s | {r['puntaje']:.1%} | {r['decision']} | "
            f"**{r['estado_final']}** |"
        )

    lineas.append("\n---\n")

    for r in resultados:
        lineas.append(f"## {r['titulo']}\n")
        lineas.append(f"{r['por_que']}\n")
        lineas.append(f"- **Quién compra:** {r['nombre']} · cuenta de {r['antiguedad_dias']} día(s)")
        lineas.append(
            f"- **Producto:** {r['producto']} · S/ {r['monto']:,.2f}"
            f"{' · categoría de alto riesgo' if r['alto_riesgo'] else ''}"
        )
        lineas.append(f"- **Tiempo en el checkout:** {r['segundos']:.0f} segundos")
        lineas.append(f"- **Puntaje del modelo:** {r['puntaje']:.1%} → **{r['decision']}**")
        lineas.append(f"- **Estado al crearse:** {r['estado_inicial']}")

        if r["cobro"]:
            resultado_cobro = "aprobado" if r["cobro"]["aprobado"] else "rechazado"
            lineas.append(
                f"- **Cobro:** {resultado_cobro} · código `{r['cobro']['codigo']}`"
                + (f" · {r['cobro']['motivo']}" if r["cobro"].get("motivo") else "")
            )
            if r["referencia"]:
                lineas.append(f"- **Referencia del cobro:** `{r['referencia']}`")
            if r["tarjeta_guardada"]:
                lineas.append(
                    f"- **Tarjeta guardada:** •••• {r['tarjeta_guardada']} · "
                    f"titular «{r['titular_guardado']}»"
                )
        else:
            lineas.append("- **Cobro:** no llegó a pedirse")

        lineas.append(f"- **Estado final:** **{r['estado_final']}**")
        lineas.append(
            f"- **Stock del producto:** {r['stock_antes']} → {r['stock_despues']}"
        )
        if r["explicacion"]:
            lineas.append(f"\n> {r['explicacion']}\n")
        lineas.append("")

    lineas.append(
        "*Generado por `app/scripts/demostracion.py`. Las compras y las cuentas "
        "son de demostración; las decisiones del modelo y los estados del pedido "
        "son los que produjo el sistema.*\n"
    )
    return "\n".join(lineas)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cuatro compras que enseñan lo que decide el modelo."
    )
    parser.add_argument(
        "--acepto-datos-simulados-en-esta-base",
        action="store_true",
        help="Necesario para correr contra una base que no sea SQLite.",
    )
    argumentos = parser.parse_args()

    if (
        not settings.DATABASE_URL.startswith("sqlite")
        and not argumentos.acepto_datos_simulados_en_esta_base
    ):
        print(
            "ABORTADO: la base configurada no es SQLite.\n\n"
            "Estas compras descuentan stock de verdad y quedan en el historial\n"
            "que alimenta los indicadores. En la tienda desplegada los ensuciarían.\n"
            "Si es una base de pruebas, repite con\n"
            "--acepto-datos-simulados-en-esta-base."
        )
        return 1

    resultados = asyncio.run(demostrar())

    print("\n" + "=" * 78)
    for r in resultados:
        estado = r["estado_final"]
        marca = "OK " if estado == r["esperado"] else "!! "
        print(f"\n{marca}{r['titulo']}")
        print(f"   {r['nombre']}, cuenta de {r['antiguedad_dias']} día(s)")
        print(f"   {r['producto']} · S/ {r['monto']:,.2f} · {r['segundos']:.0f} s de checkout")
        print(f"   Puntaje {r['puntaje']:.1%} → {r['decision']}")
        if r["cobro"]:
            print(
                f"   Cobro {'aprobado' if r['cobro']['aprobado'] else 'rechazado'} "
                f"(código {r['cobro']['codigo']})"
            )
        else:
            print("   Cobro: no llegó a pedirse")
        print(f"   Estado final: {estado}   (esperado {r['esperado']})")
        print(f"   Stock: {r['stock_antes']} → {r['stock_despues']}")

    fallidos = [r for r in resultados if r["estado_final"] != r["esperado"]]
    print("\n" + "=" * 78)
    if fallidos:
        print(
            f"\n{len(fallidos)} caso(s) no terminaron donde se esperaba. El modelo "
            "puede haber cambiado de umbrales o de entrenamiento; revisa los "
            "puntajes de arriba antes de usar esto como evidencia."
        )
    else:
        print("\nLos cuatro casos terminaron donde debían.")

    destino = Path(__file__).resolve().parents[2] / "ml" / "informes"
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / "demostracion_del_modelo.md"
    archivo.write_text(_informe(resultados), encoding="utf-8")
    print(f"\nEvidencia guardada en {archivo}")

    print("\nLas cuentas quedan creadas, por si quieres repetirlo a mano:")
    for correo in dict.fromkeys(c["correo"] for c in CASOS):
        print(f"   {correo}  /  {CLAVE}")

    asyncio.run(engine.dispose())
    return 0


if __name__ == "__main__":
    sys.exit(main())
