# DOIs do Zenodo: passo a passo

Cada artigo e o guia (com o curso) podem ter um DOI próprio no Zenodo. O DOI aparece no bloco
"Como citar" de cada página e nos metadados que o Google Acadêmico lê.

Esta pasta fica fora do site publicado: o Quarto ignora pastas que começam com `_`.

## Quantos DOIs

- 1 para o **guia e o curso** (`guia-espacial` no `dois.yml`), tratado como um livro;
- 1 para **cada artigo** (13).

## Caminho A: pelo site do Zenodo (sem programar)

1. Entre em <https://zenodo.org> com a sua conta (dá para entrar com o GitHub ou o ORCID).
2. **New upload**.
3. Em **Digital Object Identifier**, clique em **Get a DOI now!** (reserva o DOI antes de publicar).
4. Preencha com os dados do arquivo `_zenodo/<artigo>.json` desta pasta: título, autores, resumo,
   palavras-chave, licença CC BY 4.0, idioma português e o link da página em **Related works**
   ("Is identical to").
5. Anexe um arquivo: o PDF da página (no navegador, **Imprimir → Salvar como PDF**) ou os scripts.
6. Copie o DOI reservado para a linha certa do `dois.yml`.
7. Clique em **Publish**. O DOI só funciona depois de publicado, e um registro publicado **não pode
   ser apagado** (só ganhar versões novas).

## Caminho B: pela API, com os scripts

```bash
python scripts/zenodo_metadados.py          # gera _zenodo/*.json a partir das páginas
export ZENODO_TOKEN=seu_token               # zenodo.org > Applications > Personal access tokens
python scripts/zenodo_reservar.py --teste   # primeiro no sandbox.zenodo.org, para treinar
python scripts/zenodo_reservar.py           # depois no Zenodo de verdade
```

O `zenodo_reservar.py` cria **rascunhos** e reserva os DOIs, sem publicar nada, e grava os DOIs no
`dois.yml`. Depois, no site do Zenodo, anexe o arquivo de cada rascunho e clique em **Publish**.

Dê ao token só as permissões `deposit:write` e `deposit:actions`, e nunca o grave em arquivo do site.

## Colocar os DOIs no site

```bash
python scripts/aplicar_doi.py
quarto preview
```

## Versões novas

Quando atualizar um artigo de forma importante (dados novos, correção de resultado), abra o registro
no Zenodo, clique em **New version** e anexe o arquivo novo. O Zenodo dá um DOI para a versão e mantém
um DOI geral ("concept DOI") que sempre aponta para a mais recente. Use o DOI geral no `dois.yml`
e registre a mudança na seção **Atualizações** do artigo e no campo `date-modified`.
