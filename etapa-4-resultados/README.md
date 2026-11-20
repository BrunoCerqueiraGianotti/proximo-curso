# Etapa 4: Resultados e Conclusões

Entrega final do Projeto Aplicado III. Reúne os resultados da avaliação offline dos modelos, a avaliação do site Próximo Curso com pessoas da comunidade, a conclusão e os trabalhos futuros.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `Projeto_Aplicado_III_Etapa4.docx` / `.pdf` | Documento final (capítulos 1 a 6 e apêndices) |
| `Apresentacao_Etapa4.pptx` | Apresentação usada no vídeo, com os resultados da pesquisa com a comunidade |
| `analise_etapa4.py` | Análises complementares do capítulo 4: números da análise exploratória, bootstrap do híbrido contra cada modelo, desempenho por perfil de usuário e diversidade das recomendações |
| `resultados/analise_etapa4.json` | Saída do script acima |
| `resultados/coleta_resumo_15nov2026.json` | Números agregados da coleta no site (9 a 15/11/2026), como exibidos no painel |
| `figuras/` | Gráficos usados no documento |

Para reproduzir as análises: `python analise_etapa4.py Coursera_courses.csv Coursera_reviews.csv` (a base está no Kaggle, ver `dados/README.md`).

## Principais resultados

| Modelo (teste, 1.500 usuários) | Precision@5 | NDCG@10 |
|---|---|---|
| Popularidade (baseline) | 2,29% | 0,076 |
| Content-Based (TF-IDF) | 3,83% | 0,142 |
| Colaborativo (KNN) | 4,79% | 0,188 |
| **Híbrido final (α = 0,4)** | **5,32%** | **0,202** |

- O híbrido supera o baseline e cada técnica isolada em todas as métricas, com diferença consistente no bootstrap pareado.
- Comunidade (47 sessões, 9 a 15/11/2026): taxa de cliques de 10,6%, nota média de utilidade 4,64 de 5 e SUS médio de 95,6 (4 respostas).

## Vídeos

- Apresentação do projeto: https://www.youtube.com/watch?v=uf3b11qDDcQ
- Aplicação na comunidade (CEPAC, Barueri): https://www.youtube.com/watch?v=ji7cZiH5KbM
