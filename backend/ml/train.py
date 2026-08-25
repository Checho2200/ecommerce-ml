import os
import pandas as pd
from lightgbm import LGBMClassifier
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, roc_auc_score

import sqlite3

DATASET_URL = "https://raw.githubusercontent.com/dphi-official/Imbalanced_classes/master/fraud_data.csv"
MIN_SAMPLES_FOR_TRAINING = 50

def fetch_and_prepare_real_data():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sanchez_ecommerce.db")
    
    # Intento 1: Obtener datos reales de la base de datos
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            query = """
                SELECT 
                    o.total_amount,
                    f.feature_vector,
                    f.is_actual_fraud
                FROM orders o
                JOIN fraud_logs f ON o.id = f.order_id
            """
            df_db = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df_db) >= MIN_SAMPLES_FOR_TRAINING:
                print(f"📊 Usando {len(df_db)} registros reales de la base de datos para entrenar.")
                
                # Desempaquetar feature_vector (suponiendo formato JSON con las variables)
                # En un caso real más avanzado se hace un parsing del JSON
                # Para simplificar, si las características están en otras columnas o en el JSON,
                # adaptamos el DataFrame. Por ahora, extraemos de un JSON simple o devolvemos nulos:
                import json
                
                features_list = []
                for _, row in df_db.iterrows():
                    vec = row['feature_vector']
                    if isinstance(vec, str):
                        try:
                            vec = json.loads(vec)
                        except:
                            vec = {}
                    if not vec: vec = {}
                    
                    features_list.append({
                        'total_amount': float(row['total_amount']),
                        'high_risk_items_count': int(vec.get('high_risk_items_count', 0)),
                        'checkout_duration_seconds': float(vec.get('checkout_duration_seconds', 0.0)),
                        'is_new_shipping_address': int(vec.get('is_new_shipping_address', 0)),
                        'is_fraud': int(row['is_actual_fraud'])
                    })
                    
                return pd.DataFrame(features_list)
            else:
                print(f"⚠️ Solo se encontraron {len(df_db)} registros en la BD. Se necesitan al menos {MIN_SAMPLES_FOR_TRAINING}.")
                print("⏳ Usando dataset genérico de respaldo...")
        except Exception as e:
            print(f"⚠️ Error al consultar la BD ({e}). Usando respaldo...")
            
    # Intento 2: Respaldo (Descarga de CSV genérico)
    print(f"Descargando dataset genérico desde: {DATASET_URL}...")
    df_raw = pd.read_csv(DATASET_URL)
    print(f"Dataset descargado con forma: {df_raw.shape}")
    
    df_raw['C1'] = df_raw['C1'].fillna(0)
    df_raw['dist1'] = df_raw['dist1'].fillna(0)
    df_raw['TransactionAmt'] = df_raw['TransactionAmt'].fillna(df_raw['TransactionAmt'].median())
    df_raw['TransactionDT'] = df_raw['TransactionDT'].fillna(0)
    
    df = pd.DataFrame()
    df['total_amount'] = df_raw['TransactionAmt']
    df['high_risk_items_count'] = df_raw['C1'].astype(int)
    df['is_new_shipping_address'] = (df_raw['dist1'] > 50).astype(int)
    df['checkout_duration_seconds'] = (df_raw['TransactionDT'] % 120) + 10.0
    df['is_fraud'] = df_raw['isFraud']
    
    return df

def train_and_save_model():
    df = fetch_and_prepare_real_data()
    
    X = df.drop("is_fraud", axis=1)
    y = df["is_fraud"]
    
    print("Distribución de clases (1 = Fraude, 0 = Legítimo):")
    print(y.value_counts(normalize=True) * 100)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Iniciando búsqueda de hiperparámetros (GridSearchCV)...")
    base_model = LGBMClassifier(class_weight='balanced', random_state=42)
    
    param_grid = {
        'n_estimators': [50, 100, 150],
        'learning_rate': [0.01, 0.05, 0.1],
        'max_depth': [3, 5, 7]
    }
    
    grid = GridSearchCV(base_model, param_grid, cv=3, scoring='roc_auc', n_jobs=-1)
    grid.fit(X_train, y_train)
    
    print(f"Mejores parámetros encontrados: {grid.best_params_}")
    model = grid.best_estimator_
    
    # Evaluación
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(f"ROC AUC: {roc_auc_score(y_test, y_prob):.4f}")
    
    # Asegurar que el directorio exista
    services_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "services")
    os.makedirs(services_dir, exist_ok=True)
    
    model_path = os.path.join(services_dir, "fraud_model.joblib")
    print(f"Guardando modelo en: {model_path}")
    joblib.dump(model, model_path)
    print("¡Modelo guardado exitosamente!")

if __name__ == "__main__":
    train_and_save_model()

