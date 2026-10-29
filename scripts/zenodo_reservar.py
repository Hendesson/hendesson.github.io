"""Cria rascunhos no Zenodo e reserva um DOI para cada um, sem publicar nada.

Uso (na pasta do site, depois do zenodo_metadados.py):
    export ZENODO_TOKEN=seu_token        # zenodo.org > Applications > Personal access tokens
    python scripts/zenodo_reservar.py            # Zenodo de verdade
    python scripts/zenodo_reservar.py --teste    # sandbox.zenodo.org, para treinar

O script grava os DOIs reservados no dois.yml. Os rascunhos ficam na sua conta: para publicar,
anexe um arquivo (o PDF da página, por exemplo) e clique em "Publish" no site do Zenodo.
Um DOI só passa a funcionar depois de publicado.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = "https://sandbox.zenodo.org" if "--teste" in sys.argv else "https://zenodo.org"
TOKEN = os.environ.get("ZENODO_TOKEN") or sys.exit("Defina a variável ZENODO_TOKEN.")


def criar_rascunho(metadata):
    corpo = json.dumps({"metadata": {**metadata, "prereserve_doi": True}}).encode()
    pedido = urllib.request.Request(f"{BASE}/api/deposit/depositions", data=corpo, method="POST",
                                    headers={"Content-Type": "application/json",
                                             "Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(pedido) as r:
        resposta = json.load(r)
    return resposta["metadata"]["prereserve_doi"]["doi"], resposta["links"]["html"]


dois_txt = (RAIZ / "dois.yml").read_text(encoding="utf-8")
for arq in sorted((RAIZ / "_zenodo").glob("*.json")):
    registro = json.loads(arq.read_text(encoding="utf-8"))
    chave = registro["chave"]
    if re.search(rf'^{re.escape(chave)}: "10\.', dois_txt, flags=re.M):
        print("já tem DOI:", chave)
        continue
    doi, link = criar_rascunho(registro["metadata"])
    dois_txt = re.sub(rf'^{re.escape(chave)}: ".*"', f'{chave}: "{doi}"', dois_txt, flags=re.M)
    (RAIZ / "dois.yml").write_text(dois_txt, encoding="utf-8")
    print(f"{doi}  {chave}  (rascunho: {link})")
