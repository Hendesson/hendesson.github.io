/* =====================================================================================
   04_views_powerbi.sql
   Views prontas para o Power BI, no schema "powerbi".

   O Power BI não entende o tipo geometry do PostGIS. Por isso cada view entrega:
     lat / lon -> um ponto dentro do polígono (para os mapas nativos, como o Azure Maps)
     wkt       -> o polígono como texto WKT (para visuais como o Icon Map Pro)
   O Power BI corta textos com mais de 32.766 caracteres, então os polígonos são
   simplificados e as coordenadas arredondadas para 5 casas (~1 m).

   Modelo (estrela):
       dim_ucs ──< fato_deter
              ──< fato_prodes
              ──< fato_embargos
       dim_calendario ──< fato_deter (data) / fato_embargos (data)
   ===================================================================================== */

CREATE SCHEMA IF NOT EXISTS powerbi;


/* ---------- Dimensão: Unidades de Conservação --------------------------------------- */
CREATE OR REPLACE VIEW powerbi.dim_ucs AS
SELECT u.cnuc, u.nome_uc, u.categoria, u.grupo, u.esfera, u.uf, u.area_ha,
       ST_Y(ST_PointOnSurface(u.geom)) AS lat,
       ST_X(ST_PointOnSurface(u.geom)) AS lon,
       w.wkt
FROM limites.ucs u
CROSS JOIN LATERAL (
    -- tenta simplificações cada vez mais fortes até o texto caber no limite do Power BI
    SELECT ST_AsText(ST_SimplifyPreserveTopology(u.geom, tol), 5) AS wkt
    FROM unnest(ARRAY[0.0005, 0.001, 0.005, 0.01, 0.05]) AS tol
    WHERE length(ST_AsText(ST_SimplifyPreserveTopology(u.geom, tol), 5)) < 32000
    ORDER BY tol
    LIMIT 1
) w;


/* ---------- Fato: alertas DETER ------------------------------------------------------ */
CREATE OR REPLACE VIEW powerbi.fato_deter AS
SELECT a.id_alerta, a.cnuc, a.data, a.ano, a.ano_prodes, a.mes_num, a.mes,
       a.classname AS classe, a.local, a.area_ha,
       a.apuracao, a.legalidade,
       coalesce(p.prioridade, 'Sem prioridade') AS prioridade,   -- alertas fora da janela da priorização
       p.ind_priori, p.cluster_id,
       ST_Y(ST_PointOnSurface(a.geom)) AS lat,
       ST_X(ST_PointOnSurface(a.geom)) AS lon,
       ST_AsText(ST_SimplifyPreserveTopology(a.geom, 0.0001), 5) AS wkt
FROM desmatamento.apuracao_deter a
LEFT JOIN desmatamento.vw_deter_prioridade p USING (id_alerta);


/* ---------- Fato: desmatamento anual PRODES ----------------------------------------- */
CREATE OR REPLACE VIEW powerbi.fato_prodes AS
SELECT id_alerta, cnuc, ano, local, area_ha, apuracao, legalidade,
       ST_Y(ST_PointOnSurface(geom)) AS lat,
       ST_X(ST_PointOnSurface(geom)) AS lon,
       ST_AsText(ST_SimplifyPreserveTopology(geom, 0.0001), 5) AS wkt
FROM desmatamento.apuracao_prodes;


/* ---------- Fato: embargos dentro das UCs ou no entorno ------------------------------
   Sem nome nem CPF/CNPJ (esses campos nem foram copiados no passo 01). */
CREATE OR REPLACE VIEW powerbi.fato_embargos AS
WITH areas AS (                    -- interior e entorno numa tabela só
    SELECT cnuc, 'Interior' AS local, 1 AS ordem, geom FROM limites.ucs
    UNION ALL
    SELECT cnuc, 'Entorno', 2, geom FROM limites.ucs_entorno
)
SELECT DISTINCT ON (e.id_embargo)  -- se tocar mais de uma área, "Interior" ganha
       e.id_embargo, e.num_embargo, e.data,
       extract(year FROM e.data)::int AS ano,
       e.origem_geom, e.area_embargada_ha,
       a.cnuc, a.local,
       ST_Y(ST_PointOnSurface(e.geom)) AS lat,
       ST_X(ST_PointOnSurface(e.geom)) AS lon
FROM fiscalizacao.embargos e
JOIN areas a ON ST_Intersects(e.geom, a.geom)   -- ST_Intersects usa o índice espacial
ORDER BY e.id_embargo, a.ordem;


/* ---------- Dimensão: calendário ------------------------------------------------------
   (Também dá para criar no Power BI com DAX; veja o tutorial 07.) */
CREATE OR REPLACE VIEW powerbi.dim_calendario AS
SELECT d::date                                   AS data,
       extract(year FROM d)::int                 AS ano,
       extract(month FROM d)::int                AS mes_num,
       (ARRAY['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'])
           [extract(month FROM d)::int]          AS mes,
       to_char(d, 'YYYY-MM')                     AS ano_mes,
       (extract(year FROM d) + CASE WHEN extract(month FROM d) >= 8 THEN 1 ELSE 0 END)::int AS ano_prodes
FROM generate_series(DATE '2000-01-01', (CURRENT_DATE + 365)::date, INTERVAL '1 day') AS d;


/* ---------- Conferência ------------------------------------------------------------- */
SELECT 'dim_ucs' AS view, count(*), max(length(wkt)) AS maior_wkt FROM powerbi.dim_ucs
UNION ALL SELECT 'fato_deter',    count(*), max(length(wkt)) FROM powerbi.fato_deter
UNION ALL SELECT 'fato_prodes',   count(*), max(length(wkt)) FROM powerbi.fato_prodes
UNION ALL SELECT 'fato_embargos', count(*), NULL FROM powerbi.fato_embargos;
