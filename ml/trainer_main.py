"""
ml/trainer_main.py
==================
Orquestador principal del servicio ml-trainer.
Ejecuta todos los modelos ML cada 30 minutos en orden:

  1. trainer.py          — GradientBoosting por producto (ingresos + unidades, 30 dias)
  2. trainer_vendedor.py — GradientBoosting por vendedor (ingresos semanales, 8 semanas)
  3. trainer_anomalias.py — IsolationForest por producto (anomalias ultimos 7 dias)
  4. trainer_clientes.py — KMeans RFM (segmentos VIP / Regular / En Riesgo)

Ciclo:
  [arranque] → esperar PostgreSQL → ejecutar todos los modelos → dormir 30min → repetir

Variables de entorno:
  DATABASE_URL (opcional, sobreescribe la URL por defecto si se usa en otros contextos)
"""
import logging
import time
from datetime import datetime

import sqlalchemy as sa

# Importar los modulos de cada trainer
from trainer import (
    esperar_postgres, ciclo_entrenamiento, get_engine,
    RETRAIN_INTERVAL,
)
import trainer_vendedor
import trainer_anomalias
import trainer_clientes
import trainer_forecast

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def main() -> None:
    log.info("=" * 70)
    log.info("  CasaMarket — ML Trainer Service")
    log.info("  Modelos: GBM Quantile | GBM Vendedores | IsolationForest | KMeans RFM")
    log.info("  Forecast: Mensual P10/P90 | predicciones_mes_siguiente")
    log.info("  Ciclo  : cada %d min", RETRAIN_INTERVAL // 60)
    log.info("=" * 70)

    # Esperar a PostgreSQL
    engine = esperar_postgres()

    ciclo = 0
    while True:
        ciclo += 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log.info("\n>>> CICLO %d — %s <<<\n", ciclo, ts)

        # ── 1. Productos: GradientBoosting diario (el mas importante) ──────────
        try:
            ciclo_entrenamiento(engine)
        except Exception as exc:
            log.error("[TRAINER-PRODUCTOS] Error: %s", exc)

        # ── 2. Vendedores: GradientBoosting semanal ────────────────────────────
        try:
            trainer_vendedor.ejecutar(engine)
        except Exception as exc:
            log.error("[TRAINER-VENDEDOR] Error: %s", exc)

        # ── 3. Anomalias: IsolationForest ──────────────────────────────────────
        try:
            trainer_anomalias.ejecutar(engine)
        except Exception as exc:
            log.error("[TRAINER-ANOMALIAS] Error: %s", exc)

        # ── 4. Clientes: KMeans RFM ────────────────────────────────────────────
        try:
            trainer_clientes.ejecutar(engine)
        except Exception as exc:
            log.error("[TRAINER-CLIENTES] Error: %s", exc)

        # ── 5. Forecast mensual: agrega predicciones_diarias → mes siguiente ───
        try:
            trainer_forecast.ejecutar(engine)
        except Exception as exc:
            log.error("[TRAINER-FORECAST] Error: %s", exc)

        log.info("[CICLO %d] Completado. Proximo en %d min.", ciclo, RETRAIN_INTERVAL // 60)
        time.sleep(RETRAIN_INTERVAL)


if __name__ == "__main__":
    main()
