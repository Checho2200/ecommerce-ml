"""
Qué contraseña acepta la tienda, y por qué esa y no otra.

La regla vive aquí y no repetida en cada schema porque el registro y el
restablecimiento tienen que exigir lo mismo: una política que solo se aplica en
la puerta de entrada la esquiva cualquiera pidiendo un enlace de recuperación.

Sobre lo que NO se hace, que también es una decisión:

- **No se prohíbe pegar la contraseña.** Es una costumbre extendida y
  contraproducente: quien no puede pegar no usa un gestor de contraseñas, y sin
  gestor la gente elige claves cortas que pueda escribir de memoria. El NIST
  (SP 800-63B) y el NCSC británico recomiendan expresamente permitir el pegado
  por ese motivo. Además no defiende de nada: quien ya está frente al teclado
  puede escribirla igual.
- **No se obliga a mezclar mayúsculas, números y símbolos.** Esa exigencia
  produce "Password1!" —que un atacante prueba de primero— y no una clave
  fuerte. Lo que sí mide la fuerza es la longitud, y eso es lo que se pide.
- **No caduca cada tres meses.** Forzar cambios periódicos hace que la gente
  vaya sumando un número al final. La misma guía del NIST lo desaconseja.
"""

import re
import unicodedata

# Ocho caracteres es el mínimo que el NIST fija para una clave elegida por una
# persona. Con menos, un ataque por fuerza bruta contra el hash es cuestión de
# horas por muy bien guardado que esté.
LONGITUD_MINIMA = 8
LONGITUD_MAXIMA = 100

# Las que aparecen primero en cualquier diccionario de ataque. No pretende ser
# una lista exhaustiva —para eso están la longitud y el límite de intentos por
# IP—, sino frenar lo que se teclea sin pensar.
CLAVES_PROHIBIDAS = {
    "12345678", "123456789", "1234567890", "password", "contrasena",
    "contraseña", "qwertyui", "qwerty123", "admin123", "administrador",
    "iloveyou", "princess", "abc12345", "password1", "password123",
    "11111111", "00000000", "letmein1", "welcome1", "gruposts",
}


class ContrasenaDebil(ValueError):
    """La contraseña no cumple la política. El mensaje se le muestra al usuario."""


def _sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def validar(password: str, email: str | None = None) -> str:
    """
    Devuelve la contraseña si es aceptable; si no, explica qué le falta.

    El mensaje dice exactamente qué corregir. "Contraseña inválida" a secas
    obliga a adivinar, y quien adivina termina probando la variante más simple
    que pase.
    """
    if len(password) < LONGITUD_MINIMA:
        raise ContrasenaDebil(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres."
        )
    if len(password) > LONGITUD_MAXIMA:
        raise ContrasenaDebil(
            f"La contraseña no puede pasar de {LONGITUD_MAXIMA} caracteres."
        )
    if password.strip() != password:
        raise ContrasenaDebil(
            "La contraseña no puede empezar ni terminar con un espacio."
        )

    normalizada = _sin_tildes(password.lower())
    if normalizada in CLAVES_PROHIBIDAS:
        raise ContrasenaDebil(
            "Esa contraseña es de las primeras que prueba un atacante. Elige otra."
        )
    if re.fullmatch(r"(.)\1+", password):
        raise ContrasenaDebil("La contraseña no puede ser el mismo carácter repetido.")

    # La parte local del correo es lo primero que se prueba contra una cuenta
    # concreta, y en la del administrador es pública.
    if email:
        usuario = _sin_tildes(email.split("@")[0].lower())
        if len(usuario) >= 4 and usuario in normalizada:
            raise ContrasenaDebil(
                "La contraseña no puede contener tu correo. Elige una distinta."
            )

    return password


def fuerza(password: str) -> int:
    """
    Puntúa de 0 a 4 lo robusta que es, para la barra que ve el usuario.

    Es una guía visual, no la validación: lo que decide si se acepta es
    `validar`. Pesa la longitud por encima de la variedad de caracteres, que es
    el orden en que ambas cosas importan de verdad.
    """
    if not password:
        return 0

    puntos = 0
    if len(password) >= LONGITUD_MINIMA:
        puntos += 1
    if len(password) >= 12:
        puntos += 1
    if len(password) >= 16:
        puntos += 1

    variedad = sum(
        bool(re.search(patron, password))
        for patron in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]")
    )
    if variedad >= 3:
        puntos += 1

    if _sin_tildes(password.lower()) in CLAVES_PROHIBIDAS:
        return 0
    return min(puntos, 4)
