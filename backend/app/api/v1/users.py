"""
Gestión de cuentas desde el panel de administración.

Hasta ahora la única forma de crear un administrador era un script de consola
con variables de entorno (`app/scripts/crear_admin.py`), lo que dejaba la
tienda con un solo administrador y sin manera de dar de alta a otro sin tocar
el servidor. Aquí está esa gestión: listar quién tiene cuenta, crear cuentas
—incluidas las de administrador—, cambiar roles y dar de baja.

Dos guardas que no son adorno, porque protegen de dejar la tienda sin nadie
que pueda entrar a administrarla:

1. **Nadie se toca a sí mismo.** Un administrador no puede quitarse el rol ni
   desactivarse: sería cerrarse la puerta desde dentro, y encima por accidente.
2. **Siempre queda un administrador activo.** No se le puede quitar el rol ni
   desactivar al último que quede. Si eso pasara, no quedaría nadie capaz de
   volver a nombrar administradores y habría que entrar a la base de datos a
   mano para recuperar la tienda.

Lo que no se puede hacer desde aquí es cambiarle la contraseña a otra persona:
eso es suplantarla. Para eso está el enlace de recuperación, que llega a su
propio correo.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import (
    UserAdminUpdate,
    UserCreateByAdmin,
    UserListResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["Usuarios"])


async def _administradores_activos(db: AsyncSession) -> int:
    return (
        await db.execute(
            select(func.count(User.id)).where(
                User.role == UserRole.ADMIN, User.is_active.is_(True)
            )
        )
    ).scalar() or 0


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Busca por nombre o correo"),
    role: str | None = Query(None, pattern="^(CLIENTE|ADMIN)$"),
    active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Las cuentas de la tienda, paginadas (solo admin)."""
    filtros = []
    if search:
        patron = f"%{search.strip()}%"
        filtros.append(or_(User.full_name.ilike(patron), User.email.ilike(patron)))
    if role:
        filtros.append(User.role == role)
    if active is not None:
        filtros.append(User.is_active.is_(active))

    total = (
        await db.execute(select(func.count(User.id)).where(*filtros))
    ).scalar() or 0

    resultado = await db.execute(
        select(User)
        .where(*filtros)
        # Los administradores primero y luego por antigüedad: en una tienda con
        # cientos de clientes, quien administra es lo que se viene a buscar.
        #
        # Se ordena por un caso explícito y no por `role.desc()`, que ordenaría
        # alfabéticamente y pondría CLIENTE antes que ADMIN. Además, así el
        # orden no depende de cómo se llamen los roles el día que se añada uno.
        .order_by(
            case((User.role == UserRole.ADMIN, 0), else_=1), User.created_at.desc()
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    return UserListResponse(
        items=list(resultado.scalars().all()),
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
        active_admins=await _administradores_activos(db),
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateByAdmin,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Crea una cuenta, con el rol que se le indique (solo admin).

    Es la vía por la que la tienda deja de depender de un único administrador.
    A diferencia del registro público, aquí sí se puede crear un ADMIN: quien
    llama ya es uno, así que no hay escalada de privilegios que impedir.
    """
    existe = await db.execute(select(User).where(User.email == data.email))
    if existe.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una cuenta con ese correo",
        )

    usuario = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
    )
    db.add(usuario)
    await db.flush()
    await db.refresh(usuario)
    return usuario


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Cambia el rol, el estado o los datos de una cuenta (solo admin).

    Las dos guardas de las que habla el módulo se aplican aquí, y en este
    orden: primero la de no tocarse a sí mismo —que da un mensaje más claro— y
    después la del último administrador.
    """
    resultado = await db.execute(select(User).where(User.id == user_id))
    usuario = resultado.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cambios = data.model_dump(exclude_unset=True)

    pierde_el_rol = cambios.get("role") == UserRole.CLIENTE and usuario.role == UserRole.ADMIN
    se_desactiva = cambios.get("is_active") is False and usuario.is_active

    if usuario.id == admin.id and (pierde_el_rol or se_desactiva):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No puedes quitarte a ti mismo el rol de administrador ni "
                "desactivar tu propia cuenta. Pídeselo a otro administrador."
            ),
        )

    if (pierde_el_rol or se_desactiva) and usuario.role == UserRole.ADMIN:
        if await _administradores_activos(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Es el único administrador activo. Nombra a otro antes de "
                    "quitarle el rol o desactivarlo, o la tienda se quedaría "
                    "sin nadie que pueda administrarla."
                ),
            )

    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)

    await db.flush()
    await db.refresh(usuario)
    return usuario


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Da de baja una cuenta y borra sus datos personales (solo admin).

    **No borra sus pedidos.** Esto es lo importante y conviene explicarlo,
    porque la primera versión que uno escribe es un `DELETE` sobre la fila del
    usuario y eso rompe dos cosas a la vez: revienta contra la clave foránea de
    `orders`, y si se forzara en cascada se llevaría por delante las
    evaluaciones del antifraude —con ellas, los fraudes confirmados que
    sostienen los indicadores de la tesis y los ejemplos con los que se
    reentrena el modelo—. Borrar un cliente no puede cambiar la historia de lo
    que la tienda vendió ni de lo que el modelo acertó.

    Lo que se hace es lo que hace cualquier tienda cuando alguien pide su baja:
    la cuenta deja de existir como tal —no puede entrar, y su correo, nombre y
    teléfono desaparecen— mientras los pedidos quedan, ya sin nombre detrás.
    El correo se sustituye por uno irrepetible para no chocar con la restricción
    de unicidad si otra persona se registra después con el mismo.

    Las mismas dos guardas que en el resto del módulo: nadie se borra a sí mismo
    y no se puede borrar al último administrador activo.
    """
    usuario = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No puedes eliminar tu propia cuenta. Pídeselo a otro "
                "administrador."
            ),
        )

    if usuario.role == UserRole.ADMIN and await _administradores_activos(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Es el único administrador activo. Nombra a otro antes de "
                "eliminarlo, o la tienda se quedaría sin nadie que pueda "
                "administrarla."
            ),
        )

    usuario.email = f"cuenta-eliminada-{usuario.id}@invalido.local"
    usuario.full_name = "Cuenta eliminada"
    usuario.phone = None
    usuario.is_active = False
    usuario.role = UserRole.CLIENTE
    # La contraseña se sustituye por un valor que ningún hash puede producir,
    # así que ninguna contraseña vuelve a validar contra esta fila.
    usuario.hashed_password = "cuenta-eliminada"
    await db.flush()
