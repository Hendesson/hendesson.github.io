#!/usr/bin/env bash
# Roda o projeto inteiro, na ordem: baixar dados -> preparar -> apurar -> priorizar -> views do Power BI.
# Uso: ./rodar_tudo.sh            (use PGDATABASE, BBOX etc. como no 00_baixar_dados.sh)
set -euo pipefail
cd "$(dirname "$0")"
BANCO="${PGDATABASE:-monitoramento_ambiental}"

# cria o banco se ele ainda não existir
psql -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname = '$BANCO'" | grep -q 1 || createdb "$BANCO"

./00_baixar_dados.sh
for f in 01_preparar_tabelas.sql 02_apuracao.sql 03_priorizacao.sql 04_views_powerbi.sql; do
    echo "== $f"
    psql -q -v ON_ERROR_STOP=1 -d "$BANCO" -f "$f"
done
