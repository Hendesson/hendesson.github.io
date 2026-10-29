#!/usr/bin/env bash
# Baixa os dados públicos usados nos artigos do Guia de dados espaciais
# e grava tudo num único GeoPackage (dados/artigos.gpkg), que abre no QGIS,
# no ArcGIS Pro, no Python (geopandas) e pode ser carregado no PostGIS.
#
# Requisitos: GDAL 3.6 ou mais novo (ogr2ogr) e curl.
# Uso:  bash baixar_dados_artigos.sh
#
# Recortes:
#   Amazônia: região de Novo Progresso/PA (o mesmo do curso)
#   Cerrado:  região da Chapada dos Veadeiros/GO (só no artigo do PRODES Cerrado)

set -euo pipefail

AMZ="-56.5 -8.5 -54.5 -5.5"
CER="-48.0 -14.5 -47.3 -13.8"
PASTA="${PASTA_DADOS:-./dados}"
GPKG="$PASTA/artigos.gpkg"
mkdir -p "$PASTA"

TB="https://terrabrasilis.dpi.inpe.br/geoserver"
OPC=(-f GPKG -nlt MULTIPOLYGON -lco GEOMETRY_NAME=geom)

echo "1/8 Unidades de Conservação (CNUC/MMA, agosto de 2025), sem as RPPNs (muito pequenas)"
CNUC_URL="https://dados.mma.gov.br/dataset/44b6dc8a-dc82-4a84-8d95-1b0da7c85dac/resource/6ba9a557-87e8-4882-acb7-b3e0f0ea192d/download/shp_cnuc_2025_08.zip"
[ -f "$PASTA/cnuc.zip" ] || curl -L --fail -sS -o "$PASTA/cnuc.zip" "$CNUC_URL"
for REGIAO in Amazonia Cerrado; do
  if [ "$REGIAO" = Amazonia ]; then B=$AMZ; MODO=(-overwrite -lco GEOMETRY_NAME=geom); else B=$CER; MODO=(-append); fi
  ogr2ogr -f GPKG -nlt MULTIPOLYGON "${MODO[@]}" "$GPKG" "/vsizip/$PASTA/cnuc.zip" -nln ucs -makevalid -spat $B \
    -dialect SQLite -sql "SELECT cd_cnuc AS cnuc, nome_uc, categoria, grupo, esfera, uf,
                                 '$REGIAO' AS regiao, geometry FROM cnuc_2025_08
                          WHERE categoria <> 'Reserva Particular do Patrimônio Natural'"
done

echo "2/8 Entorno de 3 km: faixa em volta de cada UC menos todas as UCs (em metros, EPSG:5880)"
ogr2ogr "${OPC[@]}" -update -overwrite "$GPKG" "$GPKG" -nln ucs_entorno -dialect SQLite -sql "
  SELECT u.cnuc, u.nome_uc, u.regiao,
         ST_Transform(ST_Difference(
             ST_Buffer(ST_Transform(u.geom, 5880), 3000, 32),
             (SELECT ST_Union(ST_Transform(v.geom, 5880)) FROM ucs v WHERE v.regiao = u.regiao)
         ), 4674) AS geom
  FROM ucs u"

echo "3/8 DETER Amazônia desde 2024 (INPE/TerraBrasilis, WFS)"
ogr2ogr "${OPC[@]}" -update -overwrite "$GPKG" "WFS:$TB/deter-amz/ows" deter-amz:deter_amz \
  -nln deter -spat $AMZ -where "view_date >= '2024-01-01'" \
  -select gid,classname,view_date,sensor,satellite,municipality,uf

echo "4/8 PRODES Amazônia desde 2019 (INPE/TerraBrasilis, WFS)"
ogr2ogr "${OPC[@]}" -update -overwrite "$GPKG" "WFS:$TB/prodes-legal-amz/ows" \
  prodes-legal-amz:yearly_deforestation -nln prodes_amz -spat $AMZ -where "year >= 2019" \
  -select uuid,state,main_class,class_name,year,area_km,image_date

echo "5/8 PRODES Cerrado desde 2019 (INPE/TerraBrasilis, WFS)"
ogr2ogr "${OPC[@]}" -update -overwrite "$GPKG" "WFS:$TB/prodes-cerrado-nb/ows" \
  prodes-cerrado-nb:yearly_deforestation -nln prodes_cerrado -spat $CER -where "year >= 2019" \
  -select uuid,state,main_class,class_name,year,area_km,image_date

echo "6/8 Áreas embargadas (IBAMA, WFS) - sem nome nem CPF/CNPJ"
ogr2ogr "${OPC[@]}" -update -overwrite "$GPKG" \
  "WFS:https://pamgia.ibama.gov.br/server/services/01_Publicacoes_Bases/adm_embargos_ibama_a/MapServer/WFSServer" \
  "adm_embargos_ibama_a:base.adm_embargos_ibama_a" -nln embargos -spat $AMZ \
  -select num_tad,origem_geom,uf,municipio,dat_embargo,qtd_area_embargada,des_tipo_bioma

echo "7/8 Imóveis do CAR no Pará (SICAR, WFS)"
ogr2ogr "${OPC[@]}" -update -overwrite "$GPKG" "WFS:https://geoserver.car.gov.br/geoserver/sicar/wfs" \
  sicar:sicar_imoveis_pa -nln car -spat $AMZ -makevalid \
  -select cod_imovel,status_imovel,condicao,tipo_imovel,area,m_fiscal,municipio

echo "8/8 Contorno da Amazônia Legal (INPE, WFS em GeoJSON)"
curl -s --fail -o "$PASTA/amazonia_legal.geojson" \
  "$TB/prodes-legal-amz/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=prodes-legal-amz:brazilian_legal_amazon&outputFormat=application/json"
ogr2ogr "${OPC[@]}" -update -overwrite "$GPKG" "$PASTA/amazonia_legal.geojson" -nln amazonia_legal

echo "Pronto: $GPKG"
for c in ucs ucs_entorno deter prodes_amz prodes_cerrado embargos car amazonia_legal; do
  printf "  %-15s %s feições\n" "$c" "$(ogrinfo -so "$GPKG" $c | sed -n 's/Feature Count: //p')"
done
