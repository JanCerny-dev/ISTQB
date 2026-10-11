# -*- coding: utf-8 -*-
"""Stránka s přiřazovacími cvičeními podle kapitol sylabu.

Volá se z build_site.py. Zdrojová data jsou ručně psaná v
tools/prirazovani/sady.json; každá sada má kategorie a položky
[text, klíč kategorie, zdůvodnění, (kód otázky vzorového testu, např. „D4“)].
Položky s kódem se na stránce zvýrazní jako převzaté ze vzorových zkoušek.

Výstup:
  web/prirazovani.html             kostra stránky (navigace, patička)
  web/assets/prirazovani-data.js   data cvičení (window.PRIRAZOVANI)
Logika cvičení je ve statickém souboru web/assets/prirazovani.js.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ZDROJ = Path(__file__).resolve().parent / "prirazovani" / "sady.json"
KOD_VZORU = re.compile(r"^[A-D]([1-9]|[1-3]\d|40)$")


def nacti(kapitoly: dict[int, str]) -> list[dict]:
    """Načte a zkontroluje sady. Chyba v datech zastaví sestavení webu."""
    sady = json.loads(ZDROJ.read_text(encoding="utf-8"))
    chyby: list[str] = []
    videne: set[str] = set()
    for s in sady:
        sid = s.get("id", "?")
        if sid in videne:
            chyby.append(f"{sid}: duplicitní id sady")
        videne.add(sid)
        for pole in ("sek", "nazev", "zdroj", "otazka", "kat", "pol"):
            if not s.get(pole):
                chyby.append(f"{sid}: chybí pole „{pole}“")
        kapitola = int(s["sek"][0]) if s.get("sek", "")[:1].isdigit() else 0
        if kapitola not in kapitoly:
            chyby.append(f"{sid}: sekce „{s.get('sek')}“ nepatří do žádné kapitoly")
        s["kap"] = kapitola
        klice = [k[0] for k in s.get("kat", [])]
        if len(klice) != len(set(klice)):
            chyby.append(f"{sid}: duplicitní klíč kategorie")
        if len(klice) > 9:
            chyby.append(f"{sid}: víc než 9 kategorií (nejdou zvolit klávesou)")
        for i, p in enumerate(s.get("pol", [])):
            if len(p) not in (3, 4):
                chyby.append(f"{sid}#{i}: položka má mít 3 nebo 4 prvky")
                continue
            if p[1] not in klice:
                chyby.append(f"{sid}#{i}: neznámá kategorie „{p[1]}“")
            if len(p) == 4 and not KOD_VZORU.match(p[3]):
                chyby.append(f"{sid}#{i}: neplatný kód vzorové otázky „{p[3]}“")
    if chyby:
        raise SystemExit("Chyby v tools/prirazovani/sady.json:\n  " + "\n  ".join(chyby))
    return sady


def telo_stranky(sady: list[dict]) -> str:
    polozek = sum(len(s["pol"]) for s in sady)
    ze_vzoru = sum(1 for s in sady for p in s["pol"] if len(p) == 4)
    return f"""<div class="stranka uvod">
<main id="text">

<section id="prehled">
  <div class="uvod-hlava">
    <p class="drobky">Procvičování</p>
    <h1>Přiřazovací cvičení</h1>
    <p class="perex">Ve zkoušce se často objevují otázky typu „přiřaďte 1–4 k A–D“. Tady dostanete
    vždy jednu položku a zařadíte ji do správné kategorie. Hned uvidíte, jestli jste trefili,
    a proč. Na volby jde klikat, nebo mačkat čísla <kbd>1</kbd>–<kbd>9</kbd>; <kbd>Enter</kbd> posune dál.</p>
    <p class="pr-souhrn">{len(sady)} sad · {polozek} položek · <span class="pr-vzor-znacka">vzorový test</span>
    {ze_vzoru} položek vychází přímo z otázek oficiálních vzorových zkoušek A–D a jsou zvýrazněné.
    Ostatní jsou rozšíření podle textu sylabu.</p>
    <div class="pr-akce">
      <button type="button" class="pr-tl pr-tl--hlavni" id="tl-vzor">Jen položky ze vzorových testů</button>
      <button type="button" class="pr-tl" id="tl-slabe" hidden>Procvičit položky, ve kterých chybuju</button>
      <button type="button" class="pr-tl" id="tl-reset">Smazat uložené výsledky</button>
    </div>
    <p class="pr-napoveda">Výsledky se ukládají jen ve vašem prohlížeči.</p>
  </div>
  <div id="kapitoly-prirazovani"></div>
</section>

<section id="cviceni" class="pr-cviceni" hidden>
  <div class="pr-horni">
    <h1 id="c-nazev"></h1>
    <span class="pr-pocitadlo" id="c-pocitadlo"></span>
    <button type="button" class="pr-tl" id="c-zpet">← Přehled</button>
  </div>
  <div class="pr-lista"><span id="c-lista"></span></div>
  <div id="c-krok">
    <p class="pr-stitky"><span class="pr-stitek" id="c-stitek" hidden></span><span class="pr-vzor-znacka" id="c-vzor" hidden></span></p>
    <p class="pr-otazka" id="c-otazka"></p>
    <div class="pr-polozka" id="c-polozka"></div>
    <div class="pr-volby" id="c-volby"></div>
    <div id="c-zpetna" hidden></div>
    <div class="pr-dalsi" id="c-dalsi" hidden>
      <button type="button" class="pr-tl pr-tl--hlavni" id="c-tl-dalsi">Další →</button>
      <span class="pr-napoveda">nebo Enter</span>
    </div>
  </div>
  <div id="c-vysledek" hidden></div>
  <details class="pr-tahak">
    <summary>Tahák: co která kategorie znamená</summary>
    <dl id="c-tahak-obsah"></dl>
  </details>
</section>

<noscript><p class="poznamka">Cvičení potřebuje zapnutý JavaScript.</p></noscript>

</main>
</div>
<script src="assets/prirazovani-data.js"></script>
<script src="assets/prirazovani.js"></script>"""


def zapis(web: Path, stranka, kapitoly: dict[int, str]) -> list[str]:
    sady = nacti(kapitoly)
    data = {
        "kapitoly": {str(k): v for k, v in sorted(kapitoly.items())},
        "sady": sady,
    }
    (web / "assets" / "prirazovani-data.js").write_text(
        "/* Vygenerováno z tools/prirazovani/sady.json, neupravovat ručně. */\n"
        "window.PRIRAZOVANI = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (web / "prirazovani.html").write_text(
        stranka(
            titulek="Přiřazovací cvičení | ISTQB CTFL v4.0",
            popis="Přiřazovací cvičení k ISTQB CTFL v4.0 podle kapitol: ke každé položce vyberte "
            "správnou kategorii (činnost, úroveň, roli, nástroj, riziko…). Položky ze vzorových "
            "zkoušek jsou zvýrazněné.",
            telo=telo_stranky(sady),
            korenova_cesta="",
            aktivni="prirazovani",
        ),
        encoding="utf-8",
    )
    return ["prirazovani.html", "assets/prirazovani-data.js"]
