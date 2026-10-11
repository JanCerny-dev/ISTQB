# -*- coding: utf-8 -*-
"""Kontrola vygenerovaného webu.

Spuštění (ze složky projektu):

    python tools/check_site.py

Ověřuje to, co pohledem u 87 000 slov nepoznáte:

  1. každý zdrojový .docx má svou stránku
  2. počet slov na stránce přesně odpovídá zdrojovému .docx
     (invariant projektu: text se nikde nemění ani nevypouští)
  3. barevná sémantika je přiřazena podle varianty, ne globálně
  4. každý oddíl má kotvu a je v bočním obsahu
  5. všechny vnitřní odkazy a kotvy někam vedou
  6. odkazované soubory (CSS, JS) existují

Návratový kód 0 = vše v pořádku, 1 = nalezeny chyby.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model import KAPITOLY, VARIANTA_NAZEV, nacti_vse, pocet_slov

KOREN = Path(__file__).resolve().parent.parent
WEB = KOREN / "web"

SOUBOR_VARIANTY = {"vyklad": "vyklad.html", "zkracena": "zkracena.html", "otazky": "otazky.html"}

# Třídy, které do HTML přidává až JavaScript za běhu.
TRIDY_ZE_SKRIPTU = {"aktivni", "odhalena"}

# Kolik barevných pasáží která varianta smí obsahovat.
POVOLENE_TRIDY = {
    "vyklad": {"vsuvka--nad-ramec", "vsuvka--praxe"},
    "zkracena": {"vsuvka--nad-ramec", "vsuvka--praxe"},
    "otazky": {"k1", "k2", "k3"},
}


class Rozbor(HTMLParser):
    """Vytáhne ze stránky text vybraných oblastí, id, odkazy a použité třídy."""

    SLEDOVANE_OBLASTI = {"h1", "podtitul", "text", "md"}
    IGNOROVANE = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hloubka_obsahu = 0
        self.hloubka_ignorace = 0
        self.zasobnik: list[tuple[str, bool]] = []
        self.text: list[str] = []
        self.identifikatory: set[str] = set()
        self.odkazy: list[str] = []
        self.tridy: set[str] = set()
        self.strom_kotvy: list[str] = []
        self._ve_stromu = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        tridy = set((a.get("class") or "").split())
        self.tridy |= tridy

        if a.get("id"):
            self.identifikatory.add(a["id"])
        if tag == "a" and a.get("href"):
            self.odkazy.append(a["href"])
            if self._ve_stromu:
                self.strom_kotvy.append(a["href"])

        if "strom" in tridy:
            self._ve_stromu += 1
        elif self._ve_stromu:
            self._ve_stromu += 1

        sleduj = tag == "h1" or bool(tridy & self.SLEDOVANE_OBLASTI) or a.get("id") == "text"
        if tag in self.IGNOROVANE:
            self.hloubka_ignorace += 1
        if sleduj:
            self.hloubka_obsahu += 1
        self.zasobnik.append((tag, sleduj))

    def handle_endtag(self, tag):
        while self.zasobnik:
            znacka, sleduj = self.zasobnik.pop()
            if sleduj:
                self.hloubka_obsahu = max(0, self.hloubka_obsahu - 1)
            if znacka in self.IGNOROVANE:
                self.hloubka_ignorace = max(0, self.hloubka_ignorace - 1)
            if self._ve_stromu:
                self._ve_stromu -= 1
            if znacka == tag:
                break

    def handle_data(self, data):
        if self.hloubka_obsahu > 0 and self.hloubka_ignorace == 0:
            self.text.append(data)

    @property
    def slova(self) -> int:
        return pocet_slov(" ".join(self.text))


def rozeber(cesta: Path) -> Rozbor:
    r = Rozbor()
    r.feed(cesta.read_text(encoding="utf-8"))
    return r


def zkontroluj() -> int:
    chyby: list[str] = []
    varovani: list[str] = []

    if not WEB.exists():
        print("Složka web/ neexistuje. Spusť nejdřív: python tools/build_site.py", file=sys.stderr)
        return 1

    dokumenty = nacti_vse(KOREN)
    rozbory: dict[Path, Rozbor] = {}

    print("Kontrola úplnosti a shody počtu slov")
    print("-" * 72)

    for (kapitola, varianta), d in sorted(dokumenty.items()):
        cesta = WEB / f"kapitola-{kapitola}" / SOUBOR_VARIANTY[varianta]
        popis = f"kapitola-{kapitola}/{SOUBOR_VARIANTY[varianta]}"

        if not cesta.exists():
            chyby.append(f"{popis}: stránka chybí")
            continue

        r = rozeber(cesta)
        rozbory[cesta] = r

        ocekavano = d.slova_zdroje()
        skutecnost = r.slova
        rozdil = skutecnost - ocekavano
        znak = "OK  " if rozdil == 0 else "CHYBA"
        print(f"  {znak} {popis:<34} {skutecnost:>6} / {ocekavano:>6} slov")
        if rozdil != 0:
            chyby.append(
                f"{popis}: počet slov nesedí — na stránce {skutecnost}, "
                f"ve zdrojovém .docx {ocekavano} (rozdíl {rozdil:+d})"
            )

        # barevná sémantika podle varianty
        cizi = set()
        for jina_varianta, tridy in POVOLENE_TRIDY.items():
            if jina_varianta == varianta:
                continue
            cizi |= tridy - POVOLENE_TRIDY[varianta]
        pouzite_cizi = r.tridy & cizi
        if pouzite_cizi:
            chyby.append(
                f"{popis}: použita barevná sémantika jiné varianty: {sorted(pouzite_cizi)}"
            )

        # oddíly mají kotvy a jsou v bočním obsahu
        for oddil in d.oddily:
            if oddil.kotva not in r.identifikatory:
                chyby.append(f"{popis}: oddíl „{oddil.text[:40]}“ nemá kotvu #{oddil.kotva}")
        kotvy_stromu = {unquote(h.lstrip("#")) for h in r.strom_kotvy if h.startswith("#")}
        chybi_ve_stromu = {o.kotva for o in d.oddily} - kotvy_stromu
        if chybi_ve_stromu and d.oddily:
            chyby.append(f"{popis}: v bočním obsahu chybí oddíly {sorted(chybi_ve_stromu)}")

        # otázky mají kotvu a úroveň
        if varianta == "otazky" and d.pocet_otazek == 0:
            chyby.append(f"{popis}: nenalezena ani jedna otázka")

    print("-" * 72)

    # samostatné stránky
    for nazev in ("index.html", "kapitoly.html", "zkouska.html", "prirazovani.html", "zdroje.html"):
        cesta = WEB / nazev
        if not cesta.exists():
            chyby.append(f"{nazev}: stránka chybí")
        else:
            rozbory[cesta] = rozeber(cesta)

    # odkazy
    print("\nKontrola odkazů a kotev")
    print("-" * 72)
    celkem_odkazu = 0
    for cesta, r in sorted(rozbory.items()):
        popis = cesta.relative_to(WEB).as_posix()
        for href in r.odkazy:
            celkem_odkazu += 1
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            rozdeleno = urlparse(href)
            if rozdeleno.path:
                cil = (cesta.parent / unquote(rozdeleno.path)).resolve()
                if not cil.exists():
                    chyby.append(f"{popis}: odkaz vede na neexistující soubor „{href}“")
                    continue
                if rozdeleno.fragment:
                    cilovy_rozbor = rozbory.get(cil)
                    if cilovy_rozbor is None and cil.suffix == ".html":
                        cilovy_rozbor = rozeber(cil)
                        rozbory[cil] = cilovy_rozbor
                    if cilovy_rozbor and unquote(rozdeleno.fragment) not in cilovy_rozbor.identifikatory:
                        chyby.append(f"{popis}: kotva „{href}“ v cílové stránce neexistuje")
            elif rozdeleno.fragment:
                if unquote(rozdeleno.fragment) not in r.identifikatory:
                    chyby.append(f"{popis}: kotva „{href}“ na stránce neexistuje")
    print(f"  prověřeno {celkem_odkazu} odkazů")

    # statické soubory
    for soubor in ("assets/styl.css", "assets/skript.js", ".nojekyll"):
        if not (WEB / soubor).exists():
            chyby.append(f"chybí soubor web/{soubor}")

    # Každá třída použitá v HTML musí mít pravidlo v CSS. Chytá tiché smazání
    # bloku stylů při úpravách — vizuálně se to na jedné stránce nemusí projevit.
    print("\nKontrola stylů")
    print("-" * 72)
    styl = (WEB / "assets" / "styl.css").read_text(encoding="utf-8")
    v_css = set(re.findall(r"\.([a-zA-Z_][\w-]*)", re.sub(r"/\*.*?\*/", "", styl, flags=re.S)))
    v_css |= TRIDY_ZE_SKRIPTU
    pouzite: dict[str, set[str]] = {}
    for cesta in sorted(WEB.rglob("*.html")):
        for skupina in re.findall(r'class="([^"]+)"', cesta.read_text(encoding="utf-8")):
            for trida in skupina.split():
                pouzite.setdefault(trida, set()).add(cesta.relative_to(WEB).as_posix())
    for trida, kde in sorted(pouzite.items()):
        if trida not in v_css:
            chyby.append(
                f"třída „{trida}“ se používá v HTML ({sorted(kde)[0]}), ale nemá pravidlo v CSS"
            )
    print(f"  {len(pouzite)} tříd v HTML, všechny dohledány v CSS"
          if not any("třída" in ch for ch in chyby)
          else f"  {len(pouzite)} tříd v HTML")

    # chráněné dokumenty se nesmí dostat do publikované složky
    print("\nKontrola publikované složky")
    print("-" * 72)
    nezadouci = [
        p.relative_to(WEB).as_posix()
        for p in WEB.rglob("*")
        if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".pptx"}
    ]
    if nezadouci:
        chyby.append(
            "ve složce web/ jsou dokumenty, které se nemají publikovat: " + ", ".join(nezadouci)
        )
    else:
        print("  žádná PDF, DOCX ani PPTX — složku lze zveřejnit")

    velikost = sum(p.stat().st_size for p in WEB.rglob("*") if p.is_file())
    print(f"  celkem {sum(1 for p in WEB.rglob('*') if p.is_file())} souborů, {velikost / 1024:.0f} kB")

    # souhrn
    print("\n" + "=" * 72)
    for v in varovani:
        print(f"  varování: {v}")
    if chyby:
        print(f"NALEZENO {len(chyby)} CHYB:")
        for ch in chyby:
            print(f"  - {ch}")
        return 1

    pocet_stranek = len(rozbory)
    slov_celkem = sum(r.slova for r in rozbory.values())
    print(f"VŠE V POŘÁDKU — {pocet_stranek} stránek, {slov_celkem:,} slov".replace(",", " "))
    print("Zbývá ověřit ručně v Edge: předčítání (Ctrl+Shift+U) a oba barevné režimy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(zkontroluj())
