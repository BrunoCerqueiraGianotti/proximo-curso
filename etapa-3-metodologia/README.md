# Etapa 3: Metodologia

| Arquivo | O que é |
|---|---|
| `Projeto_Aplicado_III_Etapa3.docx` | Documento da etapa: introdução com questões de pesquisa, referencial teórico, metodologia com fluxograma e referências |
| `Projeto_Aplicado_III_Etapa3.pdf` | Mesmo documento em PDF, versão de entrega |
| `Apresentacao_Etapa3.pptx` | Apresentação feita na aula |
| `Projeto_Recomendacao_Cursos_v2.ipynb` | Notebook com os ajustes da forma de medir e a varredura do α |
| `Projeto_Recomendacao_Cursos_v3.ipynb` | Notebook atual, já executado: seção 8 com validação separada, n-gramas, vizinhos, NDCG, K = 10 e bootstrap |
| `fluxograma_metodologia.png` | Figura 1 do documento |
| `resultados/` | Tabelas geradas pelo notebook (busca na validação, varredura do α, resultado final no teste) |

## Ajustes desta etapa

1. Perfil textual dos cursos montado só com o treino (vazamento de dados corrigido).
2. Baseline de popularidade por número de avaliações, em vez de nota média.
3. Mesma amostra de 1.500 usuários para todos os modelos.
4. Normalização do híbrido depois de tirar os cursos já feitos.
5. α, número de vizinhos e n-gramas escolhidos em uma validação separada; o teste é usado uma única vez.
6. Novas métricas: NDCG@K, K = 10 e teste de significância por bootstrap.

Configuração escolhida: **α = 0,4, 30 vizinhos no KNN, TF-IDF com palavras isoladas**. É a que está em uso no site.
