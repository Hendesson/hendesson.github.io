"""Gera os mapas, gráficos e diagramas dos artigos do Guia de dados espaciais.

Uso:  pip install geopandas sqlalchemy psycopg2-binary matplotlib
      python figuras_artigos.py
Precisa de:
  - dados/artigos.gpkg (baixar_dados_artigos.sh);
  - as tabelas do schema "artigos" no PostGIS, criadas pelos códigos PostGIS dos artigos
    2, 3, 4, 6, 8, 9 e 12;
  - opcional: os PNGs e PDFs gerados nos artigos 10 e 11 (mapas e boletins).
As figuras vão para a pasta "figuras/" (mude com a variável SAIDA).
"""
import math
import os
import shutil
import subprocess
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Rectangle, FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from sqlalchemy import create_engine

warnings.filterwarnings("ignore")
SAIDA = os.environ.get("SAIDA", "figuras/")
os.makedirs(SAIDA, exist_ok=True)
G = os.environ.get("GPKG", "dados/artigos.gpkg")
E = create_engine("postgresql+psycopg2://", connect_args={"dbname": "monitoramento_ambiental"})
q = lambda s: gpd.read_postgis(s, E, geom_col="geom")
t = lambda s: pd.read_sql(s, E)

OI = dict(laranja="#E69F00", azul_claro="#56B4E9", verde="#009E73", amarelo="#F0E442",
          azul="#0072B2", vermelho="#D55E00", roxo="#CC79A7", preto="#000000", cinza="#999999")
PRIO = {"Muito Baixa": "#ffffb2", "Baixa": "#fecc5c", "Média": "#fd8d3c", "Alta": "#f03b20",
        "Muito Alta": "#bd0026"}
UC_FILL, UC_EDGE = "#e5ecdc", "#3a3a3a"
FONTE = "Fontes: INPE/TerraBrasilis, MMA (CNUC). Dados de out. 2026. Elaboração: Hendesson Alves."
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "axes.titlesize": 10, "axes.titleweight": "bold"})
X0, X1, Y0, Y1 = -56.5, -54.5, -8.5, -5.5
EF = [pe.withStroke(linewidth=2.5, foreground="white")]


def fmt_graus(ax):
    ax.xaxis.set_major_formatter(lambda v, p: f"{abs(v):.1f}°O".replace(".", ","))
    ax.yaxis.set_major_formatter(lambda v, p: f"{abs(v):.1f}°S".replace(".", ","))
    ax.tick_params(labelsize=6.5)
    ax.grid(color="#bbbbbb", linewidth=0.3, linestyle=":")


def quadro(ax, x0=X0, y0=Y0, x1=X1, y1=Y1):
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(1 / math.cos(math.radians((y0 + y1) / 2)))
    ax.set_xlabel("")
    ax.set_ylabel("")
    fmt_graus(ax)


def escala_norte(ax, km=None, lado="esq"):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    km_por_grau = 111.32 * math.cos(math.radians((y0 + y1) / 2))
    largura_km = (x1 - x0) * km_por_grau
    if km is None:
        km = [k for k in (1, 2, 5, 10, 20, 25, 50, 100) if k <= largura_km / 4][-1]
    dx = km / km_por_grau
    bx = x0 + (x1 - x0) * 0.05 if lado == "esq" else x1 - (x1 - x0) * 0.05 - dx
    by = y0 + (y1 - y0) * 0.04
    h = (y1 - y0) * 0.01
    ax.add_patch(Rectangle((bx, by), dx / 2, h, color="black", zorder=20))
    ax.add_patch(Rectangle((bx + dx / 2, by), dx / 2, h, facecolor="white", edgecolor="black",
                           lw=0.6, zorder=20))
    ax.text(bx, by + h * 1.8, "0", fontsize=6, ha="center", zorder=21, path_effects=EF)
    ax.text(bx + dx, by + h * 1.8, f"{km} km", fontsize=6, ha="center", zorder=21, path_effects=EF)
    nx, ny = x1 - (x1 - x0) * 0.07, y1 - (y1 - y0) * 0.11
    ax.annotate("N", xy=(nx, ny + (y1 - y0) * 0.06), xytext=(nx, ny), ha="center", fontsize=9,
                weight="bold", arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2),
                zorder=21, path_effects=EF)


def rodape(fig, texto=FONTE):
    fig.text(0.99, 0.005, texto, ha="right", va="bottom", fontsize=5.8, color="#444")


def salvar(fig, nome):
    fig.savefig(SAIDA + nome, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("ok", nome)


def nome_curto(n):
    n = " ".join(p if p in ("de", "do", "da", "dos", "das") else p.capitalize()
                 for p in n.lower().split())
    for a, b in [("Floresta Nacional", "Flona"), ("Parque Nacional", "Parna"),
                 ("Área de Proteção Ambiental", "APA"), ("Floresta Estadual", "Flota")]:
        n = n.replace(a, b)
    return n


def rotular(ax, ucs, recorte=box(X0, Y0, X1, Y1), minimo=0.03, tamanho=6.5):
    for _, r in ucs.iterrows():
        g = r.geometry.intersection(recorte)
        if g.is_empty or g.area < minimo:
            continue
        p = g.representative_point()
        ax.text(p.x, p.y, nome_curto(r.nome_uc), fontsize=tamanho, ha="center", va="center",
                style="italic", color="#1d3b1d", path_effects=EF, zorder=15)


ucs = gpd.read_file(G, layer="ucs")
amz_ucs = ucs[ucs.regiao == "Amazonia"]
entorno = gpd.read_file(G, layer="ucs_entorno")
amz_ent = entorno[entorno.regiao == "Amazonia"]


def base_mapa(ax, cor_uc=UC_FILL, com_entorno=True):
    if com_entorno:
        amz_ent.plot(ax=ax, color=OI["amarelo"], alpha=0.45, linewidth=0)
    amz_ucs.plot(ax=ax, facecolor=cor_uc, edgecolor=UC_EDGE, linewidth=0.6)


# ------------------------------------------------------------ 1. equivalências (diagrama)
linhas = [("Selecionar por local", "SelectLayerByLocation", "extractbylocation", "ST_Intersects", "sjoin"),
          ("Interseção", "PairwiseIntersect", "intersection", "ST_Intersection", "overlay"),
          ("Apagar", "PairwiseErase", "difference", "ST_Difference", "overlay difference"),
          ("Buffer", "PairwiseBuffer", "buffer", "ST_Buffer", "buffer"),
          ("Dissolver", "PairwiseDissolve", "dissolve", "ST_Union", "dissolve"),
          ("Juntar tabela", "JoinField", "joinattributestable", "JOIN", "merge"),
          ("Área (ha)", "AREA_GEODESIC", "$area", "::geography", "to_crs().area")]
cab = ["Operação", "ArcGIS Pro", "QGIS", "PostGIS", "geopandas"]
cores = ["#444444", "#2C7FB8", "#589632", "#336791", "#E69F00"]
fig, ax = plt.subplots(figsize=(10, 4.4))
ax.set_xlim(0, 5)
ax.set_ylim(-len(linhas) - 0.2, 1.1)
ax.set_axis_off()
for j, (c, cor) in enumerate(zip(cab, cores)):
    ax.add_patch(FancyBboxPatch((j + 0.04, 0.12), 0.92, 0.76, boxstyle="round,pad=0.02",
                                facecolor=cor, edgecolor="none"))
    ax.text(j + 0.5, 0.5, c, ha="center", va="center", color="white", fontsize=10, weight="bold")
for i, lin in enumerate(linhas):
    y = -i - 0.5
    ax.add_patch(Rectangle((0, y - 0.45), 5, 0.9, facecolor="#f4f4f4" if i % 2 else "white",
                           edgecolor="none"))
    for j, txt in enumerate(lin):
        ax.text(j + 0.5, y, txt, ha="center", va="center", fontsize=8.2 if j else 8.8,
                family="DejaVu Sans Mono" if j else "DejaVu Sans", weight="normal" if j else "bold")
ax.set_title("A mesma operação em cada programa", fontsize=12)
salvar(fig, "equivalencias.png")

# ------------------------------------------------------------ 2. interior e entorno (mapa)
zonas = q("SELECT local, geom FROM artigos.zonas_ucs")
cruz = q("SELECT local, nome_uc, area_ha, classname, geom FROM artigos.deter_interior_entorno")
fig, ax = plt.subplots(figsize=(6.2, 8))
zonas[zonas.local == "entorno"].plot(ax=ax, color=OI["amarelo"], alpha=0.6, linewidth=0)
zonas[zonas.local == "interior"].plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.6)
cruz[cruz.local == "interior"].plot(ax=ax, color=OI["azul"], linewidth=0)
cruz[cruz.local == "entorno"].plot(ax=ax, color=OI["vermelho"], linewidth=0)
quadro(ax)
rotular(ax, amz_ucs)
escala_norte(ax)
ax.legend(handles=[Patch(facecolor=UC_FILL, edgecolor=UC_EDGE, label="Interior das UCs"),
                   Patch(facecolor=OI["amarelo"], alpha=0.6, label="Entorno de 3 km"),
                   Patch(color=OI["azul"], label="Alerta no interior"),
                   Patch(color=OI["vermelho"], label="Alerta no entorno")],
          loc="lower right", fontsize=7, framealpha=0.95)
ax.set_title("Alertas do DETER (jan. 2024 a out. 2026) no interior e no entorno das UCs")
rodape(fig)
salvar(fig, "interior_entorno_zonas.png")

# ------------------------------------------------------------ 3. interior e entorno (barras)
tab = cruz.groupby(["nome_uc", "local"]).area_ha.sum().unstack(fill_value=0)[["interior", "entorno"]]
tab = tab.sort_values("interior")
tab.index = [nome_curto(n) for n in tab.index]
fig, ax = plt.subplots(figsize=(7, 3.4))
tab.plot.barh(ax=ax, color=[OI["verde"], OI["laranja"]], width=0.75)
ax.set_xlabel("Área de alertas (ha), todas as classes do DETER")
ax.xaxis.set_major_formatter(lambda v, p: f"{v:,.0f}".replace(",", "."))
ax.legend(["Interior", "Entorno de 3 km"], frameon=False, loc="lower right")
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Área de alertas por UC, de janeiro de 2024 a outubro de 2026")
fig.tight_layout()
fig.subplots_adjust(bottom=0.2)
rodape(fig)
salvar(fig, "interior_entorno_barras.png")

# ------------------------------------------------------------ 4. PRODES nos dois biomas
serie = t("SELECT bioma, ano, sum(area_ha) AS ha FROM artigos.prodes_ucs GROUP BY 1, 2")
fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
for ax, (bioma, cor) in zip(axs, [("Amazônia", OI["vermelho"]), ("Cerrado", OI["laranja"])]):
    s = serie[serie.bioma == bioma].sort_values("ano")
    ax.bar(s.ano.astype(str), s.ha, color=cor)
    for x, y in zip(s.ano.astype(str), s.ha):
        ax.text(x, y, f"{y:,.0f}".replace(",", "."), ha="center", va="bottom", fontsize=6.5)
    ax.set_title(f"{bioma}: UCs do recorte")
    ax.set_ylabel("Desmatamento (ha)")
    ax.yaxis.set_major_formatter(lambda v, p: f"{v:,.0f}".replace(",", "."))
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("Desmatamento PRODES dentro das UCs, por ano PRODES", fontsize=11, weight="bold")
fig.tight_layout()
rodape(fig, "Fonte: INPE (PRODES Amazônia Legal e PRODES Cerrado), MMA (CNUC). O PRODES Amazônia 2026 ainda não foi publicado.")
salvar(fig, "prodes_biomas.png")

# ------------------------------------------------------------ 5. focos de calor 48 h
tem = t("SELECT to_regclass('artigos.focos_snapshot') IS NOT NULL AS sim").sim[0]
tab_focos = "artigos.focos_snapshot" if tem else \
    "(SELECT *, now() AT TIME ZONE 'UTC' AS consulta FROM artigos.focos) f0"
focos = q(f"""SELECT satelite, data_hora_gmt, consulta,
                     ST_SetSRID(ST_MakePoint(lon, lat), 4674) AS geom
              FROM {tab_focos}
              WHERE data_hora_gmt >= consulta - interval '48 hours'""")
focos = focos[focos.intersects(box(X0, Y0, X1, Y1))]          # só o que aparece no mapa
focos["janela"] = np.where(focos.data_hora_gmt >= focos.consulta - pd.Timedelta(hours=24),
                           "Últimas 24 h", "24 a 48 h")
fig, ax = plt.subplots(figsize=(6.2, 8))
base_mapa(ax)
for jan, cor, tam in [("24 a 48 h", OI["laranja"], 10), ("Últimas 24 h", OI["vermelho"], 14)]:
    f = focos[focos.janela == jan]
    ax.scatter(f.geometry.x, f.geometry.y, s=tam, color=cor, edgecolor="black", linewidth=0.3,
               zorder=10, label=f"{jan} ({len(f)})")
quadro(ax)
rotular(ax, amz_ucs)
escala_norte(ax)
hora = (focos.consulta.max() - pd.Timedelta(hours=3)).strftime("%d/%m/%Y %Hh%M")
ax.legend(handles=[Patch(facecolor=UC_FILL, edgecolor=UC_EDGE, label="UCs"),
                   Patch(facecolor=OI["amarelo"], alpha=0.45, label="Entorno de 3 km")]
          + ax.get_legend_handles_labels()[0], loc="lower right", fontsize=7, framealpha=0.95)
ax.set_title(f"Focos de calor, todos os satélites (consulta de {hora}, Brasília)")
rodape(fig, "Fontes: INPE (Programa Queimadas, focos diários), MMA (CNUC). Elaboração: Hendesson Alves.")
salvar(fig, "focos_48h.png")

# ------------------------------------------------------------ 6. calendário PRODES
meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
fig, ax = plt.subplots(figsize=(10, 2.8))
ax.set_xlim(-0.5, 18.5)
ax.set_ylim(-1.6, 1.4)
ax.set_axis_off()
for i in range(19):                                    # jan/2024 a jul/2025
    ano, m = 2024 + (i // 12), i % 12
    ax.add_patch(Rectangle((i - 0.45, 0.35), 0.9, 0.6, facecolor="#eeeeee", edgecolor="#999"))
    ax.text(i, 0.65, f"{meses[m]}\n{ano}", ha="center", va="center", fontsize=6.5)
    if i >= 7:
        mp = i - 6
        ax.add_patch(Rectangle((i - 0.45, -1.05), 0.9, 0.6, facecolor=OI["verde"], alpha=0.25 + 0.05 * mp,
                               edgecolor=OI["verde"]))
        ax.text(i, -0.75, f"mês {mp}", ha="center", va="center", fontsize=6.5, weight="bold")
        ax.annotate("", xy=(i, -0.42), xytext=(i, 0.33), arrowprops=dict(arrowstyle="->", color="#777", lw=0.6))
ax.text(-0.45, 1.15, "Ano civil", fontsize=9, weight="bold")
ax.text(6.55, -1.45, "Ano PRODES 2025: de 1º de agosto de 2024 a 31 de julho de 2025", fontsize=9,
        weight="bold", color=OI["verde"])
salvar(fig, "calendario_prodes.png")

# ------------------------------------------------------------ 7. acumulado mensal
acum = t("""SELECT ano_prodes, mes_prodes, acumulado_ha, valido FROM artigos.deter_mensal_acumulado
            WHERE nome_uc = 'FLORESTA NACIONAL DO JAMANXIM' AND ano_prodes >= 2025""")
fig, ax = plt.subplots(figsize=(7, 3.6))
estilos = {2025: ("#999999", "--"), 2026: (OI["azul"], "-"), 2027: (OI["vermelho"], "-")}
for ano, s in acum.groupby("ano_prodes"):
    s = s[s.valido].sort_values("mes_prodes")
    cor, ls = estilos[ano]
    ax.plot(s.mes_prodes, s.acumulado_ha, color=cor, ls=ls, marker="o", ms=3, lw=1.8,
            label=f"Ano PRODES {ano}")
    ax.text(s.mes_prodes.iloc[-1] + 0.15, s.acumulado_ha.iloc[-1], f"{s.acumulado_ha.iloc[-1]:,.0f} ha".replace(",", "."),
            color=cor, fontsize=7, va="center")
ax.set_xticks(range(1, 13), ["ago", "set", "out", "nov", "dez", "jan", "fev", "mar", "abr", "mai", "jun", "jul"])
ax.set_ylabel("Área acumulada (ha)")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="upper left")
ax.set_title("Flona do Jamanxim: desmatamento acumulado no ano PRODES (DETER, ≥ 6,25 ha)")
rodape(fig, "Fonte: INPE (DETER), MMA (CNUC). Classes: corte raso, com vegetação e mineração, interior da UC.")
salvar(fig, "acumulado_mensal.png")

# ------------------------------------------------------------ 8. junção (diagrama)
fig, ax = plt.subplots(figsize=(9, 4))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.set_axis_off()


def tabela_desenho(x, y, cab, linhas, cores_cab):
    larg = 1.35
    for j, c in enumerate(cab):
        ax.add_patch(Rectangle((x + j * larg, y), larg, 0.5, facecolor=cores_cab[j], edgecolor="white"))
        ax.text(x + j * larg + larg / 2, y + 0.25, c, ha="center", va="center", color="white",
                fontsize=7.5, weight="bold")
    for i, lin in enumerate(linhas):
        for j, v in enumerate(lin):
            ax.add_patch(Rectangle((x + j * larg, y - (i + 1) * 0.42), larg, 0.42,
                                   facecolor="#f6f6f6" if i % 2 else "white", edgecolor="#ccc"))
            ax.text(x + j * larg + larg / 2, y - (i + 1) * 0.42 + 0.21, v, ha="center", va="center",
                    fontsize=7, family="DejaVu Sans Mono")


A, B, C = OI["azul"], OI["verde"], "#555555"
tabela_desenho(0.2, 5.2, ["gid", "cnuc", "area_ha"], [["101", "…0266", "12,4"], ["102", "…0267", "3,1"],
                                                      ["103", "…0266", "8,0"]], [C, A, C])
ax.text(0.2, 5.85, "Alertas", fontsize=9, weight="bold")
tabela_desenho(5.6, 5.2, ["cnuc", "categoria", "grupo"], [["…0266", "Floresta", "Uso Sust."],
                                                          ["…0267", "Parque", "Prot. Int."]], [A, B, B])
ax.text(5.6, 5.85, "UCs", fontsize=9, weight="bold")
ax.add_patch(FancyArrowPatch((2.2, 3.7), (3.6, 2.55), arrowstyle="-|>", mutation_scale=14, color=A))
ax.add_patch(FancyArrowPatch((6.9, 4.1), (5.6, 2.55), arrowstyle="-|>", mutation_scale=14, color=B))
ax.text(4.75, 3.35, "mesmo cnuc", ha="center", fontsize=8, color=A, style="italic")
tabela_desenho(1.9, 2.3, ["gid", "cnuc", "area_ha", "categoria", "grupo"],
               [["101", "…0266", "12,4", "Floresta", "Uso Sust."], ["102", "…0267", "3,1", "Parque", "Prot. Int."],
                ["103", "…0266", "8,0", "Floresta", "Uso Sust."]], [C, A, C, B, B])
ax.text(1.9, 2.95, "Resultado da junção", fontsize=9, weight="bold")
salvar(fig, "juncao.png")

# ------------------------------------------------------------ 9. CAR nas UCs
car = gpd.read_file(G, layer="car")
dentro = t("SELECT DISTINCT cod_imovel FROM artigos.car_ucs WHERE pct_imovel >= 1")
car = car[car.cod_imovel.isin(dentro.cod_imovel)]
STATUS = {"AT": ("Ativo", OI["azul"]), "PE": ("Pendente", OI["laranja"]),
          "SU": ("Suspenso", OI["roxo"]), "CA": ("Cancelado", "#bbbbbb")}
fig, ax = plt.subplots(figsize=(6.2, 8))
amz_ucs.plot(ax=ax, facecolor=UC_FILL, edgecolor="none")
for cod in ["CA", "SU", "PE", "AT"]:
    rot, cor = STATUS[cod]
    car[car.status_imovel == cod].plot(ax=ax, facecolor=cor, edgecolor="white", linewidth=0.15,
                                       alpha=0.85)
amz_ucs.plot(ax=ax, facecolor="none", edgecolor=OI["verde"], linewidth=1.1)
quadro(ax)
rotular(ax, amz_ucs)
escala_norte(ax)
ax.legend(handles=[Patch(facecolor="none", edgecolor=OI["verde"], linewidth=1.1, label="Limite das UCs")]
          + [Patch(color=STATUS[c][1], label=f"CAR {STATUS[c][0].lower()}") for c in ["AT", "PE", "SU", "CA"]],
          loc="lower right", fontsize=7, framealpha=0.95)
ax.set_title("Imóveis do CAR com pelo menos 1% da área dentro de UCs")
rodape(fig, "Fontes: SICAR (CAR, Pará), MMA (CNUC). Dados de out. 2026. Elaboração: Hendesson Alves.")
salvar(fig, "car_ucs.png")

# ------------------------------------------------------------ 10. Kernel
k = t("SELECT ST_X(geom) AS x, ST_Y(geom) AS y, indice FROM artigos.kernel_grade")
xs, ys = np.sort(k.x.unique()), np.sort(k.y.unique())
grade = np.full((len(ys), len(xs)), np.nan)
grade[np.searchsorted(ys, k.y), np.searchsorted(xs, k.x)] = k.indice.astype(float)
grade = np.where(np.isnan(grade), 0, grade)
quente = k.loc[k.indice.astype(float).idxmax()]
quente_ll = gpd.GeoSeries(gpd.points_from_xy([quente.x], [quente.y]), crs=5880).to_crs(4674).iloc[0]
print("ponto mais quente (lon, lat):", round(quente_ll.x, 3), round(quente_ll.y, 3),
      "dentro de UC:", bool(amz_ucs.contains(quente_ll).any()))
fig, ax = plt.subplots(figsize=(6.2, 8))
u5880 = gpd.clip(amz_ucs, box(X0, Y0, X1, Y1)).to_crs(5880)
im = ax.imshow(np.ma.masked_less(grade, 0.02), origin="lower", cmap="YlOrRd", vmin=0, vmax=0.7,
               extent=(xs.min() - 500, xs.max() + 500, ys.min() - 500, ys.max() + 500), zorder=1)
u5880.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.7, zorder=3)
rec = gpd.GeoSeries([box(X0, Y0, X1, Y1)], crs=4674).to_crs(5880)
rec.plot(ax=ax, facecolor="none", edgecolor="#777", linewidth=0.6, linestyle="--", zorder=3)
ax.scatter([quente.x], [quente.y], marker="x", color="black", s=30, zorder=4)
ax.annotate("ponto mais quente", (quente.x, quente.y), xytext=(8, 8), textcoords="offset points",
            fontsize=7, path_effects=EF)
for _, r in u5880.iterrows():
    if r.geometry.area > 2e9:
        p = r.geometry.representative_point()
        ax.text(p.x, p.y, nome_curto(r.nome_uc), fontsize=6.5, ha="center", style="italic",
                path_effects=EF, zorder=5)
ax.set_axis_off()
cb = fig.colorbar(im, ax=ax, shrink=0.5, pad=0.02)
cb.set_label("Índice de densidade (0 a 1)")
ax.set_title("Densidade Kernel do PRODES 2025 (raio 10 km, célula 1 km)")
rodape(fig, "Fonte: INPE (PRODES), MMA (CNUC). Áreas com índice < 0,02 em branco. EPSG:5880.")
salvar(fig, "kernel.png")

# ------------------------------------------------------------ 11. priorização
pr = q("SELECT tipo, prioridade, indice, ST_Transform(geom, 4674) AS geom FROM artigos.prior_clusters")
pr["geom"] = pr.buffer(0.004)                        # engrossa os grupos pequenos para aparecerem
fig, ax = plt.subplots(figsize=(6.2, 8))
amz_ucs.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.5)
for cls in PRIO:
    pr[pr.prioridade == cls].plot(ax=ax, color=PRIO[cls], edgecolor="#555", linewidth=0.2, zorder=5)
quadro(ax)
rotular(ax, amz_ucs)
escala_norte(ax)
ax.legend(handles=[Patch(facecolor=PRIO[c], edgecolor="#555", label=f"{c} ({(pr.prioridade == c).sum()})")
                   for c in reversed(list(PRIO))], title="Prioridade (grupos)", loc="lower right",
          fontsize=7, title_fontsize=7.5, framealpha=0.95)
ax.set_title("Grupos de alertas do último ano, por prioridade")
rodape(fig, "Fonte: INPE (DETER, 17/10/2025 a 16/10/2026), MMA (CNUC). Grupos ampliados 400 m para aparecer.")
salvar(fig, "priorizacao_grupos.png")

# ------------------------------------------------------------ 12. padrões de atualização
fig, axs = plt.subplots(1, 4, figsize=(11, 3.3))
titulos = ["1. Substituir tudo", "2. Substituir um pedaço", "3. Anexar só o novo", "4. Inserir ou atualizar"]
for ax, tit in zip(axs, titulos):
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 7)
    ax.set_axis_off()
    ax.set_title(tit, fontsize=9)
cinza, novo, apag, atual = "#d9d9d9", OI["verde"], "#ffffff", OI["azul_claro"]
for i in range(6):                                       # 1: tudo novo
    axs[0].add_patch(Rectangle((0.5, 6 - i), 3, 0.8, facecolor=novo, edgecolor="#555"))
axs[0].text(2, 0.2, "toda a camada é trocada", ha="center", fontsize=7)
for i in range(6):                                       # 2: só ano 2025
    cor = novo if i in (4, 5) else cinza
    axs[1].add_patch(Rectangle((0.5, 6 - i), 3, 0.8, facecolor=cor, edgecolor="#555"))
    axs[1].text(2, 6.4 - i, "2025" if i in (4, 5) else str(2019 + i), ha="center", va="center", fontsize=7)
axs[1].text(2, 0.2, "só as linhas de 2025", ha="center", fontsize=7)
for i in range(6):                                       # 3: novas no fim
    cor = novo if i >= 4 else cinza
    axs[2].add_patch(Rectangle((0.5, 6 - i), 3, 0.8, facecolor=cor, edgecolor="#555"))
axs[2].text(2, 0.2, "linhas novas entram no fim", ha="center", fontsize=7)
for i in range(6):                                       # 4: upsert
    cor = novo if i >= 5 else (atual if i in (2, 4) else cinza)
    axs[3].add_patch(Rectangle((0.5, 6 - i), 3, 0.8, facecolor=cor, edgecolor="#555"))
axs[3].text(2, 0.2, "novas entram; as que mudaram\nsão atualizadas pela chave", ha="center", fontsize=7)
fig.legend(handles=[Patch(facecolor=cinza, edgecolor="#555", label="não muda"),
                    Patch(facecolor=novo, edgecolor="#555", label="entra (nova)"),
                    Patch(facecolor=atual, edgecolor="#555", label="atualizada")],
           loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.06))
salvar(fig, "atualizacao.png")

# ------------------------------------------------------------ 13. imagens dos artigos 10 e 11
if os.path.exists("dados/mapas/mapa_0000.00.0267.png"):
    shutil.copy("dados/mapas/mapa_0000.00.0267.png", SAIDA + "mapa_atlas.png")
    print("ok mapa_atlas.png")
for pdf, nome, pagina in [("dados/boletim.pdf", "boletim", 1),
                          ("boletim/boletim_0000.00.0268.pdf", "boletim_quarto", 1)]:
    if os.path.exists(pdf) and shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-r", "80", "-png", "-singlefile", "-f", str(pagina),
                        "-l", str(pagina), pdf, SAIDA + nome], check=True)
        print("ok", nome + ".png")

# ------------------------------------------------------------ 14. capa da página dos artigos
partes = ["interior_entorno_zonas.png", "focos_48h.png", "car_ucs.png", "kernel.png"]
if all(os.path.exists(SAIDA + p) for p in partes):
    fig, axs = plt.subplots(1, 4, figsize=(16, 5.6))
    for ax, p in zip(axs, partes):
        img = plt.imread(SAIDA + p)
        h = img.shape[0]
        ax.imshow(img[int(h * 0.04):int(h * 0.9)])
        ax.set_axis_off()
    fig.subplots_adjust(wspace=0.02, left=0, right=1, top=1, bottom=0)
    salvar(fig, "capa_artigos.png")
