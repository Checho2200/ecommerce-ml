"""
Endpoints de evaluación y monitoreo de fraude usando el modelo LightGBM.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.fraud_log import FraudLog
from app.models.user import User
from app.services import fraud_metrics_service, reporte_de_indicadores
from app.services.fraud_service import fraud_service
from app.schemas.fraud import (
    FraudEvaluationRequest,
    FraudEvaluationResponse,
    FraudHistoryPeriod,
    FraudHistoryResponse,
    FraudLabelRequest,
    FraudLogResponse,
    FraudMetricsResponse,
    FraudModelInfo,
)

router = APIRouter(prefix="/fraud", tags=["Detección de Fraude"])

@router.post("/evaluate", response_model=FraudEvaluationResponse)
async def evaluate_fraud(
    data: FraudEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Evalúa el riesgo de fraude de una transacción con el modelo LightGBM.

    Solo para administradores: es una herramienta de prueba del modelo. La
    evaluación que decide de verdad una compra ocurre dentro de `crear_pedido`,
    no aquí. Antes este endpoint era público, y sin autenticación cualquiera
    podía sondear el modelo —probar entradas y leer su respuesta— sin coste.
    """
    checkout_duration = (
        data.checkout_duration_seconds if data.checkout_duration_seconds is not None else 120.0
    )
    is_new_address = 1 if data.is_new_shipping_address else 0

    evaluacion = fraud_service.evaluar(
        total_amount=data.total_amount,
        high_risk_items_count=data.high_risk_items_count,
        checkout_duration_seconds=checkout_duration,
        is_new_shipping_address=is_new_address,
    )

    return FraudEvaluationResponse(
        order_id=data.order_id,
        fraud_score=round(evaluacion.puntaje, 4),
        decision=evaluacion.decision,
        risk_level=evaluacion.nivel_de_riesgo,
        explanation=evaluacion.explicacion,
        contributions=evaluacion.aportes,
    )


@router.get("/logs", response_model=list[FraudLogResponse])
async def list_fraud_logs(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Últimas evaluaciones del modelo (solo admin)."""
    result = await db.execute(
        select(FraudLog).order_by(FraudLog.evaluated_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/model", response_model=FraudModelInfo)
async def get_model_info(admin: User = Depends(require_admin)):
    """
    Con qué se publicó el modelo que está sirviendo (solo admin).

    Los umbrales y los indicadores viajan en `fraud_model.meta.json`, que
    escribe el entrenamiento. Si el archivo falta, el servicio cae en los
    umbrales históricos y aquí se ve: los campos de medición vienen nulos.
    """
    meta = fraud_service.metadatos or {}
    return FraudModelInfo(
        loaded=fraud_service.is_loaded(),
        trained_at=meta.get("entrenado_en"),
        data_source=meta.get("origen_de_los_datos"),
        approve_below=fraud_service.umbral_aprobacion,
        block_above=fraud_service.umbral_bloqueo,
        average_precision=meta.get("average_precision"),
        roc_auc=meta.get("roc_auc"),
        detection_rate=meta.get("tasa_de_deteccion"),
        detection_time_ms=meta.get("tiempo_de_deteccion_ms"),
        base_value=fraud_service.valor_base(),
        n_trees=fraud_service.cantidad_de_arboles(),
        features=meta.get("variables", []),
    )


@router.get("/metrics", response_model=FraudMetricsResponse)
async def get_fraud_metrics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Rendimiento del modelo, medido contra los pedidos que ya se revisaron.

    El cálculo vive en `app/services/fraud_metrics_service.py`; aquí solo se
    traduce a la forma que espera el panel.
    """
    m = await fraud_metrics_service.calcular(db)

    return FraudMetricsResponse(
        total_evaluations=m.total_evaluaciones,
        # Se conservan con su nombre original para no romper el panel.
        detected_fraud_rate=round(m.exhaustividad * 100, 2),
        undetected_fraud_rate=round(
            (1 - m.exhaustividad) * 100 if m.verdaderos_positivos + m.falsos_negativos else 0.0,
            2,
        ),
        average_detection_time_ms=round(m.tiempo_medio_ms, 2),
        reviewed_count=m.revisados,
        true_positives=m.verdaderos_positivos,
        false_positives=m.falsos_positivos,
        true_negatives=m.verdaderos_negativos,
        false_negatives=m.falsos_negativos,
        precision=round(m.precision * 100, 2),
        recall=round(m.exhaustividad * 100, 2),
        f1_score=round(m.f1 * 100, 2),
        loss_prevented=round(m.perdida_evitada, 2),
        loss_absorbed=round(m.perdida_asumida, 2),
        revenue_lost=round(m.venta_perdida, 2),
    )


def _a_respuesta_de_historial(
    granularidad: str, serie: list
) -> FraudHistoryResponse:
    """
    Traduce la serie del servicio a la forma que espera el panel.

    Los totales de la ventana se calculan sumando los casos y dividiendo una
    sola vez, no promediando las tasas de cada período: el promedio de
    porcentajes le daría el mismo peso a un mes con un fraude que a uno con
    cien, y el indicador que cita la tesis dejaría de ser el que dice ser.
    """
    reales = sum(p.fraudes_reales for p in serie)
    detectados = sum(p.fraudes_detectados for p in serie)
    no_detectados = sum(p.fraudes_no_detectados for p in serie)

    # El tiempo medio se pondera por evaluaciones por la misma razón.
    con_tiempo = sum(p.evaluaciones for p in serie if p.tiempo_medio_ms)
    suma_ms = sum(p.tiempo_medio_ms * p.evaluaciones for p in serie if p.tiempo_medio_ms)

    return FraudHistoryResponse(
        granularity=granularidad,
        periods=[
            FraudHistoryPeriod(
                period_start=p.inicio,
                evaluations=p.evaluaciones,
                approved=p.aprobadas,
                in_review=p.en_revision,
                blocked=p.bloqueadas,
                approved_amount=p.monto_aprobado,
                held_amount=p.monto_retenido,
                average_score=p.puntaje_medio,
                reviewed=p.revisados,
                actual_frauds=p.fraudes_reales,
                detected_frauds=p.fraudes_detectados,
                undetected_frauds=p.fraudes_no_detectados,
                detection_rate=p.tasa_de_deteccion,
                undetected_rate=p.tasa_de_no_deteccion,
                average_detection_time_ms=p.tiempo_medio_ms,
            )
            for p in serie
        ],
        total_evaluations=sum(p.evaluaciones for p in serie),
        total_approved=sum(p.aprobadas for p in serie),
        total_held=sum(p.en_revision + p.bloqueadas for p in serie),
        total_reviewed=sum(p.revisados for p in serie),
        total_actual_frauds=reales,
        total_detected_frauds=detectados,
        total_undetected_frauds=no_detectados,
        detection_rate=round(detectados / reales, 4) if reales else None,
        undetected_rate=round(no_detectados / reales, 4) if reales else None,
        average_detection_time_ms=round(suma_ms / con_tiempo, 2) if con_tiempo else 0.0,
    )


@router.get("/history", response_model=FraudHistoryResponse)
async def get_fraud_history(
    granularity: str = Query("day", pattern="^(day|week|month|year)$"),
    periods: int | None = Query(None, ge=1, le=366),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Las decisiones del modelo repartidas en el tiempo (solo admin).

    `/metrics` responde cómo va el modelo hoy; esto responde cómo ha ido. Un
    promedio sobre toda la vida de la tienda esconde que los bloqueos se
    dispararon la semana pasada, y esa es justo la lectura que sirve para
    decidir si hay que revisar el umbral.

    Devuelve la ventana completa, incluidos los períodos sin evaluaciones: una
    gráfica a la que le faltan los días tranquilos une dos picos con una recta
    y hace parecer sostenido lo que fue puntual.
    """
    serie = await fraud_metrics_service.historial(db, granularity, periods)
    return _a_respuesta_de_historial(granularity, serie)


@router.get("/report.xlsx")
async def download_fraud_report(
    granularity: str = Query("month", pattern="^(day|week|month|year)$"),
    periods: int | None = Query(None, ge=1, le=366),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    El reporte de indicadores en un archivo de Excel (solo admin).

    Devuelve exactamente los mismos números que `/history`: el archivo se arma
    desde la misma función, así que no puede desviarse de lo que enseña el
    panel. Un reporte que no cuadra con la pantalla de la que sale es peor que
    no tener reporte.
    """
    serie = await fraud_metrics_service.historial(db, granularity, periods)
    datos = _a_respuesta_de_historial(granularity, serie)
    libro = reporte_de_indicadores.construir(datos)

    nombre = f"indicadores-antifraude-{granularity}-{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        libro,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


async def _etiquetar(db: AsyncSession, log_id: str, es_fraude: bool) -> FraudLog:
    result = await db.execute(select(FraudLog).where(FraudLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log no encontrado")

    log.is_actual_fraud = es_fraude
    log.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(log)
    return log


@router.put("/logs/{log_id}/label", response_model=FraudLogResponse)
async def label_fraud_log(
    log_id: str,
    data: FraudLabelRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Etiqueta una evaluación con lo que realmente pasó.

    Las dos respuestas cuentan. Marcar los fraudes reales permite medir cuántos
    se escapan; marcar los pedidos legítimos permite medir cuántas ventas
    buenas se están frenando. Con una sola de las dos, la precisión del modelo
    no se puede calcular, y son también los ejemplos con los que se reentrena.
    """
    return await _etiquetar(db, log_id, data.is_fraud)


@router.put("/logs/{log_id}/actual-fraud", response_model=FraudLogResponse)
async def mark_actual_fraud(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Marca una evaluación como fraude real (contracargo confirmado)."""
    return await _etiquetar(db, log_id, True)


def run_training_task():
    """
    Reentrena el modelo en un proceso aparte y lo recarga en memoria.

    Va en un proceso aislado porque el entrenamiento usa todos los núcleos y
    bloquearía el servidor. `ml/train.py` decide por su cuenta si el modelo
    nuevo merece reemplazar al que está sirviendo: si sale peor, lo descarta y
    deja el informe para revisarlo.
    """
    import os
    import subprocess
    import sys

    try:
        print("Iniciando tarea de reentrenamiento en segundo plano...")
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        subprocess.run([sys.executable, "-m", "ml.train"], cwd=backend_dir, check=True)
        fraud_service.recargar()
        print("Reentrenamiento completado y modelo recargado.")
    except Exception as e:  # noqa: BLE001 - la tarea corre sin nadie mirando
        print(f"Error en reentrenamiento asíncrono: {e}")


@router.post("/retrain", status_code=status.HTTP_202_ACCEPTED)
async def retrain_model(
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
):
    """
    Desencadena el reentrenamiento del modelo en segundo plano.

    Usa los pedidos etiquetados por los administradores si ya alcanzan —con un
    mínimo por clase— y, si no, el conjunto sintético del dominio. Solo
    accesible para administradores.
    """
    background_tasks.add_task(run_training_task)
    return {
        "message": (
            "Reentrenamiento iniciado en segundo plano. Puede tomar varios "
            "minutos por la búsqueda de hiperparámetros. El modelo solo se "
            "reemplaza si el nuevo no es peor que el actual."
        )
    }
