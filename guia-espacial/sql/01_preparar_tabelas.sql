/* =====================================================================================
   01_preparar_tabelas.sql
   Transforma os dados brutos (schema "bruto", carregado pelo 00_baixar_dados.sh)
   em tabelas limpas e padronizadas para as análises.

   Schemas criados:
     limites       -> Unidades de Conservação e entorno
     desmatamento  -> alertas DETER e PRODES cruzados com as UCs
     fiscalizacao  -> áreas embargadas
   Rodar com:  psql -d monitoramento_ambiental -f 01_preparar_tabelas.sql
   ===================================================================================== */

SET client_min_messages = warning;   -- esconde os avisos de geometria inválida

CREATE SCHEMA IF NOT EXISTS limites;
CREATE SCHEMA IF NOT EXISTS desmatamento;
CREATE SCHEMA IF NOT EXISTS fiscalizacao;


/* ---------- 1. Unidades de Conservação ---------------------------------------------- */
DROP TABLE IF EXISTS limites.ucs CASCADE;
CREATE TABLE limites.ucs AS
SELECT cd_cnuc                                            AS cnuc,
       nome_uc,
       categoria,
       grupo,                                             -- 'Proteção Integral' ou 'Uso Sustentável'
       esfera,                                            -- Federal, Estadual, Municipal
       uf,
       ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))::geometry(MultiPolygon, 4674) AS geom
FROM bruto.cnuc;

ALTER TABLE limites.ucs ADD PRIMARY KEY (cnuc);
ALTER TABLE limites.ucs ADD COLUMN area_ha numeric;
UPDATE limites.ucs SET area_ha = round((ST_Area(geom::geography) / 10000)::numeric, 2);
CREATE INDEX ON limites.ucs USING gist (geom);


/* ---------- 2. Entorno: faixa de 3 km em volta de cada UC (sem o interior) ----------
   3 km é uma escolha deste tutorial. Ajuste se quiser outra largura. */
DROP TABLE IF EXISTS limites.ucs_entorno CASCADE;
CREATE TABLE limites.ucs_entorno AS
SELECT cnuc,
       nome_uc,
       ST_Multi(ST_CollectionExtract(ST_MakeValid(
           ST_Difference(ST_Buffer(geom::geography, 3000)::geometry, geom)
       ), 3))::geometry(MultiPolygon, 4674) AS geom
FROM limites.ucs;

CREATE INDEX ON limites.ucs_entorno USING gist (geom);


/* ---------- 3. Embargos (IBAMA) ------------------------------------------------------
   Os dados públicos do IBAMA trazem nome e CPF/CNPJ do embargado.
   Esses campos NÃO são copiados: não são necessários para a análise e
   não devem ir para um painel público (LGPD). */
DROP TABLE IF EXISTS fiscalizacao.embargos CASCADE;
CREATE TABLE fiscalizacao.embargos AS
SELECT objectid                                             AS id_embargo,
       concat(num_tad, '-', serie_tad)                      AS num_embargo,
       concat(num_auto_infracao, '-', serie_auto_infracao)  AS num_auto,
       dat_embargo::date                                    AS data,
       origem_geom,                                         -- 'Polígono' ou 'Ponto' (só uma coordenada: círculo de ~1 m de raio)
       uf,
       municipio,
       qtd_area_embargada                                   AS area_embargada_ha,
       ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))::geometry(MultiPolygon, 4674) AS geom
FROM bruto.embargos_ibama
WHERE geom IS NOT NULL;

ALTER TABLE fiscalizacao.embargos ADD PRIMARY KEY (id_embargo);
CREATE INDEX ON fiscalizacao.embargos USING gist (geom);


/* ---------- 4. DETER: uma linha por alerta ------------------------------------------
   No WFS um mesmo alerta (gid) pode vir dividido em pedaços. Aqui juntamos os pedaços. */
DROP TABLE IF EXISTS desmatamento.deter_alertas CASCADE;
CREATE TABLE desmatamento.deter_alertas AS
SELECT gid                AS id_alerta,
       min(classname)     AS classname,
       min(view_date)     AS data,
       min(uf)            AS uf,
       min(municipality)  AS municipio,
       ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Union(ST_MakeValid(geom))), 3))::geometry(MultiPolygon, 4674) AS geom
FROM bruto.deter
GROUP BY gid;

ALTER TABLE desmatamento.deter_alertas ADD PRIMARY KEY (id_alerta);
CREATE INDEX ON desmatamento.deter_alertas USING gist (geom);


/* ---------- 5. DETER nas UCs ----------------------------------------------------------
   Cada alerta recebe:
     local = 'Interior' -> encosta numa UC; a geometria é recortada pela UC
     local = 'Entorno'  -> fora das UCs, mas a até 3 km de uma
   Se o alerta encostar em mais de uma UC (UCs sobrepostas), fica com a de maior sobreposição. */
DROP TABLE IF EXISTS desmatamento.deter_ucs CASCADE;
CREATE TABLE desmatamento.deter_ucs AS
WITH interior AS (
    SELECT DISTINCT ON (a.id_alerta)
           a.id_alerta, u.cnuc, u.nome_uc, 'Interior'::text AS local,
           ST_Multi(ST_CollectionExtract(ST_Intersection(a.geom, u.geom), 3)) AS geom
    FROM desmatamento.deter_alertas a
    JOIN limites.ucs u ON ST_Intersects(a.geom, u.geom)
    ORDER BY a.id_alerta, ST_Area(ST_Intersection(a.geom, u.geom)) DESC
),
entorno AS (
    SELECT DISTINCT ON (a.id_alerta)
           a.id_alerta, e.cnuc, e.nome_uc, 'Entorno'::text AS local, a.geom
    FROM desmatamento.deter_alertas a
    JOIN limites.ucs_entorno e ON ST_Intersects(a.geom, e.geom)
    WHERE a.id_alerta NOT IN (SELECT id_alerta FROM interior)
    ORDER BY a.id_alerta, ST_Area(ST_Intersection(a.geom, e.geom)) DESC
),
juntos AS (
    SELECT * FROM interior
    UNION ALL
    SELECT * FROM entorno
)
SELECT j.id_alerta,
       a.classname,
       a.data,
       extract(year FROM a.data)::int                                   AS ano,
       -- o "ano PRODES" vai de 1º de agosto a 31 de julho
       (extract(year FROM a.data) + CASE WHEN extract(month FROM a.data) >= 8 THEN 1 ELSE 0 END)::int AS ano_prodes,
       extract(month FROM a.data)::int                                  AS mes_num,
       (ARRAY['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho',
              'Agosto','Setembro','Outubro','Novembro','Dezembro'])[extract(month FROM a.data)::int] AS mes,
       j.local,
       j.nome_uc,
       j.cnuc,
       a.uf,
       a.municipio,
       round((ST_Area(j.geom::geography) / 10000)::numeric, 4)          AS area_ha,
       -- campos para o analista preencher (ficam vazios até alguém revisar)
       NULL::boolean AS apuracao,
       NULL::text    AS legalidade,
       NULL::text    AS info,
       NULL::text    AS embargo,
       ST_X(ST_PointOnSurface(j.geom))                                  AS x,
       ST_Y(ST_PointOnSurface(j.geom))                                  AS y,
       j.geom::geometry(MultiPolygon, 4674)                             AS geom
FROM juntos j
JOIN desmatamento.deter_alertas a USING (id_alerta)
WHERE NOT ST_IsEmpty(j.geom);

ALTER TABLE desmatamento.deter_ucs ADD PRIMARY KEY (id_alerta);
CREATE INDEX ON desmatamento.deter_ucs USING gist (geom);
CREATE INDEX ON desmatamento.deter_ucs (data);


/* ---------- 6. PRODES nas UCs (mesma lógica do DETER) ------------------------------- */
DROP TABLE IF EXISTS desmatamento.prodes_ucs CASCADE;
CREATE TABLE desmatamento.prodes_ucs AS
WITH prodes AS (
    SELECT uuid AS id_alerta, main_class AS classe, year AS ano, image_date::date AS img_date, state AS uf,
           ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3)) AS geom
    FROM bruto.prodes
),
interior AS (
    SELECT DISTINCT ON (p.id_alerta)
           p.id_alerta, u.cnuc, u.nome_uc, 'Interior'::text AS local,
           ST_Multi(ST_CollectionExtract(ST_Intersection(p.geom, u.geom), 3)) AS geom
    FROM prodes p
    JOIN limites.ucs u ON ST_Intersects(p.geom, u.geom)
    ORDER BY p.id_alerta, ST_Area(ST_Intersection(p.geom, u.geom)) DESC
),
entorno AS (
    SELECT DISTINCT ON (p.id_alerta)
           p.id_alerta, e.cnuc, e.nome_uc, 'Entorno'::text AS local, p.geom
    FROM prodes p
    JOIN limites.ucs_entorno e ON ST_Intersects(p.geom, e.geom)
    WHERE p.id_alerta NOT IN (SELECT id_alerta FROM interior)
    ORDER BY p.id_alerta, ST_Area(ST_Intersection(p.geom, e.geom)) DESC
),
juntos AS (
    SELECT * FROM interior UNION ALL SELECT * FROM entorno
)
SELECT j.id_alerta, p.classe, p.img_date, p.ano, p.uf, j.local, j.nome_uc, j.cnuc,
       round((ST_Area(j.geom::geography) / 10000)::numeric, 4) AS area_ha,
       NULL::boolean AS apuracao, NULL::text AS legalidade, NULL::text AS info, NULL::text AS embargo,
       j.geom::geometry(MultiPolygon, 4674) AS geom
FROM juntos j
JOIN prodes p USING (id_alerta)
WHERE NOT ST_IsEmpty(j.geom);

ALTER TABLE desmatamento.prodes_ucs ADD PRIMARY KEY (id_alerta);
CREATE INDEX ON desmatamento.prodes_ucs USING gist (geom);


/* ---------- Conferência ------------------------------------------------------------- */
SELECT 'limites.ucs' AS tabela, count(*) FROM limites.ucs
UNION ALL SELECT 'fiscalizacao.embargos', count(*) FROM fiscalizacao.embargos
UNION ALL SELECT 'desmatamento.deter_ucs', count(*) FROM desmatamento.deter_ucs
UNION ALL SELECT 'desmatamento.prodes_ucs', count(*) FROM desmatamento.prodes_ucs;
