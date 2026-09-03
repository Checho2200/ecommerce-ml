"""
Pruebas del ordenamiento del catálogo público.

Se comprueba lo que el cliente pidió —ordenar por precio y por abecedario— y,
sobre todo, que el precio con el que se ordena es el que el comprador paga: el
de oferta cuando existe, no siempre el de lista.
"""

from app.models.product import Category, Product


async def _tienda(sesion):
    """Deja una categoría y varios productos con precios y nombres distintos."""
    categoria = Category(name="Componentes", slug="componentes")
    sesion.add(categoria)
    await sesion.flush()

    # (nombre, precio, precio_oferta)
    catalogo = [
        ("Zócalo AM5", 120.0, None),
        ("Auriculares", 300.0, None),
        ("Monitor 4K", 1500.0, 999.0),   # paga 999, no 1500
        ("Batería", 80.0, None),
    ]
    for nombre, precio, oferta in catalogo:
        sesion.add(
            Product(
                name=nombre,
                description="x",
                price=precio,
                discount_price=oferta,
                stock=5,
                category_id=categoria.id,
            )
        )
    await sesion.commit()


async def _nombres(cliente, sort):
    respuesta = await cliente.get(f"/api/v1/products?sort={sort}")
    assert respuesta.status_code == 200, respuesta.text
    return [p["name"] for p in respuesta.json()["items"]]


async def test_orden_por_precio_usa_el_precio_que_se_paga(cliente, sesion):
    await _tienda(sesion)

    # El Monitor tiene oferta a 999, así que va por debajo de los Auriculares (300)?
    # No: 999 > 300. Pero sí por debajo de su propio precio de lista (1500).
    ascendente = await _nombres(cliente, "precio_asc")
    assert ascendente == ["Batería", "Zócalo AM5", "Auriculares", "Monitor 4K"]

    descendente = await _nombres(cliente, "precio_desc")
    assert descendente == ["Monitor 4K", "Auriculares", "Zócalo AM5", "Batería"]


async def test_orden_alfabetico_en_los_dos_sentidos(cliente, sesion):
    await _tienda(sesion)

    az = await _nombres(cliente, "nombre_asc")
    assert az == ["Auriculares", "Batería", "Monitor 4K", "Zócalo AM5"]

    za = await _nombres(cliente, "nombre_desc")
    assert za == list(reversed(az))


async def test_un_orden_desconocido_no_rompe_el_catalogo(cliente, sesion):
    await _tienda(sesion)
    respuesta = await cliente.get("/api/v1/products?sort=lo-que-sea")
    assert respuesta.status_code == 200
    assert len(respuesta.json()["items"]) == 4
