/* Procvičování cvičných otázek po kapitolách s okamžitým vyhodnocením.
   Data dodává assets/cvicne/vse.js (window.CVICNE_OTAZKY). Výchozí výběr jsou „otázky navíc“
   (ty, které nejsou v žádné cvičné zkoušce); volitelně všechny cvičné otázky.
   Oficiální otázky vzorových zkoušek se tu neprocvičují — mají vlastní stránky. */
(function () {
  "use strict";

  var C = window.CVICNE_OTAZKY;
  var koren = document.getElementById("procvicovani");
  if (!C || !koren) return;

  var PISMENA = "abcdef";
  var KLIC = "istqb-procvicovani";
  var cvicne = C.otazky.filter(function (q) { return !q.oficialni; });

  var nast = { kap: "vse", vse: false };
  try { nast = Object.assign(nast, JSON.parse(localStorage.getItem(KLIC)) || {}); } catch (e) { /* nevadí */ }
  var fronta = [], pozice = 0, odpoved = [], hotovo = false, skore = { ok: 0, celkem: 0 };

  function uloz() { try { localStorage.setItem(KLIC, JSON.stringify(nast)); } catch (e) { /* nevadí */ } }
  function esc(t) {
    return String(t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function zamichane(pole) {
    var a = pole.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function vyber() {
    return cvicne.filter(function (q) {
      return (nast.vse || q.navic) && (nast.kap === "vse" || q.lo.charAt(3) === nast.kap);
    });
  }
  function novaFronta() {
    fronta = zamichane(vyber());
    pozice = 0; odpoved = []; hotovo = false; skore = { ok: 0, celkem: 0 };
    vykresli();
  }
  function spravne(q) {
    return odpoved.length === q.ok.length && q.ok.every(function (x) { return odpoved.indexOf(x) >= 0; });
  }

  function filtry() {
    var pocty = {};
    cvicne.forEach(function (q) { if (nast.vse || q.navic) pocty[q.lo.charAt(3)] = (pocty[q.lo.charAt(3)] || 0) + 1; });
    var celkem = Object.keys(pocty).reduce(function (s, k) { return s + pocty[k]; }, 0);
    var tl = '<button type="button" class="zk-btn" data-kap="vse" aria-pressed="' + (nast.kap === "vse") + '">Všechny kapitoly (' + celkem + ')</button>';
    Object.keys(C.kapitoly).forEach(function (k) {
      tl += '<button type="button" class="zk-btn" data-kap="' + k + '" aria-pressed="' + (nast.kap === k) + '" title="' +
        esc(C.kapitoly[k]) + '">Kapitola ' + k + ' (' + (pocty[k] || 0) + ')</button>';
    });
    return '<section class="zk-karta">' +
      '<div class="zk-tlacitka">' + tl + '</div>' +
      '<label class="zk-volba"><input type="checkbox" data-vse' + (nast.vse ? " checked" : "") + '> ' +
        'Zahrnout i otázky, které jsou v cvičných zkouškách</label>' +
    '</section>';
  }

  function vykresli() {
    var q = fronta[pozice];
    var html = filtry();
    if (!q) {
      html += '<section class="zk-karta"><p>' + (fronta.length
        ? 'Hotovo — správně ' + skore.ok + ' z ' + skore.celkem + '.'
        : 'V tomto výběru nejsou žádné otázky.') + '</p>' +
        (fronta.length ? '<div class="zk-tlacitka"><button type="button" class="zk-btn zk-btn--hlavni" data-znovu>Projít znovu v jiném pořadí</button></div>' : '') +
        '</section>';
      koren.innerHTML = html;
      navaz();
      return;
    }
    var typ = q.vyber > 1 ? "checkbox" : "radio";
    html += '<div class="zk-lista">' +
        '<span>Otázka <strong>' + (pozice + 1) + '</strong> z ' + fronta.length + '</span>' +
        '<span>Správně ' + skore.ok + ' / ' + skore.celkem + '</span>' +
        '<span>' + esc(q.lo) + ' · ' + esc(q.k) + '</span>' +
      '</div>' +
      '<article class="zk-karta zk-otazka' + (hotovo ? (spravne(q) ? " spravne" : " chybne") : "") + '">' +
        '<div class="zk-zadani">' + q.q + '</div>' +
        '<p class="zk-pokyn">' + (q.vyber > 1 ? 'Vyberte DVĚ možnosti.' : 'Vyberte JEDNU možnost.') + '</p>' +
        '<ul class="zk-moznosti' + (hotovo ? ' zk-moznosti--rozbor' : '') + '">' +
          q.m.map(function (m, k) {
            if (!hotovo) {
              return '<li><label class="zk-moznost"><input type="' + typ + '" name="odp" value="' + k + '"' +
                (odpoved.indexOf(k) >= 0 ? " checked" : "") + '><span class="zk-pismeno">' + PISMENA[k] +
                ')</span> <span>' + m + '</span></label></li>';
            }
            var jeSpravna = q.ok.indexOf(k) >= 0, vybrana = odpoved.indexOf(k) >= 0;
            var vys = q.vys[PISMENA[k]];
            return '<li class="' + (jeSpravna ? "spravna" : (vybrana ? "chybna" : "")) + '">' +
              '<div class="zk-moznost-text"><span class="zk-pismeno">' + PISMENA[k] + ')</span> <span>' + m + '</span>' +
              (vybrana ? ' <em class="zk-vase">vaše odpověď</em>' : '') + '</div>' +
              (vys ? '<p class="zk-zduvodneni">' + vys + '</p>' : '') + '</li>';
          }).join("") +
        '</ul>' +
        (hotovo
          ? '<p class="zk-verdikt ' + (spravne(q) ? 'uspech">Správně.' : 'neuspech">Špatně.') + '</p>' +
            (q.obecne ? '<div class="zk-obecne">' + q.obecne + '</div>' : '') +
            '<p class="zk-odkaz">Sylabus ' + esc(q.kap.c) + ' ' + esc(q.kap.nazev) +
              ' — <a href="' + q.kap.href + '">plný výklad v kapitole ' + esc(q.kap.c.split(".")[0]) + ' →</a></p>' +
            '<p class="zk-meta">' + esc(q.zdroj) + '</p>'
          : '') +
        '<div class="zk-ovladani">' +
          (hotovo
            ? '<button type="button" class="zk-btn zk-btn--hlavni" data-dalsi>Další otázka →</button>'
            : '<button type="button" class="zk-btn zk-btn--hlavni" data-vyhodnotit disabled>Vyhodnotit</button>') +
        '</div>' +
      '</article>';
    koren.innerHTML = html;
    navaz();

    var btn = koren.querySelector("[data-vyhodnotit]");
    koren.querySelectorAll('input[name="odp"]').forEach(function (inp) {
      inp.addEventListener("change", function () {
        var v = [].slice.call(koren.querySelectorAll('input[name="odp"]:checked')).map(function (x) { return +x.value; });
        if (q.vyber > 1 && v.length > q.vyber) {
          inp.checked = false;
          v = v.filter(function (x) { return x !== +inp.value; });
        }
        odpoved = v;
        btn.disabled = odpoved.length !== q.vyber;
      });
    });
    if (btn) btn.onclick = function () {
      hotovo = true; skore.celkem++;
      if (spravne(q)) skore.ok++;
      vykresli();
    };
    var dalsi = koren.querySelector("[data-dalsi]");
    if (dalsi) dalsi.onclick = function () {
      pozice++; odpoved = []; hotovo = false; vykresli();
      window.scrollTo(0, koren.offsetTop - 80);
    };
  }

  function navaz() {
    koren.querySelectorAll("[data-kap]").forEach(function (b) {
      b.onclick = function () { nast.kap = b.dataset.kap; uloz(); novaFronta(); };
    });
    koren.querySelector("[data-vse]").onchange = function (ev) { nast.vse = ev.target.checked; uloz(); novaFronta(); };
    var z = koren.querySelector("[data-znovu]");
    if (z) z.onclick = novaFronta;
  }

  novaFronta();
})();
