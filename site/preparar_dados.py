# =============================================================
# Prepara os dados do modelo para o site (roda uma vez, offline)
# -------------------------------------------------------------
# O site nao roda Python: ele recebe, em JSON, tudo o que o modelo
# hibrido precisa ja calculado:
#   - a similaridade de CONTEUDO (TF-IDF) entre TODOS os pares de cursos,
#     guardada em bytes (arquivo sim_conteudo.b64), como no notebook
#   - para cada curso, os 30 cursos mais parecidos pelo COMPORTAMENTO
#     dos usuarios (KNN item-based sobre a matriz de notas)
#   - palavras-chave de cada curso (para a busca por tema)
#   - area, idioma, nivel, nota media e numero de avaliacoes
# Com isso o navegador combina os scores (alpha = 0.4) na hora, com a
# mesma configuracao escolhida na validacao do notebook v3 (secao 8).
# Aqui o modelo e treinado com TODO o historico limpo (nao so o
# treino), porque nao estamos mais avaliando: e a versao de uso.
# =============================================================
import json, re, sys
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors

PASTA = sys.argv[1]           # pasta com os 2 CSVs
SAIDA = sys.argv[2]           # arquivo json de saida
N_VIZ = 30                    # vizinhos colaborativos por curso (notebook v3, secao 8)

courses = pd.read_csv(f"{PASTA}/Coursera_courses.csv")
reviews = pd.read_csv(f"{PASTA}/Coursera_reviews.csv")

# ---------- 1. limpeza (mesma do notebook) ----------
reviews = reviews.drop_duplicates().dropna(subset=["reviews"])
reviews["reviewers"] = (reviews["reviewers"].str.replace(r"^By\s*", "", regex=True)
                        .str.replace(r"\s+", " ", regex=True).str.strip())
reviews["user_id"] = reviews["reviewers"].astype("category").cat.codes
print("reviews limpas:", len(reviews))

# ---------- 2. estatisticas por curso ----------
stats = reviews.groupby("course_id")["rating"].agg(["mean", "count"])
courses = courses.merge(stats, left_on="course_id", right_index=True, how="left")
courses["count"] = courses["count"].fillna(0).astype(int)
courses["mean"] = courses["mean"].fillna(0)

# ---------- 3. perfil textual + TF-IDF (Content-Based) ----------
texto = reviews.groupby("course_id")["reviews"].apply(" ".join)
courses["texto"] = courses["course_id"].map(texto).fillna(courses["name"])
vec = TfidfVectorizer(stop_words="english", max_features=5000, min_df=2)
X = vec.fit_transform(courses["texto"])
sim = cosine_similarity(X)
np.fill_diagonal(sim, 0)

# palavras-chave para a busca: TF-IDF que ignora palavras presentes
# em mais de 30% dos cursos ("great", "course"...) + nome do curso
vec_kw = TfidfVectorizer(stop_words="english", max_df=0.3, min_df=2,
                         max_features=20000, token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#]{1,}\b")
K = vec_kw.fit_transform(courses["texto"])
vocab = np.array(vec_kw.get_feature_names_out())

# ---------- 4. KNN item-based (Colaborativo) ----------
idx_curso = {c: i for i, c in enumerate(courses["course_id"])}
rv = reviews[reviews["course_id"].isin(idx_curso)]
linhas = rv["course_id"].map(idx_curso).values
colunas = rv["user_id"].astype("category").cat.codes.values
M = csr_matrix((rv["rating"].values.astype(float), (linhas, colunas)),
               shape=(len(courses), colunas.max() + 1))
knn = NearestNeighbors(metric="cosine", algorithm="brute").fit(M)
dist, viz = knn.kneighbors(M, n_neighbors=N_VIZ + 1)

# ---------- 5. idioma do curso (pelo nome) ----------
RU = re.compile(r"[Ѐ-ӿ]")
PT = ["introdução", "revisão", "ciência da computação", "fundamentos para o design"]
FR = ["étudier", "entreprise et", "devenir", "réussir", "troubles du", "introduction aux",
      "développement", "rédaction", "l'excellence", "les fondamentaux", "reporting extra-financier"]
ES = ["primeros", "contabilidad", "camino a", "cursos en línea", "nutrición", "competencias",
      "negociación", "introducción", "gestión", "fundamentos de", "excel aplicado", "claves para",
      "abogado", "democracia", "anticorrupción", "finanzas", "aprendiendo", "corrección",
      "marketing gerencial", "actualización", "hacia una", "marketing digital"]
def idioma(nome):
    n = nome.lower()
    if RU.search(n): return "ru"
    if any(k in n for k in PT): return "pt"
    if any(k in n for k in FR): return "fr"
    if any(k in n for k in ES) or "ñ" in n: return "es"
    return "en"
courses["lang"] = courses["name"].map(idioma)
courses.loc[courses["course_id"] == "spanish-vocabulary-meeting-people", "lang"] = "en"  # curso de espanhol, ensinado em ingles
courses.loc[courses["name"].str.contains("Spanish for Successful", case=False), "lang"] = "en"

# ---------- 6. nivel (nome + o que os alunos dizem nas reviews) ----------
def taxa(padrao):
    r = reviews["reviews"].str.contains(padrao, case=False, regex=True)
    return r.groupby(reviews["course_id"]).mean()
t_ini = taxa(r"\b(?:beginners?|novice|no prior|from scratch|newbie)\b")
t_dif = taxa(r"\b(?:difficult|challenging|tough|advanced|hard)\b")
courses["t_ini"] = courses["course_id"].map(t_ini).fillna(0)
courses["t_dif"] = courses["course_id"].map(t_dif).fillna(0)
INI = r"\b(introduc|intro|fundamental|basic|beginner|for everyone|for everybody|getting started|essentials|101|first step|crash course|what is|foundations|for all|learn to|part 1|part i\b|for non|principios|fundamentos|introducci|introdu)"
AVA = r"\b(advanced|avanzado|part ii|part 2|capstone|intermediate|exam prep|professional cloud architect)"
def nivel(r):
    n = r["name"].lower()
    if re.search(AVA, n): return 3
    if re.search(INI, n): return 1
    if r["t_ini"] >= courses["t_ini"].quantile(0.75): return 1
    if r["t_dif"] >= courses["t_dif"].quantile(0.80): return 3
    return 2
courses["nivel"] = courses.apply(nivel, axis=1)

# ---------- 7. areas (regras no nome; quem sobra herda dos vizinhos de conteudo) ----------
AREAS = {
 "dados": r"data|machine learning|deep learning|neural|tensorflow|\bai\b|artificial intelligence|statistic|analytics|tableau|sql|big data|bigquery|bayesian|probabilit|time series|natural language|reinforcement|regression|clustering|visualiz|econometric|causal|pca|sample-based|graphical models|quantitative|data science|process mining|self-driving|\br\b programming|sas programming|spreadsheets and models|excel",
 "programacao": r"python|programming|java|javascript|html|css|web|c\+\+|\bc\b for|c#|kotlin|scala|\bgo\b|django|react\b|bootstrap|git|algorithm|data structures|software|code|computer science|computational thinking|matlab|game development|unity|object-oriented|object oriented|ciência da computação|программ|разработ|divide and conquer|optimization|nand to tetris|hypothesis-driven|debugging|embedded|vlsi",
 "ti": r"cloud|aws|azure|gcp|google cloud|kubernetes|devops|it infrastructure|system administration|networking|operating system|security|cyber|cryptograph|technical support|containerized|reliability|continuous delivery|blockchain|cryptocurrency|g suite|google sheets|office productivity|ofimática|computers and|access controls|penetration|information systems|enterprise architecture|iot|cbrs|dialogflow|quantum|power user",
 "negocios": r"manag|business|leader|entrepreneur|strateg|project|agile|scrum|negotiat|negociaci|negocia|human resources|recruit|hiring|team|organiz|innovation|design thinking|six sigma|supply chain|operations|lean|product management|compliance|change|company|pymes|empresarial|gestión|gestionar|personas|transformation|coach|hotel|food & beverage|consult|career|competencias laborales|jira|pricing|excellence|excelencia|remote team|diversity and inclusion in the workplace|corporate strategy|digital business",
 "marketing": r"marketing|brand|advertis|social media|seo|search engine|content|customer|viral|sales|prospecting|neuromarketing|gamification|personal branding|digital media|customer engagement",
 "financas": r"financ|accounting|contabilidad|invest|equity|valuation|econom|money|banking|trading|fintech|portfolio|tax|budget|cost|markets?\b|crisis|finanzas",
 "saude": r"health|medic|clinical|anatomy|physiolog|nutrition|nutrici|diabet|covid|epidemi|pandemic|disease|drug|cancer|immun|dental|dentist|oral cavity|nursing|emt|vital signs|healthcare|antibiotic|dermatolog|pregnan|exercise|yoga|sleep|addiction|food and health|weight|chemicals and health|microbiome|contact tracing|stem cells|genomic|genetics|epigenetic|schizophrenia|autism|autisme|chinese medicine|curanderismo",
 "psicologia": r"psycholog|psicol|well-being|wellness|mindful|mental health|happiness|positive psych|brain|neurosc|neurobio|neuroecon|neuroimag|resilience|purpose|motivation|self-determination|learning how to learn|aprendiendo a aprender|mindshift|relationships|parenting|child development|success|moralities|social norms|mind control|addicted|cognition",
 "idiomas": r"english|korean|chinese for|japanese|spanish|french|grammar|writing|pronunciation|verb tenses|perfect tenses|vocabulary|composition|public speaking|communication|presentations|emails|essay|lengua|linguistic|human language|journalism|storytelling|editing",
 "design": r"design|ux|ui\b|user experience|user interface|graphic\b|typography|arts?\b|music|guitar|songwriting|photograph|cameras|film|screenplay|novel|creative|fashion|architecture|final cut|revit|autocad|painting|musicianship|memoir|plot|wine",
 "ciencias": r"physics|chemistry|biology|biotech|ecology|energy|solar|wind|renewable|climate|sustainab|environment|astronomy|einstein|dinosaur|paleo|insect|bugs|plants|animal|dog|cat|horse|equine|veterinar|dairy|engineering|electronics|mechanics|nanotechnology|spectroscopy|gis|cities|cycling city|oil & gas|electric industry|circular economy|green|bioinformatics|osteoarchaeology|food system|calculus|mathematic|math|stochastic|model thinking|evolution|changement climatique|dino",
 "humanidades": r"law|legal|droit|derecho|abogado|contrat|rights|human rights|politic|polític|diplomacy|international|security management|terror|refugee|migration|history|philosophy|ancient|egypt|greek|roman|mythology|magic|sociolog|social justice|feminism|race|gender|indigenous|aboriginal|social work|social impact|social innovation|changemaker|policy|public policy|democracia|anticorrupción|geopolitic|sports and society|what is social|global order|big history|forensic|teach|teaching|education|instructional|e-learning|cursos en línea|constructivista|reading and writing|learning to teach|love as a force|arguments|research methods|research data|systematic review|revisão sistemática|meta-analysis|privacy|intellectual property",
}
nomes = courses["name"].str.lower()
area_lista = []
for n in nomes:
    a = [k for k, rx in AREAS.items() if re.search(r"\b(?:" + rx + r")", n)]
    area_lista.append(a)
# quem nao casou com nenhuma regra herda a area mais comum entre
# os 10 vizinhos de conteudo (TF-IDF) que ja tem area
for i, a in enumerate(area_lista):
    if not a:
        viz_c = np.argsort(-sim[i])[:10]
        votos = pd.Series([x for j in viz_c for x in area_lista[j]]).value_counts()
        area_lista[i] = [votos.index[0]] if len(votos) else ["humanidades"]
courses["areas"] = area_lista
# ajustes manuais onde as regras de palavras-chave erraram
AJUSTES = {
 "Design and Interpretation of Clinical Trials": ["saude", "dados"],
 "Game Theory": ["financas", "dados"],
 "Financial Engineering and Risk Management": ["financas", "dados"],
 "Introduction to English Common Law": ["humanidades"],
 "Weight Management": ["saude"],
 "Mind Control: Managing Your Mental Health": ["psicologia", "saude"],
 "Leading for Equity, Diversity": ["humanidades", "negocios"],
 "Investigating and Prosecuting": ["humanidades"],
 "Probabilistic Graphical Models": ["dados"],
 "Introduction to Chemistry": ["ciencias"],
 "Penetration Testing": ["ti"],
 "Business English: Networking": ["idiomas", "negocios"],
 "Memoir and Personal Essay": ["idiomas", "design"],
 "Embedded Software and Hardware": ["programacao", "ciencias"],
 "Reliable Google Cloud Infrastructure": ["ti"],
 "Enterprise Architecture": ["ti"],
 "Applied Plotting, Charting": ["dados", "programacao"],
 "High Stakes Leadership": ["negocios"],
 "Equine Welfare": ["ciencias"],
 "The Horse Course": ["ciencias"],
 "IT Security: Defense against": ["ti"],
 "Site Reliability Engineering": ["ti"],
 "Strategic Business Management - Microeconomics": ["negocios", "financas"],
 "Healing with the Arts": ["design", "saude"],
}
for trecho, novas in AJUSTES.items():
    m = courses["name"].str.contains(trecho, regex=False)
    assert m.any(), trecho
    for i in courses.index[m]:
        courses.at[i, "areas"] = novas
area_lista = list(courses["areas"])

# ---------- 8. exportar ----------
saida = []
for i, r in courses.iterrows():
    colab = [(int(j), round(float(1 - d), 4)) for j, d in zip(viz[i], dist[i]) if j != i][:N_VIZ]
    linha_kw = K[i].toarray().ravel()
    top = np.argsort(-linha_kw)[:40]
    kw = {vocab[t]: round(float(linha_kw[t]), 4) for t in top if linha_kw[t] > 0}
    saida.append({
        "id": r["course_id"], "n": r["name"], "i": r["institution"], "u": r["course_url"],
        "r": round(float(r["mean"]), 2), "c": int(r["count"]), "l": r["lang"], "v": int(r["nivel"]),
        "a": r["areas"],
        "cf": [[j, s] for j, s in colab if r["count"] > 0],
        "k": kw,
    })
json.dump(saida, open(SAIDA, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# matriz completa de similaridade de conteudo: 623 x 623 valores de 0 a 1,
# arredondados para 1 byte (0-255) e codificados em base64 (~500 KB)
import base64, os
sim_bytes = np.clip(np.rint(sim * 255), 0, 255).astype(np.uint8)
open(os.path.join(os.path.dirname(SAIDA) or ".", "sim_conteudo.b64"), "w").write(base64.b64encode(sim_bytes.tobytes()).decode())
print("cursos:", len(saida))
print(courses["lang"].value_counts().to_dict())
print(courses["nivel"].value_counts().to_dict())
print(pd.Series([x for a in area_lista for x in a]).value_counts().to_dict())
