# Site pessoal

Site feito com [Quarto](https://quarto.org) e publicado no GitHub Pages: projetos, currículo, códigos e tutoriais do [localdatasus](projetos/localdatasus/index.qmd).

## Estrutura

| Arquivo / pasta | Página |
|---|---|
| `index.qmd` | início: foto, apresentação e links |
| `cv.qmd` | currículo (o PDF vai em `documentos/cv.pdf`) |
| `projetos.qmd` + `projetos/*/index.qmd` | projetos (um card por pasta) |
| `codigo.qmd` | pacotes e repositórios |
| `tutoriais.qmd` + `tutoriais/localdatasus/*.qmd` | tutoriais do localdatasus |
| `documentos.qmd` + `documentos/` | PDFs, slides e notas técnicas |
| `blog.qmd` + `posts/*/index.qmd` | blog (um post por pasta) |
| `_quarto.yml` | menu, rodapé e tema |
| `styles.scss` | cores e fontes |

## O que trocar antes de publicar

Procure por `Hendesson`, `SEU_EMAIL` e `TROQUE` nos arquivos:

- `_quarto.yml`: `site-url` e links do GitHub;
- `index.qmd`: apresentação e links (GitHub, ORCID, Lattes, Scholar, e-mail);
- `imagens/perfil.svg`: troque por uma foto sua (`imagens/perfil.jpg`) e ajuste `image:` em `index.qmd`;
- `cv.qmd`: formação, experiência e publicações.

## Publicar (uma vez)

1. No GitHub, crie um repositório chamado **`hendesson.github.io`** (público, vazio).
2. No terminal:
   ```bash
   cd ~/site_pessoal
   git init -b main
   git add .
   git commit -m "Primeira versão do site"
   git remote add origin https://github.com/Hendesson/hendesson.github.io.git
   git push -u origin main
   ```
3. Espere a ação "Publicar site" terminar (aba *Actions* do repositório, ~2 min).
4. Em *Settings → Pages*, escolha **Branch: `gh-pages`** e salve.
5. O site estará em `https://hendesson.github.io`.

Depois disso, todo `git push` atualiza o site sozinho.

## Ver no seu computador (opcional)

Instale o [Quarto](https://quarto.org/docs/get-started/) e rode `quarto preview` nesta pasta.

## Novo post ou novo tutorial

- **Post:** crie `posts/AAAA-MM-DD-titulo/index.qmd` com `title`, `date`, `description` e `categories`.
- **Tutorial:** crie `tutoriais/localdatasus/07-nome.qmd` com `ordem: 7` e acrescente-o à barra lateral em `_quarto.yml`.
