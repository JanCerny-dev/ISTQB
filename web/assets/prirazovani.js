/* Přiřazovací cvičení ISTQB CTFL v4.0.
   Data dodává assets/prirazovani-data.js (window.PRIRAZOVANI), generované
   z tools/prirazovani/sady.json. Položka sady: [text, klíč kategorie,
   zdůvodnění, (kód otázky vzorového testu)]. Výsledky a seznam chybných
   položek se ukládají jen do localStorage prohlížeče.
   Nic se nenačítá přes fetch, stránka funguje i otevřená z disku. */
(function () {
  "use strict";

  var D = window.PRIRAZOVANI;
  if (!D || !document.getElementById("prehled")) return;

  var SADY = D.sady;
  var KLIC = "istqb-prirazovani-v2";
  var MIX = 20;

  function $(id) { return document.getElementById(id); }

  function el(tag, trida, text) {
    var x = document.createElement(tag);
    if (trida) x.className = trida;
    if (text !== undefined) x.textContent = text;
    return x;
  }

  function nactiStav() {
    try {
      var s = JSON.parse(localStorage.getItem(KLIC));
      if (s && s.sady && s.chyby) return s;
    } catch (e) {}
    return { sady: {}, chyby: {} };
  }
  function ulozStav() {
    try { localStorage.setItem(KLIC, JSON.stringify(stav)); } catch (e) {}
  }
  var stav = nactiStav();

  function zamichat(pole) {
    var a = pole.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  /* Každá položka nese odkaz na svou sadu, aby šlo míchat napříč sadami. */
  function polozkySady(sada) {
    return sada.pol.map(function (p, i) {
      return { sada: sada, text: p[0], spr: p[1], proc: p[2], vzor: p[3] || "", klic: sada.id + ":" + i };
    });
  }
  function vsechnyPolozky() {
    return SADY.reduce(function (a, s) { return a.concat(polozkySady(s)); }, []);
  }
  function slabePolozky() {
    return vsechnyPolozky().filter(function (p) { return (stav.chyby[p.klic] || 0) > 0; });
  }
  function vzorovePolozky(kap) {
    return vsechnyPolozky().filter(function (p) { return p.vzor && (!kap || p.sada.kap === kap); });
  }

  /* ---------- přehled ---------- */

  function vykresliPrehled() {
    var kontejner = $("kapitoly-prirazovani");
    kontejner.textContent = "";
    Object.keys(D.kapitoly).forEach(function (k) {
      var kap = +k;
      var sadyKap = SADY.filter(function (s) { return s.kap === kap; });
      if (!sadyKap.length) return;

      var sekce = el("section", "pr-kapitola");
      sekce.id = "kapitola-" + kap;
      sekce.setAttribute("data-kapitola", String(kap));
      var h2 = el("h2", "pr-kapitola-nadpis");
      h2.append(el("span", "pr-kapitola-cislo", String(kap)), document.createTextNode(D.kapitoly[k]));
      sekce.append(h2);

      var polKap = sadyKap.reduce(function (a, s) { return a.concat(polozkySady(s)); }, []);
      var vzorKap = polKap.filter(function (p) { return p.vzor; });
      var akce = el("div", "pr-akce");
      var mix = el("button", "pr-tl", "Namíchat " + Math.min(MIX, polKap.length) + " položek z kapitoly");
      mix.type = "button";
      mix.addEventListener("click", function () {
        spust("Kapitola " + kap + ": mix", zamichat(polKap).slice(0, MIX), true);
      });
      akce.append(mix);
      if (vzorKap.length) {
        var vz = el("button", "pr-tl", "Jen ze vzorových testů (" + vzorKap.length + ")");
        vz.type = "button";
        vz.addEventListener("click", function () {
          spust("Kapitola " + kap + ": ze vzorových testů", zamichat(vzorKap), true);
        });
        akce.append(vz);
      }
      sekce.append(akce);

      var mrizka = el("div", "pr-mrizka");
      sadyKap.forEach(function (s) {
        var b = el("button", "pr-karta");
        b.type = "button";
        var pocetVzor = s.pol.filter(function (p) { return p[3]; }).length;
        b.append(el("small", "", "Sylabus " + s.sek + " · " + s.pol.length + " položek"));
        b.append(el("b", "", s.nazev));
        b.append(el("span", "pr-puvod", s.zdroj));
        if (pocetVzor) {
          b.append(el("span", "pr-vzor-znacka", pocetVzor + " ze vzorových testů"));
        }
        var z = stav.sady[s.id];
        if (z) {
          b.append(el("span", "pr-stav " + (z.posledni >= 85 ? "pr-stav--ok" : "pr-stav--slabe"),
            "Naposledy " + z.posledni + " % · nejlépe " + z.nejlepe + " %"));
        }
        b.addEventListener("click", function () { spust(s.nazev, zamichat(polozkySady(s)), false, s); });
        mrizka.append(b);
      });
      sekce.append(mrizka);
      kontejner.append(sekce);
    });

    var slabe = slabePolozky();
    $("tl-slabe").hidden = slabe.length === 0;
    $("tl-slabe").textContent = "Procvičit položky, ve kterých chybuju (" + slabe.length + ")";
    $("tl-vzor").textContent = "Jen položky ze vzorových testů (" + vzorovePolozky().length + ", náhodně " + MIX + ")";
  }

  /* ---------- cvičení ---------- */

  var beh = null;

  function spust(nazev, polozky, smiseny, sada) {
    if (!polozky.length) return;
    beh = { nazev: nazev, polozky: polozky, smiseny: smiseny, sada: sada || null, krok: 0, body: 0, omyly: [] };
    $("prehled").hidden = true;
    $("cviceni").hidden = false;
    $("c-vysledek").hidden = true;
    $("c-krok").hidden = false;
    $("c-nazev").textContent = nazev;
    window.scrollTo(0, 0);
    ukazKrok();
  }

  function pocitadlo() {
    $("c-pocitadlo").textContent = (beh.krok + 1) + " / " + beh.polozky.length + " · správně " + beh.body;
  }

  function ukazKrok() {
    var p = beh.polozky[beh.krok];
    var s = p.sada;
    $("cviceni").setAttribute("data-kapitola", String(s.kap));
    pocitadlo();
    $("c-lista").style.width = (beh.krok / beh.polozky.length * 100) + "%";
    var stitek = $("c-stitek");
    stitek.hidden = !beh.smiseny;
    stitek.textContent = s.nazev + " (" + s.sek + ")";
    var vzor = $("c-vzor");
    vzor.hidden = !p.vzor;
    vzor.textContent = "Ze vzorového testu " + p.vzor;
    $("c-otazka").textContent = s.otazka;
    var pol = $("c-polozka");
    pol.textContent = p.text;
    pol.classList.toggle("pr-polozka--vzor", !!p.vzor);

    var volby = $("c-volby");
    volby.textContent = "";
    s.kat.forEach(function (k, idx) {
      var b = el("button", "pr-volba");
      b.type = "button";
      b.dataset.klic = k[0];
      var span = el("span", "", k[1]);
      span.append(el("em", "", k[2]));
      b.append(el("kbd", "", String(idx + 1)), span);
      b.addEventListener("click", function () { odpovez(k[0]); });
      volby.append(b);
    });
    $("c-zpetna").hidden = true;
    $("c-dalsi").hidden = true;
    vykresliTahak(s);
    beh.odpovezeno = false;
  }

  function vykresliTahak(s) {
    var dl = $("c-tahak-obsah");
    if (dl.dataset.sada === s.id) return;
    dl.dataset.sada = s.id;
    dl.textContent = "";
    s.kat.forEach(function (k) {
      var dt = el("dt", "", k[1] + " ");
      dt.append(el("span", "", "(" + k[2] + ")"));
      dl.append(dt, el("dd", "", k[3] || "—"));
    });
  }

  function nazevKat(sada, klic) {
    for (var i = 0; i < sada.kat.length; i++) if (sada.kat[i][0] === klic) return sada.kat[i][1];
    return klic;
  }

  function odpovez(klic) {
    if (beh.odpovezeno) return;
    beh.odpovezeno = true;
    var p = beh.polozky[beh.krok];
    var ok = klic === p.spr;
    if (ok) {
      beh.body++;
      if (stav.chyby[p.klic]) {
        stav.chyby[p.klic]--;
        if (!stav.chyby[p.klic]) delete stav.chyby[p.klic];
      }
    } else {
      beh.omyly.push({ p: p, tvoje: klic });
      stav.chyby[p.klic] = (stav.chyby[p.klic] || 0) + 1;
    }
    ulozStav();
    Array.prototype.forEach.call($("c-volby").children, function (b) {
      b.disabled = true;
      if (b.dataset.klic === p.spr) b.classList.add("pr-volba--spravne");
      else if (b.dataset.klic === klic) b.classList.add("pr-volba--spatne");
      else b.classList.add("pr-volba--tlumit");
    });
    var z = $("c-zpetna");
    z.className = "pr-zpetna " + (ok ? "pr-zpetna--ok" : "pr-zpetna--chyba");
    z.textContent = "";
    z.append(el("strong", "", ok ? "Správně." : "Špatně. Správně je: " + nazevKat(p.sada, p.spr)));
    z.append(el("span", "", p.proc));
    z.hidden = false;
    $("c-dalsi").hidden = false;
    pocitadlo();
    $("c-tl-dalsi").focus({ preventScroll: true });
  }

  function dalsi() {
    if (!beh || !beh.odpovezeno) return;
    beh.krok++;
    if (beh.krok >= beh.polozky.length) konec();
    else ukazKrok();
  }

  function konec() {
    var b = beh;
    var pct = Math.round(b.body / b.polozky.length * 100);
    $("c-lista").style.width = "100%";
    if (b.sada) {
      var z = stav.sady[b.sada.id] || { nejlepe: 0 };
      stav.sady[b.sada.id] = { posledni: pct, nejlepe: Math.max(z.nejlepe, pct) };
      ulozStav();
    }
    $("c-krok").hidden = true;
    var v = $("c-vysledek");
    v.hidden = false;
    v.textContent = "";
    var cislo = el("div", "pr-vysledek-cislo " + (pct >= 85 ? "pr-vysledek--ok" : pct >= 65 ? "" : "pr-vysledek--slabe"), pct + " %");
    v.append(cislo, el("p", "", b.body + " z " + b.polozky.length + " správně." +
      (b.omyly.length ? " Níže jsou chybně zařazené položky i s vysvětlením." : " Bez chyby.")));

    var akce = el("div", "pr-akce");
    if (b.omyly.length) {
      var b1 = el("button", "pr-tl pr-tl--hlavni", "Zopakovat jen chybné (" + b.omyly.length + ")");
      b1.type = "button";
      var chybne = b.omyly.map(function (o) { return o.p; });
      b1.addEventListener("click", function () { spust(b.nazev + " (chybné)", zamichat(chybne), true); });
      akce.append(b1);
    }
    var b2 = el("button", "pr-tl", "Znovu celé");
    b2.type = "button";
    b2.addEventListener("click", function () { spust(b.nazev, zamichat(b.polozky), b.smiseny, b.sada); });
    var b3 = el("button", "pr-tl", "Zpět na přehled");
    b3.type = "button";
    b3.addEventListener("click", naPrehled);
    akce.append(b2, b3);
    v.append(akce);

    if (b.omyly.length) {
      var ul = el("ul", "pr-chyby");
      b.omyly.forEach(function (o) {
        var li = el("li", o.p.vzor ? "pr-chyba--vzor" : "");
        if (o.p.vzor) li.append(el("span", "pr-vzor-znacka", "Ze vzorového testu " + o.p.vzor));
        li.append(el("div", "pr-text", o.p.text));
        li.append(el("div", "pr-tvoje", "Vaše odpověď: " + nazevKat(o.p.sada, o.tvoje)));
        li.append(el("div", "pr-spr", "Správně: " + nazevKat(o.p.sada, o.p.spr)));
        li.append(el("div", "pr-proc", o.p.proc));
        ul.append(li);
      });
      v.append(ul);
    }
  }

  function naPrehled() {
    beh = null;
    $("cviceni").hidden = true;
    $("prehled").hidden = false;
    vykresliPrehled();
    window.scrollTo(0, 0);
  }

  document.addEventListener("keydown", function (e) {
    if (!beh || $("cviceni").hidden || e.ctrlKey || e.metaKey || e.altKey) return;
    if (!beh.odpovezeno && /^[1-9]$/.test(e.key)) {
      var kat = beh.polozky[beh.krok].sada.kat[+e.key - 1];
      if (kat) { e.preventDefault(); odpovez(kat[0]); }
    } else if (beh.odpovezeno && e.key === "Enter" && !$("c-dalsi").hidden) {
      e.preventDefault();
      dalsi();
    }
  });

  $("c-tl-dalsi").addEventListener("click", dalsi);
  $("c-zpet").addEventListener("click", naPrehled);
  $("tl-slabe").addEventListener("click", function () {
    spust("Moje slabá místa", zamichat(slabePolozky()), true);
  });
  $("tl-vzor").addEventListener("click", function () {
    spust("Položky ze vzorových testů", zamichat(vzorovePolozky()).slice(0, MIX), true);
  });
  $("tl-reset").addEventListener("click", function () {
    if (confirm("Smazat uložené výsledky a seznam chybně zařazených položek?")) {
      stav = { sady: {}, chyby: {} };
      ulozStav();
      vykresliPrehled();
    }
  });

  vykresliPrehled();
})();
