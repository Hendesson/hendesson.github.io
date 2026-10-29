#!/usr/bin/env bash
# Baixa os dados públicos direto das fontes oficiais e carrega no PostgreSQL/PostGIS.
#
# Requisitos: GDAL (ogr2ogr), curl, unzip e um banco com PostGIS.
# Uso:
#   ./00_baixar_dados.sh                  # recorte de exemplo (região de Novo Progresso/PA)
#   BBOX="-74 -18.1 -43.9 5.3" ./00_baixar_dados.sh   # Amazônia Legal inteira (demora!)
#
# Conexão: usa as variáveis padrão do PostgreSQL (PGHOST, PGPORT, PGUSER, PGPASSWORD)
# e o banco em PGDATABASE (padrão: monitoramento_ambiental).

set -euo pipefail

BANCO="${PGDATABASE:-monitoramento_ambiental}"
PG="PG:dbname=${BANCO}"

# Área de interesse: xmin ymin xmax ymax (graus, SIRGAS 2000)
BBOX="${BBOX:--56.5 -8.5 -54.5 -5.5}"

# Período
DETER_DESDE="${DETER_DESDE:-2023-01-01}"
PRODES_DESDE="${PRODES_DESDE:-2019}"

PASTA="${PASTA_DADOS:-./dados}"
mkdir -p "$PASTA"

# Opções comuns do ogr2ogr:
#   -nlt MULTIPOLYGON   converte MultiSurface/Polygon em MultiPolygon
#   -lco GEOMETRY_NAME  nome da coluna de geometria
#   -spat               recorta pela área de interesse (o filtro é feito no servidor)
OPC=(-overwrite -nlt MULTIPOLYGON -lco GEOMETRY_NAME=geom -lco SCHEMA=bruto -spat $BBOX)

psql -d "$BANCO" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE SCHEMA IF NOT EXISTS bruto;"

echo "1/4 Unidades de Conservação (CNUC/MMA, agosto de 2025)"
CNUC_URL="https://dados.mma.gov.br/dataset/44b6dc8a-dc82-4a84-8d95-1b0da7c85dac/resource/6ba9a557-87e8-4882-acb7-b3e0f0ea192d/download/shp_cnuc_2025_08.zip"
[ -f "$PASTA/cnuc.zip" ] || curl -L --fail -o "$PASTA/cnuc.zip" "$CNUC_URL"
ogr2ogr -f PostgreSQL "$PG" "/vsizip/$PASTA/cnuc.zip" cnuc_2025_08 \
    -nln cnuc "${OPC[@]}" -makevalid

echo "2/4 DETER Amazônia (INPE/TerraBrasilis, WFS)"
ogr2ogr -f PostgreSQL "$PG" "WFS:https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/ows" \
    deter-amz:deter_amz -nln deter "${OPC[@]}" \
    -where "view_date >= '${DETER_DESDE}'"

echo "3/4 PRODES Amazônia Legal, desmatamento anual (INPE/TerraBrasilis, WFS)"
ogr2ogr -f PostgreSQL "$PG" "WFS:https://terrabrasilis.dpi.inpe.br/geoserver/prodes-legal-amz/ows" \
    prodes-legal-amz:yearly_deforestation -nln prodes "${OPC[@]}" \
    -where "year >= ${PRODES_DESDE}"

echo "4/4 Áreas embargadas (IBAMA, WFS)"
ogr2ogr -f PostgreSQL "$PG" "WFS:https://pamgia.ibama.gov.br/server/services/01_Publicacoes_Bases/adm_embargos_ibama_a/MapServer/WFSServer" \
    "adm_embargos_ibama_a:base.adm_embargos_ibama_a" -nln embargos_ibama "${OPC[@]}"

echo "Pronto. Contagem por tabela:"
psql -d "$BANCO" -c "
SELECT 'cnuc' AS tabela, count(*) FROM bruto.cnuc
UNION ALL SELECT 'deter', count(*) FROM bruto.deter
UNION ALL SELECT 'prodes', count(*) FROM bruto.prodes
UNION ALL SELECT 'embargos_ibama', count(*) FROM bruto.embargos_ibama;"
