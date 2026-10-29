"""Copia os DOIs de dois.yml para as páginas do site.

Uso (na pasta do site):  python scripts/aplicar_doi.py
- guia-espacial: vai para guia-espacial/_metadata.yml (vale para o guia e o curso inteiro);
- artigos/...qmd: vai para o cabeçalho de cada artigo e da versão em inglês (_en/articles).
Um DOI vazio remove o campo. Rode de novo sempre que mudar o dois.yml.
"""
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
FORMATO = re.compile(r"^10\.\d{4,9}/\S+$")


def colocar_doi(arquivo, doi, dentro_de_cabecalho):
    texto = arquivo.read_text(encoding="utf-8")
    if dentro_de_cabecalho:
        _, cabecalho, corpo = texto.split("---\n", 2)
    else:
        cabecalho, corpo = texto, None
    cabecalho = re.sub(r"^doi: .*\n", "", cabecalho, flags=re.M)
    if doi:
        cabecalho = cabecalho.rstrip("\n") + f"\ndoi: {doi}\n"
    novo = f"---\n{cabecalho}---\n{corpo}" if dentro_de_cabecalho else cabecalho
    arquivo.write_text(novo, encoding="utf-8")


dois = yaml.safe_load((RAIZ / "dois.yml").read_text(encoding="utf-8")) or {}
erros = [f"{k}: {v}" for k, v in dois.items() if v and not FORMATO.match(str(v))]
if erros:
    sys.exit("DOI em formato errado (use 10.5281/zenodo.1234567):\n  " + "\n  ".join(erros))

for chave, doi in dois.items():
    doi = str(doi or "").strip()
    if chave == "guia-espacial":
        colocar_doi(RAIZ / "guia-espacial/_metadata.yml", doi, dentro_de_cabecalho=False)
    else:
        colocar_doi(RAIZ / chave, doi, dentro_de_cabecalho=True)
        # a versão em inglês do artigo (mesmo número no começo do nome) recebe o mesmo DOI
        numero = Path(chave).name[:2]
        for ingles in (RAIZ / "_en/articles").glob(f"{numero}-*.qmd"):
            colocar_doi(ingles, doi, dentro_de_cabecalho=True)
    print(f"{'DOI ' + doi if doi else 'sem DOI':32} {chave}")
