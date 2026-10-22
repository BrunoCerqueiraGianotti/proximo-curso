# Próximo Curso

**Recomendação de Cursos Online para Desenvolvimento Profissional: uma Aplicação de Filtragem Colaborativa e Baseada em Conteúdo**

Projeto Aplicado III · Universidade Presbiteriana Mackenzie · São Paulo, 2026

Bruno Cerqueira Gianotti · Reginaldo Rogério de Campos · Samya Camily de Santana Silva

---

## Links

| | |
|---|---|
| Site para a comunidade | https://brunocerqueiragianotti.github.io/proximo-curso/ |
| Painel de avaliação de uso | https://brunocerqueiragianotti.github.io/proximo-curso/painel.html |
| Notebook atual (Etapa 3) | [`etapa-3-metodologia/Projeto_Recomendacao_Cursos_v3.ipynb`](etapa-3-metodologia/Projeto_Recomendacao_Cursos_v3.ipynb) |
| Base de dados | [Course Reviews on Coursera (Kaggle)](https://www.kaggle.com/datasets/imuhammad/course-reviews-on-coursera) |

## O projeto

Quem quer se qualificar encontra centenas de cursos online e pouca orientação. Este projeto constrói um sistema que recomenda cursos da Coursera para cada pessoa, a partir de 519.886 avaliações reais de 623 cursos (2015 a 2020). O trabalho está alinhado aos ODS 4 (Educação de Qualidade) e 8 (Trabalho Decente e Crescimento Econômico).

O sistema combina duas técnicas:

- **Filtragem baseada em conteúdo:** TF-IDF sobre o texto das avaliações de cada curso e similaridade do cosseno. Recomenda cursos de assunto parecido com os que a pessoa gostou.
- **Filtragem colaborativa:** KNN item-based sobre a matriz de notas. Segue a lógica "quem avaliou bem este curso também avaliou bem aquele".
- **Híbrido ponderado:** `α × colaborativo + (1 − α) × conteúdo`, com α = 0,4, 30 vizinhos e TF-IDF só com palavras isoladas. Essa configuração foi escolhida em uma validação separada.

A avaliação usa Precision@K, Recall@K e NDCG@K (K = 5 e 10) e compara os modelos com um baseline de popularidade. A divisão dos dados é por usuário e respeita a ordem do tempo.

## Estrutura do repositório

```
proximo-curso/
├── docs/                         site publicado pelo GitHub Pages
│   ├── index.html                o site Próximo Curso (um arquivo, com o modelo embutido)
│   └── painel.html               painel com os números agregados da avaliação de uso
├── site/                         código-fonte do site e da coleta
│   ├── preparar_dados.py         treina o modelo com os CSVs e gera modelo.json + sim_conteudo.b64
│   ├── traducoes.py              nomes dos 623 cursos em português
│   ├── template.html             código do site (sem os dados)
│   ├── painel.html               código do painel
│   ├── montar_site.py            junta template + dados e grava docs/index.html e docs/painel.html
│   ├── coleta_apps_script.gs     script da planilha Google que recebe as avaliações
│   ├── analise_coleta.py         análise dos dados coletados (Etapa 4)
│   └── README.md                 como publicar o site e ligar a coleta
├── etapa-1-concepcao/            documento da Etapa 1
├── etapa-2-prova-de-conceito/    documento e notebook da Etapa 2 (prova de conceito)
├── etapa-3-metodologia/          documento, apresentação, notebooks v2 e v3, fluxograma e resultados
├── etapa-4-resultados/           (próxima etapa)
└── dados/                        como obter a base de dados
```

## Histórico por etapa

| Etapa | Entrega | O que contém |
|---|---|---|
| 1. Concepção | [`etapa-1-concepcao`](etapa-1-concepcao) | Tema, contexto, objetivos, base de dados e objetivo extensionista |
| 2. Prova de conceito | [`etapa-2-prova-de-conceito`](etapa-2-prova-de-conceito) | Bibliotecas, análise exploratória, limpeza, modelos de conteúdo, colaborativo e híbrido (α = 0,6), Precision@5 e Recall@5 |
| 3. Metodologia | [`etapa-3-metodologia`](etapa-3-metodologia) | Ajustes no pipeline (vazamento de dados, baseline, amostra, normalização), escolha de parâmetros em validação, NDCG e K = 10, metodologia com fluxograma, site com avaliação de usabilidade |
| 4. Resultados | [`etapa-4-resultados`](etapa-4-resultados) | Em andamento: resultados, discussão e análise do uso real do site |

## Como reproduzir

1. **Notebook:** abra `etapa-3-metodologia/Projeto_Recomendacao_Cursos_v3.ipynb` no Google Colab e execute todas as células. O notebook baixa a base do Kaggle sozinho. Se não houver credencial do Kaggle, ele pede o upload dos dois CSVs.
2. **Site:** veja [`site/README.md`](site/README.md).

## Privacidade

O site calcula as recomendações no navegador. Quando a coleta está ligada, registra de forma anônima as respostas do questionário, os cursos mostrados, os cliques, a nota e o questionário de usabilidade (SUS). Não coleta nome, e-mail nem dados que identifiquem a pessoa. O painel público mostra só números agregados.
