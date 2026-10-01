"""Busca no GitHub os dados dos projetos e grava trechos de texto em _dados/,
que as páginas do site incluem. Roda antes de montar o site (no GitHub
Actions) e também pode ser rodado à mão: python3 scripts/atualizar_dados.py

Gera:
  _dados/repositorios.md          tabela com todos os repositórios públicos
  _dados/localdatasus_versao.md   versão atual do localdatasus
  _dados/localdatasus_novidades.md   o NEWS.md do localdatasus
  _dados/localdatasus_citacao.md  como citar (Alves, Hendesson)
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
PASTA = Path(__file__).resolve().parent.parent / "_dados"


def baixar(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": "site-hendesson"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        pedido.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(pedido, timeout=60) as resposta:
        return resposta.read().decode("utf-8")


def gravar(nome, texto):
    PASTA.mkdir(exist_ok=True)
    (PASTA / nome).write_text(texto.strip() + "\n", encoding="utf-8")
    print("atualizado:", nome)


def tabela_repositorios():
    repos = json.loads(baixar(f"https://api.github.com/users/{USUARIO}/repos?per_page=100&sort=pushed"))
    linhas = [
        "| Repositório | Linguagem | Descrição | Atualizado em |",
        "|---|---|---|---|",
    ]
    for r in repos:
        if r["fork"] or r["private"] or r["name"] in OCULTAR:
            continue
        descricao = (r["description"] or "—").replace("|", "/").strip()
        linguagem = r["language"] or "—"
        dia, mes, ano = r["pushed_at"][8:10], r["pushed_at"][5:7], r["pushed_at"][:4]
        linhas.append(f"| [{r['name']}]({r['html_url']}) | {linguagem} | {descricao} | {dia}/{mes}/{ano} |")
    gravar("repositorios.md", "\n".join(linhas))


def dados_do_pacote():
    bruto = f"https://raw.githubusercontent.com/{USUARIO}/{PACOTE}/main/"
    descricao = baixar(bruto + "DESCRIPTION")
    versao = re.search(r"^Version:\s*(\S+)", descricao, re.M).group(1)
    titulo = re.search(r"^Title:\s*(.+)", descricao, re.M).group(1).strip()
    repo = json.loads(baixar(f"https://api.github.com/repos/{USUARIO}/{PACOTE}"))
    ano = repo["created_at"][:4]

    gravar("localdatasus_versao.md", f"Versão atual: **{versao}**")
    gravar("localdatasus_citacao.md",
           f"> Alves, Hendesson ({ano}). *{PACOTE}: {titulo}*. Pacote R, versão {versao}. "
           f"<https://github.com/{USUARIO}/{PACOTE}>")
    try:
        novidades = baixar(bruto + "NEWS.md")
        # Os títulos do NEWS.md ("# localdatasus 0.1.0") viram subtítulos da página.
        novidades = re.sub(r"^# ", "### ", novidades, flags=re.M)
    except Exception:
        novidades = "Sem novidades registradas."
    gravar("localdatasus_novidades.md", novidades)


if __name__ == "__main__":
    tabela_repositorios()
    dados_do_pacote()
