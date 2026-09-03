"""
Taxonomía del catálogo: qué subcategorías tiene cada categoría raíz y cómo se
reconoce, por su texto, a qué subcategoría pertenece un producto.

Es la única fuente de esta estructura. La usan el sembrado (`app/seed.py`), que
construye el catálogo de cero, y la migración que reorganizó en producción las
categorías que ya existían. Tenerla en un solo sitio evita que las dos copias
se separen con el tiempo.

El emparejamiento mira el nombre y la descripción del producto, y solo se aplica
dentro de la categoría raíz correspondiente —a un producto de "Memorias RAM" se
le prueban las subcategorías de RAM, no las de monitores—, así que una palabra
clave suelta no puede arrastrarlo a otra familia.
"""

# slug de la categoría raíz -> lista de (nombre, slug, palabras_clave).
# El orden importa: un producto cae en la PRIMERA subcategoría cuyas palabras
# clave aparezcan en su texto. Por eso "SSD NVMe" va antes que "SSD SATA": un
# NVMe también dice "SSD", y se quiere la lectura más específica.
SUBCATEGORIAS = {
    "procesadores": [
        ("Intel Core i3", "intel-core-i3", ["i3"]),
        ("Intel Core i5", "intel-core-i5", ["i5"]),
        ("Intel Core i7", "intel-core-i7", ["i7"]),
        ("Intel Core i9", "intel-core-i9", ["i9"]),
        ("AMD Ryzen 3", "amd-ryzen-3", ["ryzen 3"]),
        ("AMD Ryzen 5", "amd-ryzen-5", ["ryzen 5"]),
        ("AMD Ryzen 7", "amd-ryzen-7", ["ryzen 7"]),
        ("AMD Ryzen 9", "amd-ryzen-9", ["ryzen 9"]),
    ],
    "tarjetas-de-video": [
        ("NVIDIA GeForce RTX", "nvidia-rtx", ["rtx"]),
        ("NVIDIA GeForce GTX", "nvidia-gtx", ["gtx"]),
        ("AMD Radeon RX", "amd-radeon-rx", ["radeon", "rx "]),
    ],
    "memorias-ram": [
        ("DDR3", "ram-ddr3", ["ddr3"]),
        ("DDR4", "ram-ddr4", ["ddr4"]),
        ("DDR5", "ram-ddr5", ["ddr5"]),
    ],
    "almacenamiento": [
        ("SSD NVMe", "ssd-nvme", ["nvme"]),
        ("SSD SATA", "ssd-sata", ["ssd"]),
        ("Disco Duro (HDD)", "hdd", ["hdd", "disco duro"]),
    ],
    "monitores": [
        ("4K UHD", "monitores-4k", ["4k", "uhd"]),
        ("2K QHD (1440p)", "monitores-2k", ["1440", "2k", "qhd"]),
        ("Full HD (1080p)", "monitores-fhd", ["1080", "full hd", "fhd"]),
    ],
    "placas-madre": [
        ("Socket AM5", "placas-am5", ["am5"]),
        ("Socket AM4", "placas-am4", ["am4"]),
        ("Socket LGA1700", "placas-lga1700", ["lga1700", "lga 1700"]),
    ],
    "perifericos": [
        ("Teclados", "teclados", ["teclado", "keyboard"]),
        ("Mouses", "mouses", ["mouse", "ratón", "raton"]),
    ],
    "cases-y-fuentes": [
        ("Fuentes de Poder", "fuentes-de-poder", ["fuente", "psu", "80+", "modular"]),
        ("Cases / Gabinetes", "cases", ["case", "gabinete", "airflow", "torre"]),
    ],
    "audio": [
        ("Audífonos", "audifonos", ["audífono", "audifono", "headset", "cascos", "cloud"]),
        ("Micrófonos", "microfonos", ["micrófono", "microfono", "micro"]),
    ],
    "redes": [
        ("Routers", "routers", ["router", "archer", "wifi"]),
        ("Switches", "switches", ["switch"]),
    ],
}


def subcategoria_para(texto: str, subcats: list) -> str | None:
    """
    Slug de la subcategoría que corresponde a un producto, o None si ninguna
    palabra clave coincide —en cuyo caso el producto se queda en la raíz—.

    `texto` es el nombre más la descripción del producto, en cualquier caja:
    se normaliza a minúsculas aquí.
    """
    t = texto.lower()
    for _nombre, slug, claves in subcats:
        if any(clave in t for clave in claves):
            return slug
    return None
