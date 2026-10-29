#!/usr/bin/env bash
# Exporta as views do schema "powerbi" para CSV (UTF-8, separador vírgula).
# Use quando o Power BI estiver em outro computador ou quando o relatório publicado
# não puder acessar o banco (o Power BI lê os CSVs com "Obter dados > Texto/CSV").
set -euo pipefail
BANCO="${PGDATABASE:-monitoramento_ambiental}"
SAIDA="${1:-./csv_powerbi}"
mkdir -p "$SAIDA"

for v in dim_ucs dim_calendario fato_deter fato_prodes fato_embargos; do
    echo "exportando powerbi.$v"
    psql -d "$BANCO" -c "\copy (SELECT * FROM powerbi.$v) TO '$SAIDA/$v.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
done
ls -lh "$SAIDA"
