# Sincronizacion MySQL — Debezium CDC

El sistema implementa **Change Data Capture (CDC)** para replicar en tiempo real los datos de PostgreSQL hacia una instancia MySQL de Laragon en el host Windows.

---

## Diagrama de Flujo CDC

```mermaid
flowchart LR
    subgraph DOCKER["Docker — ec-kafka-dev-net"]
        PG["PostgreSQL 16\nwal_level=logical\npublication: debezium_ventas_pub\nslot: debezium_ventas_slot"]
        KC["kafka-connect\nDebezium 2.7\n:8083"]
        K["Apache Kafka\nTopic:\ncasamarket.public.ventas"]
        MS["mysql-sync.py\nConsumer group:\ndebezium-consumer"]
    end

    subgraph HOST["Host Windows"]
        MY["MySQL Laragon\nhost.docker.internal:3306\nDB: casamarket_mysql\nTabla: ventas_ifersan"]
    end

    PG -->|"WAL changes\npgoutput plugin"| KC
    KC -->|"eventos CDC\nschema + payload"| K
    K -->|"poll()"| MS
    MS -->|"INSERT/UPDATE\nvia PyMySQL"| MY

    style DOCKER fill:#F9FBE7,stroke:#827717
    style HOST fill:#E3F2FD,stroke:#1565C0
```

---

## Componente: registrar_conector.py

**Archivo:** `mysql_sync/registrar_conector.py` — 68 lineas  
**Proposito:** Registra el conector Debezium via REST API en Kafka Connect

### Proceso de registro

```mermaid
flowchart TD
    START([Inicio]) --> WAIT["Espera a Kafka Connect\nGET http://localhost:8083/connectors\nmax 20 intentos | delay 10s"]
    WAIT -->|"OK"| CHECK{"Conector ya\nexiste?"}
    CHECK -->|"Si"| DELETE["DELETE /connectors/ventas-pg-connector"]
    DELETE --> REGISTER
    CHECK -->|"No"| REGISTER["POST /connectors\npayload JSON con config"]
    REGISTER --> LOG["log: conector registrado"]
    LOG --> END([Fin])

    style START fill:#E8F5E9,stroke:#2E7D32
    style END fill:#E8F5E9,stroke:#2E7D32
```

### Payload de registro

```json
{
  "name": "ventas-pg-connector",
  "config": {
    "connector.class":           "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname":         "postgres",
    "database.port":             "5432",
    "database.user":             "casamarket",
    "database.password":         "casamarket",
    "database.dbname":           "casamarket",
    "topic.prefix":              "casamarket",
    "table.include.list":        "public.ventas",
    "plugin.name":               "pgoutput",
    "publication.name":          "debezium_ventas_pub",
    "slot.name":                 "debezium_ventas_slot",
    "snapshot.mode":             "initial",
    "snapshot.include.collection.list": "public.ventas",
    "heartbeat.interval.ms":     "10000",
    "decimal.handling.mode":     "double",
    "time.precision.mode":       "connect"
  }
}
```

---

## Componente: mysql_sync.py

**Archivo:** `mysql_sync/mysql_sync.py`  
**Topic de entrada:** `casamarket.public.ventas`  
**Consumer group:** `debezium-consumer`

### Configuracion

| Variable | Valor | Descripcion |
|---------|-------|-------------|
| `KAFKA_BOOTSTRAP` | `ec-kafka:9092` | Broker interno Docker |
| `MYSQL_HOST` | `host.docker.internal` | MySQL Laragon en host |
| `MYSQL_PORT` | `3306` | Puerto MySQL estandar |
| `MYSQL_DB` | `casamarket_mysql` | Base de datos destino |
| `MYSQL_USER` | `root` | Usuario MySQL |
| `MYSQL_PASSWORD` | `""` (vacio) | Sin password (Laragon default) |

### extra_hosts en docker-compose

```yaml
mysql-sync:
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

Esta linea permite que el contenedor Docker resuelva `host.docker.internal` hacia la IP gateway del host, necesario para alcanzar MySQL Laragon en Windows.

---

## Tabla Destino en MySQL

```sql
-- Base de datos: casamarket_mysql
CREATE TABLE IF NOT EXISTS ventas_ifersan (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    fecha           DATE,
    producto        VARCHAR(500),
    cod_producto    VARCHAR(200),
    marca           VARCHAR(200),
    categoria       VARCHAR(200),
    subcategoria    VARCHAR(200),
    cantidad        DOUBLE,
    precio_unitario DOUBLE,
    total           DOUBLE,
    cliente         VARCHAR(500),
    ruc_cliente     VARCHAR(100),
    vendedor        VARCHAR(200),
    razon_social    VARCHAR(200),
    zona            VARCHAR(200),
    procesado_ts    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Kafka Connect REST API

| Endpoint | Metodo | Descripcion |
|---------|--------|-------------|
| `/connectors` | GET | Lista conectores activos |
| `/connectors` | POST | Registra nuevo conector |
| `/connectors/{name}` | GET | Estado del conector |
| `/connectors/{name}` | DELETE | Elimina conector |
| `/connectors/{name}/status` | GET | Detalle de tareas |
| `/connectors/{name}/restart` | POST | Reinicia conector |

```bash
# Verificar estado del conector
curl http://localhost:8083/connectors/ventas-pg-connector/status

# Ver conectores activos
curl http://localhost:8083/connectors
```
