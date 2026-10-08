#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demonstração – Amazon DynamoDB
Computação de Alto Desempenho · UEPB · Vítor Raimundo Fernandes Gabínio

Rodar no AWS CloudShell:   python3 demo_dynamodb.py
Apagar a tabela no final:  python3 demo_dynamodb.py --apagar

O script:
  1. cria a tabela LeiturasSensores (modo on-demand);
  2. grava 2.000 leituras de sensores: parte em sequência, parte em paralelo;
  3. mede a latência de leituras (GetItem) – eventual x forte;
  4. compara Query (usa a chave) com Scan (lê a tabela inteira).
"""
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.config import Config

TABELA = "LeiturasSensores"
N_SENSORES = 20
LEITURAS_POR_SENSOR = 100   # 20 x 100 = 2.000 itens
N_SEQUENCIAL = 200          # itens gravados um a um
THREADS = 16                # threads da escrita paralela
N_LEITURAS = 300            # GetItems para medir latência

client = boto3.client("dynamodb", config=Config(
    max_pool_connections=THREADS * 2,
    retries={"max_attempts": 10, "mode": "adaptive"},
))
REGIAO = client.meta.region_name


def titulo(texto):
    print(f"\n{'=' * 64}\n  {texto}\n{'=' * 64}")


def criar_tabela():
    try:
        client.describe_table(TableName=TABELA)
        print(f"Tabela '{TABELA}' já existe em {REGIAO} – reaproveitando.")
        return
    except client.exceptions.ResourceNotFoundException:
        pass
    print(f"Criando tabela '{TABELA}' (on-demand) em {REGIAO}...")
    t0 = time.perf_counter()
    client.create_table(
        TableName=TABELA,
        KeySchema=[
            {"AttributeName": "sensor_id", "KeyType": "HASH"},   # partition key
            {"AttributeName": "ts", "KeyType": "RANGE"},         # sort key
        ],
        AttributeDefinitions=[
            {"AttributeName": "sensor_id", "AttributeType": "S"},
            {"AttributeName": "ts", "AttributeType": "N"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=TABELA)
    print(f"Tabela ACTIVE em {time.perf_counter() - t0:.1f} s")


def gerar_itens():
    base = 1_760_000_000_000  # timestamp fixo (ms) → rodar de novo sobrescreve, não duplica
    itens = []
    for s in range(N_SENSORES):
        for i in range(LEITURAS_POR_SENSOR):
            itens.append({
                "sensor_id": {"S": f"sensor-{s:02d}"},
                "ts": {"N": str(base + i * 1000)},
                "temperatura": {"N": f"{random.uniform(18, 40):.2f}"},
                "umidade": {"N": f"{random.uniform(20, 95):.1f}"},
            })
    random.shuffle(itens)
    return itens


def escrita_sequencial(itens):
    t0 = time.perf_counter()
    for item in itens:
        client.put_item(TableName=TABELA, Item=item)
    return time.perf_counter() - t0


def enviar_lote(lote):
    pedido = {TABELA: [{"PutRequest": {"Item": item}} for item in lote]}
    tentativas = 0
    while pedido:
        resposta = client.batch_write_item(RequestItems=pedido)
        pedido = resposta.get("UnprocessedItems") or {}
        if pedido:  # throttling: tenta de novo com espera exponencial
            tentativas += 1
            time.sleep(min(0.05 * 2 ** tentativas, 2))


def escrita_paralela(itens):
    lotes = [itens[i:i + 25] for i in range(0, len(itens), 25)]  # BatchWriteItem: até 25 itens
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        list(executor.map(enviar_lote, lotes))
    return time.perf_counter() - t0


def medir_latencia(chaves, forte):
    tempos = []
    for chave in chaves:
        t0 = time.perf_counter()
        client.get_item(TableName=TABELA, Key=chave, ConsistentRead=forte)
        tempos.append((time.perf_counter() - t0) * 1000)
    return tempos


def resumo(nome, tempos):
    q = statistics.quantiles(tempos, n=100)
    print(f"{nome:<20} média {statistics.mean(tempos):6.2f} ms | "
          f"p50 {q[49]:6.2f} | p90 {q[89]:6.2f} | p99 {q[98]:6.2f} ms")


def query_vs_scan(sensor):
    valores = {":s": {"S": sensor}}

    t0 = time.perf_counter()
    r = client.query(
        TableName=TABELA,
        KeyConditionExpression="sensor_id = :s",
        ExpressionAttributeValues=valores,
        ReturnConsumedCapacity="TOTAL",
    )
    tq = (time.perf_counter() - t0) * 1000
    print(f"QUERY  → retornou {r['Count']:4d} | leu {r['ScannedCount']:5d} itens | "
          f"{r['ConsumedCapacity']['CapacityUnits']:6.1f} RCU | {tq:7.1f} ms")

    t0 = time.perf_counter()
    retornados = lidos = 0
    capacidade = 0.0
    params = dict(TableName=TABELA, FilterExpression="sensor_id = :s",
                  ExpressionAttributeValues=valores, ReturnConsumedCapacity="TOTAL")
    while True:
        r = client.scan(**params)
        retornados += r["Count"]
        lidos += r["ScannedCount"]
        capacidade += r["ConsumedCapacity"]["CapacityUnits"]
        if "LastEvaluatedKey" not in r:
            break
        params["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    ts = (time.perf_counter() - t0) * 1000
    print(f"SCAN   → retornou {retornados:4d} | leu {lidos:5d} itens | "
          f"{capacidade:6.1f} RCU | {ts:7.1f} ms")


def apagar():
    print(f"Apagando a tabela '{TABELA}' em {REGIAO}...")
    try:
        client.delete_table(TableName=TABELA)
    except client.exceptions.ResourceNotFoundException:
        print("A tabela não existe. Nada a fazer.")
        return
    client.get_waiter("table_not_exists").wait(TableName=TABELA)
    print("Tabela apagada.")


def main():
    titulo(f"1) Criando a tabela  ·  região {REGIAO}")
    criar_tabela()

    itens = gerar_itens()
    titulo(f"2) Escrita de {len(itens)} itens: sequencial x paralela")
    seq, par = itens[:N_SEQUENCIAL], itens[N_SEQUENCIAL:]
    t_seq = escrita_sequencial(seq)
    t_par = escrita_paralela(par)
    v_seq, v_par = len(seq) / t_seq, len(par) / t_par
    print(f"Sequencial (PutItem, 1 por vez)     : {len(seq):5d} itens em {t_seq:5.2f} s → {v_seq:8.0f} itens/s")
    print(f"Paralela   ({THREADS} threads, lotes de 25): {len(par):5d} itens em {t_par:5.2f} s → {v_par:8.0f} itens/s")
    print(f"Ganho com paralelismo: {v_par / v_seq:.1f}x")

    titulo(f"3) Latência de {N_LEITURAS} leituras por chave (GetItem)")
    chaves = [{"sensor_id": it["sensor_id"], "ts": it["ts"]}
              for it in random.sample(itens, N_LEITURAS)]
    medir_latencia(chaves[:20], forte=False)  # aquecimento (abre conexões HTTPS)
    resumo("Leitura eventual", medir_latencia(chaves, forte=False))
    resumo("Leitura forte", medir_latencia(chaves, forte=True))

    titulo("4) Buscar as leituras de UM sensor: Query x Scan")
    query_vs_scan("sensor-07")

    titulo("Fim! Para apagar a tabela:  python3 demo_dynamodb.py --apagar")


if __name__ == "__main__":
    if "--apagar" in sys.argv:
        apagar()
    else:
        main()
