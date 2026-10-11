# -*- coding: utf-8 -*-
"""Generátor statického webu ze studijních materiálů ISTQB CTFL.

Spuštění (ze složky projektu):

    python tools/build_site.py

Výstup je celý ve složce web/. Ta je samostatná a jde ji nahrát na GitHub
Pages nebo otevřít dvojklikem z disku — všechny cesty jsou relativní,
nic se nenačítá přes fetch a nepoužívají se JS moduly.
"""

from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import markdown_min
import prirazovani
import vzorove_zkousky
from model import (
    KAPITOLY,
    KAPITOLY_KRATCE,
    MINUTY_VYUKY,
    VARIANTA_NAZEV,
    VARIANTA_POPIS,
    VSUVKA_POPIS,
    Dokument,
    Legenda,
    Nadpis,
    Odstavec,
    Otazka,
    Vsuvka,
    nacti_vse,
    pocet_slov,
)

KOREN = Path(__file__).resolve().parent.parent
WEB = KOREN / "web"

NAZEV_WEBU = "ISTQB CTFL v4.0"
PODNAZEV_WEBU = "česká studijní příručka"

PORADI_VARIANT = ["vyklad", "zkracena", "otazky"]
SOUBOR_VARIANTY = {"vyklad": "vyklad.html", "zkracena": "zkracena.html", "otazky": "otazky.html"}

SLOV_ZA_MINUTU_CTENI = 170
SLOV_ZA_MINUTU_POSLECHU = 145


def e(text: str) -> str:
    return html.escape(text, quote=False)


def minuty(slov: int, tempo: int) -> int:
    return max(1, round(slov / tempo))


def slova_dokumentu(d: Dokument) -> int:
    celkem = pocet_slov(d.nadpis) + pocet_slov(d.podtitul)
    for b in d.bloky:
        if isinstance(b, Nadpis):
            celkem += pocet_slov(b.text)
        elif isinstance(b, Odstavec):
            celkem += pocet_slov(b.text)
        elif isinstance(b, Legenda):
            celkem += pocet_slov(b.text)
        elif isinstance(b, Vsuvka):
            celkem += sum(pocet_slov(o) for o in b.odstavce)
        elif isinstance(b, Otazka):
            celkem += pocet_slov(b.text) + sum(pocet_slov(o) for o in b.odpovedi)
    return celkem


# --- společné části stránky -------------------------------------------------


def hlavicka(
    korenova_cesta: str,
    aktivni: str,
    *,
    varianta_podmenu: str = "vyklad",
    aktivni_kapitola: int | None = None,
) -> str:
    """Hlavička s navigací.

    Podmenu kapitol míří na tu variantu, ve které uživatel právě je — kdo čte
    zkrácené verze, přeskočí na zkrácenou verzi další kapitoly, ne na výklad.
    """

    def odkaz(cil: str, popisek: str, klic: str, trida: str = "") -> str:
        aktualni = ' aria-current="page"' if klic == aktivni else ""
        atribut_tridy = f' class="{trida}"' if trida else ""
        return f'<a href="{korenova_cesta}{cil}"{atribut_tridy}{aktualni}>{popisek}</a>'

    polozky_podmenu = "".join(
        f'<li><a href="{korenova_cesta}kapitola-{k}/{SOUBOR_VARIANTY[varianta_podmenu]}"'
        f'{" aria-current=\"page\"" if k == aktivni_kapitola else ""}>'
        f"<b>{k}</b> {e(KAPITOLY_KRATCE[k])}</a></li>"
        for k in sorted(KAPITOLY)
    )

    return f"""<a class="preskocit" href="#text">Přeskočit na text</a>
<div class="postup" aria-hidden="true"></div>
<header class="hlavicka">
  <div class="hlavicka-vnitrek">
    <a class="znacka" href="{korenova_cesta}index.html">{NAZEV_WEBU} <span>{PODNAZEV_WEBU}</span></a>
    <nav class="navigace" aria-label="Hlavní navigace">
      {odkaz('index.html', 'Úvod', 'uvod')}
      <span class="skupina" data-skupina>
        {odkaz('kapitoly.html', 'Kapitoly', 'kapitoly', 'zvyraznit')}
        <ul class="podmenu" id="podmenu-kapitoly" aria-label="Seznam kapitol">{polozky_podmenu}</ul>
      </span>
      {odkaz('prirazovani.html', 'Přiřazování', 'prirazovani')}
      {odkaz('zdroje.html', 'Zdroje', 'zdroje')}
      {odkaz('zkouska.html', 'Zkouška', 'zkouska')}
      <button type="button" class="prepinac-tema" data-prepinac-tema>Tmavý režim</button>
    </nav>
  </div>
</header>"""


def paticka(korenova_cesta: str) -> str:
    return f"""<footer class="paticka">
  <div class="paticka-vnitrek">
    <p><strong>Neoficiální studijní materiál.</strong> Tento web není produktem ani publikací ISTQB® ani CaSQB.
    ISTQB® je registrovaná ochranná známka International Software Testing Qualifications Board.
    Texty jsou vlastním zpracováním autora vytvořeným při přípravě na zkoušku; oficiální sylabus,
    slovník a vzorové zkoušky si stáhněte přímo u certifikační autority.</p>
    <p>Ke zkoušce vždy platí znění oficiálního sylabu CTFL v4.0. Doplněné informace na tomto webu
    slouží k porozumění a k praxi, nikoli jako zdroj správných odpovědí u zkoušky.</p>
    <ul>
      <li><a href="https://casqb.org/ke-stazeni" target="_blank" rel="noopener noreferrer">CaSQB — dokumenty ke stažení</a></li>
      <li><a href="https://casqb.org/certifikace/zkousky" target="_blank" rel="noopener noreferrer">CaSQB — registrace ke zkoušce</a></li>
      <li><a href="https://istqb.org/certifications/certified-tester-foundation-level-ctfl-v4-0/" target="_blank" rel="noopener noreferrer">ISTQB — CTFL v4.0</a></li>
      <li><a href="https://glossary.istqb.org" target="_blank" rel="noopener noreferrer">Slovník ISTQB</a></li>
      <li><a href="{korenova_cesta}zdroje.html">Zdroje a citace</a></li>
    </ul>
  </div>
</footer>"""


def stranka(
    *,
    titulek: str,
    popis: str,
    telo: str,
    korenova_cesta: str,
    aktivni: str,
    kapitola: int | None = None,
    varianta_podmenu: str = "vyklad",
) -> str:
    atribut_kapitoly = f' data-kapitola="{kapitola}"' if kapitola else ""
    return f"""<!doctype html>
<html lang="cs" data-tema="">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulek)}</title>
<meta name="description" content="{html.escape(popis, quote=True)}">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="{korenova_cesta}assets/styl.css">
<script>
/* Nastaví uložený režim ještě před vykreslením, aby stránka neproblikla. */
(function(){{try{{var t=localStorage.getItem('istqb-tema');if(t){{document.documentElement.setAttribute('data-tema',t);}}}}catch(e){{}}}})();
</script>
</head>
<body{atribut_kapitoly}>
{hlavicka(korenova_cesta, aktivni, varianta_podmenu=varianta_podmenu, aktivni_kapitola=kapitola)}
{telo}
{paticka(korenova_cesta)}
<script src="{korenova_cesta}assets/skript.js"></script>
</body>
</html>
"""


# --- vykreslení obsahu kapitoly ---------------------------------------------


def vykresli_bloky(d: Dokument) -> str:
    kusy: list[str] = []
    i = 0
    bloky = d.bloky
    n = len(bloky)

    while i < n:
        b = bloky[i]

        if isinstance(b, Nadpis):
            kusy.append(
                f'<h2 id="{b.kotva}">{e(b.text)}'
                f'<a class="kotva" href="#{b.kotva}" aria-label="Odkaz na tento oddíl"></a></h2>'
            )
            i += 1

        elif isinstance(b, Odstavec):
            kusy.append(f"<p>{e(b.text)}</p>")
            i += 1

        elif isinstance(b, Vsuvka):
            stitek = VSUVKA_POPIS[b.druh]
            odstavce = "".join(f"<p>{e(o)}</p>" for o in b.odstavce)
            kusy.append(
                f'<aside class="vsuvka vsuvka--{b.druh}" data-stitek="{stitek}" '
                f'aria-label="{stitek}">{odstavce}</aside>'
            )
            i += 1

        elif isinstance(b, Legenda):
            polozky: list[str] = []
            while i < n and isinstance(bloky[i], Legenda):
                l = bloky[i]
                polozky.append(
                    f'<li class="{l.uroven.lower()}" data-uroven="{l.uroven}">{e(l.text)}</li>'
                )
                i += 1
            kusy.append(
                '<ul class="legenda" aria-label="Význam barev otázek">' + "".join(polozky) + "</ul>"
            )

        elif isinstance(b, Otazka):
            odpovedi = "".join(f'<p class="odpoved">{e(o)}</p>' for o in b.odpovedi)
            kusy.append(
                f'<div class="otazka {b.uroven.lower()}" id="{b.kotva}">'
                f'<p class="dotaz" data-uroven="{b.uroven}">{e(b.text)}</p>'
                f"{odpovedi}</div>"
            )
            i += 1

        else:  # pragma: no cover — model nemá jiné bloky
            i += 1

    return "\n".join(kusy)


def prepinac_variant(kapitola: int, aktivni: str) -> str:
    odkazy = []
    for v in PORADI_VARIANT:
        aktualni = ' aria-current="page"' if v == aktivni else ""
        # Bez title: dlouhý popis v přístupnostním stromu přebíjel text odkazu,
        # takže se přepínač ohlašoval celou větou místo názvu varianty.
        odkazy.append(f'<a href="{SOUBOR_VARIANTY[v]}"{aktualni}>{VARIANTA_NAZEV[v]}</a>')
    return (
        f'<nav class="varianty" aria-label="Varianta zpracování kapitoly {kapitola}">'
        + "".join(odkazy)
        + "</nav>"
    )


def strom_oddilu(d: Dokument) -> str:
    if not d.oddily:
        return ""
    polozky = "".join(
        f'<li><a href="#{o.kotva}">{e(o.text)}</a></li>' for o in d.oddily
    )
    return (
        '<aside class="strom" aria-label="Obsah kapitoly">'
        "<h2>V této kapitole</h2>"
        f"<ol>{polozky}</ol>"
        "</aside>"
    )


def sousedni_kapitoly(kapitola: int, varianta: str) -> str:
    odkazy = []
    if kapitola > 1:
        odkazy.append(
            f'<a href="../kapitola-{kapitola - 1}/{SOUBOR_VARIANTY[varianta]}">'
            f"← {kapitola - 1}. {e(KAPITOLY_KRATCE[kapitola - 1])}</a>"
        )
    if kapitola < 6:
        odkazy.append(
            f'<a href="../kapitola-{kapitola + 1}/{SOUBOR_VARIANTY[varianta]}">'
            f"{kapitola + 1}. {e(KAPITOLY_KRATCE[kapitola + 1])} →</a>"
        )
    if not odkazy:
        return ""
    return (
        '<nav class="naradi" style="margin-top:3.5rem" aria-label="Sousední kapitoly">'
        + "".join(odkazy)
        + "</nav>"
    )


def stranka_kapitoly(d: Dokument) -> str:
    slov = slova_dokumentu(d)
    meta = [
        f"{slov:,} slov".replace(",", " "),
        f"≈ {minuty(slov, SLOV_ZA_MINUTU_CTENI)} min čtení",
        f"≈ {minuty(slov, SLOV_ZA_MINUTU_POSLECHU)} min poslechu",
    ]
    if d.varianta == "otazky":
        meta.append(f"{d.pocet_otazek} otázek")
    else:
        meta.append(f"{len(d.oddily)} oddílů")
    meta.append(f"{MINUTY_VYUKY[d.kapitola]} min výuky podle sylabu")

    if d.varianta == "otazky":
        naradi = (
            '<div class="naradi">'
            '<button type="button" class="tlacitko" data-prepinac-odpovedi aria-pressed="false">Skrýt odpovědi</button>'
            '<span class="napoveda">Se skrytými odpověďmi odhalíš jednotlivou odpověď kliknutím na otázku. '
            "Skryté odpovědi se zároveň nepředčítají.</span>"
            "</div>"
        )
        atribut_odpovedi = ' data-odpovedi="viditelne"'
    else:
        naradi = ""
        atribut_odpovedi = ""

    telo = f"""<div class="stranka">
<div class="layout">
<main>
<div class="zahlavi">
  <p class="drobky">Kapitola {d.kapitola} · {e(VARIANTA_NAZEV[d.varianta])}</p>
  <h1>{e(d.nadpis)}</h1>
  <p class="podtitul">{e(d.podtitul)}</p>
  <ul class="meta">{''.join(f'<li>{e(m)}</li>' for m in meta)}</ul>
</div>
{prepinac_variant(d.kapitola, d.varianta)}
{naradi}
<article class="text" id="text"{atribut_odpovedi}>
{vykresli_bloky(d)}
</article>
{sousedni_kapitoly(d.kapitola, d.varianta)}
</main>
{strom_oddilu(d)}
</div>
</div>"""

    titulek = f"{d.kapitola}. {KAPITOLY_KRATCE[d.kapitola]} — {VARIANTA_NAZEV[d.varianta]} | {NAZEV_WEBU}"
    return stranka(
        titulek=titulek,
        popis=f"{VARIANTA_NAZEV[d.varianta]} kapitoly {d.kapitola} sylabu ISTQB CTFL v4.0: {KAPITOLY[d.kapitola]}. {VARIANTA_POPIS[d.varianta]}",
        telo=telo,
        korenova_cesta="../",
        aktivni="kapitoly",
        kapitola=d.kapitola,
        varianta_podmenu=d.varianta,
    )


# --- úvodní stránka ---------------------------------------------------------


def karta_kapitoly(kapitola: int, dokumenty: dict) -> str:
    """Dlaždice kapitoly se třemi odkazy na varianty.

    Odkaz na plný výklad je navíc roztažený přes celou dlaždici (viz .hlavni
    v CSS), takže kliknutí kamkoli mimo ostatní dva odkazy otevře výklad.
    Řeší se to pseudoprvkem, ne vnořeným odkazem — ten by nebyl platný.
    """
    odkazy = []
    for v in PORADI_VARIANT:
        d = dokumenty.get((kapitola, v))
        if d is None:
            continue
        slov = slova_dokumentu(d)
        if v == "otazky":
            doplnek = f"{d.pocet_otazek} otázek"
        else:
            doplnek = f"≈ {minuty(slov, SLOV_ZA_MINUTU_CTENI)} min"
        trida = ' class="hlavni"' if v == "vyklad" else ""
        odkazy.append(
            f'<li><a href="kapitola-{kapitola}/{SOUBOR_VARIANTY[v]}"{trida}>'
            f"{VARIANTA_NAZEV[v]}<span>{doplnek}</span></a></li>"
        )

    return f"""<li class="karta" id="kapitola-{kapitola}" data-kapitola="{kapitola}">
  <p class="karta-cislo">Kapitola {kapitola}</p>
  <h3>{e(KAPITOLY[kapitola])}</h3>
  <p class="karta-meta">{MINUTY_VYUKY[kapitola]} minut výuky podle sylabu</p>
  <ul>{''.join(odkazy)}</ul>
</li>"""


def stranka_uvodu(dokumenty: dict) -> str:
    celkem_slov = sum(slova_dokumentu(d) for d in dokumenty.values())
    celkem_otazek = sum(d.pocet_otazek for d in dokumenty.values() if d.varianta == "otazky")

    telo = f"""<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava">
  <p class="drobky">Foundation Level · sylabus v4.0</p>
  <h1>Příprava na ISTQB CTFL v češtině</h1>
  <p class="perex">Celý sylabus Foundation Level ve třech podobách: výklad k pochopení,
  zkrácená verze k opakování a otázky k procvičení.
  {celkem_slov // 1000} tisíc slov a {celkem_otazek} otázek, česky a zdarma.</p>
</div>

<div class="uvod-sloupce">

<section class="sekce" id="jak-studovat">
  <h2>Jak web používat</h2>
  <p>Ke každé kapitole jsou tři varianty téhož obsahu. Nejsou to alternativy k výběru,
  ale tři průchody látkou za sebou.</p>
  <ul>
    <li><strong>Plný výklad</strong> — souvislý text se souvislostmi, doplňky nad rámec
    sylabu a příklady z praxe. Tudy začni.</li>
    <li><strong>Zkrácená verze</strong> — jen to, co je nutné znát ke zkoušce.
    Na opakování týden před termínem.</li>
    <li><strong>Otázky a odpovědi</strong> — ke všem studijním cílům. Jedním tlačítkem
    se odpovědi skryjí a stránka se změní ve zkoušecí režim.</li>
  </ul>
</section>

<section class="sekce" id="predcitani">
  <h2>Nechte si to předčítat</h2>
  <dl class="zkratky">
    <div>
      <dt>Ctrl + Shift + U</dt>
      <dd>Spustí a zastaví předčítání v Microsoft Edge. Hlas a rychlost se vybírají
      v panelu nahoře, čeština je k dispozici.</dd>
    </div>
  </dl>
</section>

</div>

</main>
</div>"""

    return stranka(
        titulek=f"{NAZEV_WEBU} — {PODNAZEV_WEBU}",
        popis="Kompletní sylabus ISTQB Certified Tester Foundation Level v4.0 v češtině: "
        "plný výklad, zkrácené verze k opakování a otázky k procvičení. Optimalizováno pro předčítání v Edge.",
        telo=telo,
        korenova_cesta="",
        aktivni="uvod",
    )


# --- stránka Kapitoly -------------------------------------------------------


def stranka_kapitol(dokumenty: dict) -> str:
    karty = "".join(karta_kapitoly(k, dokumenty) for k in sorted(KAPITOLY))

    telo = f"""<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava uvod-hlava--strucna">
  <h1>Kapitoly sylabu</h1>
</div>

<ul class="mrizka">{karty}</ul>

</main>
</div>"""

    return stranka(
        titulek=f"Kapitoly sylabu | {NAZEV_WEBU}",
        popis="Všech šest kapitol sylabu ISTQB CTFL v4.0 v češtině, každá v plném výkladu, "
        "zkrácené verzi a jako otázky s odpověďmi.",
        telo=telo,
        korenova_cesta="",
        aktivni="kapitoly",
    )


# --- stránka Zkouška (placeholder) ------------------------------------------


def stranka_zkousky() -> str:
    telo = """<div class="stranka uvod">
<main id="text">

<div class="uvod-hlava">
  <p class="drobky">Připravuje se</p>
  <h1>Simulace zkoušky</h1>
  <p class="perex">Tahle část webu zatím není hotová. Až bude, půjde si tady odsimulovat
  reálnou zkoušku za stejných podmínek, jaké vás čekají u certifikace.</p>
</div>

<section class="sekce">
  <h2>Jak zkouška vypadá</h2>
  <dl class="zkratky">
    <div><dt>40 otázek</dt><dd>S výběrem odpovědi, pokrývající všech šest kapitol sylabu.</dd></div>
    <div><dt>60 minut</dt><dd>Kdo skládá zkoušku v jiném než rodném jazyce, má nárok na 75 minut.</dd></div>
    <div><dt>65 % k úspěchu</dt><dd>Tedy 26 správných odpovědí ze 40.</dd></div>
    <div><dt>Uzavřená kniha</dt><dd>Bez materiálů. Certifikát pak platí bez expirace.</dd></div>
  </dl>
</section>

<section class="sekce">
  <h2>Co tady bude</h2>
  <ul>
    <li>Test o 40 otázkách s odpočtem 60 minut, ve stejném formátu jako reálná zkouška.</li>
    <li>Rozdělení otázek podle kapitol a podle kognitivních úrovní K1, K2 a K3 tak,
    aby odpovídalo skutečnému rozložení ve zkoušce.</li>
    <li>Vyhodnocení po odevzdání — nejen správná odpověď, ale i vysvětlení,
    proč jsou ostatní varianty špatně.</li>
    <li>Přehled slabých míst podle kapitol, abyste věděli, kam se vrátit.</li>
    <li>Možnost procvičovat jen vybranou kapitolu místo celého sylabu.</li>
  </ul>
</section>

<section class="sekce">
  <h2>Než to bude hotové</h2>
  <p>Zkoušet se dá už teď. U každé kapitoly je varianta
  <a href="kapitoly.html">Otázky a odpovědi</a> — tlačítkem <em>Skrýt odpovědi</em> se z ní
  stane zkoušecí režim, kde se odpověď odhalí až kliknutím na otázku. Není to formát reálné
  zkoušky, ale na ověření, jestli látku umíte vlastními slovy, je to lepší.</p>
  <p class="poznamka">Oficiální vzorové zkoušky A až D si zdarma stáhněte na
  <a href="https://casqb.org/ke-stazeni" target="_blank" rel="noopener noreferrer">casqb.org/ke-stazeni</a>.
  CaSQB je má přeložené do češtiny a jsou to nejbližší dostupná náhrada skutečné zkoušky.</p>
</section>

</main>
</div>"""

    return stranka(
        titulek=f"Simulace zkoušky | {NAZEV_WEBU}",
        popis="Simulace zkoušky ISTQB CTFL v4.0 se teprve připravuje: 40 otázek, 60 minut, "
        "hranice úspěchu 65 %.",
        telo=telo,
        korenova_cesta="",
        aktivni="zkouska",
    )


# --- stránka Zdroje ---------------------------------------------------------


def stranka_zdroju(zdrojovy_md: Path) -> str:
    surovy = zdrojovy_md.read_text(encoding="utf-8")

    # První řádek je nadpis dokumentu — stane se z něj <h1> stránky.
    radky = surovy.split("\n")
    nadpis = radky[0].lstrip("# ").strip()
    zbytek = "\n".join(radky[1:])

    telo = f"""<div class="stranka">
<main>
<div class="zahlavi">
  <p class="drobky">Doklad původu informací</p>
  <h1>{e(nadpis)}</h1>
  <p class="podtitul">U každého tvrzení v materiálech je dohledatelné, odkud pochází.</p>
</div>
<article class="md" id="text">
{markdown_min.prevod(zbytek)}
</article>
</main>
</div>"""

    return stranka(
        titulek=f"Zdroje a citace | {NAZEV_WEBU}",
        popis="Doklad původu všech informací použitých ve studijních materiálech ISTQB CTFL v4.0 "
        "včetně úrovně ověření a odkazů na primární zdroje.",
        telo=telo,
        korenova_cesta="",
        aktivni="zdroje",
    )


# --- sestavení --------------------------------------------------------------


def sestav() -> int:
    dokumenty = nacti_vse(KOREN)
    if not dokumenty:
        print("Ve složce projektu nejsou žádné soubory CTFL_Kap*.docx.", file=sys.stderr)
        return 1

    for kapitola in sorted(KAPITOLY):
        slozka = WEB / f"kapitola-{kapitola}"
        if slozka.exists():
            shutil.rmtree(slozka)
        slozka.mkdir(parents=True, exist_ok=True)

    napsano = 0
    for (kapitola, varianta), d in sorted(dokumenty.items()):
        cil = WEB / f"kapitola-{kapitola}" / SOUBOR_VARIANTY[varianta]
        cil.write_text(stranka_kapitoly(d), encoding="utf-8")
        napsano += 1
        print(f"  kapitola-{kapitola}/{SOUBOR_VARIANTY[varianta]}  ({slova_dokumentu(d):>6} slov)")

    (WEB / "index.html").write_text(stranka_uvodu(dokumenty), encoding="utf-8")
    print("  index.html")

    (WEB / "kapitoly.html").write_text(stranka_kapitol(dokumenty), encoding="utf-8")
    print("  kapitoly.html")

    # Simulace zkoušky z oficiálních vzorových testů; bez dat zůstane původní
    # informační stránka.
    zkousky = vzorove_zkousky.zapis(KOREN, WEB, stranka)
    if len(zkousky) == 1:
        (WEB / "zkouska.html").write_text(stranka_zkousky(), encoding="utf-8")
    for nazev in zkousky:
        print(f"  {nazev}")

    # Přiřazovací cvičení podle kapitol (data v tools/prirazovani/sady.json).
    for nazev in prirazovani.zapis(WEB, stranka, KAPITOLY):
        print(f"  {nazev}")

    zdroje_md = KOREN / "ZDROJE.md"
    if zdroje_md.exists():
        (WEB / "zdroje.html").write_text(stranka_zdroju(zdroje_md), encoding="utf-8")
        print("  zdroje.html")
    else:
        print("  ZDROJE.md nenalezen — stránka Zdroje se nevygenerovala.", file=sys.stderr)

    # GitHub Pages jinak prožene obsah Jekyllem, což tady není potřeba.
    (WEB / ".nojekyll").write_text("", encoding="utf-8")

    print(f"\nHotovo: {napsano} stránek kapitol + úvod + zdroje ve složce {WEB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(sestav())
