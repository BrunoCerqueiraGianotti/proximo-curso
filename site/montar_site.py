# Junta o template HTML com os dados do modelo (compactados) em um único arquivo
# e grava o site em ../docs (pasta publicada pelo GitHub Pages).
# Uso:  python montar_site.py .                      -> site sem coleta
#       python montar_site.py . "URL_DO_APPS_SCRIPT"  -> site com a coleta ligada
import json, sys, os
pasta = sys.argv[1]
d = json.load(open(f"{pasta}/modelo.json", encoding="utf-8"))
sys.path.insert(0, pasta)
from traducoes import NOMES_PT
assert len(NOMES_PT) == len(d)
for c, pt in zip(d, NOMES_PT):
    c.pop("id", None)
    c["p"] = pt
    c["k"] = {t: round(w, 3) for t, w in sorted(c["k"].items(), key=lambda x: -x[1])[:30]}
    c["cf"] = [[j, round(s, 3)] for j, s in c["cf"]]
dados = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
endpoint = sys.argv[2].strip() if len(sys.argv) > 2 else ""   # endereço do Apps Script (opcional)
simcb = open(f"{pasta}/sim_conteudo.b64").read().strip()   # matriz de conteúdo (gerada pelo preparar_dados.py)
assert len(simcb) * 3 // 4 >= len(d) ** 2
base = (open(f"{pasta}/template.html", encoding="utf-8").read()
        .replace("__DADOS__", dados).replace("__SIMCB__", simcb))
html_github = base.replace("__ENDPOINT__", endpoint)  # versão do GitHub Pages
saida = os.path.join(pasta, "..", "docs")                # pasta publicada pelo GitHub Pages
# versão completa para hospedar no GitHub Pages (precisa do esqueleto <html><head>)
cabeca = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
          '<meta name="description" content="Recomendador de cursos online para desenvolvimento profissional - Projeto Aplicado III, Mackenzie">'
          '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}'
          'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>')
# o <title> do template vai para dentro do <head>
titulo = html_github[:html_github.index("</title>") + len("</title>")]
corpo = html_github[len(titulo):]
open(os.path.join(saida, "index.html"), "w", encoding="utf-8").write(cabeca.replace("</head>", titulo + "</head>") + corpo + "</body></html>")
# painel de avaliação (lê só números agregados do Apps Script)
painel = open(f"{pasta}/painel.html", encoding="utf-8").read().replace("__ENDPOINT__", endpoint)
open(os.path.join(saida, "painel.html"), "w", encoding="utf-8").write(painel)
print("ok: docs/index.html", round(len(html_github.encode()) / 1024), "KB e docs/painel.html")
