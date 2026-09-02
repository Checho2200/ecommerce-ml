"""
Endpoints de evaluación y monitoreo de fraude usando el modelo LightGBM.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.fraud_log import FraudLog
from app.models.user import User
from app.services import fraud_metrics_service
from app.services.fraud_service import fraud_service
from app.schemas.fraud import (
    FraudEvaluationRequest,
    FraudEvaluationResponse,
    FraudLabelRequest,
    FraudLogResponse,
    FraudMetricsResponse,
)

router = APIRouter(prefix="/fraud", tags=["Detección de Fraude"])

@router.post("/evaluate", response_model=FraudEvaluationResponse)
async def evaluate_fraud(
    data: FraudEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Evalúa el riesgo de fraude de una transacción con el modelo LightGBM."""
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
