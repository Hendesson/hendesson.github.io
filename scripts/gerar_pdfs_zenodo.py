"""Gera os PDFs para anexar no Zenodo: um por artigo e um com o guia e o curso inteiros.

Uso (na pasta do site, depois do quarto render):
    python scripts/gerar_pdfs_zenodo.py            # PDFs em ~/zenodo_pdfs
Precisa do Google Chrome (ou Chromium) e do pdfunite (poppler-utils).
As abas de programa (ArcGIS Pro, QGIS, PostGIS, Python...) saem todas, uma depois da outra.
"""
import functools
import http.server
import re
import shutil
import subprocess
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / "_site"
SAIDA = Path.home() / "zenodo_pdfs"
SAIDA.mkdir(exist_ok=True)
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
PORTA = 8799

ESTILO_PDF = """<style>
  .tab-content > .tab-pane { display: block !important; opacity: 1 !important; }
  .panel-tabset .nav-tabs, #quarto-header, #quarto-sidebar, #quarto-margin-sidebar,
  .navegacao-livro, .code-copy-button, .quarto-listing { display: none !important; }
  .rotulo-aba { font-size: 1rem; border-bottom: 2px solid #0072B2; margin: 1.2rem 0 .5rem;
                padding-bottom: .2rem; color: #0072B2; }
  pre, figure, .callout { break-inside: avoid; }
  pre code { white-space: pre-wrap !important; }
</style>"""


def versao_para_pdf(html):
    """Põe o nome do programa antes de cada aba e as regras de impressão."""
    rotulos = {}
    for tag, nome in re.findall(r'(<a[^>]*class="nav-link[^"]*"[^>]*>)(.*?)</a>', html, re.S):
        alvo = re.search(r'aria-controls="([^"]+)"', tag)
        if alvo:
            rotulos[alvo.group(1)] = nome.strip()
    for pane, nome in rotulos.items():
        html = re.sub(rf'(<div[^>]*id="{re.escape(pane)}"[^>]*class="tab-pane[^"]*"[^>]*>)',
                      rf'\1<h3 class="rotulo-aba">{nome}</h3>', html, count=1)
    # sem as classes de aba, nenhuma regra do site esconde as versões que não estão abertas
    html = html.replace('class="tab-pane', 'class="pane-pdf').replace('class="tab-content', 'class="conteudo-pdf')
    return html.replace("</head>", ESTILO_PDF + "</head>")


def imprimir(caminho_html, pdf):
    temporario = caminho_html.with_name("_pdf_" + caminho_html.name)
    temporario.write_text(versao_para_pdf(caminho_html.read_text(encoding="utf-8")), encoding="utf-8")
    url = f"http://localhost:{PORTA}/{temporario.relative_to(SITE)}"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--virtual-time-budget=8000",
                    f"--print-to-pdf={pdf}", url], check=True, capture_output=True)
    temporario.unlink()
    print("ok", pdf.name)


servidor = http.server.ThreadingHTTPServer(
    ("localhost", PORTA),
    functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE)))
threading.Thread(target=servidor.serve_forever, daemon=True).start()
try:
    for html in sorted((SITE / "en/articles").glob("[0-9]*.html")):     # artigos: em inglês
        imprimir(html, SAIDA / f"article-{html.stem}.pdf")

    partes = []
    paginas = ([SITE / "guia-espacial/index.html"]
               + sorted((SITE / "guia-espacial/guia").glob("*.html"))
               + sorted((SITE / "guia-espacial/curso").glob("*.html")))
    for i, html in enumerate(paginas):
        parte = SAIDA / f"_parte_{i:02d}.pdf"
        imprimir(html, parte)
        partes.append(parte)
    final = SAIDA / "guia-dados-espaciais-e-curso.pdf"
    subprocess.run(["pdfunite", *map(str, partes), str(final)], check=True)
    for parte in partes:
        parte.unlink()
    print("ok", final.name)
finally:
    servidor.shutdown()
print("PDFs em", SAIDA)
