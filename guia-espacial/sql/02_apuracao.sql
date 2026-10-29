/* =====================================================================================
   02_apuracao.sql
   Para cada alerta (DETER e PRODES), verifica se já existe um EMBARGO cobrindo a área.

   Regra de "apurado" (casou com um grupo de embargos):
     1. o alerta toca o grupo de embargos;
     2. o embargo não é muito mais antigo que o alerta
        (DETER: até 580 dias antes; PRODES: ano do embargo >= ano do PRODES - 1);
     3. o grupo de embargos cobre mais de 40% de alguma parte do alerta.

   Embargos do tipo 'Ponto' (só uma coordenada, desenhada como círculo de ~1 m de raio) não entram
   na decisão, porque não representam a área real. Eles aparecem só na lista de embargos.

   Saídas: desmatamento.apuracao_deter, desmatamento.apuracao_prodes
   Uma tabela só para todos os anos (coluna "ano"), em vez de uma tabela por ano.
   ===================================================================================== */

SET client_min_messages = warning;


/* ---------- Grupos de embargos vizinhos ----------------------------------------------
   Embargos a até ~66 m (0,0006 grau) um do outro viram um grupo só, dissolvido. */
DROP TABLE IF EXISTS fiscalizacao.embargos_grupos CASCADE;
CREATE TABLE fiscalizacao.embargos_grupos AS
SELECT cluster_id                                  AS id_grupo,
       string_agg(num_embargo, ', ' ORDER BY num_embargo) AS num_embargo,
       max(data)                                   AS data,
       ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(geom)), 3))::geometry(MultiPolygon, 4674) AS geom
FROM (
    SELECT num_embargo, data, geom,
           ST_ClusterDBSCAN(geom, eps => 0.0006, minpoints => 1) OVER () AS cluster_id
    FROM fiscalizacao.embargos
    WHERE origem_geom = 'Polígono'
) c
GROUP BY cluster_id;

CREATE INDEX ON fiscalizacao.embargos_grupos USING gist (geom);


/* ---------- Apuração DETER ----------------------------------------------------------- */
DROP TABLE IF EXISTS desmatamento.apuracao_deter CASCADE;
CREATE TABLE desmatamento.apuracao_deter AS
WITH
partes AS (                                   -- cada parte do alerta numa linha
    SELECT id_alerta, data, (ST_Dump(geom)).geom AS geom
    FROM desmatamento.deter_ucs
),
casamentos AS (                               -- partes que casam com um grupo de embargos
    SELECT DISTINCT p.id_alerta
    FROM partes p
    JOIN fiscalizacao.embargos_grupos g
      ON ST_Intersects(p.geom, g.geom)
     AND g.data - p.data > -580
     AND ST_Area(ST_Intersection(p.geom, g.geom)) / NULLIF(ST_Area(p.geom), 0) > 0.4
),
lista AS (                                    -- todos os embargos que tocam o alerta
    SELECT d.id_alerta, string_agg(DISTINCT e.num_embargo, ', ') AS embargos
    FROM desmatamento.deter_ucs d
    JOIN fiscalizacao.embargos e ON ST_Intersects(d.geom, e.geom)
    GROUP BY d.id_alerta
)
SELECT row_number() OVER (ORDER BY d.id_alerta) AS vw_id,
       d.id_alerta, d.classname, d.data, d.ano, d.ano_prodes, d.mes_num, d.mes,
       d.local, d.nome_uc, d.cnuc, d.uf, d.area_ha,
       -- o que o analista preencheu sempre vence o cálculo automático
       CASE WHEN d.apuracao IS TRUE OR c.id_alerta IS NOT NULL THEN 'Sim' ELSE 'Não' END AS apuracao,
       coalesce(d.legalidade, CASE WHEN c.id_alerta IS NOT NULL THEN 'Ilegal' END)       AS legalidade,
       d.info,
       coalesce(d.embargo,    CASE WHEN c.id_alerta IS NOT NULL THEN l.embargos END)     AS embargo,
       l.embargos AS embargos_que_tocam,
       d.geom
FROM desmatamento.deter_ucs d
LEFT JOIN casamentos c USING (id_alerta)
LEFT JOIN lista l      USING (id_alerta);

ALTER TABLE desmatamento.apuracao_deter ADD PRIMARY KEY (id_alerta);


/* ---------- Apuração PRODES ---------------------------------------------------------- */
DROP TABLE IF EXISTS desmatamento.apuracao_prodes CASCADE;
CREATE TABLE desmatamento.apuracao_prodes AS
WITH
partes AS (
    SELECT id_alerta, ano, (ST_Dump(geom)).geom AS geom
    FROM desmatamento.prodes_ucs
),
casamentos AS (
    SELECT DISTINCT p.id_alerta
    FROM partes p
    JOIN fiscalizacao.embargos_grupos g
      ON ST_Intersects(p.geom, g.geom)
     AND extract(year FROM g.data) >= p.ano - 1
     AND ST_Area(ST_Intersection(p.geom, g.geom)) / NULLIF(ST_Area(p.geom), 0) > 0.4
),
lista AS (
    SELECT p.id_alerta, string_agg(DISTINCT e.num_embargo, ', ') AS embargos
    FROM desmatamento.prodes_ucs p
    JOIN fiscalizacao.embargos e ON ST_Intersects(p.geom, e.geom)
    GROUP BY p.id_alerta
)
SELECT row_number() OVER (ORDER BY p.id_alerta) AS vw_id,
       p.id_alerta, p.classe, p.img_date, p.ano, p.uf, p.local, p.nome_uc, p.cnuc, p.area_ha,
       CASE WHEN p.apuracao IS TRUE OR c.id_alerta IS NOT NULL THEN 'Sim' ELSE 'Não' END AS apuracao,
       coalesce(p.legalidade, CASE WHEN c.id_alerta IS NOT NULL THEN 'Ilegal' END)       AS legalidade,
       p.info,
       coalesce(p.embargo,    CASE WHEN c.id_alerta IS NOT NULL THEN l.embargos END)     AS embargo,
       l.embargos AS embargos_que_tocam,
       p.geom
FROM desmatamento.prodes_ucs p
LEFT JOIN casamentos c USING (id_alerta)
LEFT JOIN lista l      USING (id_alerta);

ALTER TABLE desmatamento.apuracao_prodes ADD PRIMARY KEY (id_alerta);


/* ---------- Conferência ------------------------------------------------------------- */
SELECT 'DETER' AS fonte, ano, apuracao, count(*), round(sum(area_ha)) AS area_ha
FROM desmatamento.apuracao_deter GROUP BY ano, apuracao
UNION ALL
SELECT 'PRODES', ano, apuracao, count(*), round(sum(area_ha))
FROM desmatamento.apuracao_prodes GROUP BY ano, apuracao
ORDER BY 1, 2, 3;
