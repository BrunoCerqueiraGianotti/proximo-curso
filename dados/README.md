# Dados

A base **Course Reviews on Coursera** é pública e está no Kaggle:
https://www.kaggle.com/datasets/imuhammad/course-reviews-on-coursera

| Arquivo | Conteúdo |
|---|---|
| `Coursera_courses.csv` | 623 cursos: nome, instituição, link e `course_id` |
| `Coursera_reviews.csv` | 1.454.711 avaliações (2015 a 2020): texto, nome do avaliador, data, nota de 1 a 5 e `course_id` |

Os arquivos não ficam neste repositório. O de avaliações tem cerca de 270 MB, acima do limite do GitHub, e os dados pertencem ao autor original. O notebook baixa a base automaticamente pela biblioteca `kagglehub`. Se preferir, baixe os dois CSVs no Kaggle e suba no Colab quando o notebook pedir.
