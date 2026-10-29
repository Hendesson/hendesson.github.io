"""Gera um arquivo de metadados do Zenodo (_zenodo/*.json) para o guia e para cada artigo.

Uso (na pasta do site):  python scripts/zenodo_metadados.py
Os arquivos servem para preencher o formulário do Zenodo ou para o zenodo_reservar.py.
"""
import json
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SITE = "https://hendesson.github.io"
AUTOR = [{"name": "Alves, Hendesson"}]


def cabecalho(arquivo):
    return yaml.safe_load(arquivo.read_text(encoding="utf-8").split("---\n", 2)[1])


def metadados(titulo, resumo, url, palavras, tipo, data):
    return {
        "title": titulo,
        "upload_type": "publication",
        "publication_type": tipo,
        "description": resumo,
        "creators": AUTOR,
        "keywords": palavras,
        "language": "por",
        "license": "cc-by-4.0",
        "access_right": "open",
        "publication_date": data,
        "related_identifiers": [
            {"identifier": url, "relation": "isIdenticalTo", "resource_type": "publication"}],
    }


saida = RAIZ / "_zenodo"
saida.mkdir(exist_ok=True)
registros = {}

guia = cabecalho(RAIZ / "guia-espacial/index.qmd")
registros["guia-espacial"] = metadados(
    guia["title"], guia["description"], f"{SITE}/guia-espacial/",
    ["monitoramento ambiental", "PostGIS", "SQL", "Power BI", "dados espaciais", "Amazônia"],
    "book", str(guia.get("date", "2026-10-29")))

for arq in sorted((RAIZ / "artigos").glob("[0-9]*.qmd")):
    c = cabecalho(arq)
    registros[f"artigos/{arq.name}"] = metadados(
        c["title"], c.get("abstract", c["description"]),
        f"{SITE}/artigos/{arq.stem}.html",
        c.get("categories", []) + ["geoprocessamento", "monitoramento ambiental"],
        "technicalnote", str(c["date"]))

for chave, meta in registros.items():
    nome = re.sub(r"[^a-z0-9-]+", "-", chave.lower().replace(".qmd", "")).strip("-")
    (saida / f"{nome}.json").write_text(json.dumps({"chave": chave, "metadata": meta},
                                                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("ok", nome + ".json")
