"""Projeto Aplicado III - Etapa 4: análises complementares dos resultados.

Reproduz, sobre o mesmo pré-processamento e as mesmas funções do notebook v3
(etapa-3-metodologia), as análises usadas no capítulo 4 do documento:
  - números da análise exploratória (seção 4.1);
  - bootstrap pareado do híbrido contra popularidade, Content-Based e KNN (Tabela 2);
  - desempenho por número de avaliações no treino (Figura 6);
  - diversidade das cinco primeiras recomendações (Tabela 4);
  - exemplos de recomendações (Quadro 5).

Uso: python analise_etapa4.py <Coursera_courses.csv> <Coursera_reviews.csv>
Saída: resultados/analise_etapa4.json
"""
import sys, json
import numpy as np, pandas as pd
CAMINHO_COURSES, CAMINHO_REVIEWS = sys.argv[1], sys.argv[2]
DATA_DIR = "./"

# ===== pré-processamento (cópia da seção 2 do notebook v3) =====

# -------------------------------------------------------------
# 1. Carregar os dados originais
# -------------------------------------------------------------
courses = pd.read_csv(CAMINHO_COURSES)
reviews = pd.read_csv(CAMINHO_REVIEWS)

print(f"Antes da limpeza: {reviews.shape[0]:,} reviews")

# -------------------------------------------------------------
# 2. Remover duplicatas exatas
# -------------------------------------------------------------
# No EDA vimos que a mesma review (mesmo texto, usuario, curso,
# data e nota) aparecia repetida 2-3x -- provavelmente um
# artefato do processo de coleta (scraping). Remover para nao
# distorcer o peso de usuarios/cursos no modelo.
reviews = reviews.drop_duplicates()
print(f"Depois de remover duplicatas: {reviews.shape[0]:,} reviews")

# -------------------------------------------------------------
# 3. Tratar valores nulos
# -------------------------------------------------------------
# So 153 reviews sem texto -- decidimos descartar, ja que sao
# poucas e o texto e essencial pro modelo Content-Based.
antes = reviews.shape[0]
reviews = reviews.dropna(subset=["reviews"])
print(f"Removidas {antes - reviews.shape[0]} reviews sem texto")

# -------------------------------------------------------------
# 4. Limpar o nome do reviewer
# -------------------------------------------------------------
# Os nomes vem no formato "By \t Nome Sobrenome" -- vamos tirar
# o prefixo "By" e espacos/tabs extras, pra ficar so o nome.
reviews["reviewers"] = (
    reviews["reviewers"]
    .str.replace(r"^By\s*", "", regex=True)  # remove "By " do inicio
    .str.replace(r"\s+", " ", regex=True)     # colapsa espacos/tabs multiplos
    .str.strip()
)

# -------------------------------------------------------------
# 5. Converter a data para formato datetime
# -------------------------------------------------------------
reviews["date_reviews"] = pd.to_datetime(reviews["date_reviews"], format="%b %d, %Y")

# -------------------------------------------------------------
# 6. Criar um ID numerico para cada usuario
# -------------------------------------------------------------
# Motivo: nomes de reviewer podem se repetir entre pessoas
# diferentes (ex: dois "John Smith"). Isso e uma limitacao
# conhecida do dataset (nao ha ID unico de usuario, so o nome
# que a pessoa digitou). Vamos documentar isso no relatorio
# como uma limitacao dos dados.
# Criamos um ID interno so pra facilitar o processamento.
reviews["user_id"] = reviews["reviewers"].astype("category").cat.codes


# -------------------------------------------------------------
# 7. Split treino/teste (80/20 por usuario)
# -------------------------------------------------------------
# Importante: NAO e um split aleatorio simples em cima de todas
# as linhas. Fazemos por usuario, pra garantir que todo usuario
# tenha pelo menos uma interacao no treino E no teste (senao a
# gente nao consegue avaliar recomendacao pra ele).
# Ordenamos por data e pegamos os ultimos 20% de cada usuario
# pro teste -- isso simula "prever o futuro" com base no passado,
# que e mais realista do que embaralhar aleatoriamente.

reviews = reviews.sort_values(["user_id", "date_reviews"]).reset_index(drop=True)

# Posicao de cada review dentro do historico do seu usuario (0, 1, 2...)
posicao_no_grupo = reviews.groupby("user_id").cumcount()
# Tamanho total do historico daquele usuario
tamanho_grupo = reviews.groupby("user_id")["user_id"].transform("size")
# Ponto de corte: 80% do historico de cada usuario (minimo 1 review no treino)
corte = (tamanho_grupo * 0.8).astype(int).clip(lower=1)

reviews["conjunto"] = "treino"
reviews.loc[posicao_no_grupo >= corte, "conjunto"] = "teste"

print("\nDistribuicao do split:")
print(reviews["conjunto"].value_counts())

# Usuarios com so 1 review inteira caem 100% no treino (nao tem
# como testar neles) -- isso e esperado e sera discutido como
# limitacao (problema de cold-start).

# -------------------------------------------------------------
# 8. Perfil de conteudo dos cursos (SO COM O TREINO)
# -------------------------------------------------------------
treino_tmp = reviews[reviews["conjunto"] == "treino"]

perfil_conteudo = (
    treino_tmp.groupby("course_id")["reviews"]
    .apply(" ".join)
    .reset_index(name="conteudo_textual")
)

courses = (
    courses.drop(columns="conteudo_textual", errors="ignore")
           .merge(perfil_conteudo, on="course_id", how="left")
)

sem_review = courses["conteudo_textual"].isnull().sum()
print(f"\nCursos sem nenhuma review no TREINO (sem conteudo textual): {sem_review}")
courses["conteudo_textual"] = courses["conteudo_textual"].fillna(courses["name"])

# -------------------------------------------------------------
# 9. Salvar os dados limpos para os proximos passos
# -------------------------------------------------------------
# Os DataFrames "reviews" e "courses" ja ficam disponiveis em memoria
# para as proximas celulas deste notebook (nao precisamos salvar em CSV aqui).

print("\nDados limpos prontos em memória (DataFrames reviews e courses).")
print("\nPre-processamento concluido.")
# ===== funções da seção 8.1 do notebook v3 =====
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors

# -------------------------------------------------------------
# 1. Um índice único para os cursos (0, 1, 2, ...)
# -------------------------------------------------------------
# Trabalhar com posições numéricas (arrays do numpy) em vez de
# DataFrames deixa a busca de parâmetros bem mais rápida.
cursos8 = courses.drop_duplicates("course_id").reset_index(drop=True)
CURSO_IDX = {c: i for i, c in enumerate(cursos8["course_id"])}
N_CURSOS = len(cursos8)


# -------------------------------------------------------------
# 2. Separar uma VALIDAÇÃO de dentro do treino
# -------------------------------------------------------------
# Mesma regra do split original: para cada usuário, as avaliações
# mais recentes (últimos 20% do TREINO) viram validação.
# O conjunto de TESTE não é tocado até a avaliação final.
def separar_validacao(treino_df):
    t = treino_df.sort_values(["user_id", "date_reviews"]).reset_index(drop=True)
    pos = t.groupby("user_id").cumcount()
    tam = t.groupby("user_id")["user_id"].transform("size")
    corte = (tam * 0.8).astype(int).clip(lower=1)
    return t[pos < corte], t[pos >= corte]


# -------------------------------------------------------------
# 3. "Treinar" os dois modelos com um conjunto qualquer
# -------------------------------------------------------------
def treinar_conteudo(base, ngramas=(1, 1)):
    """TF-IDF sobre o texto das avaliações de cada curso (só da base
    recebida) e similaridade de cosseno entre todos os cursos."""
    texto = base.groupby("course_id")["reviews"].apply(" ".join)
    docs = cursos8["course_id"].map(texto).fillna(cursos8["name"])
    tfidf = TfidfVectorizer(stop_words="english", max_features=5000, min_df=2, ngram_range=ngramas)
    sim = cosine_similarity(tfidf.fit_transform(docs))
    np.fill_diagonal(sim, 0)  # o próprio curso não conta como vizinho
    return sim


def treinar_colaborativo(base, max_vizinhos=30):
    """KNN item-based com distância de cosseno. Guarda, para cada curso,
    os 'max_vizinhos' mais parecidos e a similaridade (1 - distância)."""
    usuarios = base["user_id"].astype("category").cat.codes
    linhas = base["course_id"].map(CURSO_IDX)
    M = csr_matrix((base["rating"].values, (linhas, usuarios)),
                   shape=(N_CURSOS, usuarios.max() + 1))
    knn = NearestNeighbors(metric="cosine", algorithm="brute").fit(M)
    tem_nota = np.asarray(M.getnnz(axis=1)).ravel() > 0
    viz = np.full((N_CURSOS, max_vizinhos), -1)
    sim = np.zeros((N_CURSOS, max_vizinhos))
    idx_com_nota = np.where(tem_nota)[0]
    d, v = knn.kneighbors(M[idx_com_nota], n_neighbors=max_vizinhos + 1)
    for linha, i in enumerate(idx_com_nota):
        outros = [(vv, 1 - dd) for dd, vv in zip(d[linha], v[linha]) if vv != i][:max_vizinhos]
        for k, (vv, s) in enumerate(outros):
            viz[i, k], sim[i, k] = vv, s
    return viz, sim


# -------------------------------------------------------------
# 4. Scores de cada modelo para um usuário (mesma lógica da seção 6)
# -------------------------------------------------------------
def minmax(x, presentes):
    """Normalização 0-1 só entre os cursos que têm score (presentes)."""
    out = np.zeros(N_CURSOS)
    if not presentes.any():
        return out
    a, b = x[presentes].min(), x[presentes].max()
    out[presentes] = 0 if a == b else (x[presentes] - a) / (b - a)
    return out


def scores_usuario(bons, feitos, sim_cb, viz, sim_cf, n_vizinhos):
    """Devolve os scores já normalizados do conteúdo e do colaborativo,
    depois de tirar os cursos que o usuário já fez (ajuste 4 da Etapa 3)."""
    livres = np.ones(N_CURSOS, bool)
    livres[feitos] = False
    cb = sim_cb[:, bons].sum(axis=1)
    cf = np.zeros(N_CURSOS)
    for i in bons:
        v, s = viz[i, :n_vizinhos], sim_cf[i, :n_vizinhos]
        ok = v >= 0
        np.add.at(cf, v[ok], s[ok])
    tem_cf = (cf > 0) & livres
    return minmax(cb, livres), minmax(cf, tem_cf), tem_cf.any()


def combinar(ncb, ncf, tem_cf, alpha):
    # fallback: se o colaborativo não gerou nada, usa só o conteúdo
    return alpha * ncf + (1 - alpha) * ncb if tem_cf else ncb


# -------------------------------------------------------------
# 5. Métricas: Precision@K, Recall@K e NDCG@K
# -------------------------------------------------------------
# NDCG@K (Normalized Discounted Cumulative Gain): além de contar os
# acertos, dá mais peso a quem acerta nas PRIMEIRAS posições.
# Um acerto na posição p vale 1 / log2(p + 1): 1º lugar = 1,0;
# 2º = 0,63; 5º = 0,39. Dividimos pelo melhor valor possível
# (todos os acertos no topo), então o NDCG vai de 0 a 1.
def metricas(recomendados, relevantes, k):
    top = list(recomendados[:k])
    acertos = [1 if c in relevantes else 0 for c in top]
    dcg = sum(a / np.log2(p + 2) for p, a in enumerate(acertos))
    idcg = sum(1 / np.log2(p + 2) for p in range(min(len(relevantes), k)))
    return sum(acertos) / k, sum(acertos) / len(relevantes), dcg / idcg


def top_k(score, feitos, k):
    s = score.copy()
    s[feitos] = -np.inf
    return np.argsort(-s, kind="stable")[:k]


def perfis_usuarios(base):
    """Para cada usuário: cursos avaliados com nota >= 4 (usados para
    recomendar) e todos os cursos já feitos (excluídos da lista)."""
    b = base.assign(i=base["course_id"].map(CURSO_IDX))
    bons = b[b["rating"] >= 4].groupby("user_id")["i"].apply(lambda s: np.unique(s.values))
    feitos = b.groupby("user_id")["i"].apply(lambda s: np.unique(s.values))
    return bons, feitos


def relevantes_de(alvo):
    a = alvo[alvo["rating"] >= 4].assign(i=lambda d: d["course_id"].map(CURSO_IDX))
    return a.groupby("user_id")["i"].apply(set)


def amostrar(relevantes, bons, n=1500, semente=42):
    com_bons = set(bons.index)
    eleg = [u for u in relevantes.index if u in com_bons]
    return pd.Series(eleg).sample(n=min(n, len(eleg)), random_state=semente).tolist()
# ===== análises da Etapa 4 =====
bruto = pd.read_csv(CAMINHO_REVIEWS)
eda = {"bruto_linhas": len(bruto), "dup_exatas": int(bruto.duplicated().sum()), "limpo_linhas": len(reviews),
       "usuarios": int(reviews.user_id.nunique()), "cursos_com_aval": int(reviews.course_id.nunique()),
       "notas_pct": (reviews.rating.value_counts(normalize=True).sort_index() * 100).round(2).to_dict(),
       "nota_media": float(reviews.rating.mean())}
apu = reviews.groupby("user_id").size(); apc = reviews.groupby("course_id").size()
eda["aval_por_usuario"] = {"1": int((apu == 1).sum()), "2": int((apu == 2).sum()), "3a4": int(apu.between(3, 4).sum()),
                           "5a9": int(apu.between(5, 9).sum()), "10+": int((apu >= 10).sum()), "media": float(apu.mean()), "max": int(apu.max())}
eda["aval_por_curso"] = {"mediana": float(apc.median()), "max": int(apc.max()),
                         "top10pct_cursos_share": float(apc.sort_values(ascending=False).head(int(len(apc) * 0.1)).sum() / apc.sum())}
treino = reviews[reviews["conjunto"] == "treino"]; teste = reviews[reviews["conjunto"] == "teste"]
eda["esparsidade_treino"] = len(treino.drop_duplicates(["user_id", "course_id"])) / (treino.user_id.nunique() * treino.course_id.nunique())

bons_tr, feitos_tr = perfis_usuarios(treino); rel = relevantes_de(teste); usuarios = amostrar(rel, bons_tr)
sim = treinar_conteudo(treino, (1, 1)); viz, simcf = treinar_colaborativo(treino, max_vizinhos=30)
populares = treino["course_id"].map(CURSO_IDX).value_counts().index.to_numpy()
n_aval = treino.groupby("user_id").size(); nomes = cursos8["name"].tolist()
M = {k: [] for k in ["pop", "cb", "cf", "h"]}; R = {k: {} for k in M}; reg = []
for u in usuarios:
    f = feitos_tr[u]; ncb, ncf, tem = scores_usuario(bons_tr[u], f, sim, viz, simcf, 30)
    r = {"h": top_k(combinar(ncb, ncf, tem, 0.4), f, 10), "pop": np.array([c for c in populares if c not in set(f)][:10]),
         "cb": top_k(ncb, f, 10), "cf": top_k(ncf, f, 10) if tem else np.array([], int)}
    for k in M:
        R[k][u] = r[k]; M[k].append(list(metricas(r[k], rel[u], 5)) + list(metricas(r[k], rel[u], 10)))
    reg.append({"u": u, "n_treino": int(n_aval[u]), "tem_cf": bool(tem)})
M = {k: np.array(v) for k, v in M.items()}
nomes_m = ["precision@5", "recall@5", "ndcg@5", "precision@10", "recall@10", "ndcg@10"]
rng = np.random.default_rng(42); S = rng.integers(0, len(usuarios), size=(2000, len(usuarios)))
boot = []
for k in ["pop", "cb", "cf"]:
    d = M["h"] - M[k]
    for j, n in enumerate(nomes_m):
        b = d[:, j][S].mean(1); lo, hi = np.percentile(b, [2.5, 97.5])
        boot.append({"contra": k, "metrica": n, "dif": float(d[:, j].mean()), "ic95": [float(lo), float(hi)]})
df = pd.DataFrame(reg); df["p5_h"] = M["h"][:, 0]; df["ndcg10_h"] = M["h"][:, 5]; df["p5_p"] = M["pop"][:, 0]; df["ndcg10_p"] = M["pop"][:, 5]
df["faixa"] = pd.cut(df.n_treino, [0, 1, 2, 4, 10**6], labels=["1", "2", "3 a 4", "5 ou mais"])
seg = df.groupby("faixa", observed=True).agg(usuarios=("u", "size"), p5_h=("p5_h", "mean"), ndcg10_h=("ndcg10_h", "mean"),
                                              p5_p=("p5_p", "mean"), ndcg10_p=("ndcg10_p", "mean")).reset_index()
top20 = set(populares[:20]); cob = {}
for k in M:
    todos = [c for u in usuarios for c in R[k][u][:5]]
    cob[k] = {"cursos_distintos_top5": len(set(todos)), "pct_catalogo": len(set(todos)) / len(cursos8),
              "pct_entre_20_mais_populares": float(np.mean([c in top20 for c in todos])) if todos else 0.0}
out = {"eda": eda, "medias": {k: dict(zip(nomes_m, M[k].mean(0).tolist())) for k in M}, "bootstrap": boot,
       "por_faixa": seg.astype({"faixa": str}).to_dict("records"), "diversidade": cob,
       "sem_vizinho_colaborativo": float((~df.tem_cf).mean())}
json.dump(out, open("resultados/analise_etapa4.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out["medias"], indent=1)); print(pd.DataFrame(boot).round(4).to_string()); print(seg.round(4).to_string())
