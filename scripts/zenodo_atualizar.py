"""Atualiza os rascunhos do Zenodo (metadados de _zenodo/*.json) e anexa os PDFs de ~/zenodo_pdfs.
Não publica nada: a publicação é feita por você, no site do Zenodo.

Uso:  export ZENODO_TOKEN=seu_token
      python scripts/zenodo_atualizar.py
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = "https://zenodo.org/api/deposit/depositions"
TOKEN = os.environ.get("ZENODO_TOKEN") or sys.exit("Defina a variável ZENODO_TOKEN.")
PDFS = Path.home() / "zenodo_pdfs"


def pedir(url, metodo="GET", dados=None, tipo="application/json"):
    pedido = urllib.request.Request(url, data=dados, method=metodo,
                                    headers={"Authorization": f"Bearer {TOKEN}",
                                             "Content-Type": tipo})
    try:
        with urllib.request.urlopen(pedido) as r:
            corpo = r.read()
    except urllib.error.HTTPError as erro:
        sys.exit(f"Zenodo recusou ({erro.code}) {url}:\n{erro.read().decode()[:800]}")
    return json.loads(corpo) if corpo else {}


dois = dict(re.findall(r'^(\S+): "(10\.5281/zenodo\.\d+)"', (RAIZ / "dois.yml").read_text(), re.M))
for arq in sorted((RAIZ / "_zenodo").glob("*.json")):
    registro = json.loads(arq.read_text(encoding="utf-8"))
    doi = dois.get(registro["chave"])
    if not doi:
        print("sem DOI reservado:", registro["chave"])
        continue
    numero = doi.split(".")[-1]
    atual = pedir(f"{BASE}/{numero}")
    meta = {**atual["metadata"], **registro["metadata"]}          # mantém o DOI reservado
    pedir(f"{BASE}/{numero}", "PUT", json.dumps({"metadata": meta}).encode())

    # PDF: artigo NN em inglês, ou o guia com o curso
    nn = Path(registro["chave"]).name[:2]
    pdf = (next(PDFS.glob(f"article-{nn}-*.pdf"), None) if registro["chave"].startswith("artigos/")
           else PDFS / "guia-dados-espaciais-e-curso.pdf")
    if pdf and pdf.exists() and not any(f["filename"] == pdf.name for f in atual.get("files", [])):
        pedir(f"{atual['links']['bucket']}/{pdf.name}", "PUT", pdf.read_bytes(),
              "application/octet-stream")
    print(f"ok  {doi}  {meta['title'][:60]}  + {pdf.name if pdf else 'sem PDF'}")
