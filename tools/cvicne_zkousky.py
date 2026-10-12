# -*- coding: utf-8 -*-
"""Cvičné zkoušky z AI vygenerovaných otázek, otázky navíc a náhodná zkouška.

Volá se z build_site.py stejně jako vzorove_zkousky.py (odkazy do výkladu se
skládají ze stejné mapy oddílů).

Zdrojová data: cvicne-otazky/data/otazky.json — prověřené otázky ze tří
neoficiálních sad, zpracované pomocí AI (překlad, úprava, kontrola proti CZ sylabu 4.0.1.1).
Na webu se označují jako AI vygenerované otázky, zdroj se u nich neuvádí.
Žádná z nich není otázkou oficiálních vzorových zkoušek.

Cvičné zkoušky se skládají podle rozpisu odvozeného ze vzorových zkoušek A–D:
40 pozic, každá pozice připouští jen určité studijní cíle (LO), v jedné zkoušce
se žádný LO neopakuje. Tím sedí počty otázek po kapitolách (8/6/4/11/9/2)
i po K-úrovních (K1 8, K2 24, K3 8) přesně jako u ostré zkoušky.
Otázky, které se do žádné úplné zkoušky nevejdou, jsou „otázky navíc“.

Výstup:
  web/cvicna-zkouska-N.html          stránka testu (běh řídí assets/zkouska.js)
  web/nahodna-zkouska.html           náhodná zkouška podle rozpisu ze všech otázek
  web/otazky-navic.html              procvičování otázek mimo zkoušky
  web/assets/cvicne/zkouska-N.js     data testu (window.VZOROVA_ZKOUSKA)
  web/assets/cvicne/vse.js           všechny otázky pro náhodnou zkoušku a procvičování
"""

from __future__ import annotations

import html
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import vzorove_zkousky as vz

# Rozpis zkoušky: každá pozice = množina přípustných LO (bez předpony FL-).
# Odvozeno z oficiálních vzorových zkoušek A–D (které LO se na dané pozici střídají).
ROZPIS: list[list[str]] = [
    # kapitola 1: K1 2, K2 6
    ["1.1.1", "1.2.2"], ["1.5.2"],
    ["1.1.2", "1.2.1", "1.2.3"], ["1.3.1"], ["1.4.1"], ["1.4.2", "1.4.3"], ["1.4.4", "1.4.5"], ["1.5.1", "1.5.3"],
    # kapitola 2: K1 2, K2 4
    ["2.1.2"], ["2.1.3"],
    ["2.1.1", "2.1.4", "2.1.5", "2.1.6"], ["2.1.1", "2.1.4", "2.1.5", "2.1.6"],
    ["2.2.1", "2.2.2", "2.2.3", "2.3.1"], ["2.2.1", "2.2.2", "2.2.3", "2.3.1"],
    # kapitola 3: K1 2, K2 2
    ["3.1.1", "3.2.1"], ["3.2.3", "3.2.5"], ["3.1.2", "3.1.3"], ["3.2.2", "3.2.4"],
    # kapitola 4: K2 6, K3 5
    ["4.1.1"], ["4.2.1"], ["4.2.2"], ["4.2.3"], ["4.2.4"],
    ["4.3.1", "4.3.2", "4.3.3"], ["4.3.1", "4.3.2", "4.3.3"],
    ["4.4.1", "4.4.2", "4.4.3"], ["4.4.1", "4.4.2", "4.4.3"],
    ["4.5.1", "4.5.2"], ["4.5.3"],
    # kapitola 5: K1 1, K2 5, K3 3
    ["5.1.2", "5.1.6", "5.2.1", "5.3.1"], ["5.1.1", "5.1.3"], ["5.1.4"], ["5.1.5"], ["5.1.7"],
    ["5.2.2", "5.2.3", "5.2.4"], ["5.3.2", "5.3.3"], ["5.4.1"], ["5.5.1"],
    # kapitola 6: K1 1, K2 1
    ["6.1.1"], ["6.2.1"],
]
assert len(ROZPIS) == 40

OZNACENI = "AI vygenerovaná otázka"
SEMINKO = 4001  # pevné, aby se sady při každém sestavení nepřeskládaly
PISMENA = "abcdef"
# Text, který se odvolává na písmeno možnosti — takové otázce nelze míchat pořadí.
ODKAZ_NA_PISMENO = re.compile(r"(možnost[iíe]?\s+[a-fA-F]\b|\b[a-fA-F]\)|\(\s*[a-fA-F]\s*\))")


def e(text: str) -> str:
    return html.escape(text, quote=False)


def lo_cislo(lo: str) -> str:
    return lo.replace("FL-", "")


def zarazitelna(q: dict) -> bool:
    """Může otázka stát na pozici zkoušky? K3 jen tehdy, když opravdu jde o aplikaci."""
    return q["k"] != "K3" or q.get("k3_fit", False)


def nacti(koren: Path) -> dict:
    cesta = koren / "cvicne-otazky" / "data" / "otazky.json"
    if not cesta.exists():
        return {}
    data = json.loads(cesta.read_text(encoding="utf-8"))
    for q in data["otazky"]:
        n = len(q["moznosti"])
        assert 2 <= n <= len(PISMENA), q["id"]
        assert q["spravne"] and all(p in PISMENA[:n] for p in q["spravne"]), q["id"]
        assert lo_cislo(q["lo"]) in {lo for poz in ROZPIS for lo in poz}, (q["id"], q["lo"])
        assert q["stav"] in ("ok", "varianta"), q["id"]
    return data


def sestav_sady(otazky: list[dict]) -> tuple[list[list[dict]], list[dict]]:
    """Rozdělí otázky do co nejvíce úplných zkoušek podle ROZPISU; zbytek vrátí jako navíc."""
    rnd = random.Random(SEMINKO)
    podle_lo: dict[str, list[dict]] = defaultdict(list)
    for q in otazky:
        if q["stav"] == "ok" and zarazitelna(q):
            podle_lo[lo_cislo(q["lo"])].append(q)
    for seznam in podle_lo.values():
        rnd.shuffle(seznam)

    sady: list[list[dict]] = []
    while True:
        pouzite_lo: set[str] = set()
        vybrane: list[tuple[int, dict]] = []
        # Nejdřív pozice s nejmenší zásobou, aby je nevyčerpaly obecnější pozice.
        poradi = sorted(range(len(ROZPIS)),
                        key=lambda i: sum(len(podle_lo[lo]) for lo in ROZPIS[i]))
        uspech = True
        for i in poradi:
            kandidati = [lo for lo in ROZPIS[i] if lo not in pouzite_lo and podle_lo[lo]]
            if not kandidati:
                uspech = False
                break
            # LO s největší zbývající zásobou; při shodě náhodně (pestrost mezi sadami).
            rnd.shuffle(kandidati)
            lo = max(kandidati, key=lambda x: len(podle_lo[x]))
            pouzite_lo.add(lo)
            vybrane.append((i, podle_lo[lo].pop()))
        if not uspech:
            for _, q in vybrane:  # neúplnou sadu vrátit zpět
                podle_lo[lo_cislo(q["lo"])].append(q)
            break
        vybrane.sort(key=lambda x: (x[0], x[1]["lo"]))
        sady.append([q for _, q in vybrane])

    v_sadach = {q["id"] for s in sady for q in s}
    navic = [q for q in otazky if q["id"] not in v_sadach]
    return sady, navic


def zamichej(q: dict, cil: int) -> dict:
    """Vrátí kopii otázky s možnostmi přeskládanými tak, aby správná byla na pozici `cil`.

    Míchá se jen u otázek s jednou správnou odpovědí, kde na pořadí nezáleží.
    """
    q = dict(q)
    n = len(q["moznosti"])
    texty = " ".join([q["q"], q.get("vysvetleni_obecne", ""), *q["moznosti"],
                      *q.get("vysvetleni", {}).values()])
    if q.get("keep_order") or len(q["spravne"]) != 1 or ODKAZ_NA_PISMENO.search(re.sub(r"<[^>]+>", " ", texty)):
        return q
    puvodni = PISMENA.index(q["spravne"][0])
    cil = cil % n
    ostatni = [i for i in range(n) if i != puvodni]
    random.Random(f"{SEMINKO}-{q['id']}").shuffle(ostatni)
    poradi = ostatni[:cil] + [puvodni] + ostatni[cil:]
    vys = q.get("vysvetleni") or {}
    q["moznosti"] = [q["moznosti"][i] for i in poradi]
    q["vysvetleni"] = {PISMENA[j]: vys[PISMENA[i]] for j, i in enumerate(poradi) if PISMENA[i] in vys}
    q["spravne"] = [PISMENA[cil]]
    return q


def pro_web(q: dict, mapa: dict, web: Path, n: int | None = None) -> dict:
    """Otázka ve tvaru, který čte assets/zkouska.js (stejný jako u vzorových zkoušek)."""
    return {
        "id": q["id"],
        "n": n,
        "lo": q["lo"],
        "k": q["k"],
        "k3": zarazitelna(q),
        "vyber": len(q["spravne"]),
        "q": q["q"],
        "m": q["moznosti"],
        "ok": [PISMENA.index(p) for p in q["spravne"]],
        "vys": q.get("vysvetleni") or {},
        "obecne": q.get("vysvetleni_obecne") or "",
        "pozn": "",
        "pozn_vyh": "",
        "zdroj": OZNACENI,
        "navic": q.get("navic", False),
        # Odvozeno z oficiální otázky (jiné hodnoty) — jen k procvičování, do zkoušek se nelosuje.
        "varianta": q["stav"] == "varianta",
        "kap": vz.oddil_pro(q["lo"], mapa, web),
    }


def pis_js(cesta: Path, promenna: str, data) -> None:
    cesta.parent.mkdir(parents=True, exist_ok=True)
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    cesta.write_text(f"/* Vygenerováno z cvicne-otazky/data/otazky.json, neupravovat ručně. */\n"
                     f"window.{promenna} = {js};\n", encoding="utf-8")


POZNAMKA_ZDROJE = (
    '<p class="zk-zdroj"><strong>AI vygenerované otázky.</strong> Nejde o otázky z oficiálních vzorových '
    'zkoušek ISTQB®. Otázky jsou zkontrolované proti CZ sylabu CTFL 4.0.1.1, terminologie odpovídá sylabu '
    'a slovníku CaSQB. Přesto mohou obsahovat nepřesnosti — ke zkoušce vždy platí znění oficiálního sylabu.</p>'
)


def stranka_testu(cislo: int, pocet_sad: int, stranka) -> str:
    telo = f"""<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava">
  <p class="drobky"><a href="zkouska.html">Zkouška</a> · cvičná zkouška</p>
  <h1>Cvičná zkouška {cislo}</h1>
  <p class="perex">40 otázek sestavených podle rozpisu ostré zkoušky ISTQB CTFL v4.0: stejné počty
  otázek z jednotlivých kapitol i stejné K-úrovně. AI vygenerované otázky, žádná není z oficiálních vzorových zkoušek.</p>
</div>

<div id="zkouska" data-sada="cvicna-{cislo}">
  <noscript><p>Simulace zkoušky potřebuje zapnutý JavaScript.</p></noscript>
</div>

{POZNAMKA_ZDROJE}

</main>
</div>
<script src="assets/cvicne/zkouska-{cislo}.js"></script>
<script src="assets/zkouska.js"></script>"""
    return stranka(
        titulek=f"Cvičná zkouška {cislo} | ISTQB CTFL v4.0",
        popis=f"Cvičná zkouška ISTQB CTFL v4.0 č. {cislo} z {pocet_sad}: 40 otázek česky podle rozpisu "
        "ostré zkoušky, 60 minut, vyhodnocení se zdůvodněním a odkazy do sylabu.",
        telo=telo,
        korenova_cesta="",
        aktivni="zkouska",
    )


def stranka_nahodne(stranka) -> str:
    telo = f"""<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava">
  <p class="drobky"><a href="zkouska.html">Zkouška</a> · náhodná zkouška</p>
  <h1>Náhodná zkouška</h1>
  <p class="perex">Při každém spuštění se vylosuje nových 40 otázek ze všech dostupných otázek,
  vždy podle rozpisu ostré zkoušky: 8/6/4/11/9/2 otázek z kapitol 1–6, K1/K2/K3 v poměru 8/24/8
  a každý studijní cíl nejvýš jednou.</p>
</div>

<div id="zkouska" data-sada="nahodna">
  <noscript><p>Simulace zkoušky potřebuje zapnutý JavaScript.</p></noscript>
</div>

<p class="zk-zdroj">Losuje se z AI vygenerovaných otázek a volitelně i z oficiálních vzorových zkoušek A–D
(© ISTQB®, český překlad CaSQB, převzato beze změn). Ve vyhodnocení je u každé otázky uvedeno, ze které skupiny pochází.</p>

</main>
</div>
<script src="assets/cvicne/vse.js"></script>
<script src="assets/zkouska.js"></script>"""
    return stranka(
        titulek="Náhodná zkouška | ISTQB CTFL v4.0",
        popis="Náhodně losovaná zkouška ISTQB CTFL v4.0 česky: 40 otázek podle rozpisu ostré zkoušky "
        "ze všech dostupných otázek, 60 minut, vyhodnocení se zdůvodněním.",
        telo=telo,
        korenova_cesta="",
        aktivni="zkouska",
    )


def stranka_navic(pocty: Counter, stranka) -> str:
    telo = f"""<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava">
  <p class="drobky"><a href="zkouska.html">Zkouška</a> · otázky navíc</p>
  <h1>Otázky navíc</h1>
  <p class="perex">{sum(pocty.values())} AI vygenerovaných otázek, které se nevešly do žádné cvičné zkoušky. Procvičujte je
  po kapitolách bez časového limitu, vyhodnocení a zdůvodnění uvidíte hned po každé odpovědi.</p>
</div>

<div id="procvicovani">
  <noscript><p>Procvičování potřebuje zapnutý JavaScript.</p></noscript>
</div>

{POZNAMKA_ZDROJE}

</main>
</div>
<script src="assets/cvicne/vse.js"></script>
<script src="assets/procvicovani.js"></script>"""
    return stranka(
        titulek="Otázky navíc | ISTQB CTFL v4.0",
        popis="Cvičné otázky k ISTQB CTFL v4.0 česky po kapitolách: okamžité vyhodnocení, "
        "zdůvodnění a odkaz do sylabu.",
        telo=telo,
        korenova_cesta="",
        aktivni="zkouska",
    )


def karty_rozcestniku(pocet_sad: int, pocet_navic: int, pocet_vse: int) -> str:
    """Oddíly pro rozcestník zkouska.html (vkládá je vzorove_zkousky.stranka_rozcestniku)."""
    karty = "".join(
        f"""<li class="karta" id="cvicna-{i}">
  <p class="karta-cislo">Cvičná {i}</p>
  <h3>Cvičná zkouška {i}</h3>
  <p class="karta-meta">40 otázek · 60 minut · rozpis jako ostrá zkouška</p>
  <ul><li><a href="cvicna-zkouska-{i}.html" class="hlavni">Spustit test<span>40 otázek</span></a></li></ul>
</li>"""
        for i in range(1, pocet_sad + 1)
    )
    return f"""<section class="sekce" id="cvicne">
  <h2>Cvičné zkoušky — AI vygenerované otázky</h2>
  <p>{pocet_sad} {"další zkoušky" if 2 <= pocet_sad <= 4 else "další zkouška" if pocet_sad == 1 else "dalších zkoušek"} z otázek, které <strong>nejsou</strong> z oficiálních vzorových testů.
  Jsou to AI vygenerované otázky, zkontrolované proti CZ sylabu a s jeho terminologií.
  Každá zkouška má stejný rozpis jako ostrá: počty otázek z kapitol, K-úrovně i povinné studijní cíle.</p>
  <ul class="mrizka">{karty}</ul>
</section>

<section class="sekce" id="nahodna">
  <h2>Náhodná zkouška a otázky navíc — AI vygenerované otázky</h2>
  <ul class="mrizka">
<li class="karta">
  <p class="karta-cislo">Pokaždé jiná</p>
  <h3>Náhodná zkouška</h3>
  <p class="karta-meta">40 otázek losovaných z {pocet_vse} (AI vygenerované + oficiální) podle rozpisu ostré zkoušky</p>
  <ul><li><a href="nahodna-zkouska.html" class="hlavni">Spustit test<span>40 otázek</span></a></li></ul>
</li>
<li class="karta">
  <p class="karta-cislo">Bez limitu</p>
  <h3>Otázky navíc</h3>
  <p class="karta-meta">{pocet_navic} AI vygenerovaných otázek mimo zkoušky, procvičování po kapitolách</p>
  <ul><li><a href="otazky-navic.html" class="hlavni">Procvičovat<span>okamžité vyhodnocení</span></a></li></ul>
</li>
  </ul>
</section>
"""


def zapis(koren: Path, web: Path, stranka) -> tuple[list[str], str]:
    """Zapíše stránky a data. Vrací (zapsané cesty, HTML oddíly pro rozcestník)."""
    data = nacti(koren)
    if not data:
        return [], ""
    mapa = vz.mapa_oddilu(web)
    otazky = data["otazky"]
    sady, navic = sestav_sady(otazky)

    zapsano: list[str] = []
    cvicne = web / "assets" / "cvicne"
    for stary in list(cvicne.glob("zkouska-*.js")) + list(web.glob("cvicna-zkouska-*.html")):
        stary.unlink()

    # Pozice správné odpovědi v sadě rozprostřít rovnoměrně (a, b, c, d dokola od náhodného startu).
    for c, sada in enumerate(sady, start=1):
        start = random.Random(f"{SEMINKO}-sada-{c}").randrange(4)
        polozky = [pro_web(zamichej(q, start + i), mapa, web, i + 1) for i, q in enumerate(sada)]
        pis_js(cvicne / f"zkouska-{c}.js", "VZOROVA_ZKOUSKA",
               {"sada": f"cvicna-{c}", "oficialni": False, "otazky": polozky})
        (web / f"cvicna-zkouska-{c}.html").write_text(stranka_testu(c, len(sady), stranka), encoding="utf-8")
        zapsano.append(f"cvicna-zkouska-{c}.html")

    # Pool pro náhodnou zkoušku a procvičování: cvičné otázky + oficiální A–D (jen pro náhodnou zkoušku).
    v_sadach = {q["id"] for s in sady for q in s}
    vse = []
    for i, q in enumerate(otazky):
        q = dict(q, navic=q["id"] not in v_sadach)
        vse.append(pro_web(zamichej(q, i), mapa, web))
    oficialni = []
    for s in vz.SADY:
        cesta = koren / "oficialni-vzorove-zkousky" / "data" / f"sada-{s}.json"
        if not cesta.exists():
            continue
        for q in vz.nacti_sadu(cesta, mapa, web)["otazky"]:
            q = dict(q, id=f"OF-{s.upper()}{q['n']}", k3=True, navic=False, varianta=False, oficialni=True,
                     zdroj=f"oficiální vzorová zkouška {s.upper()}, otázka {q['n']} (© ISTQB®, překlad CaSQB)")
            oficialni.append(q)
    pis_js(cvicne / "vse.js", "CVICNE_OTAZKY", {
        "rozpis": [[f"FL-{lo}" for lo in poz] for poz in ROZPIS],
        "otazky": vse + oficialni,
        "kapitoly": {str(k): n for k, n in KAPITOLY.items()},
    })
    (web / "nahodna-zkouska.html").write_text(stranka_nahodne(stranka), encoding="utf-8")
    pocty_navic = Counter(q["lo"][3] for q in navic)
    (web / "otazky-navic.html").write_text(stranka_navic(pocty_navic, stranka), encoding="utf-8")
    zapsano += ["nahodna-zkouska.html", "otazky-navic.html", "assets/cvicne/vse.js"]

    pocet_vse = sum(1 for q in vse if q["k3"] and not q["varianta"]) + len(oficialni)
    return zapsano, karty_rozcestniku(len(sady), len(navic), pocet_vse)


KAPITOLY = {
    1: "Základy testování",
    2: "Testování v průběhu životního cyklu",
    3: "Statické testování",
    4: "Testovací analýza a návrh testů",
    5: "Management testování",
    6: "Testovací nástroje",
}


def statistika(koren: Path) -> str:
    """Souhrn pro kontrolu: kolik sad, rozpis po kapitolách a K, rozložení správných písmen."""
    data = nacti(koren)
    sady, navic = sestav_sady(data["otazky"])
    radky = [f"sad: {len(sady)}, navíc: {len(navic)}"]
    for c, s in enumerate(sady, 1):
        start = random.Random(f"{SEMINKO}-sada-{c}").randrange(4)
        pis = Counter(zamichej(q, start + i)["spravne"][0] for i, q in enumerate(s) if len(q["spravne"]) == 1)
        radky.append(f"  sada {c}: kap {dict(sorted(Counter(q['lo'][3] for q in s).items()))} "
                     f"K {dict(sorted(Counter(q['k'] for q in s).items()))} "
                     f"zdroje {dict(Counter(q['zdroj'] for q in s))} písmena {dict(sorted(pis.items()))}")
    return "\n".join(radky)
