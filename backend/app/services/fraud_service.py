import os
import joblib
import pandas as pd
from typing import Tuple

import time

class FraudDetectionService:
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), "fraud_model.joblib")
        
    def load_model(self):
        """Carga el modelo LightGBM si no está cargado ya."""
        if self.model is None:
            if os.path.exists(self.model_path):
                try:
                    self.model = joblib.load(self.model_path)
                    print(f"✅ Modelo de fraude cargado desde: {self.model_path}")
                except Exception as e:
                    print(f"⚠️ Error al cargar el modelo de fraude desde {self.model_path}: {e}")
            else:
                print(f"⚠️ Advertencia: No se encontró el modelo en {self.model_path}")
                
    def is_loaded(self) -> bool:
        """Devuelve True si el modelo está cargado exitosamente."""
        return self.model is not None
    
    def evaluate_transaction(self, 
                             total_amount: float, 
                             high_risk_items_count: int, 
                             checkout_duration_seconds: float, 
                             is_new_shipping_address: int) -> Tuple[float, str, str, str, float]:
        """
        Evalúa el riesgo de fraude utilizando el modelo entrenado.
        Devuelve (fraud_score, decision, risk_level, explanation, detection_time_ms).
        """
        # Intentar cargar el modelo si no está en memoria
        if self.model is None:
            self.load_model()
            
        if self.model is None:
            # Fallback seguro si el modelo no existe
            return 0.0, "APPROVED", "LOW", "Modelo no disponible, aprobación automática", 0.0
            
        # Preparar datos para el modelo (debe ser DataFrame para coincidir con el entrenamiento)
        input_data = pd.DataFrame([{
            "total_amount": total_amount,
            "high_risk_items_count": high_risk_items_count,
            "checkout_duration_seconds": checkout_duration_seconds,
            "is_new_shipping_address": is_new_shipping_address
        }])
        
        start_time = time.perf_counter()
        
        # Obtener probabilidad de la clase 1 (fraude)
        # predict_proba retorna [[prob_clase_0, prob_clase_1]]
        fraud_score = float(self.model.predict_proba(input_data)[0][1])
        
        end_time = time.perf_counter()
        detection_time_ms = (end_time - start_time) * 1000.0
        
        # Umbrales
        if fraud_score < 0.30:
            decision = "APPROVED"
            risk_level = "LOW"
            explanation = f"Bajo riesgo de fraude detectado por IA."
        elif fraud_score < 0.70:
            decision = "REVIEW"
            risk_level = "MEDIUM"
            explanation = f"Riesgo medio de fraude detectado por IA. Se requiere revisión."
        else:
            decision = "BLOCKED"
            risk_level = "HIGH"
            explanation = f"Alto riesgo de fraude detectado por IA. Orden rechazada."
            
        return fraud_score, decision, risk_level, explanation, detection_time_ms

# Instancia global del servicio
fraud_service = FraudDetectionService()
