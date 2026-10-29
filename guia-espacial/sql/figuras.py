"""Gera os mapas e gráficos do Guia de dados espaciais a partir do banco monitoramento_ambiental.

Uso:  pip install geopandas sqlalchemy psycopg2-binary matplotlib
      python figuras.py            (depois de rodar_tudo.sh)
As figuras vão para a pasta "figuras/" (mude com a variável SAIDA).
"""
import gzip
import os
import urllib.request
import math
import warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from sqlalchemy import create_engine

warnings.filterwarnings("ignore")
SAIDA = os.environ.get("SAIDA", "figuras/")
os.makedirs(SAIDA, exist_ok=True)
os.makedirs("dados", exist_ok=True)


def baixar(url, arquivo):
    """Baixa um arquivo uma vez só (o IBGE recusa pedidos sem cabeçalho de navegador)."""
    if not os.path.exists(arquivo):
        pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(pedido) as r:
            conteudo = r.read()
        if conteudo[:2] == b"\x1f\x8b":            # o IBGE responde compactado (gzip)
            conteudo = gzip.decompress(conteudo)
        with open(arquivo, "wb") as f:
            f.write(conteudo)
    return arquivo
E = create_engine("postgresql+psycopg2://", connect_args={"dbname": "monitoramento_ambiental"})
q = lambda s: gpd.read_postgis(s, E, geom_col="geom")
t = lambda s: pd.read_sql(s, E)

# Paleta Okabe-Ito (segura para daltonismo)
OI = dict(laranja="#E69F00", azul_claro="#56B4E9", verde="#009E73", amarelo="#F0E442",
          azul="#0072B2", vermelho="#D55E00", roxo="#CC79A7", preto="#000000", cinza="#999999")
UC_FILL, UC_EDGE = "#e5ecdc", "#3a3a3a"
FONTE = "Fontes: INPE/TerraBrasilis, MMA (CNUC), IBAMA. Dados de out. 2026. Elaboração: Hendesson Alves."
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "axes.titlesize": 10, "axes.titleweight": "bold"})


def fmt_graus(ax):
    ax.xaxis.set_major_formatter(lambda v, p: f"{abs(v):.2f}°O".replace(".", ","))
    ax.yaxis.set_major_formatter(lambda v, p: f"{abs(v):.2f}°S".replace(".", ","))
    ax.tick_params(labelsize=6.5)
    ax.grid(color="#bbbbbb", linewidth=0.3, linestyle=":")


def quadro(ax, x0, y0, x1, y1):
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(1 / math.cos(math.radians((y0 + y1) / 2)))
    ax.set_xlabel("")
    ax.set_ylabel("")
    fmt_graus(ax)


def escala_norte(ax, km=None, lado="esq"):
    """Barra de escala (em km) e seta do norte, para mapas em graus (EPSG:4674)."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    lat = (y0 + y1) / 2
    km_por_grau = 111.32 * math.cos(math.radians(lat))
    largura_km = (x1 - x0) * km_por_grau
    if km is None:
        km = [k for k in (1, 2, 5, 10, 20, 25, 50, 100, 200, 500) if k <= largura_km / 4][-1]
    dx = km / km_por_grau
    bx = x0 + (x1 - x0) * 0.05 if lado == "esq" else x1 - (x1 - x0) * 0.05 - dx
    by = y0 + (y1 - y0) * 0.05
    h = (y1 - y0) * 0.012
    ax.add_patch(Rectangle((bx, by), dx / 2, h, color="black", zorder=20))
    ax.add_patch(Rectangle((bx + dx / 2, by), dx / 2, h, facecolor="white", edgecolor="black", lw=0.6, zorder=20))
    ef = [pe.withStroke(linewidth=2.5, foreground="white")]
    ax.text(bx, by + h * 1.8, "0", fontsize=6, ha="center", zorder=21, path_effects=ef)
    ax.text(bx + dx, by + h * 1.8, f"{km} km", fontsize=6, ha="center", zorder=21, path_effects=ef)
    nx, ny = x1 - (x1 - x0) * 0.06, y1 - (y1 - y0) * 0.13
    ax.annotate("N", xy=(nx, ny + (y1 - y0) * 0.07), xytext=(nx, ny), ha="center", fontsize=9, weight="bold",
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2), zorder=21, path_effects=ef)


def rodape(fig, texto=FONTE):
    fig.text(0.99, 0.008, texto, ha="right", va="bottom", fontsize=5.8, color="#444")


def salvar(fig, nome):
    fig.savefig(SAIDA + nome, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("ok", nome)


def nome_curto(n):
    n = n.title()
    for a, b in [("Floresta Nacional", "Flona"), ("Parque Nacional", "Parna"), ("Área De Proteção Ambiental", "APA"),
                 ("Floresta Estadual", "Flota"), (" Do ", " do "), (" De ", " de "), (" I", " I")]:
        n = n.replace(a, b)
    return n


def rotular_ucs(ax, ucs, recorte, minimo=0.03, tamanho=6.5):
    ef = [pe.withStroke(linewidth=2.5, foreground="white")]
    for _, r in ucs.iterrows():
        g = r.geom.intersection(recorte)
        if g.is_empty or g.area < minimo:
            continue
        p = g.representative_point()
        ax.text(p.x, p.y, nome_curto(r.nome_uc), fontsize=tamanho, ha="center", va="center",
                style="italic", color="#1d3b1d", path_effects=ef, zorder=15)


# ---------------------------------------------------------------- dados
ucs = q("SELECT cnuc, nome_uc, grupo, categoria, geom FROM limites.ucs")
entorno = q("SELECT cnuc, nome_uc, geom FROM limites.ucs_entorno")
deter = q("SELECT id_alerta, classname, data, local, area_ha, geom FROM desmatamento.deter_ucs")
prodes = q("SELECT id_alerta, ano, local, area_ha, geom FROM desmatamento.prodes_ucs")
emb = q("SELECT id_embargo, num_embargo, data, origem_geom, geom FROM fiscalizacao.embargos")
grupos = q("SELECT id_grupo, num_embargo, geom FROM fiscalizacao.embargos_grupos")
apur = q("SELECT id_alerta, apuracao, classname, geom FROM desmatamento.apuracao_deter")
prio = q("SELECT id_alerta, cluster_id, prioridade, ind_priori, qtd_alertas, geom FROM desmatamento.vw_deter_prioridade")
X0, X1, Y0, Y1 = -56.5, -54.5, -8.45, -5.5
AREA = box(X0, Y0, X1, Y1)

GRUPO_CLASSE = {"DESMATAMENTO_CR": "Desmatamento", "DESMATAMENTO_VEG": "Desmatamento",
                "MINERACAO": "Mineração", "CS_DESORDENADO": "Corte seletivo / degradação",
                "CS_GEOMETRICO": "Corte seletivo / degradação", "DEGRADACAO": "Corte seletivo / degradação",
                "CICATRIZ_DE_QUEIMADA": "Cicatriz de queimada"}
COR_CLASSE = {"Desmatamento": OI["vermelho"], "Mineração": OI["roxo"],
              "Corte seletivo / degradação": OI["laranja"], "Cicatriz de queimada": OI["cinza"]}
deter["grupo_classe"] = deter.classname.map(GRUPO_CLASSE)

# ---------------------------------------------------------------- 1. localização
br = gpd.read_file(baixar("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF&formato=application/vnd.geo+json", "dados/br_uf.geojson"))
amz = gpd.read_file(baixar("https://terrabrasilis.dpi.inpe.br/geoserver/prodes-legal-amz/ows?service=WFS&version=1.0.0"
                          "&request=GetFeature&typeName=prodes-legal-amz:brazilian_legal_amazon&outputFormat=application/json",
                          "dados/amazonia_legal.geojson"))
br5880, amz5880 = br.to_crs(5880), amz.to_crs(5880)
caixa = gpd.GeoSeries([AREA], crs=4674).to_crs(5880)
fig, ax = plt.subplots(figsize=(6, 6))
br5880.plot(ax=ax, facecolor="#f2f2f2", edgecolor="#777", linewidth=0.4)
amz5880.plot(ax=ax, facecolor=OI["verde"], alpha=0.25, edgecolor=OI["verde"], linewidth=0.8)
caixa.plot(ax=ax, facecolor="none", edgecolor=OI["vermelho"], linewidth=2)
c = caixa.iloc[0].centroid
ax.annotate("Área de exemplo\ndo curso", xy=(c.x, c.y), xytext=(c.x + 1.9e6, c.y + 2.5e5), fontsize=8, weight="bold",
            arrowprops=dict(arrowstyle="->", color=OI["vermelho"]), color=OI["vermelho"])
ax.legend(handles=[Patch(facecolor=OI["verde"], alpha=0.4, edgecolor=OI["verde"], label="Amazônia Legal"),
                   Patch(facecolor="none", edgecolor=OI["vermelho"], linewidth=2, label="Recorte de exemplo (Novo Progresso, PA)")],
          loc="lower left", fontsize=7, frameon=True)
ax.set_axis_off()
ax.set_title("Onde fica a área de exemplo")
rodape(fig, "Fontes: IBGE (malha das UFs), INPE (Amazônia Legal). Projeção: SIRGAS 2000 / Policônica do Brasil (EPSG:5880).")
salvar(fig, "localizacao.png")

# ---------------------------------------------------------------- 2. três sistemas de coordenadas
from shapely.geometry import LineString
linhas = [LineString([(x, y) for y in np.linspace(-35, 6, 60)]) for x in range(-75, -29, 10)] + \
         [LineString([(x, y) for x in np.linspace(-75, -30, 60)]) for y in range(-30, 6, 10)]
grade = gpd.GeoDataFrame(geometry=linhas, crs=4674)
fig, axs = plt.subplots(1, 3, figsize=(12, 5.2))
for ax, (epsg, titulo, nota) in zip(axs, [
        (4674, "SIRGAS 2000 geográfico (EPSG:4674)", "Unidade: graus. Bom para guardar\ne cruzar dados."),
        (3857, "Pseudo-Mercator (EPSG:3857)", "Unidade: metros, mas infla as áreas\nlonge do equador. Só para mapas web."),
        (5880, "Policônica do Brasil (EPSG:5880)", "Unidade: metros. Boa para\nmapas do país inteiro.")]):
    grade.to_crs(epsg).plot(ax=ax, color="#9bbbd4", linewidth=0.6)
    b = br.to_crs(epsg)
    b.plot(ax=ax, facecolor="#f2f2f2", edgecolor="#666", linewidth=0.35)
    b[b.codarea.astype(str) == "43"].plot(ax=ax, facecolor=OI["azul_claro"], edgecolor="#333", linewidth=0.5)
    b[b.codarea.astype(str) == "14"].plot(ax=ax, facecolor=OI["laranja"], edgecolor="#333", linewidth=0.5)
    ax.set_title(titulo, fontsize=9)
    ax.text(0.5, -0.02, nota, transform=ax.transAxes, ha="center", va="top", fontsize=8)
    ax.set_axis_off()
fig.legend(handles=[Patch(facecolor=OI["laranja"], label="Roraima (perto do equador)"),
                    Patch(facecolor=OI["azul_claro"], label="Rio Grande do Sul (mais ao sul)"),
                    Line2D([], [], color="#9bbbd4", label="Meridianos e paralelos a cada 10°")],
           loc="lower center", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 0.04))
fig.suptitle("O mesmo Brasil em três sistemas de coordenadas", fontsize=11, weight="bold")
fig.subplots_adjust(bottom=0.2, top=0.88, wspace=0.05)
rodape(fig, "Fonte: IBGE (malha das UFs). Repare na forma da grade e no tamanho do RS em cada mapa.")
salvar(fig, "projecoes.png")

# ---------------------------------------------------------------- 3. vetor x raster
zx0, zy0, zx1, zy1 = -55.13, -6.53, -54.87, -6.27
z = box(zx0, zy0, zx1, zy1)
dz = deter[deter.intersects(z) & deter.classname.isin(["DESMATAMENTO_CR", "DESMATAMENTO_VEG", "MINERACAO"])]
passo = 0.004                                     # ~450 m
xs = np.arange(zx0, zx1, passo)
ys = np.arange(zy0, zy1, passo)
celulas = gpd.GeoDataFrame(geometry=[box(x, y, x + passo, y + passo) for x in xs for y in ys], crs=4674)
uniao = dz.union_all() if hasattr(dz, "union_all") else dz.unary_union
celulas["frac"] = celulas.geometry.intersection(uniao).area / (passo * passo)
fig, axs = plt.subplots(1, 2, figsize=(10, 5.2))
for ax in axs:
    ucs.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.6)
dz.plot(ax=axs[0], color=OI["vermelho"], edgecolor="#5a1a00", linewidth=0.3)
axs[0].set_title("Vetor: polígonos com bordas exatas")
cel = celulas[celulas.frac > 0.3]
cel.plot(ax=axs[1], color=OI["vermelho"], edgecolor="white", linewidth=0.3)
axs[1].set_title("Raster: grade de células (~450 m)")
for ax in axs:
    quadro(ax, zx0, zy0, zx1, zy1)
    escala_norte(ax)
fig.suptitle("Os mesmos alertas de desmatamento como vetor e como raster", fontsize=11, weight="bold")
rodape(fig, "Fonte: INPE (DETER). A grade é ilustrativa: uma célula é marcada quando mais de 30% dela tem desmatamento.")
salvar(fig, "vetor_raster.png")

# ---------------------------------------------------------------- 4. mosaico das fontes
fig, axs = plt.subplots(2, 2, figsize=(10, 12))
(a1, a2), (a3, a4) = axs
ucs_area = ucs.clip(AREA)
# UCs por grupo
cores_grupo = {"Proteção Integral": OI["verde"], "Uso Sustentável": OI["amarelo"]}
for g, cor in cores_grupo.items():
    ucs_area[ucs_area.grupo == g].plot(ax=a1, facecolor=cor, edgecolor=UC_EDGE, linewidth=0.6, alpha=0.8)
rotular_ucs(a1, ucs, AREA, 0.05)
a1.set_title("Unidades de Conservação (CNUC/MMA)")
a1.legend(handles=[Patch(facecolor=OI["verde"], label="Proteção integral"),
                   Patch(facecolor=OI["amarelo"], label="Uso sustentável")], loc="lower right", fontsize=7)
# DETER por classe
for a in (a2, a3, a4):
    ucs_area.plot(ax=a, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.5)
for g, cor in COR_CLASSE.items():
    s = deter[deter.grupo_classe == g]
    if len(s):
        s.plot(ax=a2, color=cor, linewidth=0)
a2.set_title("DETER: alertas desde 2023 (INPE)")
a2.legend(handles=[Patch(color=c, label=g) for g, c in COR_CLASSE.items()], loc="lower right", fontsize=7)
# PRODES por ano
anos = sorted(prodes.ano.unique())
cmap = plt.get_cmap("viridis", len(anos))
for i, a_ in enumerate(anos):
    prodes[prodes.ano == a_].plot(ax=a3, color=cmap(i), linewidth=0)
a3.set_title("PRODES: desmatamento anual (INPE)")
a3.legend(handles=[Patch(color=cmap(i), label=str(a_)) for i, a_ in enumerate(anos)], loc="lower right",
          fontsize=7, title="Ano PRODES", title_fontsize=7, ncol=2)
# Embargos
emb[emb.origem_geom == "Polígono"].plot(ax=a4, facecolor=OI["azul"], edgecolor=OI["azul"], linewidth=0.2, alpha=0.7)
emb[emb.origem_geom == "Ponto"].plot(ax=a4, facecolor="none", edgecolor=OI["vermelho"], linewidth=0.6)
a4.set_title("Áreas embargadas (IBAMA)")
a4.legend(handles=[Patch(facecolor=OI["azul"], alpha=0.7, label="Embargo com polígono"),
                   Patch(facecolor="none", edgecolor=OI["vermelho"], label="Embargo de ponto (círculo)")],
          loc="lower right", fontsize=7)
for a in (a1, a2, a3, a4):
    quadro(a, X0, Y0, X1, Y1)
    escala_norte(a)
fig.suptitle("As quatro bases do curso, no recorte de exemplo", fontsize=12, weight="bold", y=0.995)
fig.tight_layout()
fig.subplots_adjust(bottom=0.035)
rodape(fig)
salvar(fig, "fontes_mosaico.png")

# ---------------------------------------------------------------- 5. interior x entorno
ex0, ey0, ex1, ey1 = -55.75, -6.75, -55.25, -6.2
ze = box(ex0, ey0, ex1, ey1)
fig, ax = plt.subplots(figsize=(7, 7))
ucs.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.8)
entorno.plot(ax=ax, facecolor="none", edgecolor=OI["azul"], linewidth=0.4, hatch="///", alpha=0.6)
d = deter[deter.intersects(ze) & (deter.classname != "CICATRIZ_DE_QUEIMADA")]
d[d.local == "Interior"].plot(ax=ax, color=OI["vermelho"], linewidth=0)
d[d.local == "Entorno"].plot(ax=ax, color=OI["laranja"], linewidth=0)
rotular_ucs(ax, ucs, ze, 0.01, 7.5)
quadro(ax, ex0, ey0, ex1, ey1)
escala_norte(ax, lado="dir")
ax.legend(handles=[Patch(facecolor=UC_FILL, edgecolor=UC_EDGE, label="Unidade de Conservação"),
                   Patch(facecolor="none", edgecolor=OI["azul"], hatch="///", label="Entorno de 3 km (ST_Buffer)"),
                   Patch(color=OI["vermelho"], label="Alerta no interior (recortado pela UC)"),
                   Patch(color=OI["laranja"], label="Alerta no entorno")], loc="lower left", fontsize=7)
ax.set_title("Interior e entorno: como os alertas são classificados")
rodape(fig)
salvar(fig, "interior_entorno.png")

# ---------------------------------------------------------------- 6. embargos de ponto
pts = emb[emb.origem_geom == "Ponto"].copy()
pts["c"] = pts.geometry.centroid
cent = gpd.GeoSeries(pts["c"], crs=4674)
grandes_emb = emb[emb.to_crs(5880).area > 5e7]          # polígonos > 5.000 ha atrapalham a leitura
dens = [(cent.distance(p) < 0.06).sum() if not grandes_emb.intersects(box(p.x - 0.08, p.y - 0.065, p.x + 0.08, p.y + 0.065)).any() else 0
        for p in cent]
i = int(np.argmax(dens))
cx, cy = cent.iloc[i].x, cent.iloc[i].y
cx0, cx1, cy0, cy1 = cx - 0.08, cx + 0.08, cy - 0.065, cy + 0.065
zc = box(cx0, cy0, cx1, cy1)
fig, ax = plt.subplots(figsize=(7, 6))
ucs.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.6)
ep = emb[emb.intersects(zc) & (emb.origem_geom == "Polígono")]
ep.plot(ax=ax, facecolor=OI["azul"], edgecolor="#003a5c", linewidth=0.4, alpha=0.55)
cz = cent[cent.intersects(zc)]
ax.scatter(cz.x, cz.y, marker="X", s=45, color=OI["vermelho"], edgecolor="white", linewidth=0.6, zorder=10)
quadro(ax, cx0, cy0, cx1, cy1)
escala_norte(ax, lado="dir")
ax.legend(handles=[Patch(facecolor=OI["azul"], alpha=0.55, label="origem_geom = 'Polígono': área desenhada"),
                   Line2D([], [], marker="X", color="w", markerfacecolor=OI["vermelho"], markersize=8,
                          label="origem_geom = 'Ponto': só uma coordenada\n(círculo de ~1 m de raio, ampliado aqui)")],
          loc="lower left", fontsize=7)
ax.set_title("Embargos de 'Ponto' não mostram a área embargada")
rodape(fig, "Fonte: IBAMA (áreas embargadas, WFS público). Os pontos foram desenhados como marcadores para ficarem visíveis.")
salvar(fig, "embargos_circulos.png")

# ---------------------------------------------------------------- 7. grupos de embargos (ST_ClusterDBSCAN)
gx0, gx1, gy0, gy1 = -55.2, -54.95, -6.55, -6.35
zg = box(gx0, gy0, gx1, gy1)
fig, axs = plt.subplots(1, 2, figsize=(11, 5))
ev = emb[(emb.origem_geom == "Polígono") & emb.intersects(zg)].copy()
gv = grupos[grupos.intersects(zg)].copy()
paleta = [OI[k] for k in ("azul", "laranja", "verde", "roxo", "vermelho", "azul_claro", "amarelo")]
ev.plot(ax=axs[0], facecolor="#cfd8e3", edgecolor="#333", linewidth=0.5)
axs[0].set_title("Antes: cada embargo separado")
gv = gv.reset_index(drop=True)
gv["cor"] = [paleta[i % len(paleta)] for i in range(len(gv))]
gv.plot(ax=axs[1], color=gv["cor"], edgecolor="#222", linewidth=0.6, alpha=0.85)
axs[1].set_title("Depois: grupos de embargos a até ~66 m, dissolvidos")
for ax in axs:
    quadro(ax, gx0, gy0, gx1, gy1)
    escala_norte(ax)
fig.suptitle("ST_ClusterDBSCAN + ST_UnaryUnion: juntando embargos vizinhos", fontsize=11, weight="bold")
rodape(fig, "Fonte: IBAMA. Cada cor à direita é um grupo (as cores se repetem entre grupos distantes).")
salvar(fig, "grupos_embargos.png")

# ---------------------------------------------------------------- 8. apuração
fig, ax = plt.subplots(figsize=(7.5, 10))
ucs_area.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.6)
emb[emb.origem_geom == "Polígono"].plot(ax=ax, facecolor="#d9d9d9", edgecolor="#9a9a9a", linewidth=0.2)
ad = apur[apur.classname != "CICATRIZ_DE_QUEIMADA"]
ad[ad.apuracao == "Não"].plot(ax=ax, color=OI["laranja"], linewidth=0)
ad[ad.apuracao == "Sim"].plot(ax=ax, color=OI["azul"], edgecolor=OI["azul"], linewidth=0.6)
rotular_ucs(ax, ucs, AREA, 0.05)
quadro(ax, X0, Y0, X1, Y1)
escala_norte(ax)
n_sim, n_tot = (ad.apuracao == "Sim").sum(), len(ad)
ax.legend(handles=[Patch(facecolor="#d9d9d9", edgecolor="#9a9a9a", label="Área embargada (IBAMA)"),
                   Patch(color=OI["azul"], label=f"Alerta apurado: {n_sim}"),
                   Patch(color=OI["laranja"], label=f"Alerta sem embargo: {n_tot - n_sim}")],
          loc="lower right", fontsize=7.5, title="DETER desde 2023 (sem queimadas)", title_fontsize=7.5)
ax.set_title("Apuração: quais alertas já têm embargo cobrindo a área")
rodape(fig)
salvar(fig, "apuracao.png")

# ---------------------------------------------------------------- 9. prioridade (capa)
ORDEM = ["Muito Alta", "Alta", "Média", "Baixa", "Muito Baixa"]
cm = plt.get_cmap("YlOrRd")
COR_PRIO = {"Muito Alta": cm(0.98), "Alta": cm(0.8), "Média": cm(0.6), "Baixa": cm(0.4), "Muito Baixa": cm(0.2),
            "Apurado": OI["azul"]}
fig, ax = plt.subplots(figsize=(7.5, 10))
ucs_area.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.6)
emb[emb.origem_geom == "Polígono"].plot(ax=ax, facecolor="#e3e3e3", edgecolor="#b0b0b0", linewidth=0.2)
deter[deter.grupo_classe.isin(["Desmatamento", "Mineração", "Corte seletivo / degradação"])].plot(
    ax=ax, color="#9e9e9e", linewidth=0)
for k in ["Muito Baixa", "Baixa", "Média", "Alta", "Muito Alta", "Apurado"]:
    s = prio[prio.prioridade == k]
    if len(s):
        s.plot(ax=ax, color=COR_PRIO[k], edgecolor="#222", linewidth=0.3)
rotular_ucs(ax, ucs, AREA, 0.05)
quadro(ax, X0, Y0, X1, Y1)
escala_norte(ax)
cont = prio.prioridade.value_counts()
ax.legend(handles=[Patch(facecolor="#e3e3e3", edgecolor="#b0b0b0", label="Área embargada (IBAMA)"),
                   Patch(color="#9e9e9e", label="Alertas DETER desde 2023")] +
          [Patch(facecolor=COR_PRIO[k], edgecolor="#222", label=f"{k}: {cont.get(k, 0)}") for k in ORDEM + ["Apurado"] if cont.get(k, 0)],
          loc="lower right", fontsize=7.5, title="Prioridade (último ano)", title_fontsize=7.5)
ax.set_title("Prioridade de fiscalização dos alertas do último ano")
rodape(fig)
salvar(fig, "prioridade.png")

# ---------------------------------------------------------------- 10. clusters de alertas
k = prio.groupby("cluster_id").agg(n=("id_alerta", "count")).reset_index()
grandes = k[k.n >= 3].cluster_id.tolist()
sel = prio[prio.cluster_id.isin(grandes)]
bx0, bx1, by0, by1 = -55.25, -54.85, -6.5, -5.87       # região com os maiores clusters
fig, ax = plt.subplots(figsize=(8, 8))
ucs.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.6)
prio[~prio.cluster_id.isin(grandes)].plot(ax=ax, color="#9e9e9e", linewidth=0)
for i, cid in enumerate(grandes):
    s = sel[sel.cluster_id == cid]
    s.plot(ax=ax, color=paleta[i % len(paleta)], edgecolor="#222", linewidth=0.4)
    c = s.union_all().centroid if hasattr(s, "union_all") else s.unary_union.centroid
    if bx0 < c.x < bx1 and by0 < c.y < by1:           # só rotula o que está dentro do quadro
        ax.text(c.x, c.y, f"{len(s)} alertas", fontsize=7, weight="bold", ha="center", clip_on=True,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")], zorder=20)
quadro(ax, bx0, by0, bx1, by1)
escala_norte(ax, lado="dir")
ax.legend(handles=[Patch(color=OI["azul"], label="Cada cor: um cluster com 3 ou mais alertas"),
                   Patch(color="#9e9e9e", label="Clusters com 1 ou 2 alertas")], loc="upper left", fontsize=7)
ax.set_title("Clusters: alertas a até ~66 m e até 6 meses um do outro")
rodape(fig, "Fonte: INPE (DETER), alertas de desmatamento do último ano. Agrupamento com WITH RECURSIVE.")
salvar(fig, "clusters_alertas.png")

# ---------------------------------------------------------------- gráficos
def estilo_grafico(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)


# 11. série mensal do DETER
m = deter[deter.local == "Interior"].copy()
m["mes"] = pd.to_datetime(m.data).dt.to_period("M").dt.to_timestamp()
tab = m.pivot_table(index="mes", columns="grupo_classe", values="area_ha", aggfunc="sum").fillna(0)
tab = tab[[c for c in COR_CLASSE if c in tab.columns]]
fig, ax = plt.subplots(figsize=(10, 4))
base = np.zeros(len(tab))
for col in tab.columns:
    ax.bar(tab.index, tab[col], width=25, bottom=base, color=COR_CLASSE[col], label=col)
    base += tab[col].values
estilo_grafico(ax)
ax.set_ylabel("Área (ha)")
ax.yaxis.set_major_formatter(lambda v, p: f"{v:,.0f}".replace(",", "."))
ax.legend(fontsize=7.5, frameon=False, ncol=4, loc="upper left")
ax.set_title("Alertas DETER no interior das UCs do recorte, por mês e classe")
rodape(fig, "Fonte: INPE (DETER). Recorte: região de Novo Progresso (PA).")
salvar(fig, "serie_mensal_deter.png")

# 12. PRODES anual interior x entorno
p = prodes.pivot_table(index="ano", columns="local", values="area_ha", aggfunc="sum").fillna(0)
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(p))
ax.bar(x - 0.2, p.get("Interior", 0), 0.4, color=OI["vermelho"], label="Interior das UCs")
ax.bar(x + 0.2, p.get("Entorno", 0), 0.4, color=OI["laranja"], label="Entorno de 3 km", hatch="///", edgecolor="white")
ax.set_xticks(x, p.index)
estilo_grafico(ax)
ax.set_ylabel("Área (ha)")
ax.yaxis.set_major_formatter(lambda v, p_: f"{v:,.0f}".replace(",", "."))
ax.legend(fontsize=8, frameon=False)
ax.set_title("Desmatamento PRODES por ano: interior e entorno das UCs")
rodape(fig, "Fonte: INPE (PRODES). Recorte: região de Novo Progresso (PA).")
salvar(fig, "prodes_anual.png")

# 13. percentual apurado por ano
pa = t("""SELECT 'DETER' AS fonte, ano, avg((apuracao='Sim')::int)*100 AS pct FROM desmatamento.apuracao_deter GROUP BY ano
          UNION ALL SELECT 'PRODES', ano, avg((apuracao='Sim')::int)*100 FROM desmatamento.apuracao_prodes GROUP BY ano""")
fig, ax = plt.subplots(figsize=(8, 3.8))
for f, cor, mk in (("DETER", OI["azul"], "o"), ("PRODES", OI["vermelho"], "s")):
    s = pa[pa.fonte == f].sort_values("ano")
    ax.plot(s.ano, s.pct, marker=mk, color=cor, label=f, linewidth=2)
    for _, r in s.iterrows():
        ax.text(r.ano, r.pct + 0.8, f"{r.pct:.0f}%", fontsize=6.5, ha="center", color=cor)
estilo_grafico(ax)
ax.set_ylabel("% de alertas com embargo")
ax.set_xticks(sorted(pa.ano.unique()))
ax.legend(fontsize=8, frameon=False)
ax.set_title("Percentual de alertas apurados por ano (só embargos do IBAMA)")
rodape(fig, "Fontes: INPE (DETER, PRODES), IBAMA (embargos). Critérios do Módulo 4.")
salvar(fig, "apuracao_anual.png")

# 14. funções dos índices de prioridade
fig, axs = plt.subplots(1, 4, figsize=(11, 2.8))
xa = np.linspace(0, 150, 300)
axs[0].plot(xa, np.clip(xa / 100, 0, 1), color=OI["azul"], lw=2); axs[0].set_xlabel("Área do cluster (ha)"); axs[0].set_title("ind_area")
axs[1].step([0, 1, 2, 3, 4, 5], [0, 0, 0.5, 1, 1, 1], where="post", color=OI["azul"], lw=2); axs[1].set_xlabel("Manchas separadas"); axs[1].set_title("ind_cont")
xt = np.linspace(0, 700, 300)
axs[2].plot(xt, np.clip((560 - xt) / 549, 0, 1), color=OI["azul"], lw=2); axs[2].set_xlabel("Dias desde o último alerta"); axs[2].set_title("ind_temp")
xv = np.linspace(0, 5, 300)
axs[3].plot(xv, np.clip(xv / 3, 0, 1), color=OI["azul"], lw=2); axs[3].set_xlabel("Velocidade (ha/dia)"); axs[3].set_title("ind_velo  (peso 1/2)")
for a in axs:
    estilo_grafico(a); a.set_ylim(-0.05, 1.1); a.tick_params(labelsize=7)
axs[0].set_ylabel("Índice (0 a 1)")
fig.suptitle("Como cada medida vira um índice de 0 a 1", fontsize=10, weight="bold", y=1.04)
salvar(fig, "indices_prioridade.png")

# ---------------------------------------------------------------- 15. qualidade: geometria repetida
cunha = emb[emb.geometry.apply(lambda g: g.equals(emb.loc[emb.to_crs(5880).area.idxmax(), "geom"]))]
wx0, wy0, wx1, wy1 = cunha.total_bounds
mx, my = (wx1 - wx0) * 0.35, (wy1 - wy0) * 0.6
fig, ax = plt.subplots(figsize=(7.5, 5.5))
ucs.plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.6)
emb[emb.origem_geom == "Polígono"].plot(ax=ax, facecolor="#d9d9d9", edgecolor="#9a9a9a", linewidth=0.2)
cunha.iloc[[0]].plot(ax=ax, facecolor=OI["vermelho"], alpha=0.35, edgecolor=OI["vermelho"], linewidth=1.5)
c = cunha.iloc[0].geom.representative_point()
ax.annotate(f"{len(cunha)} embargos de set./2008 com o\nmesmo polígono de "
            f"{cunha.iloc[0].geom.area and round(gpd.GeoSeries([cunha.iloc[0].geom], crs=4674).to_crs("ESRI:102033").area.iloc[0] / 1e4):,.0f} ha".replace(",", "."),
            xy=(c.x, c.y), xytext=(c.x + (wx1 - wx0) * 0.25, c.y + (wy1 - wy0) * 0.9), fontsize=8, weight="bold",
            color=OI["vermelho"], arrowprops=dict(arrowstyle="->", color=OI["vermelho"]),
            path_effects=[pe.withStroke(linewidth=3, foreground="white")])
quadro(ax, wx0 - mx, wy0 - my, wx1 + mx, wy1 + my)
escala_norte(ax, lado="dir")
ax.set_title("Qualidade dos dados: o mesmo polígono em vários registros")
rodape(fig, "Fonte: IBAMA (áreas embargadas). Encontrado com: SELECT ... WHERE ST_Equals(geom, ...).")
salvar(fig, "qualidade_geometria_repetida.png")

# ---------------------------------------------------------------- 16. capa horizontal (cartões e redes sociais)
fig, ax = plt.subplots(figsize=(10, 5.6))
kx0, kx1, ky0, ky1 = -56.5, -54.5, -6.95, -5.55
kb = box(kx0, ky0, kx1, ky1)
ucs.clip(kb).plot(ax=ax, facecolor=UC_FILL, edgecolor=UC_EDGE, linewidth=0.7)
emb[emb.origem_geom == "Polígono"].plot(ax=ax, facecolor="#e3e3e3", edgecolor="#b0b0b0", linewidth=0.2)
deter[deter.grupo_classe.isin(["Desmatamento", "Mineração", "Corte seletivo / degradação"])].plot(ax=ax, color="#9e9e9e", linewidth=0)
for k in ["Muito Baixa", "Baixa", "Média", "Alta", "Muito Alta", "Apurado"]:
    s_ = prio[prio.prioridade == k]
    if len(s_):
        s_.plot(ax=ax, color=COR_PRIO[k], edgecolor="#222", linewidth=0.3)
rotular_ucs(ax, ucs, kb, 0.03, 8)
quadro(ax, kx0, ky0, kx1, ky1)
escala_norte(ax)
ax.legend(handles=[Patch(facecolor=COR_PRIO[k], edgecolor="#222", label=k) for k in ["Alta", "Média", "Baixa", "Muito Baixa", "Apurado"]],
          loc="lower right", fontsize=7.5, title="Prioridade", title_fontsize=7.5, ncol=1)
ax.set_title("Prioridade de fiscalização de alertas de desmatamento – Novo Progresso (PA)")
rodape(fig)
salvar(fig, "capa.png")
