# Site Próximo Curso: publicação e coleta de avaliações

O site faz até cinco perguntas rápidas e recomenda cursos da Coursera usando o modelo híbrido do projeto (α = 0,4; 30 vizinhos no KNN; TF-IDF). Tudo roda no navegador: o modelo já vai calculado dentro do `docs/index.html`.

## Arquivos

| Arquivo | O que é |
|---|---|
| `preparar_dados.py` | Treina o modelo com os CSVs do Kaggle e gera `modelo.json` e `sim_conteudo.b64` |
| `traducoes.py` | Nomes dos 623 cursos em português |
| `template.html` | Código do site, sem os dados |
| `painel.html` | Código do painel de avaliação |
| `montar_site.py` | Junta tudo e grava `../docs/index.html` e `../docs/painel.html` |
| `coleta_apps_script.gs` | Script da planilha Google que guarda as avaliações e entrega os números ao painel |
| `analise_coleta.py` | Análise completa dos dados coletados (rodar no Colab) |

## 1. Publicar o site (GitHub Pages)

1. No repositório, abra **Settings → Pages**.
2. Em *Source*, escolha **Deploy from a branch**. Depois escolha a branch `main` e a pasta **`/docs`**, e clique em **Save**.
3. Em um ou dois minutos, o site fica no ar em `https://brunocerqueiragianotti.github.io/proximo-curso/`.

## 2. Ligar a coleta de avaliações (Google Planilhas)

Sem esta etapa o site funciona normalmente, mas não registra nada, e o painel mostra dados de exemplo.

**Criar a planilha e o script**

1. No Google Drive, crie uma planilha nova. Sugestão de nome: `Próximo Curso - coleta`.
2. Na planilha, abra **Extensões → Apps Script**.
3. Apague o código que aparece, cole todo o conteúdo de `coleta_apps_script.gs` e clique em **Salvar**.

**Publicar o script**

4. Clique em **Implantar → Nova implantação** e, na engrenagem, escolha **App da Web**.
5. Em *Executar como*, escolha **Eu**. Em *Quem pode acessar*, escolha **Qualquer pessoa**.
6. Clique em **Implantar** e autorize com a sua conta Google. O Google avisa que o app não foi verificado, porque o script é de vocês: clique em **Avançado → Acessar** e depois em **Permitir**.
7. Copie o **URL do App da Web**. Ele começa com `https://script.google.com/macros/s/` e termina em `/exec`.
8. Para testar, abra esse endereço no navegador. Deve aparecer `{"ok":true,"mensagem":"Coleta do Próximo Curso ativa"}`.

**Ligar no site e no painel**

9. No GitHub, abra `docs/index.html`, clique no lápis (**Edit**) e encontre, no começo do arquivo:
   ```js
   window.PROXIMO_CURSO_CONFIG = { endpoint: "" };
   ```
   Cole o endereço entre as aspas e clique em **Commit changes**.
10. Faça o mesmo em `docs/painel.html`.
11. Para testar, use o site, dê uma nota e responda o questionário. Depois confira se apareceram linhas na aba `eventos` da planilha e números no painel.

> Se mudar o código do script, publique em **Implantar → Gerenciar implantações → Editar → Versão: Nova versão**. Assim o endereço continua o mesmo.

### O que fica na planilha

Fica uma linha por acontecimento na aba `eventos`. Não há nome, e-mail ou dado que identifique a pessoa. A coluna `sessao` é um código aleatório de cada visita.

| Evento | Quando acontece |
|---|---|
| `recomendacao` | A pessoa termina as perguntas e recebe a lista |
| `clique_coursera` | Clicou para abrir um curso (colunas `curso` e `posicao`) |
| `mais_como_este` / `desmarcou` | Marcou ou desmarcou um curso como interessante |
| `nao_e_pra_mim` | Descartou um curso |
| `ver_mais` | Pediu mais cursos |
| `avaliacao` | Deu a nota de utilidade de 1 a 5, com comentário opcional |
| `usabilidade` | Respondeu o questionário SUS (`sus_1` a `sus_10`, `sus_score`) e a intenção de fazer algum curso (`intencao`) |

O painel (`docs/painel.html`) busca no script apenas números agregados (`?resumo=1`). Linhas individuais, temas digitados e comentários não saem da planilha.

## 3. Analisar os dados (Etapa 4)

1. Na planilha, com a aba `eventos` aberta, clique em **Arquivo → Fazer download → Valores separados por vírgula (.csv)**.
2. No Colab, suba o arquivo com o nome `eventos.csv` e rode o `analise_coleta.py`.

O script calcula:
- sessões e taxa de cliques;
- uso do "Mais como este";
- nota média;
- cliques por posição;
- cursos mais clicados;
- resultados por tipo de usuário;
- comentários;
- pontuação SUS (média, faixas e média por afirmação);
- intenção de fazer os cursos.

Ele também salva `graficos_coleta.png` para o relatório.

## 4. Gerar o site de novo (opcional)

Só é preciso se o modelo ou o código mudar. Rode dentro da pasta `site/`, com os CSVs do Kaggle em `PASTA_COM_OS_CSVS`:

```bash
python preparar_dados.py PASTA_COM_OS_CSVS modelo.json
python montar_site.py .                                                  # sem coleta
python montar_site.py . "https://script.google.com/macros/s/.../exec"    # com a coleta ligada
```
