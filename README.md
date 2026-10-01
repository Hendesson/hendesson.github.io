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
| `perguntas.qmd` | perguntas frequentes e caixa de perguntas (giscus) |
| `_quarto.yml` | menu, rodapé e tema |
| `styles.scss` | cores e fontes |

## Atualizar o site

Edite os arquivos `.qmd` e rode `git add . && git commit -m "..." && git push`. O GitHub monta e publica o site sozinho em cerca de 2 minutos.

- **Foto:** `imagens/perfil.jpg`.
- **Novo projeto:** crie a pasta `projetos/nome/` com um `index.qmd` (veja `projetos/geocalor/index.qmd`).
- **Mapa de visitantes:** o MapMyVisitors fica no fim de `index.qmd`.

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
3. Em *Settings → Pages → Build and deployment*, escolha **Source: GitHub Actions**.
4. Na aba *Actions*, rode de novo o "Publicar site", se ele tiver falhado antes. Leva uns 2 minutos.
5. O site estará em `https://hendesson.github.io`.

Depois disso, todo `git push` atualiza o site sozinho.

## Ver no seu computador (opcional)

Instale o [Quarto](https://quarto.org/docs/get-started/) e rode `quarto preview` nesta pasta.

## Atualização automática dos projetos

Antes de montar o site, `scripts/atualizar_dados.py` busca no GitHub:

- **todos os repositórios públicos** (descrição, linguagem, última atualização), para a página *Pacotes & Código*;
- do **localdatasus**: versão (do `DESCRIPTION`), novidades (do `NEWS.md`) e citação.

Os resultados vão para `_dados/` e entram nas páginas com `{{< include >}}`.

O site é montado de novo:
1. a cada `git push` neste repositório;
2. **todo dia às 6h** (horário de Brasília);
3. **na hora**, quando o localdatasus recebe um push. Isso precisa do segredo `SITE_TOKEN` no repositório do localdatasus (veja abaixo).

Para ver as mudanças antes no seu computador: `python3 scripts/atualizar_dados.py && quarto preview`.

Para esconder um repositório da lista, acrescente o nome em `OCULTAR`, no topo do script.

### Aviso imediato (opcional)

1. Crie um token em <https://github.com/settings/personal-access-tokens/new> (*fine-grained*):
   - **Repository access:** *Only select repositories* → `hendesson.github.io`;
   - **Permissions → Repository permissions → Contents:** *Read and write*.
2. No repositório **localdatasus**: *Settings → Secrets and variables → Actions → New repository secret*. Use o nome `SITE_TOKEN` e cole o token.
3. Para fazer o mesmo em outro projeto, copie o arquivo `.github/workflows/avisar-site.yml` do localdatasus para ele e crie o mesmo segredo.

## Caixa de perguntas (giscus), uma vez

A página **Perguntas** usa o [giscus](https://giscus.app): as perguntas ficam nas *Discussions* deste repositório. Para ligar:

1. Em *Settings → General → Features*, marque **Discussions**.
2. Instale o app do giscus em <https://github.com/apps/giscus>, escolhendo só o repositório `hendesson.github.io`.
3. Faça qualquer `git push` (ou rode de novo a ação "Publicar site"): a caixa aparece no fim da página.

Para responder, vá à aba *Discussions* do repositório, ou responda direto no site.

## Novo tutorial

Crie `tutoriais/localdatasus/07-nome.qmd` com `ordem: 7` e acrescente-o à barra lateral em `_quarto.yml`.
