"""
Endpoints de evaluación y monitoreo de fraude usando el modelo LightGBM.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.fraud_log import FraudLog
from app.models.user import User
from app.schemas.fraud import FraudEvaluationRequest, FraudEvaluationResponse, FraudLogResponse, FraudMetricsResponse
from app.api.deps import require_admin
from sqlalchemy import func

router = APIRouter(prefix="/fraud", tags=["Detección de Fraude"])


@router.post("/evaluate", response_model=FraudEvaluationResponse)
async def evaluate_fraud(
    data: FraudEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Evalúa el riesgo de fraude de una transacción utilizando el modelo LightGBM.
    """
    from app.services.fraud_service import fraud_service
    
    checkout_duration = data.checkout_duration_seconds if data.checkout_duration_seconds is not None else 120.0
    is_new_address = 1 if data.is_new_shipping_address else 0

    fraud_score, decision, risk_level, explanation, detection_time_ms = fraud_service.evaluate_transaction(
        total_amount=data.total_amount,
        high_risk_items_count=data.high_risk_items_count,
        checkout_duration_seconds=checkout_duration,
        is_new_shipping_address=is_new_address
    )

    return FraudEvaluationResponse(
        order_id=data.order_id,
        fraud_score=round(fraud_score, 4),
        decision=decision,
        risk_level=risk_level,
        explanation=explanation,
    )


@router.get("/logs", response_model=list[FraudLogResponse])
async def list_fraud_logs(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Lista los registros de evaluación de fraude (solo admin)."""
    result = await db.execute(
        select(FraudLog).order_by(FraudLog.evaluated_at.desc()).limit(50)
    )
    logs = result.scalars().all()
    return logs


@router.get("/metrics", response_model=FraudMetricsResponse)
async def get_fraud_metrics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Calcula las métricas de rendimiento del modelo de fraude."""
    # Total de evaluaciones
    total_result = await db.execute(select(func.count(FraudLog.id)))
    total_evaluations = total_result.scalar() or 0

    if total_evaluations == 0:
        return FraudMetricsResponse(
            total_evaluations=0,
            detected_fraud_rate=0.0,
            undetected_fraud_rate=0.0,
            average_detection_time_ms=0.0
        )

    # Fraudes detectados (la IA dijo REVIEW/BLOCKED y efectivamente era fraude)
    # Si la IA bloquea o manda a revisión, asumimos que fue "Detectado"
    # Para ser estrictos: es un True Positive si is_actual_fraud es True y la IA lo detectó.
    detected_result = await db.execute(
        select(func.count(FraudLog.id)).where(
            FraudLog.is_actual_fraud == True,
            FraudLog.decision.in_(["REVIEW", "BLOCKED"])
        )
    )
    detected_frauds = detected_result.scalar() or 0

    # Fraudes no detectados (la IA dijo APPROVED pero era fraude real)
    undetected_result = await db.execute(
        select(func.count(FraudLog.id)).where(
            FraudLog.is_actual_fraud == True,
            FraudLog.decision == "APPROVED"
        )
    )
    undetected_frauds = undetected_result.scalar() or 0

    # Total real frauds
    total_real_frauds = detected_frauds + undetected_frauds
    
    detected_rate = (detected_frauds / total_real_frauds) * 100 if total_real_frauds > 0 else 0.0
    undetected_rate = (undetected_frauds / total_real_frauds) * 100 if total_real_frauds > 0 else 0.0

    # Average detection time
    avg_time_result = await db.execute(select(func.avg(FraudLog.detection_time_ms)))
    avg_time = avg_time_result.scalar() or 0.0

    return FraudMetricsResponse(
        total_evaluations=total_evaluations,
        detected_fraud_rate=round(detected_rate, 2),
        undetected_fraud_rate=round(undetected_rate, 2),
        average_detection_time_ms=round(avg_time, 2)
    )


@router.put("/logs/{log_id}/actual-fraud", response_model=FraudLogResponse)
async def mark_actual_fraud(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Marca un log de evaluación como Fraude Real (simulación de contracargo)."""
    result = await db.execute(select(FraudLog).where(FraudLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log no encontrado")
    
    log.is_actual_fraud = True
    await db.commit()
    await db.refresh(log)
    
    return log

def run_training_task():
    import subprocess
    import os
    from app.services.fraud_service import fraud_service
    
    try:
        print("Iniciando tarea de reentrenamiento en segundo plano...")
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        # Ejecutar el script de entrenamiento en un proceso aislado
        subprocess.run(["python", "-m", "ml.train"], cwd=backend_dir, check=True)
        # Recargar el modelo en memoria
        fraud_service.load_model()
        print("Reentrenamiento asíncrono completado y modelo recargado exitosamente.")
    except Exception as e:
        print(f"Error en reentrenamiento asíncrono: {e}")

@router.post("/retrain", status_code=status.HTTP_202_ACCEPTED)
async def retrain_model(
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
):
    """
    Desencadena el reentrenamiento del modelo de fraude en segundo plano usando GridSearchCV.
    Actualiza el modelo en memoria una vez terminado.
    Solo accesible para administradores.
    """
    background_tasks.add_task(run_training_task)
    return {"message": "Reentrenamiento iniciado en segundo plano. Esto puede tomar algunos minutos debido a la optimización de hiperparámetros."}

