"""
PayTrack Colombia — Generador de datos sintéticos
Genera transacciones, comercios, clientes y eventos de fraude.

Uso:
    python labs/shared/generate_data.py --transactions 10000 --output data/
    python labs/shared/generate_data.py --transactions 10000 --dirty-rate 0.02  # con errores

Lotes incrementales (Lab 2): el segundo lote reutiliza los clientes del primero,
trae transacciones nuevas, contracargos de transacciones anteriores y cambios de clientes:
    python labs/shared/generate_data.py --start-date 2026-08-01 --days 60 --output data/batch1
    python labs/shared/generate_data.py --start-date 2026-09-30 --days 1 --transactions 2000 \
        --from-batch data/batch1 --id-prefix B2 --output data/batch2
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker
from faker.providers import bank, company

fake = Faker("es_CO")
fake.add_provider(bank)
fake.add_provider(company)

# ── Catálogos ──────────────────────────────────────────────────────────────────

MERCHANTS = [
    {"id": "M001", "name": "Éxito Laureles", "category": "retail", "city": "Medellín"},
    {"id": "M002", "name": "Rappi Colombia", "category": "delivery", "city": "Bogotá"},
    {"id": "M003", "name": "Claro Tienda", "category": "telco", "city": "Medellín"},
    {"id": "M004", "name": "Copa Airlines", "category": "travel", "city": "Bogotá"},
    {"id": "M005", "name": "Netflix CO", "category": "streaming", "city": "Online"},
    {"id": "M006", "name": "Falabella CO", "category": "retail", "city": "Cali"},
    {"id": "M007", "name": "TuBodega.com", "category": "grocery", "city": "Medellín"},
    {"id": "M008", "name": "Uber CO", "category": "transport", "city": "Bogotá"},
]

PAYMENT_METHODS = ["credit_card", "debit_card", "nequi", "daviplata", "pse"]

FRAUD_PATTERNS = [
    "amount_spike",      # monto inusualmente alto
    "rapid_sequence",    # muchas transacciones en segundos
    "foreign_merchant",  # comercio fuera del historial
    "odd_hours",         # transacción a las 3am
]


def generate_customers(n: int = 500) -> list[dict]:
    customers = []
    for i in range(n):
        customers.append({
            "customer_id": f"C{i+1:06d}",
            "name": fake.name(),
            "email": fake.unique.email(),  # email es UNIQUE en el OLTP
            "city": random.choice(["Medellín", "Bogotá", "Cali", "Barranquilla"]),
            "segment": random.choice(["mass", "mass", "mass", "premium", "high_value"]),
            "monthly_income_cop": random.randint(1_500_000, 15_000_000),
            "created_at": fake.date_time_between(
                start_date="-3y", end_date="-180d"  # ojo: en Faker "m" son minutos
            ).isoformat(),
        })
    return customers


def generate_transactions(
    customers: list[dict],
    n: int = 10_000,
    fraud_rate: float = 0.004,  # 0.4% fraude
    start_date: datetime | None = None,
    days: int = 90,
    id_prefix: str = "",
) -> tuple[list[dict], list[dict]]:
    if start_date is None:
        start_date = datetime.now() - timedelta(days=days)

    transactions = []
    fraud_events = []

    for i in range(n):
        customer = random.choice(customers)
        merchant = random.choice(MERCHANTS)
        ts = start_date + timedelta(
            seconds=random.randint(0, days * 24 * 3600 - 1)
        )
        amount = round(random.lognormvariate(10.5, 1.2), 2)  # distribución realista
        is_fraud = random.random() < fraud_rate

        txn = {
            "transaction_id": f"TXN{id_prefix}{i+1:010d}",
            "customer_id": customer["customer_id"],
            "merchant_id": merchant["id"],
            "merchant_name": merchant["name"],
            "merchant_category": merchant["category"],
            "amount_cop": amount,
            "payment_method": random.choice(PAYMENT_METHODS),
            "status": "declined" if is_fraud and random.random() < 0.3 else "approved",
            "is_fraud": is_fraud,
            "timestamp": ts.isoformat(),
            "city": merchant["city"],
        }
        transactions.append(txn)

        if is_fraud:
            fraud_events.append({
                "event_id": f"FRD{id_prefix}{len(fraud_events)+1:08d}",
                "transaction_id": txn["transaction_id"],
                "pattern": random.choice(FRAUD_PATTERNS),
                "risk_score": round(random.uniform(0.7, 1.0), 4),
                "detected_at": (ts + timedelta(seconds=random.randint(1, 300))).isoformat(),
            })

    return transactions, fraud_events


def inject_dirty_data(transactions: list[dict], rate: float) -> list[dict]:
    """Simula los problemas típicos de una fuente real: duplicados por reintentos,
    montos inválidos, llaves faltantes y tipos inconsistentes."""
    n = int(len(transactions) * rate)
    dirty = [dict(t) for t in transactions]

    # Reenvíos: la misma transacción llega dos veces
    dirty += [dict(t) for t in random.sample(transactions, n)]

    victims = random.sample(range(len(dirty)), n * 4)
    for i in victims[:n]:
        dirty[i]["amount_cop"] = random.choice([0, -abs(dirty[i]["amount_cop"])])
    for i in victims[n:2 * n]:
        dirty[i]["amount_cop"] = round(random.uniform(1e8, 1e9), 2)  # fuera de rango
    for i in victims[2 * n:3 * n]:
        dirty[i]["customer_id"] = None
    for i in victims[3 * n:]:
        dirty[i]["amount_cop"] = str(dirty[i]["amount_cop"])  # número como texto

    random.shuffle(dirty)
    return dirty


def change_customers(customers: list[dict], rate: float = 0.05) -> list[dict]:
    """Algunos clientes se mudan de ciudad o cambian de segmento entre lotes."""
    changed = [dict(c) for c in customers]
    for c in random.sample(changed, int(len(changed) * rate)):
        if random.random() < 0.5:
            c["city"] = random.choice([x for x in ["Medellín", "Bogotá", "Cali", "Barranquilla"] if x != c["city"]])
        else:
            c["segment"] = random.choice([x for x in ["mass", "premium", "high_value"] if x != c["segment"]])
    return changed


def chargebacks(previous: list[dict], rate: float = 0.01) -> list[dict]:
    """Reenvía transacciones aprobadas de un lote anterior con estado 'chargeback'."""
    valid = [t for t in previous if t["status"] == "approved" and t["customer_id"]
             and isinstance(t["amount_cop"], (int, float)) and 0 < t["amount_cop"] < 1e8]
    unique = list({t["transaction_id"]: t for t in valid}.values())
    return [{**t, "status": "chargeback"} for t in random.sample(unique, int(len(unique) * rate))]


def main():
    parser = argparse.ArgumentParser(description="Generador de datos PayTrack")
    parser.add_argument("--transactions", type=int, default=10_000)
    parser.add_argument("--customers", type=int, default=500)
    parser.add_argument("--output", default="data")
    parser.add_argument(
        "--dirty-rate", type=float, default=0.0,
        help="fracción de registros con problemas de calidad (ej. 0.02)",
    )
    parser.add_argument("--start-date", help="YYYY-MM-DD (por defecto: hace --days días)")
    parser.add_argument("--days", type=int, default=90, help="días que cubren las transacciones")
    parser.add_argument("--from-batch", type=Path, help="lote anterior: reutiliza clientes y genera contracargos")
    parser.add_argument("--id-prefix", default="", help="prefijo para que los IDs no choquen entre lotes")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    if args.from_batch:
        print(f"Reutilizando clientes de {args.from_batch} (con cambios de ciudad/segmento)...")
        customers = change_customers(json.loads((args.from_batch / "customers.json").read_text()))
    else:
        print(f"Generando {args.customers} clientes...")
        customers = generate_customers(args.customers)

    print(f"Generando {args.transactions} transacciones...")
    start = datetime.fromisoformat(args.start_date) if args.start_date else None
    transactions, fraud_events = generate_transactions(
        customers, args.transactions, start_date=start, days=args.days, id_prefix=args.id_prefix
    )
    if args.dirty_rate:
        print(f"Inyectando errores de calidad ({args.dirty_rate:.0%})...")
        transactions = inject_dirty_data(transactions, args.dirty_rate)
    if args.from_batch:
        updates = chargebacks(json.loads((args.from_batch / "transactions.json").read_text()))
        print(f"Agregando {len(updates)} contracargos de transacciones del lote anterior...")
        transactions += updates

    # Guardar
    for name, data in [
        ("customers", customers),
        ("merchants", MERCHANTS),
        ("transactions", transactions),
        ("fraud_events", fraud_events),
    ]:
        path = output / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"  ✓ {path} ({len(data)} registros)")

    print("\n¡Listo! Datos generados en:", output)


if __name__ == "__main__":
    main()
