"""
ML — Predicción de Ventas 2026 para CasaMarket
================================================
Lee ventas reales desde PostgreSQL, entrena un modelo de regresión lineal
por producto y proyecta ingresos mensuales para todo 2026.
Guarda predicciones en la tabla `predicciones_2026`.

Ejecutar:
    docker compose exec jupyter-spark python /home/jovyan/ml/prediccion_ventas.py
"""
import logging
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PG_URL = "postgresql://casamarket:casamarket@postgres:5432/casamarket"
MIN_MESES = 1       # mínimo de meses históricos para entrenar
TOP_N     = 15      # productos top a proyectar
MESES_2026 = pd.date_range("2026-01-01", "2026-12-01", freq="MS")


def load_ventas(engine) -> pd.DataFrame:
    sql = """
        SELECT
            DATE_TRUNC('month', fecha)::DATE AS mes,
            TRIM(producto) AS producto,
            COUNT(*) AS transacciones,
            SUM(cantidad) AS unidades,
            ROUND(SUM(total)::NUMERIC, 2) AS ingresos
        FROM ventas
        WHERE total > 0 AND fecha IS NOT NULL AND producto IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    df = pd.read_sql(sql, engine)
    df["mes"] = pd.to_datetime(df["mes"])
    return df


def top_productos(df: pd.DataFrame, n: int) -> list[str]:
    return (
        df.groupby("producto")["ingresos"]
        .sum()
        .nlargest(n)
        .index.tolist()
    )


def mes_a_numero(fechas: pd.Series) -> np.ndarray:
    """Convierte fechas a número ordinal relativo al mínimo."""
    epoch = fechas.min()
    return ((fechas.dt.year - epoch.year) * 12 + (fechas.dt.month - epoch.month)).values.reshape(-1, 1)


def predecir_producto(hist: pd.DataFrame, meses_pred: pd.DatetimeIndex):
    """Entrena LinearRegression y devuelve (df_pred, r2)."""
    hist = hist.sort_values("mes")
    X = mes_a_numero(hist["mes"])
    y = hist["ingresos"].values

    if len(X) < 2:
        # Con 1 solo punto usamos el promedio como constante
        media = float(y.mean())
        pred_vals = [media] * len(meses_pred)
        r2 = float("nan")
    else:
        model = LinearRegression()
        model.fit(X, y)
        y_hat = model.predict(X)
        r2 = r2_score(y, y_hat)

        epoch = hist["mes"].min()
        X_fut = np.array([
            (m.year - epoch.year) * 12 + (m.month - epoch.month)
            for m in meses_pred
        ]).reshape(-1, 1)
        pred_vals = model.predict(X_fut).tolist()

    # No predecimos ingresos negativos
    pred_vals = [max(0, v) for v in pred_vals]

    df_pred = pd.DataFrame({
        "mes": meses_pred,
        "ingresos_pred": pred_vals,
        "r2_score": round(r2, 4) if not (isinstance(r2, float) and np.isnan(r2)) else None,
    })
    return df_pred, r2


def main():
    engine = create_engine(PG_URL)

    log.info("Leyendo ventas históricas desde PostgreSQL...")
    df = load_ventas(engine)
    if df.empty:
        log.error("Sin datos en la tabla ventas. Abortando.")
        return

    log.info("Periodo histórico: %s → %s  |  %d filas de datos",
             df["mes"].min().date(), df["mes"].max().date(), len(df))

    productos = top_productos(df, TOP_N)
    log.info("Top %d productos a proyectar: %s", TOP_N, productos[:5])

    registros = []
    for prod in productos:
        hist = df[df["producto"] == prod].copy()
        df_pred, r2 = predecir_producto(hist, MESES_2026)
        df_pred["producto"] = prod
        df_pred["modelo"] = "LinearRegression"

        # Unir ingresos reales donde existan
        reales = hist.set_index("mes")["ingresos"].to_dict()
        df_pred["ingresos_real"] = df_pred["mes"].map(reales)
        df_pred["unidades_pred"] = df_pred["ingresos_pred"] / (
            hist["ingresos"].sum() / hist["unidades"].sum()
            if hist["unidades"].sum() > 0 else 1
        )
        registros.append(df_pred)
        log.info("  [OK] %-35s  R²=%.3f  pred_dic=S/%.0f",
                 prod[:35], r2 if not np.isnan(r2) else 0,
                 df_pred[df_pred["mes"].dt.month == 12]["ingresos_pred"].values[0])

    resultado = pd.concat(registros, ignore_index=True)

    log.info("Guardando %d predicciones en PostgreSQL...", len(resultado))
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE predicciones_2026 RESTART IDENTITY"))

    resultado.to_sql(
        "predicciones_2026", engine,
        if_exists="append", index=False,
        dtype=None,
    )

    log.info("✓ Predicciones guardadas. Resumen:")
    resumen = resultado.groupby("producto")["ingresos_pred"].sum().nlargest(5)
    for prod, total in resumen.items():
        log.info("  %-35s  S/ %,.0f proyectados en 2026", prod[:35], total)

    log.info("¡Listo! Abre Grafana → Dashboard Ventas para ver las predicciones.")


if __name__ == "__main__":
    main()
