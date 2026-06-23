"""
Registra el conector Debezium PostgreSQL via REST API.
Ejecutar UNA VEZ después de que kafka-connect esté Up:
    python mysql_sync/registrar_conector.py
"""
import json
import time
import requests

CONNECT_URL = "http://localhost:8083"

conector = {
    "name": "pg-ventas-debezium",
    "config": {
        "connector.class":               "io.debezium.connector.postgresql.PostgresConnector",
        "database.hostname":             "postgres",
        "database.port":                 "5432",
        "database.user":                 "casamarket",
        "database.password":             "casamarket",
        "database.dbname":               "casamarket",
        "topic.prefix":                  "casamarket",
        "table.include.list":            "public.ventas",
        "plugin.name":                   "pgoutput",
        "slot.name":                     "debezium_ventas_slot",
        "publication.name":              "debezium_ventas_pub",
        "publication.autocreate.mode":   "filtered",
        "snapshot.mode":                 "initial",
        "heartbeat.interval.ms":         "10000",
        "decimal.handling.mode":         "double",
        "time.precision.mode":           "connect",
    }
}

print("Esperando que Kafka Connect este listo...")
for i in range(20):
    try:
        r = requests.get(f"{CONNECT_URL}/connectors", timeout=5)
        if r.status_code == 200:
            print("Kafka Connect OK")
            break
    except Exception:
        pass
    print(f"  reintento {i+1}/20...")
    time.sleep(5)

# Eliminar conector si ya existe
r = requests.get(f"{CONNECT_URL}/connectors/pg-ventas-debezium")
if r.status_code == 200:
    requests.delete(f"{CONNECT_URL}/connectors/pg-ventas-debezium")
    print("Conector anterior eliminado.")
    time.sleep(2)

# Registrar conector
r = requests.post(
    f"{CONNECT_URL}/connectors",
    headers={"Content-Type": "application/json"},
    data=json.dumps(conector),
    timeout=15,
)

if r.status_code in (200, 201):
    print("\nConector registrado exitosamente!")
    print(f"Topic generado: casamarket.public.ventas")
    print(f"Verificar en: {CONNECT_URL}/connectors/pg-ventas-debezium/status")
else:
    print(f"\nError al registrar: {r.status_code}")
    print(r.text)
