"""Subcategorías del catálogo (jerarquía de categorías)

Da a las categorías un segundo nivel: cada raíz —"Procesadores", "Memorias
RAM"…— pasa a agrupar subcategorías —las líneas Intel/AMD, DDR3/DDR4/DDR5…—.

La migración es aditiva y no borra nada en producción:

1. Añade `categories.parent_id`, nulo en las raíces.
2. Crea las subcategorías de cada raíz que ya exista, sin duplicar las que
   ya estuvieran (se identifican por su slug).
3. Recoloca los productos que cuelgan de una raíz en la subcategoría que les
   toca por su texto (nombre + descripción). Lo que no encaje en ninguna se
   queda en la raíz, así que ningún producto queda sin categoría.

La estructura y las reglas de emparejamiento viven en `app/taxonomia.py`, que
es la misma fuente que usa el sembrado.

Revision ID: e3c7a1f9d240
Revises: c4f1a9e27b30
"""

from alembic import op
import sqlalchemy as sa

from app.taxonomia import SUBCATEGORIAS, subcategoria_para

revision = "e3c7a1f9d240"
down_revision = "c4f1a9e27b30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("categories", sa.Column("parent_id", sa.Integer(), nullable=True))
    # SQLite no admite añadir índices/llaves con ALTER sobre una tabla ya
    # creada; en desarrollo el esquema se arma con create_all, no con Alembic,
    # así que estos adornos solo hacen falta en PostgreSQL (producción).
    if bind.dialect.name != "sqlite":
        op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
        op.create_foreign_key(
            "fk_categories_parent", "categories", "categories", ["parent_id"], ["id"]
        )

    meta = sa.MetaData()
    categories = sa.Table("categories", meta, autoload_with=bind)
    products = sa.Table("products", meta, autoload_with=bind)

    # Categorías raíz existentes, por slug.
    filas = bind.execute(
        sa.select(
            categories.c.id,
            categories.c.slug,
            categories.c.is_high_risk,
            categories.c.image_url,
        )
    ).all()
    por_slug = {f.slug: f for f in filas}

    # 1) Crear las subcategorías que falten.
    id_hija_por_slug: dict[str, int] = {}
    for raiz_slug, hijas in SUBCATEGORIAS.items():
        raiz = por_slug.get(raiz_slug)
        if raiz is None:
            continue
        for nombre, slug, _claves in hijas:
            ya = por_slug.get(slug)
            if ya is not None:
                id_hija_por_slug[slug] = ya.id
                continue
            resultado = bind.execute(
                sa.insert(categories).values(
                    name=nombre,
                    slug=slug,
                    is_high_risk=raiz.is_high_risk,
                    parent_id=raiz.id,
                    image_url=raiz.image_url,
                )
            )
            id_hija_por_slug[slug] = resultado.inserted_primary_key[0]

    # 2) Recolocar los productos de cada raíz en su subcategoría.
    for raiz_slug, hijas in SUBCATEGORIAS.items():
        raiz = por_slug.get(raiz_slug)
        if raiz is None:
            continue
        productos = bind.execute(
            sa.select(products.c.id, products.c.name, products.c.description).where(
                products.c.category_id == raiz.id
            )
        ).all()
        for p in productos:
            slug = subcategoria_para(f"{p.name} {p.description or ''}", hijas)
            if slug and slug in id_hija_por_slug:
                bind.execute(
                    sa.update(products)
                    .where(products.c.id == p.id)
                    .values(category_id=id_hija_por_slug[slug])
                )


def downgrade() -> None:
    bind = op.get_bind()

    meta = sa.MetaData()
    categories = sa.Table("categories", meta, autoload_with=bind)
    products = sa.Table("products", meta, autoload_with=bind)

    # Devolver cada producto a la categoría padre antes de borrar las hijas,
    # para no dejar productos apuntando a una categoría inexistente.
    hijas = bind.execute(
        sa.select(categories.c.id, categories.c.parent_id).where(
            categories.c.parent_id.isnot(None)
        )
    ).all()
    for h in hijas:
        bind.execute(
            sa.update(products)
            .where(products.c.category_id == h.id)
            .values(category_id=h.parent_id)
        )

    bind.execute(sa.delete(categories).where(categories.c.parent_id.isnot(None)))

    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_categories_parent", "categories", type_="foreignkey")
        op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_column("categories", "parent_id")
