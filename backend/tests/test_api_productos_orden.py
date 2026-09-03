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


async def _tienda_con_subcategorias(sesion):
    """Una raíz 'Memorias RAM' con hijas DDR4/DDR5 y un producto en cada una."""
    ram = Category(name="Memorias RAM", slug="memorias-ram")
    sesion.add(ram)
    await sesion.flush()
    ddr4 = Category(name="DDR4", slug="ram-ddr4", parent_id=ram.id)
    ddr5 = Category(name="DDR5", slug="ram-ddr5", parent_id=ram.id)
    sesion.add_all([ddr4, ddr5])
    await sesion.flush()
    sesion.add_all([
        Product(name="Kit DDR4 16GB", description="x", price=189.0, stock=5, category_id=ddr4.id),
        Product(name="Kit DDR5 32GB", description="x", price=449.0, stock=5, category_id=ddr5.id),
    ])
    await sesion.commit()
    return ram, ddr4, ddr5


async def test_filtrar_por_raiz_incluye_las_subcategorias(cliente, sesion):
    ram, ddr4, _ddr5 = await _tienda_con_subcategorias(sesion)

    # La raíz trae lo de todas sus hijas.
    raiz = await cliente.get(f"/api/v1/products?category_id={ram.id}")
    assert raiz.status_code == 200
    nombres = {p["name"] for p in raiz.json()["items"]}
    assert nombres == {"Kit DDR4 16GB", "Kit DDR5 32GB"}

    # Una subcategoría trae solo lo suyo.
    solo_ddr4 = await cliente.get(f"/api/v1/products?category_id={ddr4.id}")
    assert {p["name"] for p in solo_ddr4.json()["items"]} == {"Kit DDR4 16GB"}


async def test_la_categoria_expone_su_parent_id(cliente, sesion):
    _ram, ddr4, _ddr5 = await _tienda_con_subcategorias(sesion)
    respuesta = await cliente.get("/api/v1/categories")
    assert respuesta.status_code == 200
    porslug = {c["slug"]: c for c in respuesta.json()}
    assert porslug["memorias-ram"]["parent_id"] is None
    assert porslug["ram-ddr4"]["parent_id"] == ddr4.parent_id
