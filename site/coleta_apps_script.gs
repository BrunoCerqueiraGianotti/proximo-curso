/**
 * =============================================================
 * Próximo Curso — coleta de avaliações (Google Apps Script)
 * Projeto Aplicado III — Universidade Presbiteriana Mackenzie
 * -------------------------------------------------------------
 * Este script fica DENTRO de uma planilha do Google. O site envia
 * cada acontecimento (uma recomendação mostrada, um clique, uma
 * nota...) e o script grava uma linha na aba "eventos".
 *
 * Como instalar (resumo — o passo a passo completo está no README):
 *   1. Crie uma planilha nova no Google Planilhas.
 *   2. Menu Extensões > Apps Script. Apague o que houver e cole este arquivo.
 *   3. Salve. Clique em Implantar > Nova implantação > tipo "App da Web".
 *      Executar como: Eu. Quem pode acessar: Qualquer pessoa.
 *   4. Autorize e copie o endereço do App da Web (termina em /exec).
 *   5. Cole esse endereço no topo do index.html do site.
 * =============================================================
 */

// Nome da aba onde os dados ficam guardados
const ABA = "eventos";

// Colunas da base, na ordem em que aparecem na planilha
const COLUNAS = [
  "data_hora",       // quando aconteceu (horário do servidor do Google)
  "sessao",          // código aleatório de cada visita (não identifica a pessoa)
  "evento",          // recomendacao | clique_coursera | mais_como_este | desmarcou | nao_e_pra_mim | ver_mais | avaliacao | usabilidade
  "modo",            // tema | areas | perfil (como a pessoa respondeu a 1ª pergunta)
  "tema",            // o que a pessoa digitou, se escolheu "tenho um tema"
  "areas",           // áreas escolhidas (ou sugeridas pelo perfil)
  "objetivo",        // primeiro | mudar | crescer | interesse
  "nivel",           // 1 iniciante | 2 básico | 3 experiente
  "idioma",          // legenda | sim | es
  "curso",           // identificador do curso (parte final do link da Coursera)
  "curso_nome",      // nome original do curso
  "posicao",         // posição do curso na lista (1 = primeiro)
  "lista_exibida",   // cursos mostrados, separados por " | "
  "cursos_marcados", // cursos marcados como "Mais como este" naquele momento
  "nota",            // 1 a 5 (só no evento "avaliacao")
  "comentario",      // comentário opcional (só no evento "avaliacao")
  "versao",          // versão do site
  // ---- questionário de usabilidade SUS (só no evento "usabilidade") ----
  "sus_1", "sus_2", "sus_3", "sus_4", "sus_5",   // respostas de 1 a 5
  "sus_6", "sus_7", "sus_8", "sus_9", "sus_10",
  "sus_score",       // nota SUS de 0 a 100 calculada no site
  "intencao"         // pretende fazer algum curso? sim | talvez | nao
];

// Recebe os dados enviados pelo site
function doPost(e) {
  const trava = LockService.getScriptLock();
  trava.waitLock(10000); // evita que dois envios ao mesmo tempo gravem na mesma linha
  try {
    const dados = JSON.parse(e.postData.contents);
    const lista = Array.isArray(dados) ? dados : [dados];
    const aba = obterAba_();
    const linhas = lista.slice(0, 20).map(function (d) {
      return COLUNAS.map(function (c) { return c === "data_hora" ? new Date() : limpar_(d[c]); });
    });
    aba.getRange(aba.getLastRow() + 1, 1, linhas.length, COLUNAS.length).setValues(linhas);
    return resposta_({ ok: true, gravados: linhas.length });
  } catch (erro) {
    return resposta_({ ok: false, erro: String(erro) });
  } finally {
    trava.releaseLock();
  }
}

// Abrir o endereço no navegador mostra se a coleta está no ar.
// Com ?resumo=1 devolve só NÚMEROS AGREGADOS para o painel público
// (nenhuma linha individual, tema digitado ou comentário sai daqui).
function doGet(e) {
  if (e && e.parameter && e.parameter.resumo) return resposta_(resumo_());
  return resposta_({ ok: true, mensagem: "Coleta do Próximo Curso ativa" });
}

function resumo_() {
  const aba = obterAba_();
  const n = aba.getLastRow() - 1;
  const vazio = { ok: true, atualizado: new Date().toISOString(), sessoes: 0 };
  if (n <= 0) return vazio;
  const cab = aba.getRange(1, 1, 1, aba.getLastColumn()).getValues()[0];
  const col = {}; cab.forEach(function (c, k) { col[c] = k; });
  const linhas = aba.getRange(2, 1, n, cab.length).getValues();
  const v = function (l, c) { return col[c] === undefined ? "" : l[col[c]]; };

  const sessoes = {}, comRec = {}, comClique = {}, porDia = {}, modo = {}, objetivo = {}, nivel = {}, idioma = {};
  const notas = [0, 0, 0, 0, 0], sus = [], intencao = { sim: 0, talvez: 0, nao: 0 }, cursos = {}, posicao = {};
  let cliques = 0, mais = 0, descartes = 0, susItens = [];
  for (let k = 0; k < 10; k++) susItens.push([]);

  linhas.forEach(function (l) {
    const s = v(l, "sessao"), ev = v(l, "evento");
    if (!s) return;
    sessoes[s] = true;
    const d = v(l, "data_hora");
    const dia = d instanceof Date ? Utilities.formatDate(d, "America/Sao_Paulo", "yyyy-MM-dd") : String(d).slice(0, 10);
    if (ev === "recomendacao") {
      if (!comRec[s]) {
        comRec[s] = true;
        porDia[dia] = (porDia[dia] || 0) + 1;
        conta_(modo, v(l, "modo")); conta_(objetivo, v(l, "objetivo"));
        conta_(nivel, String(v(l, "nivel"))); conta_(idioma, v(l, "idioma"));
      }
    } else if (ev === "clique_coursera") {
      cliques++; comClique[s] = true; conta_(cursos, v(l, "curso_nome")); conta_(posicao, String(v(l, "posicao")));
    } else if (ev === "mais_como_este") { mais++;
    } else if (ev === "nao_e_pra_mim") { descartes++;
    } else if (ev === "avaliacao") {
      const nt = Number(v(l, "nota")); if (nt >= 1 && nt <= 5) notas[nt - 1]++;
    } else if (ev === "usabilidade") {
      const sc = Number(v(l, "sus_score")); if (!isNaN(sc) && v(l, "sus_score") !== "") sus.push(sc);
      for (let k = 0; k < 10; k++) { const x = Number(v(l, "sus_" + (k + 1))); if (x >= 1 && x <= 5) susItens[k].push(x); }
      const it = v(l, "intencao"); if (intencao[it] !== undefined) intencao[it]++;
    }
  });

  const media = function (a) { return a.length ? a.reduce(function (x, y) { return x + y; }, 0) / a.length : null; };
  const totalNotas = notas.reduce(function (x, y) { return x + y; }, 0);
  return {
    ok: true,
    atualizado: new Date().toISOString(),
    sessoes: Object.keys(sessoes).length,
    sessoes_com_recomendacao: Object.keys(comRec).length,
    sessoes_com_clique: Object.keys(comClique).length,
    cliques: cliques, mais_como_este: mais, nao_e_pra_mim: descartes,
    notas: notas, nota_media: totalNotas ? notas.reduce(function (t, q, k) { return t + q * (k + 1); }, 0) / totalNotas : null,
    sus_respostas: sus.length, sus_media: media(sus),
    sus_faixas: faixasSus_(sus), sus_itens: susItens.map(media),
    intencao: intencao,
    por_dia: porDia, modo: modo, objetivo: objetivo, nivel: nivel, idioma: idioma,
    cursos_mais_clicados: topo_(cursos, 10), cliques_por_posicao: posicao
  };
}

function conta_(obj, chave) { if (chave === "" || chave === undefined) return; obj[chave] = (obj[chave] || 0) + 1; }
function topo_(obj, n) {
  return Object.keys(obj).map(function (k) { return [k, obj[k]]; })
    .sort(function (a, b) { return b[1] - a[1]; }).slice(0, n);
}
// Faixas usuais de interpretação da nota SUS (Bangor, Kortum e Miller, 2009)
function faixasSus_(lista) {
  const f = { "abaixo de 51 (ruim)": 0, "51 a 67 (regular)": 0, "68 a 80 (bom)": 0, "acima de 80 (excelente)": 0 };
  lista.forEach(function (s) {
    if (s < 51) f["abaixo de 51 (ruim)"]++; else if (s < 68) f["51 a 67 (regular)"]++;
    else if (s <= 80) f["68 a 80 (bom)"]++; else f["acima de 80 (excelente)"]++;
  });
  return f;
}

// Cria a aba e o cabeçalho na primeira vez
function obterAba_() {
  const planilha = SpreadsheetApp.getActiveSpreadsheet();
  let aba = planilha.getSheetByName(ABA);
  if (!aba) aba = planilha.insertSheet(ABA);
  if (aba.getLastRow() === 0) {
    aba.appendRow(COLUNAS);
    aba.setFrozenRows(1);
  } else if (aba.getLastColumn() < COLUNAS.length) {
    // planilha criada com a versão 1.0 do script: acrescenta as colunas novas no cabeçalho
    aba.getRange(1, 1, 1, COLUNAS.length).setValues([COLUNAS]);
  }
  return aba;
}

// Limpa cada valor: limita o tamanho e impede que um texto vire fórmula
function limpar_(valor) {
  if (valor === undefined || valor === null) return "";
  if (typeof valor === "number") return valor;
  if (Array.isArray(valor)) valor = valor.join(" | ");
  let texto = String(valor).slice(0, 500);
  if (/^[=+\-@]/.test(texto)) texto = "'" + texto; // proteção contra injeção de fórmulas
  return texto;
}

function resposta_(objeto) {
  return ContentService.createTextOutput(JSON.stringify(objeto))
    .setMimeType(ContentService.MimeType.JSON);
}
