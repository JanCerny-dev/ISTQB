/* Simulace zkoušky ISTQB CTFL v4.0.
   Data dodává assets/vzorove/sada-*.js nebo assets/cvicne/zkouska-*.js (window.VZOROVA_ZKOUSKA),
   náhodnou zkoušku assets/cvicne/vse.js (window.CVICNE_OTAZKY) — otázky se losují při spuštění
   podle rozpisu ostré zkoušky a jejich id se ukládají do stavu, aby obnova stránky vrátila stejný test.
   Průběh: úvod → test → výsledek → (oprava 10 min) → vyhodnocení.
   Nic se nenačítá přes fetch, stránka funguje i otevřená z disku. */
(function () {
  "use strict";

  var C = window.CVICNE_OTAZKY;
  var D = window.VZOROVA_ZKOUSKA || (C && { sada: "nahodna", oficialni: false, nahodna: true, otazky: [] });
  var koren = document.getElementById("zkouska");
  if (!D || !koren) return;

  var OTAZKY = D.otazky;
  var POCET = D.nahodna ? C.rozpis.length : OTAZKY.length;
  var OFICIALNI = D.oficialni !== false;
  var HRANICE = Math.ceil(POCET * 0.65);
  var MINUT_TEST = 60;
  var MINUT_PRODLOUZENO = 75;
  var MINUT_OPRAVA = 10;
  var KLIC = "istqb-vzorova-" + D.sada.toLowerCase();
  var KLIC_VYSLEDKY = "istqb-zkousky-vysledky";   // souhrn pro rozcestník zkouska.html
  var PISMENA = "abcde";

  var S = null;          // stav, ukládá se do localStorage
  var casovac = null;

  /* --- úložiště (v soukromém režimu nemusí být k dispozici) --- */
  function uloz() {
    try { localStorage.setItem(KLIC, JSON.stringify(S)); } catch (e) { /* nevadí */ }
  }
  function nacti() {
    try { return JSON.parse(localStorage.getItem(KLIC)); } catch (e) { return null; }
  }
  function smaz() {
    try { localStorage.removeItem(KLIC); } catch (e) { /* nevadí */ }
  }
  // Výsledek pokusu do souhrnu. Oprava přepíše výsledek téhož pokusu, nepočítá se jako nový.
  function zapisVysledek(b) {
    try {
      var vse = JSON.parse(localStorage.getItem(KLIC_VYSLEDKY)) || {};
      var sada = D.sada.toLowerCase();
      var z = vse[sada] || { pokusu: 0, nejlepe: 0 };
      if (z.pokus !== S.pokus) { z.pokusu++; z.pokus = S.pokus; }
      z.posledni = b;
      z.nejlepe = Math.max(z.nejlepe, b);
      z.celkem = POCET;
      z.hranice = HRANICE;
      vse[sada] = z;
      localStorage.setItem(KLIC_VYSLEDKY, JSON.stringify(vse));
    } catch (e) { /* nevadí */ }
  }

  /* --- pomocné funkce --- */
  function esc(t) {
    return String(t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function el(html) {
    var t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }
  function spravne(i, odp) {
    var ok = OTAZKY[i].ok;
    return odp && odp.length === ok.length && ok.every(function (x) { return odp.indexOf(x) >= 0; });
  }
  function skore(odpovedi) {
    var b = 0;
    for (var i = 0; i < POCET; i++) if (spravne(i, odpovedi[i])) b++;
    return b;
  }
  function zodpovezeno(odpovedi) {
    return odpovedi.filter(function (o) { return o && o.length; }).length;
  }
  function mmss(ms) {
    var s = Math.max(0, Math.round(ms / 1000));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  }
  function nahoru() { window.scrollTo(0, koren.offsetTop - 80); }

  /* --- náhodná zkouška: losování podle rozpisu --- */
  function zamichane(pole) {
    var a = pole.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  // Každá pozice rozpisu připouští určité studijní cíle; v jedné zkoušce se cíl neopakuje.
  // Pozice s nejmenší zásobou se obsazují první. Vrací seznam id seřazený podle rozpisu.
  function losuj(sOficialnimi) {
    var zasoba = {};
    C.otazky.forEach(function (q) {
      if (!q.k3 || q.varianta || (q.oficialni && !sOficialnimi)) return;
      (zasoba[q.lo] = zasoba[q.lo] || []).push(q);
    });
    function velikost(poz) { return poz.reduce(function (s, lo) { return s + (zasoba[lo] || []).length; }, 0); }
    for (var pokus = 0; pokus < 50; pokus++) {
      var poradi = C.rozpis.map(function (_, i) { return i; })
        .sort(function (a, b) { return velikost(C.rozpis[a]) - velikost(C.rozpis[b]); });
      var pouzite = {}, vyber = [], ok = true;
      poradi.forEach(function (i) {
        if (!ok) return;
        var kandidati = [];
        C.rozpis[i].forEach(function (lo) {
          if (pouzite[lo]) return;
          (zasoba[lo] || []).forEach(function (q) { kandidati.push(q); });
        });
        if (!kandidati.length) { ok = false; return; }
        var q = kandidati[Math.floor(Math.random() * kandidati.length)];
        pouzite[q.lo] = true;
        vyber.push({ i: i, id: q.id });
      });
      if (ok) return vyber.sort(function (a, b) { return a.i - b.i; }).map(function (x) { return x.id; });
    }
    return null;
  }
  function otazkyPodleId(ids) {
    var mapa = {};
    C.otazky.forEach(function (q) { mapa[q.id] = q; });
    return ids.map(function (id) { return mapa[id]; }).filter(Boolean);
  }
  function pripravStav(stav) {
    if (D.nahodna && stav && stav.ids) OTAZKY = otazkyPodleId(stav.ids);
    return stav;
  }

  /* --- časovač --- */
  function spustCasovac() {
    zastavCasovac();
    casovac = setInterval(tik, 1000);
    tik();
  }
  function zastavCasovac() {
    if (casovac) clearInterval(casovac);
    casovac = null;
  }
  function tik() {
    var zbyva = S.konec - Date.now();
    var u = koren.querySelector("[data-cas]");
    if (u) {
      u.textContent = mmss(zbyva);
      u.classList.toggle("dochazi", zbyva < 5 * 60 * 1000);
    }
    if (zbyva <= 0) {
      zastavCasovac();
      if (S.faze === "test") odevzdej();
      else if (S.faze === "oprava") ukonciOpravu();
    }
  }

  /* --- úvod --- */
  function uvod() {
    zastavCasovac();
    var ulozeny = nacti();
    var rozpracovany = ulozeny && ulozeny.faze !== "vyhodnoceni" && ulozeny.faze;
    koren.innerHTML = "";
    koren.appendChild(el(
      '<section class="zk-karta zk-uvod">' +
        '<h2>Pravidla</h2>' +
        '<ul>' +
          '<li><strong>' + POCET + ' otázek</strong>, u každé jedna správná odpověď (u otázek „vyberte DVĚ“ obě musí být správně).</li>' +
          '<li><strong>' + MINUT_TEST + ' minut</strong>. Po vypršení času se test odevzdá sám.</li>' +
          '<li>K úspěchu je potřeba <strong>' + HRANICE + ' správných odpovědí</strong> (65 %).</li>' +
          '<li>Po odevzdání uvidíte jen počet správných odpovědí. Pokud test nesplníte, můžete ještě ' +
            '<strong>' + MINUT_OPRAVA + ' minut opravovat</strong> — které odpovědi jsou špatně, se ale nedozvíte.</li>' +
          '<li>Rozbor všech otázek se ' + (OFICIALNI ? 'oficiálním ' : '') + 'zdůvodněním přijde až ve vyhodnocení.</li>' +
          (D.nahodna ? '<li>Otázky se losují při každém spuštění: 8/6/4/11/9/2 z kapitol 1–6, K1/K2/K3 v poměru 8/24/8, ' +
            'každý studijní cíl nejvýš jednou.</li>' : '') +
        '</ul>' +
        (D.nahodna ? '<label class="zk-volba"><input type="checkbox" data-oficialni checked> ' +
          'Losovat i z otázek oficiálních vzorových zkoušek A–D</label>' : '') +
        '<label class="zk-volba"><input type="checkbox" data-prodlouzeni> ' +
          'Skládám zkoušku v jiném než rodném jazyce (+25 % času, tedy ' + MINUT_PRODLOUZENO + ' minut)</label>' +
        '<div class="zk-tlacitka">' +
          (rozpracovany
            ? '<button type="button" class="zk-btn zk-btn--hlavni" data-pokracovat>Pokračovat v rozpracovaném testu</button>' +
              '<button type="button" class="zk-btn" data-start>Začít znovu</button>'
            : '<button type="button" class="zk-btn zk-btn--hlavni" data-start>Spustit test</button>') +
        '</div>' +
      '</section>'
    ));
    koren.querySelector("[data-start]").onclick = function () {
      var minut = koren.querySelector("[data-prodlouzeni]").checked ? MINUT_PRODLOUZENO : MINUT_TEST;
      var ids = null;
      if (D.nahodna) {
        ids = losuj(koren.querySelector("[data-oficialni]").checked);
        if (!ids) { alert("Z dostupných otázek se nepodařilo sestavit úplnou zkoušku."); return; }
        OTAZKY = otazkyPodleId(ids);
      }
      S = {
        ids: ids,
        pokus: Date.now(),
        faze: "test", i: 0,
        odp: OTAZKY.map(function () { return []; }),
        oznacene: [],
        konec: Date.now() + minut * 60 * 1000,
        prvni: null, odpPrvni: null
      };
      uloz();
      vykresliTest();
    };
    var pokr = koren.querySelector("[data-pokracovat]");
    if (pokr) pokr.onclick = function () { S = pripravStav(ulozeny); obnov(); };
  }

  function obnov() {
    if (S.faze === "test" || S.faze === "oprava") {
      if (S.konec <= Date.now()) {
        if (S.faze === "test") odevzdej(); else ukonciOpravu();
      } else vykresliTest();
    } else if (S.faze === "vysledek") vysledek();
    else vyhodnoceni();
  }

  /* --- test a oprava (stejné rozhraní) --- */
  function vykresliTest() {
    var oprava = S.faze === "oprava";
    var q = OTAZKY[S.i];
    var odp = S.odp[S.i];
    var typ = q.vyber > 1 ? "checkbox" : "radio";
    var oznacena = S.oznacene.indexOf(S.i) >= 0;

    koren.innerHTML = "";
    var w = el(
      '<div class="zk-test">' +
        (oprava ? '<p class="zk-banner">Režim opravy: máte ' + MINUT_OPRAVA + ' minut na změnu odpovědí. ' +
          'Které odpovědi jsou špatně, se nedozvíte — projděte otázky sami.</p>' : '') +
        '<div class="zk-lista">' +
          '<span>Otázka <strong>' + (S.i + 1) + '</strong> z ' + POCET + '</span>' +
          '<span>Zodpovězeno ' + zodpovezeno(S.odp) + ' / ' + POCET + '</span>' +
          '<span class="zk-cas" aria-live="off">Zbývá <strong data-cas></strong></span>' +
        '</div>' +
        '<article class="zk-karta zk-otazka">' +
          '<div class="zk-zadani">' + q.q + '</div>' +
          (q.pozn ? '<p class="zk-poznamka"><strong>Poznámka webu:</strong> ' + q.pozn + '</p>' : '') +
          '<p class="zk-pokyn">' + (q.vyber > 1 ? 'Vyberte DVĚ možnosti.' : 'Vyberte JEDNU možnost.') + '</p>' +
          '<ul class="zk-moznosti">' +
            q.m.map(function (m, k) {
              return '<li><label class="zk-moznost">' +
                '<input type="' + typ + '" name="odp" value="' + k + '"' + (odp.indexOf(k) >= 0 ? " checked" : "") + '>' +
                '<span class="zk-pismeno">' + PISMENA[k] + ')</span> <span>' + m + '</span></label></li>';
            }).join("") +
          '</ul>' +
          '<div class="zk-ovladani">' +
            '<button type="button" class="zk-btn" data-pred' + (S.i === 0 ? " disabled" : "") + '>← Předchozí</button>' +
            '<button type="button" class="zk-btn' + (oznacena ? ' zk-btn--oznacena' : '') + '" data-oznacit aria-pressed="' + oznacena + '">' +
              (oznacena ? 'Označeno k revizi' : 'Označit k revizi') + '</button>' +
            '<button type="button" class="zk-btn zk-btn--hlavni" data-dalsi' + (S.i === POCET - 1 ? " disabled" : "") + '>Další →</button>' +
          '</div>' +
        '</article>' +
        '<nav class="zk-mrizka" aria-label="Přehled otázek">' +
          OTAZKY.map(function (_, k) {
            var t = [];
            if (S.odp[k].length) t.push("zodpovezena");
            if (S.oznacene.indexOf(k) >= 0) t.push("oznacena");
            if (k === S.i) t.push("aktualni");
            return '<button type="button" class="' + t.join(" ") + '" data-k="' + k + '"' +
              (k === S.i ? ' aria-current="true"' : '') + '>' + (k + 1) + '</button>';
          }).join("") +
        '</nav>' +
        '<p class="zk-legenda"><span class="zk-tecka zodpovezena"></span> zodpovězeno ' +
          '<span class="zk-tecka oznacena"></span> označeno k revizi</p>' +
        '<div class="zk-odevzdat" data-odevzdat-blok>' +
          '<button type="button" class="zk-btn zk-btn--hlavni" data-odevzdat>' +
            (oprava ? 'Ukončit opravu a zobrazit vyhodnocení' : 'Odevzdat test') + '</button>' +
        '</div>' +
      '</div>'
    );
    koren.appendChild(w);

    w.querySelectorAll('input[name="odp"]').forEach(function (inp) {
      inp.addEventListener("change", function () {
        var vybrane = [].slice.call(w.querySelectorAll('input[name="odp"]:checked')).map(function (x) { return +x.value; });
        if (q.vyber > 1 && vybrane.length > q.vyber) {
          inp.checked = false;
          vybrane = vybrane.filter(function (x) { return x !== +inp.value; });
        }
        S.odp[S.i] = vybrane;
        uloz();
        var b = w.querySelector('.zk-mrizka [data-k="' + S.i + '"]');
        b.classList.toggle("zodpovezena", vybrane.length > 0);
        w.querySelector(".zk-lista span:nth-child(2)").textContent = "Zodpovězeno " + zodpovezeno(S.odp) + " / " + POCET;
      });
    });
    function jdi(k) { S.i = k; uloz(); vykresliTest(); nahoru(); }
    w.querySelector("[data-pred]").onclick = function () { if (S.i > 0) jdi(S.i - 1); };
    w.querySelector("[data-dalsi]").onclick = function () { if (S.i < POCET - 1) jdi(S.i + 1); };
    w.querySelector("[data-oznacit]").onclick = function () {
      var p = S.oznacene.indexOf(S.i);
      if (p >= 0) S.oznacene.splice(p, 1); else S.oznacene.push(S.i);
      uloz(); vykresliTest();
    };
    w.querySelectorAll(".zk-mrizka button").forEach(function (b) {
      b.onclick = function () { jdi(+b.dataset.k); };
    });
    w.querySelector("[data-odevzdat]").onclick = function () { potvrd(w, oprava); };
    spustCasovac();
  }

  function potvrd(w, oprava) {
    var blok = w.querySelector("[data-odevzdat-blok]");
    var chybi = POCET - zodpovezeno(S.odp);
    var oznac = S.oznacene.length;
    blok.innerHTML =
      '<div class="zk-potvrzeni" role="alertdialog" aria-label="Potvrzení odevzdání">' +
        '<p><strong>' + (oprava ? 'Opravdu ukončit opravu?' : 'Opravdu odevzdat test?') + '</strong></p>' +
        (chybi ? '<p>Nezodpovězených otázek: <strong>' + chybi + '</strong>. Za nezodpovězenou otázku je 0 bodů.</p>' : '') +
        (oznac ? '<p>Otázek označených k revizi: <strong>' + oznac + '</strong>.</p>' : '') +
        '<div class="zk-tlacitka">' +
          '<button type="button" class="zk-btn zk-btn--hlavni" data-ano>' + (oprava ? 'Ano, ukončit' : 'Ano, odevzdat') + '</button>' +
          '<button type="button" class="zk-btn" data-ne>Zpět do testu</button>' +
        '</div>' +
      '</div>';
    blok.querySelector("[data-ano]").onclick = function () { if (oprava) ukonciOpravu(); else odevzdej(); };
    blok.querySelector("[data-ne]").onclick = function () { vykresliTest(); };
    blok.querySelector("[data-ano]").focus();
  }

  function odevzdej() {
    zastavCasovac();
    S.prvni = skore(S.odp);
    S.odpPrvni = S.odp.map(function (o) { return o.slice(); });
    S.faze = "vysledek";
    uloz();
    zapisVysledek(S.prvni);
    vysledek();
  }

  function ukonciOpravu() {
    zastavCasovac();
    S.faze = "vyhodnoceni";
    uloz();
    zapisVysledek(skore(S.odp));
    vyhodnoceni();
  }

  /* --- obrazovka s výsledkem (bez rozboru) --- */
  function vysledek() {
    zastavCasovac();
    var b = S.prvni;
    var ok = b >= HRANICE;
    koren.innerHTML = "";
    var w = el(
      '<section class="zk-karta zk-vysledek">' +
        '<p class="zk-skore ' + (ok ? "uspech" : "neuspech") + '">' + b + ' <span>/ ' + POCET + '</span></p>' +
        '<p class="zk-hranice">K úspěchu je potřeba <strong>' + HRANICE + '</strong> správných odpovědí (65 %).</p>' +
        (ok
          ? '<p class="zk-verdikt uspech">Test jste splnili.</p>' +
            '<div class="zk-tlacitka"><button type="button" class="zk-btn zk-btn--hlavni" data-vyhodnoceni>Přejít na vyhodnocení</button></div>'
          : '<p class="zk-verdikt neuspech">Test jste nesplnili — chybí ' + (HRANICE - b) + ' ' + (HRANICE - b === 1 ? 'bod' : (HRANICE - b < 5 ? 'body' : 'bodů')) + '.</p>' +
            '<p>Můžete test ukončit a podívat se na rozbor, nebo si dát ještě ' + MINUT_OPRAVA + ' minut na opravu. ' +
            'Při opravě se nedozvíte, které odpovědi jsou špatně — musíte je najít sami.</p>' +
            '<div class="zk-tlacitka">' +
              '<button type="button" class="zk-btn" data-vyhodnoceni>Ukončit test a přejít na vyhodnocení</button>' +
              '<button type="button" class="zk-btn zk-btn--hlavni" data-oprava>Opravit odpovědi (' + MINUT_OPRAVA + ' minut)</button>' +
            '</div>') +
      '</section>'
    );
    koren.appendChild(w);
    w.querySelector("[data-vyhodnoceni]").onclick = function () { S.faze = "vyhodnoceni"; uloz(); vyhodnoceni(); };
    var opr = w.querySelector("[data-oprava]");
    if (opr) opr.onclick = function () {
      S.faze = "oprava";
      S.i = 0;
      S.konec = Date.now() + MINUT_OPRAVA * 60 * 1000;
      uloz();
      vykresliTest();
      nahoru();
    };
    nahoru();
  }

  /* --- vyhodnocení s rozborem --- */
  function vyhodnoceni() {
    zastavCasovac();
    var b = skore(S.odp);
    var ok = b >= HRANICE;
    var opraveno = S.odpPrvni && S.odp.some(function (o, i) {
      return o.join() !== (S.odpPrvni[i] || []).join();
    });

    var kapitoly = {};
    OTAZKY.forEach(function (q, i) {
      var k = q.kap.c.split(".")[0];
      var z = kapitoly[k] || (kapitoly[k] = { spravne: 0, celkem: 0 });
      z.celkem++;
      if (spravne(i, S.odp[i])) z.spravne++;
    });

    koren.innerHTML = "";
    var w = el(
      '<div class="zk-vyhodnoceni">' +
        '<section class="zk-karta zk-souhrn">' +
          '<p class="zk-skore ' + (ok ? "uspech" : "neuspech") + '">' + b + ' <span>/ ' + POCET + '</span></p>' +
          '<p class="zk-verdikt ' + (ok ? "uspech" : "neuspech") + '">' +
            (ok ? 'Splněno' : 'Nesplněno') + ' — hranice je ' + HRANICE + ' správných odpovědí.</p>' +
          (S.odpPrvni && (S.prvni !== b || opraveno)
            ?'<p class="zk-hranice">Po prvním odevzdání: ' + S.prvni + ' / ' + POCET + ', po opravě: ' + b + ' / ' + POCET + '.</p>'
            : '') +
          '<h3>Podle kapitol sylabu</h3>' +
          '<ul class="zk-kapitoly">' +
            Object.keys(kapitoly).sort().map(function (k) {
              var z = kapitoly[k];
              return '<li><span>Kapitola ' + k + '</span><span class="zk-pruh"><i style="width:' +
                Math.round(z.spravne / z.celkem * 100) + '%"></i></span><strong>' + z.spravne + ' / ' + z.celkem + '</strong></li>';
            }).join("") +
          '</ul>' +
          '<div class="zk-tlacitka">' +
            '<button type="button" class="zk-btn" aria-pressed="true" data-filtr="vse">Všechny otázky</button>' +
            '<button type="button" class="zk-btn" aria-pressed="false" data-filtr="spatne">Jen chybné (' + (POCET - b) + ')</button>' +
            '<button type="button" class="zk-btn" data-znovu>Začít test znovu</button>' +
          '</div>' +
        '</section>' +
        '<div class="zk-rozbor">' + OTAZKY.map(function (q, i) { return rozborOtazky(q, i); }).join("") + '</div>' +
      '</div>'
    );
    koren.appendChild(w);

    w.querySelectorAll("[data-filtr]").forEach(function (t) {
      t.onclick = function () {
        w.querySelectorAll("[data-filtr]").forEach(function (x) { x.setAttribute("aria-pressed", x === t); });
        var jenSpatne = t.dataset.filtr === "spatne";
        w.querySelectorAll(".zk-rozbor-otazka").forEach(function (c) {
          c.hidden = jenSpatne && c.classList.contains("spravne");
        });
      };
    });
    w.querySelector("[data-znovu]").onclick = function () { smaz(); S = null; uvod(); nahoru(); };
    nahoru();
  }

  function rozborOtazky(q, i) {
    var odp = S.odp[i];
    var ok = spravne(i, odp);
    var zmena = S.odpPrvni && odp.join() !== (S.odpPrvni[i] || []).join();
    return '<article class="zk-karta zk-rozbor-otazka ' + (ok ? "spravne" : "chybne") + '" id="otazka-' + (i + 1) + '">' +
      '<header class="zk-rozbor-hlava">' +
        '<span class="zk-stitek ' + (ok ? "uspech" : "neuspech") + '">' + (ok ? "Správně" : (odp.length ? "Špatně" : "Nezodpovězeno")) + '</span>' +
        '<strong>Otázka ' + (i + 1) + '</strong>' +
        '<span class="zk-meta">' + esc(q.lo) + ' · ' + esc(q.k) + '</span>' +
        (q.zdroj && !OFICIALNI ? '<span class="zk-meta">' + esc(q.zdroj) + '</span>' : '') +
        (zmena ? '<span class="zk-meta">změněno při opravě</span>' : '') +
      '</header>' +
      '<div class="zk-zadani">' + q.q + '</div>' +
          (q.pozn ? '<p class="zk-poznamka"><strong>Poznámka webu:</strong> ' + q.pozn + '</p>' : '') +
      '<ul class="zk-moznosti zk-moznosti--rozbor">' +
        q.m.map(function (m, k) {
          var jeSpravna = q.ok.indexOf(k) >= 0;
          var vybrana = odp.indexOf(k) >= 0;
          var tr = jeSpravna ? "spravna" : (vybrana ? "chybna" : "");
          var vys = q.vys[PISMENA[k]];
          return '<li class="' + tr + '">' +
            '<div class="zk-moznost-text"><span class="zk-pismeno">' + PISMENA[k] + ')</span> <span>' + m + '</span>' +
              (vybrana ? ' <em class="zk-vase">vaše odpověď</em>' : '') + '</div>' +
            (vys ? '<p class="zk-zduvodneni">' + vys + '</p>' : '') +
          '</li>';
        }).join("") +
      '</ul>' +
      (q.obecne ? '<div class="zk-obecne">' + q.obecne + '</div>' : '') +
      (q.pozn_vyh ? '<p class="zk-poznamka"><strong>Poznámka webu:</strong> ' + q.pozn_vyh + '</p>' : '') +
      '<p class="zk-odkaz">Sylabus ' + esc(q.kap.c) + ' ' + esc(q.kap.nazev) +
        ' — <a href="' + q.kap.href + '">plný výklad v kapitole ' + esc(q.kap.c.split(".")[0]) + ' →</a></p>' +
    '</article>';
  }

  /* --- start --- */
  var ulozeny = pripravStav(nacti());
  if (ulozeny && ulozeny.faze === "vyhodnoceni") { S = ulozeny; vyhodnoceni(); }
  else if (ulozeny && ulozeny.faze === "vysledek") { S = ulozeny; vysledek(); }
  else uvod();
})();
