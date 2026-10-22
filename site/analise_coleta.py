# =============================================================
# ANÁLISE DA COLETA DE USO — site "Próximo Curso"
# Projeto Aplicado III — Universidade Presbiteriana Mackenzie
# -------------------------------------------------------------
# Lê a planilha de eventos gravada pelo site (Google Planilhas)
# e calcula as métricas de avaliação com usuários reais, que o
# template da Etapa 4 pede: taxa de cliques (CTR), feedback
# quantitativo (nota) e qualitativo (comentários).
#
# Como obter o arquivo:
#   Na planilha, menu Arquivo > Fazer download > Valores separados
#   por vírgula (.csv) — com a aba "eventos" aberta.
#   No Colab, suba o arquivo e ajuste o nome em ARQUIVO abaixo.
# =============================================================

import sys
import pandas as pd
import matplotlib.pyplot as plt

ARQUIVO = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "eventos.csv"

# -------------------------------------------------------------
# 1. Carregar os eventos
# -------------------------------------------------------------
# Cada linha é um acontecimento no site. A coluna "sessao" é um
# código aleatório de cada visita: permite agrupar o que uma mesma
# pessoa fez, sem saber quem ela é.
ev = pd.read_csv(ARQUIVO)
ev["data_hora"] = pd.to_datetime(ev["data_hora"], errors="coerce", dayfirst=True)
ev["posicao"] = pd.to_numeric(ev["posicao"], errors="coerce")
ev["nota"] = pd.to_numeric(ev["nota"], errors="coerce").astype("Int64")
ev["posicao"] = ev["posicao"].astype("Int64")

print("=" * 60)
print("1. VISÃO GERAL")
print("=" * 60)
print(f"Eventos registrados: {len(ev)}")
print(f"Período: {ev['data_hora'].min():%d/%m/%Y} a {ev['data_hora'].max():%d/%m/%Y}")
print("\nEventos por tipo:")
print(ev["evento"].value_counts().to_string())

# -------------------------------------------------------------
# 2. Sessões e taxa de cliques (CTR)
# -------------------------------------------------------------
# Sessão "válida" = recebeu pelo menos uma lista de recomendações.
# CTR por sessão = % de sessões em que a pessoa clicou em pelo menos
# um curso para abrir na Coursera (sinal de interesse real).
sessoes = ev.loc[ev["evento"] == "recomendacao", "sessao"].unique()
por_sessao = (ev[ev["sessao"].isin(sessoes)]
              .groupby("sessao")["evento"]
              .agg(lambda e: set(e)))

def taxa(nome_evento):
    return por_sessao.apply(lambda e: nome_evento in e).mean() * 100

print("\n" + "=" * 60)
print("2. USO DAS RECOMENDAÇÕES")
print("=" * 60)
print(f"Sessões que receberam recomendações: {len(sessoes)}")
print(f"Taxa de cliques (CTR): {taxa('clique_coursera'):.1f}% das sessões abriram ao menos um curso")
print(f"Marcaram 'Mais como este': {taxa('mais_como_este'):.1f}% das sessões")
print(f"Marcaram 'Não é pra mim': {taxa('nao_e_pra_mim'):.1f}% das sessões")
print(f"Pediram 'Ver mais cursos': {taxa('ver_mais'):.1f}% das sessões")
cliques = ev[ev["evento"] == "clique_coursera"]
print(f"Cliques por sessão (média): {len(cliques) / max(len(sessoes), 1):.2f}")

# -------------------------------------------------------------
# 3. Avaliações (nota de 1 a 5)
# -------------------------------------------------------------
# Se a mesma sessão avaliou mais de uma vez, vale a última nota.
notas = (ev[ev["evento"] == "avaliacao"]
         .sort_values("data_hora")
         .drop_duplicates("sessao", keep="last"))
print("\n" + "=" * 60)
print("3. AVALIAÇÃO DOS USUÁRIOS")
print("=" * 60)
if len(notas):
    print(f"Avaliações recebidas: {len(notas)} ({len(notas) / max(len(sessoes), 1) * 100:.0f}% das sessões)")
    print(f"Nota média: {notas['nota'].mean():.2f} de 5")
    print(f"Notas 4 ou 5 (úteis): {(notas['nota'] >= 4).mean() * 100:.0f}%")
    print("\nDistribuição das notas:")
    print(notas["nota"].value_counts().sort_index().to_string())
else:
    print("Ainda não há avaliações.")

# -------------------------------------------------------------
# 4. Cliques por posição na lista
# -------------------------------------------------------------
# Se o ranking funciona, os primeiros cursos da lista devem
# receber mais cliques que os últimos.
print("\n" + "=" * 60)
print("4. CLIQUES POR POSIÇÃO NA LISTA")
print("=" * 60)
print(cliques["posicao"].value_counts().sort_index().to_string() if len(cliques) else "Ainda não há cliques.")

# -------------------------------------------------------------
# 5. Cursos mais clicados
# -------------------------------------------------------------
print("\n" + "=" * 60)
print("5. CURSOS MAIS CLICADOS")
print("=" * 60)
print(cliques["curso_nome"].value_counts().head(10).to_string() if len(cliques) else "Ainda não há cliques.")

# -------------------------------------------------------------
# 6. Resultados por tipo de usuário
# -------------------------------------------------------------
# Compara quem já sabia o tema, quem escolheu área e quem não sabia.
rec = ev[ev["evento"] == "recomendacao"].drop_duplicates("sessao")[["sessao", "modo", "idioma", "objetivo"]]
rec["clicou"] = rec["sessao"].map(por_sessao.apply(lambda e: "clique_coursera" in e))
rec = rec.merge(notas[["sessao", "nota"]], on="sessao", how="left")
nomes_modo = {"tema": "Sabia o tema", "areas": "Escolheu área", "perfil": "Ainda não sabia"}
print("\n" + "=" * 60)
print("6. POR TIPO DE USUÁRIO")
print("=" * 60)
tabela = (rec.assign(modo=rec["modo"].map(nomes_modo).fillna(rec["modo"]))
          .groupby("modo")
          .agg(sessoes=("sessao", "count"),
               ctr_pct=("clicou", lambda x: round(x.mean() * 100, 1)),
               nota_media=("nota", lambda x: round(x.mean(), 2))))
print(tabela.to_string())

# -------------------------------------------------------------
# 7. Comentários (feedback qualitativo)
# -------------------------------------------------------------
print("\n" + "=" * 60)
print("7. COMENTÁRIOS")
print("=" * 60)
for _, linha in notas.dropna(subset=["comentario"]).iterrows():
    print(f"- (nota {int(linha['nota'])}) {linha['comentario']}")

# -------------------------------------------------------------
# 8. Usabilidade (SUS) e intenção de fazer os cursos
# -------------------------------------------------------------
# SUS: 10 afirmações de 1 a 5; ímpares positivas (nota - 1), pares
# negativas (5 - nota); soma x 2,5 = pontuação de 0 a 100.
# Referência: 68 = média; faixas de Bangor, Kortum e Miller (2009).
print("\n" + "=" * 60)
print("8. USABILIDADE (SUS)")
print("=" * 60)
usab = ev[ev["evento"] == "usabilidade"].copy() if "sus_1" in ev.columns else ev.iloc[0:0]
if len(usab):
    itens = [f"sus_{k}" for k in range(1, 11)]
    usab[itens] = usab[itens].apply(pd.to_numeric, errors="coerce")
    # recalcula a nota a partir das respostas (confere o valor enviado pelo site)
    usab["sus"] = sum((usab[f"sus_{k}"] - 1) if k % 2 else (5 - usab[f"sus_{k}"]) for k in range(1, 11)) * 2.5
    faixa = pd.cut(usab["sus"], [-1, 50.9, 67.9, 80.3, 100], labels=["ruim (<51)", "regular (51-67)", "bom (68-80)", "excelente (>80)"])
    print(f"Respostas: {len(usab)}")
    print(f"SUS médio: {usab['sus'].mean():.1f}  (mediana {usab['sus'].median():.1f})")
    print(f"Acima da média de referência (68): {(usab['sus'] >= 68).mean() * 100:.0f}%")
    print("\nFaixas:"); print(faixa.value_counts().sort_index().to_string())
    print("\nMédia por afirmação (1 a 5):"); print(usab[itens].mean().round(2).to_string())
    print("\nPretende fazer algum curso sugerido?")
    print(usab["intencao"].value_counts(normalize=True).mul(100).round(0).to_string())
else:
    print("Ainda não há respostas do questionário de usabilidade.")

# -------------------------------------------------------------
# 9. Gráficos para o relatório
# -------------------------------------------------------------
fig, eixos = plt.subplots(1, 3, figsize=(15, 4))
if len(notas):
    notas["nota"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0).plot.bar(ax=eixos[0], color="#0D6A56")
eixos[0].set_title("Distribuição das notas dos usuários")
eixos[0].set_xlabel("Nota (1 = nada útil, 5 = muito útil)")
eixos[0].set_ylabel("Avaliações")
eixos[0].tick_params(axis="x", rotation=0)
if len(cliques):
    cliques["posicao"].value_counts().sort_index().plot.bar(ax=eixos[1], color="#0D6A56")
eixos[1].set_title("Cliques por posição na lista")
eixos[1].set_xlabel("Posição do curso (1 = primeiro)")
eixos[1].set_ylabel("Cliques")
eixos[1].tick_params(axis="x", rotation=0)
if len(usab):
    eixos[2].hist(usab["sus"], bins=range(0, 105, 10), color="#0D6A56", edgecolor="white")
    eixos[2].axvline(68, color="#555", linestyle="--", label="média de referência (68)")
    eixos[2].legend()
eixos[2].set_title("Pontuação SUS")
eixos[2].set_xlabel("SUS (0 a 100)")
eixos[2].set_ylabel("Respostas")
plt.tight_layout()
plt.savefig("graficos_coleta.png", dpi=150)
print("\nGráficos salvos em graficos_coleta.png")
plt.show()
