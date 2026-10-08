"""Busca no GitHub os dados dos projetos e grava trechos de texto em _dados/,
que as páginas do site incluem. Roda antes de montar o site (no GitHub
Actions) e também pode ser rodado à mão: python3 scripts/atualizar_dados.py

Gera, em português (_dados/) e em inglês (_en/_dados/):
  repositorios.md          tabela com todos os repositórios públicos
  localdatasus_versao.md   versão atual do localdatasus
  localdatasus_novidades.md   o NEWS.md do localdatasus
  localdatasus_citacao.md  como citar (Alves, Hendesson)
"""
import json
import os
import re
import urllib.request
from pathlib import Path

USUARIO = "Hendesson"
PACOTE = "localdatasus"
# Repositórios que não aparecem na tabela (site, perfil e testes).
OCULTAR = {"hendesson.github.io", "Hendesson", "ascii-rain.svg", "blog", "teste_dash"}
RAIZ = Path(__file__).resolve().parent.parent
PASTAS = {"pt": RAIZ / "_dados", "en": RAIZ / "_en" / "_dados"}


def baixar(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": "site-hendesson"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        pedido.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(pedido, timeout=60) as resposta:
        return resposta.read().decode("utf-8")


def gravar(nome, texto, idioma="pt"):
    pasta = PASTAS[idioma]
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_text(texto.strip() + "\n", encoding="utf-8")
    print("atualizado:", pasta.name if idioma == "pt" else "_en/_dados", nome)


def tabela_repositorios():
    repos = json.loads(baixar(f"https://api.github.com/users/{USUARIO}/repos?per_page=100&sort=pushed"))
    cabecalho = {
        "pt": ["| Repositório | Linguagem | Descrição | Atualizado em |", "|---|---|---|---|"],
        "en": ["| Repository | Language | Description | Last update |", "|---|---|---|---|"],
    }
    linhas = {"pt": list(cabecalho["pt"]), "en": list(cabecalho["en"])}
    for r in repos:
        if r["fork"] or r["private"] or r["name"] in OCULTAR:
            continue
        descricao = (r["description"] or "—").replace("|", "/").strip()
        linguagem = r["language"] or "—"
        ano, mes, dia = r["pushed_at"][:4], r["pushed_at"][5:7], r["pushed_at"][8:10]
        link = f"[{r['name']}]({r['html_url']})"
        linhas["pt"].append(f"| {link} | {linguagem} | {descricao} | {dia}/{mes}/{ano} |")
        linhas["en"].append(f"| {link} | {linguagem} | {descricao} | {ano}-{mes}-{dia} |")
    gravar("repositorios.md", "\n".join(linhas["pt"]), "pt")
    gravar("repositorios.md", "\n".join(linhas["en"]), "en")


DOI = "10.5281/zenodo.23244742"   # DOI geral do localdatasus no Zenodo (todas as versões)


def dados_do_pacote():
    bruto = f"https://raw.githubusercontent.com/{USUARIO}/{PACOTE}/main/"
    descricao = baixar(bruto + "DESCRIPTION")
    versao = re.search(r"^Version:\s*(\S+)", descricao, re.M).group(1)
    titulo = re.search(r"^Title:\s*(.+)", descricao, re.M).group(1).strip()
    repo = json.loads(baixar(f"https://api.github.com/repos/{USUARIO}/{PACOTE}"))
    ano = repo["created_at"][:4]

    # O título do DESCRIPTION está em inglês (exigência prática do CRAN); a
    # citação usa o título em português, o mesmo do Zenodo e do inst/CITATION.
    citacao = (f"> Alves, Hendesson ({ano}). *{PACOTE}: dados de saúde do SUS por bairro*. "
               "{rotulo} {versao}. <https://doi.org/" + DOI + ">")
    gravar("localdatasus_versao.md", f"Versão atual: **{versao}**", "pt")
    gravar("localdatasus_versao.md", f"Current version: **{versao}**", "en")
    gravar("localdatasus_citacao.md", citacao.format(rotulo="Pacote R, versão", versao=versao), "pt")
    gravar("localdatasus_citacao.md", citacao.format(rotulo="R package version", versao=versao), "en")
    try:
        novidades = baixar(bruto + "NEWS.md")
        # Os títulos do NEWS.md ("# localdatasus 0.1.0") viram subtítulos da página.
        novidades = re.sub(r"^# ", "### ", novidades, flags=re.M)
    except Exception:
        novidades = "Sem novidades registradas."
    gravar("localdatasus_novidades.md", novidades, "pt")
    gravar("localdatasus_novidades.md", "*(The changelog is written in Portuguese.)*\n\n" + novidades, "en")


if __name__ == "__main__":
    tabela_repositorios()
    dados_do_pacote()
