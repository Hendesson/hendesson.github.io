#!/usr/bin/env bash
# Monta o site completo: português em _site/ e inglês em _site/en/.
# Uso: bash scripts/montar_site.sh   (precisa do Quarto instalado)
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/atualizar_dados.py     # dados do GitHub (as duas línguas)
quarto render                          # português -> _site/

# A versão em inglês usa as mesmas imagens e o mesmo estilo.
rm -rf _en/imagens && cp -r imagens _en/imagens
cp styles.scss _en/styles.scss
quarto render _en                      # inglês -> _site/en/
