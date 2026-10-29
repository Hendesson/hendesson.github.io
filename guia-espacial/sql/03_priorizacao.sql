/* =====================================================================================
   03_priorizacao.sql
   Dá a cada alerta DETER uma prioridade de fiscalização (Muito Alta ... Muito Baixa),
   olhando o "cluster" de desmatamento em volta dele.

   Etapas:
     1. deter_cluster      -> agrupa alertas próximos no espaço (~66 m) e no tempo (≤ 182 dias)
     2. deter_cluster_2    -> calcula medidas e índices de cada cluster
     3. vw_deter_prioridade-> uma linha por alerta, com a prioridade do seu cluster

   Depende de: 01_preparar_tabelas.sql e 02_apuracao.sql
   Atenção: o resultado depende de CURRENT_DATE (muda a cada dia em que é rodado).
   ===================================================================================== */

SET client_min_messages = warning;


/* ---------- 1. Clusters --------------------------------------------------------------
   Entram só alertas de desmatamento (sem cicatriz de queimada e degradação) do último ano. */
DROP TABLE IF EXISTS desmatamento.deter_cluster CASCADE;
CREATE TABLE desmatamento.deter_cluster AS
WITH RECURSIVE
recentes AS (
    SELECT id_alerta, data, geom
    FROM desmatamento.deter_ucs
    WHERE classname IN ('DESMATAMENTO_CR', 'DESMATAMENTO_VEG', 'MINERACAO',
                        'CS_DESORDENADO', 'CS_GEOMETRICO')
      AND data >= CURRENT_DATE - 365
),
arestas AS (                       -- pares de vizinhos (inclui o próprio alerta)
    SELECT a.id_alerta AS id1, b.id_alerta AS id2
    FROM recentes a
    JOIN recentes b
      ON ST_DWithin(a.geom, b.geom, 0.0006)
     AND abs(a.data - b.data) <= 182
),
alcance AS (                       -- de cada alerta, todos os alcançáveis (vizinho de vizinho...)
    SELECT id1 AS raiz, id2 AS membro FROM arestas
    UNION                          -- UNION sem ALL: para quando não aparece nada novo
    SELECT al.raiz, ar.id2
    FROM alcance al
    JOIN arestas ar ON ar.id1 = al.membro
)
SELECT membro AS id_alerta,
       dense_rank() OVER (ORDER BY min(raiz)) AS cluster_id
FROM alcance
GROUP BY membro;

ALTER TABLE desmatamento.deter_cluster ADD PRIMARY KEY (id_alerta);


/* ---------- 2. Medidas e índices por cluster ---------------------------------------- */
DROP TABLE IF EXISTS desmatamento.deter_cluster_2 CASCADE;
CREATE TABLE desmatamento.deter_cluster_2 AS
WITH
medidas AS (
    SELECT c.cluster_id,
           array_agg(d.id_alerta ORDER BY d.data)                  AS alertas,
           count(*)                                                AS qtd_alertas,
           min(d.data)                                             AS data_min,
           max(d.data)                                             AS data_max,
           ST_Area(ST_Union(d.geom)::geography) / 10000            AS area_ha,      -- sem contar sobreposição 2x
           ST_NumGeometries(ST_Union(d.geom))                      AS contiguo,     -- nº de manchas separadas
           CURRENT_DATE - max(d.data)                              AS dias_desde_ultimo,
           greatest(CURRENT_DATE - min(d.data), 1)                 AS dias_desde_primeiro,
           ST_Union(d.geom)                                        AS geom
    FROM desmatamento.deter_cluster c
    JOIN desmatamento.deter_ucs d USING (id_alerta)
    GROUP BY c.cluster_id
),
indices AS (                       -- cada índice vai de 0 a 1
    SELECT *,
           area_ha / dias_desde_primeiro                                       AS velocidade,  -- ha/dia
           least(1, greatest(0, area_ha / 100))                                AS ind_area,    -- 100 ha ou mais = 1
           CASE WHEN contiguo > 2 THEN 1 WHEN contiguo = 2 THEN 0.5 ELSE 0 END AS ind_cont,    -- fragmentação
           least(1, greatest(0, (560 - dias_desde_ultimo) / 549.0))            AS ind_temp,    -- recente = 1
           least(1, greatest(0, (area_ha / dias_desde_primeiro) / 3))          AS ind_velo     -- 3 ha/dia ou mais = 1
    FROM medidas
),
final AS (
    SELECT *, ind_area / 6 + ind_cont / 6 + ind_temp / 6 + ind_velo / 2 AS ind_priori
    FROM indices
)
SELECT cluster_id, alertas, qtd_alertas, data_min, data_max,
       round(area_ha::numeric, 2)    AS area_ha,
       contiguo,
       dias_desde_ultimo,
       round(velocidade::numeric, 4) AS velocidade,
       round(ind_area::numeric, 3)   AS ind_area,
       round(ind_cont::numeric, 3)   AS ind_cont,
       round(ind_temp::numeric, 3)   AS ind_temp,
       round(ind_velo::numeric, 3)   AS ind_velo,
       round(ind_priori::numeric, 3) AS ind_priori,
       CASE                          -- o CASE para na primeira condição verdadeira
           WHEN ind_priori >= 0.98 THEN 'Muito Alta'
           WHEN ind_priori >= 0.80 THEN 'Alta'
           WHEN ind_priori >= 0.60 THEN 'Média'
           WHEN ind_priori >= 0.40 THEN 'Baixa'
           ELSE 'Muito Baixa'
       END AS prioridade,
       geom::geometry(Geometry, 4674) AS geom
FROM final;

ALTER TABLE desmatamento.deter_cluster_2 ADD PRIMARY KEY (cluster_id);


/* ---------- 3. View final: uma linha por alerta -------------------------------------- */
CREATE OR REPLACE VIEW desmatamento.vw_deter_prioridade AS
SELECT d.id_alerta, d.classname, d.data, d.ano, d.mes_num, d.local, d.nome_uc, d.cnuc, d.area_ha,
       c.cluster_id,
       k.qtd_alertas, k.area_ha AS area_cluster_ha, k.contiguo, k.dias_desde_ultimo, k.velocidade,
       k.ind_area, k.ind_cont, k.ind_temp, k.ind_velo, k.ind_priori,
       CASE WHEN a.apuracao = 'Sim' THEN 'Apurado' ELSE k.prioridade END AS prioridade,
       a.embargo,
       d.x, d.y,
       d.geom
FROM desmatamento.deter_cluster c
JOIN desmatamento.deter_ucs d       USING (id_alerta)
JOIN desmatamento.deter_cluster_2 k USING (cluster_id)
LEFT JOIN desmatamento.apuracao_deter a USING (id_alerta);


/* ---------- Conferência ------------------------------------------------------------- */
SELECT prioridade, count(*) AS alertas, round(sum(area_ha)) AS area_ha
FROM desmatamento.vw_deter_prioridade
GROUP BY prioridade
ORDER BY min(ind_priori) DESC;
