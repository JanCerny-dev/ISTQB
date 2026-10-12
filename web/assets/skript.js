/* ISTQB CTFL — česká studijní příručka
   Bez závislostí a bez modulů, aby stránka fungovala i po otevření z disku. */

(function () {
  "use strict";

  var KLIC_TEMA = "istqb-tema";
  var KLIC_ODPOVEDI = "istqb-odpovedi";

  function uloz(klic, hodnota) {
    try { localStorage.setItem(klic, hodnota); } catch (e) { /* soukromý režim */ }
  }

  function nacti(klic) {
    try { return localStorage.getItem(klic); } catch (e) { return null; }
  }

  /* --- světlý / tmavý režim ---------------------------------------------- */

  function systemJeTmavy() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  /* Platný režim, ne jen ten uložený: bez vlastní volby rozhoduje systém.
     Bez toho by tlačítko na tmavém systému nabízelo "Tmavý režim" a nic nedělalo. */
  function jeTmavy() {
    var volba = document.documentElement.getAttribute("data-tema");
    if (volba === "tmavy") return true;
    if (volba === "svetly") return false;
    return systemJeTmavy();
  }

  function nastavTema() {
    var tlacitko = document.querySelector("[data-prepinac-tema]");
    if (!tlacitko) return;

    function popis() {
      var tmavy = jeTmavy();
      tlacitko.textContent = tmavy ? "☀ Světlý režim" : "☾ Tmavý režim";
      tlacitko.setAttribute(
        "aria-label",
        tmavy ? "Přepnout na světlý režim" : "Přepnout na tmavý režim"
      );
    }

    popis();

    tlacitko.addEventListener("click", function () {
      var nove = jeTmavy() ? "svetly" : "tmavy";
      document.documentElement.setAttribute("data-tema", nove);
      uloz(KLIC_TEMA, nove);
      popis();
    });

    // Dokud si uživatel režim nezvolil, sleduje se nastavení systému.
    if (window.matchMedia) {
      var dotaz = window.matchMedia("(prefers-color-scheme: dark)");
      var reakce = function () {
        if (!document.documentElement.getAttribute("data-tema")) popis();
      };
      if (dotaz.addEventListener) dotaz.addEventListener("change", reakce);
      else if (dotaz.addListener) dotaz.addListener(reakce);
    }
  }

  /* --- ukazatel postupu čtení -------------------------------------------- */

  function nastavPostup() {
    var pruh = document.querySelector(".postup");
    if (!pruh) return;

    var ceka = false;
    function prekresli() {
      var vyska = document.documentElement.scrollHeight - window.innerHeight;
      var podil = vyska > 0 ? window.scrollY / vyska : 0;
      pruh.style.width = Math.min(100, Math.max(0, podil * 100)).toFixed(2) + "%";
      ceka = false;
    }

    window.addEventListener("scroll", function () {
      if (ceka) return;
      ceka = true;
      window.requestAnimationFrame(prekresli);
    }, { passive: true });

    prekresli();
  }

  /* --- zvýraznění aktivního oddílu v bočním obsahu ------------------------ */

  function nastavStrom() {
    var odkazy = Array.prototype.slice.call(document.querySelectorAll(".strom a[href^='#']"));
    if (!odkazy.length || !("IntersectionObserver" in window)) return;

    var podleId = {};
    var nadpisy = [];
    odkazy.forEach(function (a) {
      var id = decodeURIComponent(a.getAttribute("href").slice(1));
      var cil = document.getElementById(id);
      if (cil) { podleId[id] = a; nadpisy.push(cil); }
    });

    var viditelne = {};

    function obnov() {
      var aktivni = null;
      for (var i = 0; i < nadpisy.length; i++) {
        if (viditelne[nadpisy[i].id]) { aktivni = nadpisy[i]; break; }
      }
      if (!aktivni) {
        for (var j = nadpisy.length - 1; j >= 0; j--) {
          if (nadpisy[j].getBoundingClientRect().top < 120) { aktivni = nadpisy[j]; break; }
        }
      }
      odkazy.forEach(function (a) { a.classList.remove("aktivni"); a.removeAttribute("aria-current"); });
      if (aktivni && podleId[aktivni.id]) {
        podleId[aktivni.id].classList.add("aktivni");
        podleId[aktivni.id].setAttribute("aria-current", "true");
      }
    }

    var pozorovatel = new IntersectionObserver(function (zaznamy) {
      zaznamy.forEach(function (z) { viditelne[z.target.id] = z.isIntersecting; });
      obnov();
    }, { rootMargin: "-100px 0px -70% 0px", threshold: 0 });

    nadpisy.forEach(function (h) { pozorovatel.observe(h); });
    window.addEventListener("scroll", obnov, { passive: true });
    obnov();
  }

  /* --- skrývání odpovědí -------------------------------------------------- */

  function nastavOdpovedi() {
    var text = document.querySelector("[data-odpovedi]");
    var tlacitko = document.querySelector("[data-prepinac-odpovedi]");
    if (!text || !tlacitko) return;

    var dotazy = Array.prototype.slice.call(text.querySelectorAll(".dotaz"));

    /* Ve skrytém režimu se z otázky stává ovládací prvek, aby šla odpověď
       odhalit i klávesnicí. Ve viditelném režimu je to zase jen odstavec. */
    function nastavDotazy(skryte) {
      dotazy.forEach(function (d) {
        if (skryte) {
          d.setAttribute("tabindex", "0");
          d.setAttribute("role", "button");
          d.setAttribute("aria-expanded", d.parentNode.classList.contains("odhalena") ? "true" : "false");
        } else {
          d.removeAttribute("tabindex");
          d.removeAttribute("role");
          d.removeAttribute("aria-expanded");
        }
      });
    }

    function popis() {
      var skryte = text.getAttribute("data-odpovedi") === "skryte";
      tlacitko.setAttribute("aria-pressed", skryte ? "true" : "false");
      tlacitko.textContent = skryte ? "Zobrazit odpovědi" : "Skrýt odpovědi";
      nastavDotazy(skryte);
    }

    if (nacti(KLIC_ODPOVEDI) === "skryte") text.setAttribute("data-odpovedi", "skryte");
    popis();

    tlacitko.addEventListener("click", function () {
      var skryte = text.getAttribute("data-odpovedi") === "skryte";
      var nove = skryte ? "viditelne" : "skryte";
      text.setAttribute("data-odpovedi", nove);
      uloz(KLIC_ODPOVEDI, nove);
      if (nove === "viditelne") {
        Array.prototype.forEach.call(
          text.querySelectorAll(".otazka.odhalena"),
          function (o) { o.classList.remove("odhalena"); }
        );
      }
      popis();
    });

    // Kliknutí na otázku odhalí jen ji — pro procvičování jednu po druhé.
    function prepniOtazku(dotaz) {
      var odhalena = dotaz.parentNode.classList.toggle("odhalena");
      dotaz.setAttribute("aria-expanded", odhalena ? "true" : "false");
    }

    text.addEventListener("click", function (udalost) {
      if (text.getAttribute("data-odpovedi") !== "skryte") return;
      var dotaz = udalost.target.closest(".dotaz");
      if (dotaz) prepniOtazku(dotaz);
    });

    text.addEventListener("keydown", function (udalost) {
      if (udalost.key !== "Enter" && udalost.key !== " ") return;
      if (text.getAttribute("data-odpovedi") !== "skryte") return;
      var dotaz = udalost.target.closest(".dotaz");
      if (!dotaz) return;
      udalost.preventDefault();
      prepniOtazku(dotaz);
    });
  }

  /* --- podmenu kapitol ---------------------------------------------------- */

  /* Podmenu se otevírá najetím myši a při průchodu klávesnicí — obojí řeší CSS.
     Zbývá jen možnost zavřít ho klávesou Escape. */
  function nastavPodmenu() {
    var skupina = document.querySelector("[data-skupina]");
    if (!skupina) return;

    document.addEventListener("keydown", function (udalost) {
      if (udalost.key !== "Escape") return;
      if (!skupina.contains(document.activeElement)) return;
      document.activeElement.blur();
    });
  }

  /* --- výsledky zkoušek na rozcestníku ----------------------------------- */

  /* Souhrn zapisuje assets/zkouska.js po odevzdání testu. */
  function nastavVysledky() {
    var karty = document.querySelectorAll("[data-vysledek]");
    if (!karty.length) return;
    var vse;
    try { vse = JSON.parse(nacti("istqb-zkousky-vysledky")) || {}; } catch (e) { vse = {}; }

    function body(b, z) {
      return b + " / " + z.celkem + " (" + Math.round(b / z.celkem * 100) + " %)";
    }

    [].forEach.call(karty, function (karta) {
      var z = vse[karta.getAttribute("data-vysledek")];
      if (!z || !z.celkem) return;
      var splneno = z.nejlepe >= z.hranice;
      karta.classList.add(splneno ? "karta--splneno" : "karta--nesplneno");

      var blok = document.createElement("div");
      blok.className = "karta-vysledek";
      var stitek = document.createElement("span");
      stitek.className = "karta-vysledek-stitek " + (splneno ? "uspech" : "neuspech");
      stitek.textContent = splneno ? "✓ Splněno" : "Zatím nesplněno";
      var radek = document.createElement("span");
      radek.textContent = "Naposledy " + body(z.posledni, z) + " · nejlépe " + body(z.nejlepe, z) +
        " · pokusů " + z.pokusu;
      blok.append(stitek, radek);
      karta.insertBefore(blok, karta.querySelector("ul"));
    });
  }

  function start() {
    nastavTema();
    nastavVysledky();
    nastavPodmenu();
    nastavPostup();
    nastavStrom();
    nastavOdpovedi();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
