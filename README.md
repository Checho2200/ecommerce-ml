# Sanchez Tech Store — e-commerce con detección de fraude

Tienda en línea de componentes y periféricos de cómputo para **Grupo STS SAC**
(Trujillo, La Libertad), con cobro real por MercadoPago y un modelo de
aprendizaje automático que evalúa cada pedido antes de aceptarlo.

El sistema está desplegado y funcionando:

| Pieza | Dónde vive | Dirección |
| --- | --- | --- |
| Tienda (Next.js) | Vercel | https://ecommerce-ml.vercel.app |
| API (FastAPI) | Render | https://sanchez-tech-store-api.onrender.com |
| Documentación de la API | Render | https://sanchez-tech-store-api.onrender.com/docs |
| Base de datos | Neon (PostgreSQL) | — |

> **Antes de una demostración en vivo:** el plan gratuito de Render suspende el
> servicio tras unos 15 minutos sin tráfico, y la primera petición después
> tarda entre 30 y 50 segundos. Ejecuta a mano el flujo
> *Despertar el backend* (pestaña **Actions** de GitHub) unos cinco minutos
> antes, o simplemente abre la tienda y espera a que cargue.

---

## Qué hace

- **Catálogo y compra.** Productos por categorías, búsqueda, carrito, checkout
  y seguimiento de pedidos.
- **Pago real.** Checkout Pro de MercadoPago con credenciales de producción,
  solo con tarjeta. El pedido se confirma cuando MercadoPago avisa por webhook,
  no cuando el cliente vuelve del pago.
- **Detección de fraude.** Cada pedido pasa por un modelo LightGBM que devuelve
  una probabilidad de fraude; según esa probabilidad la orden se aprueba, se
  manda a revisión o se rechaza. Todas las evaluaciones quedan registradas.
- **Servicio técnico.** Los clientes registran equipos a reparar y siguen su
  diagnóstico y costo estimado.
- **Panel de administración.** Productos, categorías, órdenes, servicios,
  métricas del modelo y reentrenamiento.

---

## Arquitectura

El proyecto está organizado en capas con una responsabilidad cada una. La regla
que las mantiene separadas se resume en dos frases: **el router no conoce las
reglas del negocio, y el servicio no conoce HTTP.**

```
Petición HTTP
    ↓
app/api/v1/        Routers: validan la entrada, delegan y presentan la salida
    ↓
app/services/      Reglas del negocio: inventario, fraude, pagos, correo
    ↓
app/models/        Tablas y relaciones (SQLAlchemy)
    ↓
PostgreSQL / SQLite
```

### Backend

```
backend/
  app/
    api/v1/        Un router por recurso: auth, products, categories, orders,
                   service_orders, reviews, fraud, upload
    core/          Configuración, base de datos, seguridad, límite de peticiones
    models/        Tablas y relaciones (SQLAlchemy)
    schemas/       Contratos de entrada y salida (Pydantic)
    services/      Lógica de negocio y trato con servicios externos
    scripts/       Tareas de operación (migraciones, contraseñas, simulaciones)
  alembic/         Migraciones versionadas del esquema
  ml/              Pipeline del modelo, independiente de la aplicación web
  tests/           Pruebas automatizadas
```

**Qué hay en `services/` y por qué.** Cada archivo encapsula una decisión del
negocio o una integración externa, y ninguno importa FastAPI:

| Servicio | De qué responde |
| --- | --- |
| `order_service.py` | Reservar inventario, evaluar el pedido, decidir su estado, caducarlo, cancelarlo, devolver stock |
| `fraud_service.py` | Cargar el modelo, puntuar un pedido, explicar la decisión |
| `fraud_metrics_service.py` | Medir el modelo contra los pedidos revisados |
| `payment_service.py` | Preferencias de cobro y lectura de notificaciones de MercadoPago |
| `webhook_security.py` | Verificar la firma de esas notificaciones |
| `email_service.py` | Correo saliente, con degradación a log si no hay SMTP |
| `errors.py` | Los errores de dominio que los servicios lanzan |

**Cómo viajan los errores.** Un servicio que no puede cumplir una regla lanza
`RecursoNoEncontrado`, `OperacionNoPermitida` o `AccesoDenegado`, sin saber qué
código HTTP le corresponde. Un único manejador en `app/main.py` los traduce a
respuestas. Así la lógica se puede ejecutar desde un script o una tarea en
segundo plano sin arrastrar el framework web detrás.

Antes de esta separación, `app/api/v1/orders.py` tenía 586 líneas donde
convivían la validación de la petición, las reglas del negocio, las consultas y
el armado de la respuesta. Hoy son 264 líneas de router y 415 de servicio, cada
una con un propósito.

### Frontend

```
frontend/src/
  app/           Rutas (App Router). Una carpeta por pantalla
  components/    Componentes de interfaz
    admin/       Formularios del panel
    producto/    Bloques de la ficha de producto
    ui/          Cabecera, pie, tarjetas, campos reutilizables
    home/        Bloques de la portada
  hooks/         Estado de datos reutilizable (useRecurso)
  lib/
    api/         Cliente HTTP, un módulo por recurso
    stores/      Estado global (carrito, tema) con Zustand
    auth.tsx     Contexto de sesión
    estados.ts   Cómo se muestra cada estado del sistema
```

**El cliente de API** era un archivo de 564 líneas con todo dentro. Ahora
`lib/api/cliente.ts` concentra el `fetch` con JWT, el manejo del 401 y el
formato de los errores, y cada recurso vive en su módulo (`orders.ts`,
`products.ts`, `fraud.ts`…). `lib/api/index.ts` los reúne, así que las pantallas
siguen escribiendo `api.orders.list()` sin saber dónde está cada cosa.

**El hook `useRecurso`** resuelve de una vez el patrón que estaba copiado en
cada pantalla del panel: pedir datos, saber si están cargando, descartar una
respuesta que llega tarde y recargar tras guardar algo. Se apoya en dos reglas
que el proyecto respeta en todas partes: el estado se guarda dentro del callback
de la promesa (nunca de forma síncrona en un efecto, que encadena renders) y
toda petición lleva un interruptor para descartar respuestas obsoletas.

**Los formularios del panel** se sacaron de las páginas a `components/admin/`, y
la sección de opiniones a `components/producto/`. Una página orquesta —trae
datos, pagina, decide qué mostrar—; un formulario captura y valida; la sección
de reseñas se administra sola. Eran responsabilidades distintas en el mismo
archivo. La ficha de producto pasó de 617 líneas a 456, y las pantallas del
panel de más de 490 a menos de 330, salvo la de pedidos.

### El pipeline de aprendizaje automático

`backend/ml/` es independiente de la aplicación web: se ejecuta por línea de
comandos, no importa nada de `app/api/`, y podría moverse a otro repositorio sin
romper la tienda. La única conexión es en un sentido: lee los pedidos
etiquetados a través del modelo de datos, y deja un archivo de modelo que
`fraud_service` carga.

| Módulo | De qué responde |
| --- | --- |
| `dataset.py` | De dónde salen los datos: la tienda o el conjunto sintético |
| `exploracion.py` | Exportar el conjunto y describirlo |
| `evaluacion.py` | Métricas, costos y elección de umbrales |
| `train.py` | Entrenar, validar y decidir si el modelo se publica |
| `baselines.py` | Comparar contra alternativas más simples |
| `experimento.py` | Medir la mejora frente al sistema anterior |

### Convenciones

- **Un archivo, una responsabilidad.** Si un router necesita explicar cómo
  funciona el negocio, esa explicación va a un servicio.
- **Los comentarios dicen por qué, no qué.** El código ya dice qué hace; el
  comentario está para la decisión que no se ve, y muchos apuntan al fallo
  concreto que motivó una línea.
- **Nada de números mágicos repartidos.** Umbrales, costos, plazos y estados
  están nombrados y en un solo sitio.
- **Cada corrección lleva su prueba.** Los fallos que se arreglaron tienen una
  prueba que falla sin el arreglo; se verificó una por una.

---

## Levantar el proyecto en tu máquina

Hacen falta **Python 3.12** y **Node 20**.

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # en Linux o macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env             # y revisa los valores (ver la tabla de abajo)
python -m app.seed               # datos de ejemplo: OJO, borra y recrea las tablas
uvicorn app.main:app --reload
```

La API queda en <http://localhost:8000> y su documentación interactiva en
<http://localhost:8000/docs>.

Sin `DATABASE_URL` la aplicación usa un archivo SQLite local
(`sanchez_ecommerce.db`) y crea las tablas sola al arrancar, así que no hace
falta instalar PostgreSQL para desarrollar.

El usuario administrador lo crea `app/seed.py` a partir de estas variables de
entorno, que no tienen ningún valor real escrito en el repositorio:

```bash
SEED_ADMIN_EMAIL=tu-correo@ejemplo.com SEED_ADMIN_PASSWORD='una-clave-larga' python -m app.seed
```

Para cambiarle la contraseña a una cuenta que ya existe —en producción, sin
borrar nada— está `app/scripts/reset_admin_password.py`.

### Frontend

```bash
cd frontend
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > .env.local
npm run dev
```

La tienda queda en <http://localhost:3000>.

---

## Variables de entorno

Todas van en `backend/.env` (hay una plantilla en `backend/.env.example`).

| Variable | Para qué sirve | Si falta |
| --- | --- | --- |
| `DATABASE_URL` | Conexión a la base | Usa SQLite local |
| `SECRET_KEY` | Firma de los JWT | Usa una clave de ejemplo: **cámbiala en producción** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración de la sesión | 60 minutos |
| `RESET_TOKEN_EXPIRE_MINUTES` | Duración del enlace de recuperación | 30 minutos |
| `MERCADOPAGO_ACCESS_TOKEN` | Cobros | El checkout responde 503 |
| `MERCADOPAGO_WEBHOOK_SECRET` | Firma de las notificaciones de pago | No se exige firma |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Correo saliente | Los correos se escriben en el log en vez de enviarse |
| `FRONTEND_URL` | CORS y enlaces de los correos | `http://localhost:3000` |
| `BACKEND_URL` | URL del webhook que se le da a MercadoPago | `http://localhost:8000` |
| `DEBUG` | Registro detallado de SQL | `true` |

En el frontend solo hace falta `NEXT_PUBLIC_API_URL`.

---

## Base de datos y migraciones

En SQLite (desarrollo y pruebas) las tablas se crean solas al arrancar. En
PostgreSQL manda **Alembic**, y el despliegue las aplica en cada build:

```bash
python -m app.scripts.apply_migrations
```

Ese script mira primero en qué estado está la base y decide: aplica lo que
falte, o —si el esquema ya existe pero Alembic todavía no lo controlaba— lo
marca en la revisión actual sin tocar los datos.

Para crear una migración nueva después de cambiar un modelo:

```bash
cd backend
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

---

## Pruebas

```bash
cd backend
python -m pytest
```

Son 106 pruebas y cubren lo que duele si se rompe:

- **Inventario.** Que comprar descuente stock, que un pedido rechazado no lo
  toque, y que cancelar —el cliente o el administrador— lo devuelva.
- **Permisos.** Que nadie vea las órdenes de otro ni entre al listado de
  administración sin serlo.
- **Contraseñas.** Que el enlace de recuperación caduque al usarse, que un
  token de sesión no sirva para cambiar la contraseña y que la cuenta
  desactivada no pueda recuperarse.
- **Pagos.** El parseo de las notificaciones de MercadoPago (los dos formatos
  que la pasarela usa hoy) y la verificación de su firma.
- **Modelo de fraude.** Que cargue, que puntúe dentro de rango, que respete los
  umbrales que salieron del entrenamiento, que explique cada decisión con los
  factores de ese pedido, y que toda orden quede con su evaluación registrada.
- **Medición del modelo.** Que el AUC-PR delate al clasificador que aprueba
  todo, que el costo de cada tipo de error se calcule como está documentado, que
  los umbrales elegidos respeten la capacidad de revisión, y que las métricas
  del panel cuenten solo los pedidos que alguien revisó de verdad.
- **Datos de entrenamiento.** Que el entrenamiento lea de verdad los pedidos
  etiquetados de la base, que descarte los que nadie revisó, que se niegue a
  entrenar sin casos suficientes de cada clase, y que un modelo peor o con un
  resultado sospechoso no llegue a producción.

Cada prueba corre contra su propio SQLite temporal, así que no tocan la base de
desarrollo ni dependen del orden.

Un aviso que salió caro aprender: la mayoría de las pruebas de la API sustituyen
la sesión de base de datos por una sola compartida, y eso llegó a **tapar un
error 500 en el checkout**. `tests/test_api_pedido_sesion_real.py` existe para
cerrar ese hueco: monta la aplicación sin ninguna sustitución, con una sesión
nueva por petición como en producción, y compra de verdad.

GitHub Actions ejecuta esto en cada *push* y cada *pull request*, junto con el
lint, la comprobación de tipos y el build del frontend
(`.github/workflows/tests.yml`).

---

## El modelo de detección de fraude

Es el centro de la tesis, así que el pipeline está separado en piezas que se
pueden ejecutar y auditar por separado:

| Archivo | Qué hace |
| --- | --- |
| `backend/ml/dataset.py` | De dónde salen los datos: los pedidos etiquetados de la tienda o, mientras no alcancen, el conjunto sintético del dominio |
| `backend/ml/evaluacion.py` | Cómo se mide el modelo y cómo se eligen sus umbrales |
| `backend/ml/train.py` | Entrena, evalúa, guarda el informe y publica el modelo |
| `backend/ml/baselines.py` | Compara LightGBM contra alternativas más simples |
| `backend/ml/exploracion.py` | Exporta el conjunto de datos y lo describe |
| `backend/ml/experimento.py` | Compara el sistema de antes con el de ahora |
| `backend/ml/informes/` | Lo que queda de cada ejecución: métricas en JSON y figuras en PNG |

```bash
cd backend
python -m ml.train                 # entrena y, si mejora, reemplaza el modelo
python -m ml.train --sinteticos    # fuerza el conjunto sintético
python -m ml.baselines             # tabla comparativa de modelos
python -m ml.dataset               # exporta el conjunto de datos y su análisis
python -m ml.experimento           # evidencia de antes y después
```

### Qué mira

Cuatro variables por pedido:

| Variable | De dónde sale |
| --- | --- |
| `total_amount` | Monto del pedido |
| `high_risk_items_count` | Unidades de categorías marcadas como alto riesgo (tarjetas de video, procesadores) |
| `checkout_duration_seconds` | Cuánto tardó la persona desde que entró al checkout hasta que confirmó |
| `is_new_shipping_address` | Si es la primera vez que ese cliente envía a esa dirección |

### Cómo se entrena y se valida

Los datos se parten en tres: **60 % entrenamiento, 20 % validación, 20 % prueba**,
estratificados para que la proporción de fraude se conserve. La partición de
prueba no se toca hasta el final; los hiperparámetros salen de una búsqueda en
rejilla sobre entrenamiento y los umbrales se eligen sobre validación. Elegir
cualquiera de las dos cosas mirando la prueba inflaría los resultados.

La métrica que gobierna la búsqueda es el **AUC-PR** (precisión media), no el
acierto global: con un 7 % de fraude, un modelo que apruebe todo acierta el
93 % de las veces sin detectar un solo caso. La estabilidad se mide con
validación cruzada estratificada de 5 particiones repetida 2 veces, y se
reporta media ± desviación.

Resultados de la última ejecución con el conjunto sintético (10 000
transacciones, 8.3 % de fraude):

| Métrica | Valor |
| --- | --- |
| AUC-PR en validación cruzada | 0.731 ± 0.031 |
| AUC-PR en la partición de prueba | 0.729 |
| AUC-ROC en prueba | 0.906 |
| Precisión / Exhaustividad / F1 | 0.752 / 0.675 / 0.711 |

Los números y las figuras se regeneran con `python -m ml.train` y quedan en
`backend/ml/informes/`: curva ROC, curva precisión-exhaustividad, distribución
de puntajes, matriz de confusión y superficie de costo.

### Por qué LightGBM y no algo más simple

Todos los candidatos se entrenan con la misma partición y se les eligen sus
propios umbrales con el mismo criterio, así que la comparación es justa
(`python -m ml.baselines`):

| Modelo | AUC-PR | AUC-ROC | F1 | Pérdida (S/) |
| --- | ---: | ---: | ---: | ---: |
| **LightGBM** | **0.697** | **0.902** | 0.664 | **45 712** |
| Bosque aleatorio | 0.673 | 0.895 | 0.664 | 81 639 |
| Árbol de decisión | 0.628 | 0.898 | 0.629 | 49 517 |
| Regresión logística | 0.598 | 0.887 | 0.387 | 65 991 |
| Reglas heurísticas | 0.531 | 0.858 | 0.547 | 91 805 |
| Clasificador trivial | 0.082 | 0.493 | 0.071 | 395 421 |

La línea base honesta son las reglas heurísticas —marcar el pedido si es caro,
rápido y va a una dirección nueva—: LightGBM le saca 17 puntos de AUC-PR y le
reduce la pérdida a la mitad.

### De dónde salen los umbrales

Las dos fronteras de decisión no están escritas a mano: se eligen minimizando
lo que cuestan los errores, con estos precios (`ml/evaluacion.py`, todos
configurables):

- Aprobar un fraude cuesta el monto del pedido más el cargo por contracargo
  (S/ 30): la mercadería ya salió.
- Bloquear una compra legítima cuesta el margen de esa venta (15 %), no el
  pedido entero.
- Revisar a mano cuesta el tiempo de una persona (S/ 4) **más sus
  equivocaciones**: el revisor acierta el 90 % de las veces, no siempre.
- Y no se puede revisar a mano más del **15 %** de los pedidos: es una
  restricción operativa de una tienda pequeña, no un costo.

Ese último punto importa. Sin él, el óptimo matemático manda el **84 %** de los
pedidos a revisión manual —la respuesta correcta para la ecuación y absurda
para el negocio—. Con la restricción, los umbrales elegidos son **aprobar por
debajo de 0.35 y bloquear a partir de 0.80**, con un 13.4 % de pedidos en
revisión.

Comparados con los 0.30 y 0.70 originales, ahorran un 9.5 % de la pérdida; y
además esos valores originales ni siquiera eran operables, porque exigían
revisar el 16.3 % de los pedidos. El informe lo dice explícitamente en
`comparacion_con_referencia`.

Los umbrales viajan con el modelo en `app/services/fraud_model.meta.json`, y el
servicio los lee al arrancar. Si ese archivo falta, vuelve a los valores
históricos para no quedarse nunca sin criterio.

| Probabilidad | Decisión | Qué pasa con la orden |
| --- | --- | --- |
| menor a 0.35 | `APPROVED` | Sigue al pago |
| 0.35 – 0.80 | `REVIEW` | Queda en `FRAUD_REVIEW` para que la revise una persona |
| mayor a 0.80 | `BLOCKED` | Nace `REJECTED` y el stock se devuelve enseguida |

### Por qué decidió lo que decidió

Cada evaluación guarda cuánto empujó cada variable el puntaje de ese pedido en
concreto. Son valores SHAP, que LightGBM calcula de forma exacta con
`pred_contrib` —sin librerías adicionales—, y con ellos se arma la explicación
que ve el administrador:

> Riesgo alto (99 %); pedido rechazado. Lo que pesó en contra: 4 artículos de
> alto riesgo, checkout de 11 s, monto de S/ 8 500.00.

Antes, todos los pedidos de alto riesgo recibían la misma frase fija, que no
explicaba nada y no se podía auditar.

### El conjunto de datos

Hay dos fuentes y se prefiere la primera:

1. **Los pedidos de la tienda.** Cada compra deja un registro en `fraud_logs`
   con las variables que se usaron para evaluarla. Cuando un administrador la
   revisa y la etiqueta, ese registro pasa a ser un ejemplo de entrenamiento.
2. **Un conjunto sintético del dominio**, mientras los reales no alcancen.

`python -m ml.dataset` exporta el conjunto que se esté usando y lo describe. Todo
va a la carpeta **`dataset/`** de la raíz, que tiene su propio README explicando
el origen de los datos y su construcción:

| Archivo | Qué es |
| --- | --- |
| `dataset/README.md` | El origen de los datos, cómo se construye el conjunto y por qué las clases se solapan |
| `dataset/dataset_sintetico.csv` | El conjunto completo, listo para adjuntar como anexo |
| `dataset/diccionario_de_datos.md` | Qué es cada variable, en qué unidad y de dónde sale |
| `dataset/estadisticas_del_dataset.md` / `.json` | Media, mediana y cuartiles por clase, más el solapamiento entre clases |
| `dataset/distribucion_de_variables.png` | Cómo se distribuye cada variable en cada clase |
| `dataset/correlacion_de_variables.png` | Matriz de correlación de Spearman |

La tabla descriptiva del conjunto sintético actual:

| Variable | Legítimas | Fraudulentas | Solapamiento |
| --- | --- | --- | ---: |
| monto del pedido | 742.70 (446.32) | 2616.82 (1694.14) | 0.239 |
| artículos de alto riesgo | 0.52 (0.00) | 1.73 (2.00) | 0.410 |
| duración del checkout | 292.86 (204.27) | 114.80 (62.30) | 0.264 |
| dirección de envío nueva | 0.20 | 0.61 | — |

*Media (mediana). El solapamiento es la proporción de pedidos legítimos que caen
dentro del rango intercuartílico del fraude.*

Esa última columna es el argumento metodológico del trabajo: entre el 24 % y el
41 % de las compras legítimas caen dentro del rango típico del fraude en cada
variable. Ninguna separa las clases por sí sola, y por eso el problema es de
clasificación estadística y no un `if` con umbrales. El conjunto sintético se
genera con esa superposición a propósito, y es reproducible: misma semilla,
mismos datos.

### Cómo aprende de la realidad

Cuando un pedido se resuelve, el administrador lo etiqueta desde el panel:
**fue fraude** (contracargo) o **fue una compra legítima**. Las dos respuestas
hacen falta —sin los "fue legítima" no hay verdaderos negativos y la precisión
no se puede calcular—, y son también los ejemplos con los que se reentrena.

El reentrenamiento lee esos pedidos de la base que use la aplicación —SQLite en
desarrollo, PostgreSQL en producción— y usa datos reales solo cuando hay al
menos 200 etiquetados con un mínimo de 30 de cada clase. Por debajo de eso
sigue con el conjunto sintético y deja dicho por qué en el informe.

Antes de publicar un modelo nuevo se comprueban dos cosas:

- **Que no empeore.** El candidato solo reemplaza al que está sirviendo si
  iguala o mejora su AUC-PR sobre la misma partición de prueba.
- **Que el resultado sea creíble.** Un AUC-PR por encima de 0.99, o una
  partición de prueba de menos de 40 casos, se rechazan: en detección de fraude
  con datos de verdad no se acierta el 100 %, y cuando eso pasa casi siempre es
  fuga de datos o un conjunto demasiado pequeño. Publicar ese modelo sería
  cambiar uno medido por uno que nadie comprobó. Con `--forzar` se puede
  publicar igual, pero hay que pedirlo.

**Para demostrar el ciclo completo** cuando todavía no hay clientes reales:

```bash
python -m app.scripts.simular_revisiones     # etiqueta lo que haya sin revisar
python -m ml.train                           # ahora entrena con "datos de la tienda"
python -m app.scripts.simular_revisiones --deshacer
```

Las etiquetas que pone ese script son inventadas y quedan marcadas como tales
en `admin_notes`; el script se niega a correr contra una base que no sea SQLite.
Sirve para enseñar que el ciclo funciona, no para sacar resultados: cualquier
métrica calculada sobre ellas mide al simulador, no a la tienda.

El botón **Reentrenar modelo** (Panel → Configuración) dispara todo el proceso
en segundo plano y recarga el modelo sin reiniciar el servidor.

Un detalle del despliegue: el disco de Render es efímero, así que un modelo
reentrenado en el servidor vive hasta el siguiente reinicio —y el plan gratuito
reinicia al despertar de la suspensión—. Para que un modelo nuevo sea
permanente hay que entrenarlo en local y subir `fraud_model.joblib` y
`fraud_model.meta.json` al repositorio. El botón sirve para demostrar el ciclo
completo de aprendizaje, que es lo que interesa mostrar en la sustentación.

### La evidencia de que mejoró

`python -m ml.experimento` compara el sistema tal como estaba con el de ahora,
sobre **4 000 compras simuladas que ninguno de los dos modelos vio** durante su
entrenamiento. El modelo anterior se conserva en `ml/modelos/` para que el
experimento se pueda repetir.

Hay tres configuraciones, no dos, porque comparar solo el principio con el
final diría *que* mejoró pero no *por qué*:

| Configuración | Umbrales | AUC-PR | Precisión | Fraudes aprobados | Legítimas bloqueadas | Pérdida (S/) |
| --- | :---: | ---: | ---: | ---: | ---: | ---: |
| A. Sistema original | 0.30 / 0.70 | 0.7690 | 0.6453 | 47 | 133 | 121 025 |
| B. Modelo anterior + umbrales por costo | 0.35 / 0.90 | 0.7690 | 0.8696 | 51 | 30 | 105 086 |
| C. Sistema actual | 0.40 / 0.85 | 0.7688 | 0.7970 | 53 | 54 | 95 657 |

**La pérdida baja un 21 %**, de S/ 121 025 a S/ 95 657.

Y ahora la parte que conviene contar entera, porque es lo primero que un jurado
va a mirar: **el modelo reentrenado no distingue mejor el fraude**. Su AUC-PR es
0.7688 frente a 0.7690, es decir, el mismo. Los dos ordenan las compras por
riesgo igual de bien. Toda la mejora viene de **qué se hace con ese puntaje**:
S/ 15 939 de dejar de elegir los umbrales a ojo (A → B) y S/ 9 429 de que los
puntajes del modelo nuevo se reparten de forma que admiten un corte más barato
(B → C).

También conviene explicar el intercambio, porque no es una mejora en todos los
frentes: el sistema actual deja pasar **6 fraudes más** (47 → 53) y a cambio
deja de frenar **79 compras legítimas** (133 → 54). Eso es exactamente lo que
pide el criterio de costo con los precios declarados; si para la tienda el
fraude pesara más que la venta perdida, se sube `cargo_por_contracargo` en
`ml/evaluacion.py` y los umbrales se recolocan solos.

En `ml/informes/` quedan la tabla completa, el desglose en JSON, dos figuras
(curvas superpuestas y de dónde sale la pérdida) y `compras_de_prueba.md`, con
diez compras concretas y lo que decidía cada sistema sobre cada una —incluida
la explicación, que antes era una frase idéntica para todos y ahora nombra los
factores de ese pedido.

### Compras de prueba en la tienda

Para evidencia de extremo a extremo, `app/scripts/simular_compras.py` hace
compras ficticias **contra la API real**, con el mismo recorrido que un cliente:
descuento de stock, evaluación, decisión y registro. Después quedan en el panel
de administración, listas para capturar pantalla.

```bash
python -m app.seed                              # catálogo de desarrollo
python -m app.scripts.simular_compras --cuantas 40
```

De las 37 compras que entraron en la última corrida: 25 aprobadas, 5 a revisión
manual y 7 bloqueadas, cada una con su explicación guardada. El detalle queda en
`ml/informes/compras_simuladas_en_la_tienda.md`.

Igual que el simulador de revisiones, se niega a correr contra una base que no
sea SQLite: son compras inventadas y descontarían inventario de verdad.

### Lo que estos números no dicen

Dos límites que conviene declarar antes de que los pregunten:

1. **Un pedido bloqueado nunca llega a cobrarse**, así que jamás tendrá un
   contracargo que lo confirme como fraude. Los aciertos más valiosos del
   modelo son, por construcción, los más difíciles de etiquetar, y las métricas
   del panel los subestiman.
2. **Los resultados de arriba son sobre datos sintéticos.** Miden que el método
   funciona y que el pipeline es correcto, no el desempeño que tendrá la tienda
   con tráfico real. Ese número solo existe cuando haya suficientes pedidos
   etiquetados.

## Cómo funciona el pago

1. El cliente confirma el pedido. El backend descuenta stock, evalúa el fraude
   y crea la orden en `PENDING`.
2. Se crea una preferencia de MercadoPago y el cliente va a pagar. El carrito
   **no** se vacía todavía.
3. MercadoPago notifica al webhook `/api/v1/orders/webhook/mercadopago`. El
   backend comprueba la firma de la notificación, vuelve a consultar el pago
   contra la API de MercadoPago y recién ahí marca la orden como `COMPLETED`
   —o la cancela y devuelve el stock si el pago fue rechazado.
4. Al confirmarse, el cliente recibe un correo con el detalle.

Las órdenes que quedan sin pagar caducan a las dos horas y liberan su
inventario.

Para probar el webhook en local hace falta exponer el puerto 8000 con un túnel
(por ejemplo `ngrok http 8000`) y poner esa dirección en `BACKEND_URL`:
MercadoPago solo notifica a direcciones públicas por HTTPS.

---

## Despliegue

- **Base de datos:** PostgreSQL en **Neon**, plan gratuito.
- **Backend:** **Render**, definido en `render.yaml`. El build instala
  dependencias y aplica migraciones; el arranque solo levanta uvicorn.
- **Frontend:** **Vercel**, conectado al repositorio. Necesita
  `NEXT_PUBLIC_API_URL` apuntando a la API de Render.

Ningún secreto vive en el repositorio: todas las credenciales se cargan como
variables de entorno en el panel de cada proveedor (`sync: false` en
`render.yaml`).

Se descartó Railway porque ya no ofrece un plan gratuito permanente.

---

## Estado del sistema

`GET /health` responde en una sola llamada si la base contesta, si el modelo
está cargado y si la pasarela tiene credenciales:

```json
{ "status": "healthy", "database": "connected", "ml_model": "loaded", "payments": "configured" }
```

Es lo que consulta el panel de administración y lo que usa el flujo que
despierta el backend antes de una demostración.
