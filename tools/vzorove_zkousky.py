# -*- coding: utf-8 -*-
"""Stránky se simulací zkoušky z oficiálních vzorových testů ISTQB CTFL v4.0.

Volá se z build_site.py až po vygenerování kapitol, protože odkazy na sylabus
míří do plných výkladů (kapitola-N/vyklad.html) a kotvy se berou přímo z nich.

Zdrojová data: oficialni-vzorove-zkousky/data/sada-{a,b,c,d}.json
(české znění CaSQB, otázky i zdůvodnění doslovně).
Výstup:
  web/zkouska.html             rozcestník
  web/zkouska-{a,b,c,d}.html   stránka testu
  web/assets/vzorove/sada-*.js data testu (window.VZOROVA_ZKOUSKA)
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

CISLOVKY = {
    "jedna": "1", "dva": "2", "tři": "3", "čtyři": "4", "pět": "5",
    "šest": "6", "sedm": "7", "osm": "8", "devět": "9",
}

SADY = ["a", "b", "c", "d"]


def e(text: str) -> str:
    return html.escape(text, quote=False)


def mapa_oddilu(web: Path) -> dict[str, tuple[str, str]]:
    """Číslo oddílu sylabu (např. „4.2.1“) → (název, odkaz do plného výkladu).

    Nadpisy ve výkladech jsou psané pro předčítání („Část čtyři tečka dva tečka
    jedna: …“), takže číslo se skládá zpět z číslovek.
    """
    mapa: dict[str, tuple[str, str]] = {}
    for vyklad in sorted(web.glob("kapitola-*/vyklad.html")):
        obsah = vyklad.read_text(encoding="utf-8")
        for kotva, text in re.findall(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', obsah, flags=re.S):
            text = re.sub(r"<[^>]+>", "", html.unescape(text)).strip()
            m = re.match(r"Část (.+?):\s*(.+)", text)
            if not m:
                continue
            slova = m.group(1).split(" tečka ")
            if not all(s.strip() in CISLOVKY for s in slova):
                continue
            cislo = ".".join(CISLOVKY[s.strip()] for s in slova)
            mapa[cislo] = (m.group(2).strip(), f"{vyklad.parent.name}/vyklad.html#{kotva}")
    return mapa


def oddil_pro(lo: str, mapa: dict[str, tuple[str, str]], web: Path) -> dict:
    """Studijní cíl FL-4.2.1 → nejbližší oddíl výkladu (4.2.1, jinak 4.2, jinak kapitola)."""
    cislo = lo.replace("FL-", "")
    casti = cislo.split(".")
    for delka in range(len(casti), 0, -1):
        klic = ".".join(casti[:delka])
        if klic in mapa:
            nazev, href = mapa[klic]
            return {"c": klic, "nazev": nazev, "href": href}
    return {"c": casti[0], "nazev": "", "href": f"kapitola-{casti[0]}/vyklad.html"}


def nacti_sadu(cesta: Path, mapa: dict, web: Path) -> dict:
    data = json.loads(cesta.read_text(encoding="utf-8"))
    otazky = []
    for q in data["otazky"]:
        otazky.append({
            "n": q["n"],
            "lo": q["lo"],
            "k": q["k"],
            "vyber": q.get("vyber", 1),
            "q": q["q"],
            "m": q["moznosti"],
            "ok": [ord(c) - ord("a") for c in q["spravne"]],
            "vys": q.get("vysvetleni") or {},
            "obecne": q.get("vysvetleni_obecne") or "",
            # Redakční upozornění webu (např. chyba v obrázku českého překladu).
            "pozn": q.get("poznamka_webu") or "",
            "pozn_vyh": q.get("poznamka_vyhodnoceni") or "",
            "kap": oddil_pro(q["lo"], mapa, web),
        })
    return {"sada": data["sada"], "verze": data.get("verze_cz", ""), "otazky": otazky}


def poznamka_zdroje(sada: str, verze: str) -> str:
    return (
        f'<p class="zk-zdroj">Otázky a zdůvodnění: <em>Certifikovaný tester, Základní úroveň — '
        f'Vzorová zkouška, sada {sada}</em>, verze {e(verze)}. © International Software Testing '
        f'Qualifications Board (ISTQB®), český překlad CaSQB. Převzato v nezměněném znění; originál '
        f'ke stažení na <a href="https://casqb.org/ke-stazeni" target="_blank" rel="noopener noreferrer">'
        f'casqb.org/ke-stazeni</a>.</p>'
    )


def stranka_testu(sada: str, data: dict, stranka) -> str:
    velke = sada.upper()
    telo = f"""<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava">
  <p class="drobky"><a href="zkouska.html">Zkouška</a> · oficiální vzorový test</p>
  <h1>Vzorová zkouška {velke}</h1>
  <p class="perex">{len(data["otazky"])} otázek z oficiální vzorové zkoušky ISTQB CTFL v4.0,
  sada {velke}, v českém překladu CaSQB. Stejný formát, čas i hranice úspěchu jako u skutečné zkoušky.</p>
</div>

<div id="zkouska" data-sada="{sada}">
  <noscript><p>Simulace zkoušky potřebuje zapnutý JavaScript.</p></noscript>
</div>

{poznamka_zdroje(velke, data["verze"])}

</main>
</div>
<script src="assets/vzorove/sada-{sada}.js"></script>
<script src="assets/zkouska.js"></script>"""

    return stranka(
        titulek=f"Vzorová zkouška {velke} | ISTQB CTFL v4.0",
        popis=f"Oficiální vzorová zkouška ISTQB CTFL v4.0, sada {velke}, česky: 40 otázek, "
        "60 minut, vyhodnocení s oficiálním zdůvodněním a odkazy do sylabu.",
        telo=telo,
        korenova_cesta="",
        aktivni="zkouska",
    )


def stranka_rozcestniku(sady: dict[str, dict], stranka, dalsi: str = "") -> str:
    karty = "".join(
        f"""<li class="karta" id="sada-{s}">
  <p class="karta-cislo">Sada {s.upper()}</p>
  <h3>Vzorová zkouška {s.upper()}</h3>
  <p class="karta-meta">{len(d["otazky"])} otázek · 60 minut · verze {e(d["verze"])}</p>
  <ul><li><a href="zkouska-{s}.html" class="hlavni">Spustit test<span>40 otázek</span></a></li></ul>
</li>"""
        for s, d in sady.items()
    )
    telo = f"""<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava">
  <p class="drobky">Simulace zkoušky</p>
  <h1>Simulace zkoušky</h1>
  <p class="perex">Čtyři oficiální vzorové zkoušky ISTQB CTFL v4.0 v českém překladu CaSQB, beze změn.
  Jsou nejbližší dostupnou náhradou skutečné zkoušky — formátem, obtížností i stylem otázek.
  K nim cvičné zkoušky se stejným rozpisem, náhodná zkouška a otázky navíc.</p>
</div>

<section class="sekce">
  <h2>Oficiální vzorové zkoušky</h2>
  <ul class="mrizka">{karty}</ul>
</section>

{dalsi}
<section class="sekce">
  <h2>Jak to probíhá</h2>
  <ul>
    <li><strong>40 otázek, 60 minut</strong> (75 minut, pokud zkoušku skládáte v jiném než rodném jazyce).
    K úspěchu je potřeba 26 správných odpovědí, tedy 65 %.</li>
    <li>Po odevzdání se ukáže jen počet správných odpovědí a hranice úspěchu.</li>
    <li>Kdo test nesplní, může ho ukončit a jít rovnou na vyhodnocení, nebo si dát ještě
    <strong>10 minut na opravu</strong>. Které odpovědi jsou špatně, se ale nedozví — musí je najít sám.</li>
    <li>Ve vyhodnocení je u každé otázky oficiální zdůvodnění, proč je která možnost správně
    nebo špatně, a odkaz na příslušnou část plného výkladu sylabu.</li>
    <li>Rozpracovaný test si prohlížeč pamatuje, takže omylem zavřená stránka nevadí.</li>
  </ul>
  <p class="poznamka">Zdroj: vzorové zkoušky © ISTQB®, český překlad CaSQB. Originály v PDF
  i s anglickou verzí jsou zdarma na
  <a href="https://casqb.org/ke-stazeni" target="_blank" rel="noopener noreferrer">casqb.org/ke-stazeni</a>.</p>
</section>

</main>
</div>"""

    return stranka(
        titulek="Simulace zkoušky | ISTQB CTFL v4.0",
        popis="Čtyři oficiální vzorové zkoušky ISTQB CTFL v4.0 česky: 40 otázek, 60 minut, "
        "hranice 65 %, vyhodnocení s oficiálním zdůvodněním.",
        telo=telo,
        korenova_cesta="",
        aktivni="zkouska",
    )


def zapis(koren: Path, web: Path, stranka, dalsi: str = "") -> list[str]:
    """Vygeneruje rozcestník, stránky testů a datové soubory. Vrací zapsané cesty."""
    zdroj = koren / "oficialni-vzorove-zkousky" / "data"
    mapa = mapa_oddilu(web)
    sady = {}
    for s in SADY:
        cesta = zdroj / f"sada-{s}.json"
        if cesta.exists():
            sady[s] = nacti_sadu(cesta, mapa, web)

    zapsano = []
    (web / "assets" / "vzorove").mkdir(parents=True, exist_ok=True)
    for s, data in sady.items():
        js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        (web / "assets" / "vzorove" / f"sada-{s}.js").write_text(
            f"window.VZOROVA_ZKOUSKA = {js};\n", encoding="utf-8")
        (web / f"zkouska-{s}.html").write_text(stranka_testu(s, data, stranka), encoding="utf-8")
        zapsano.append(f"zkouska-{s}.html")
    (web / "zkouska.html").write_text(stranka_rozcestniku(sady, stranka, dalsi), encoding="utf-8")
    zapsano.insert(0, "zkouska.html")
    return zapsano
