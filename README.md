# ISTQB CTFL v4.0 — generátor české studijní příručky

Statický web se studijními materiály k certifikaci ISTQB Certified Tester Foundation Level
(sylabus v4.0) v češtině — **a generátor, který ho staví z dokumentů Wordu, plus kontrolní
sada, která ověřuje, že se při převodu nic neztratilo.**

Šest kapitol, každá ve třech podobách: plný výklad, zkrácená verze, otázky s odpověďmi.
Dohromady přes **87 000 slov**. Texty jsou psané tak, aby se daly poslouchat — v Microsoft
Edge je přečte nahlas `Ctrl+Shift+U`, čtecí režim se zapíná klávesou `F9`.

🔗 **[Otevřít web](https://jancerny-dev.github.io/ISTQB/)**

---

## Proč je tady generátor a kontrolní sada

Obsah vzniká ve Wordu, protože se v něm dobře píše a reviduje. Web z něj musí vzniknout
převodem — a u 87 000 slov **pohledem nepoznáte, že se jeden oddíl nepřenesl nebo že
se rozpadl vnitřní odkaz.** Tak jsem si na to napsal kontrolu.

```bash
pip install -r requirements.txt
python tools/build_site.py    # postaví web/ ze zdrojových .docx
python tools/check_site.py    # ověří výstup; návratový kód 0 = OK, 1 = nálezy
```

`check_site.py` ověřuje šest invariantů:

| # | Invariant |
|---|---|
| 1 | Každý zdrojový `.docx` má svou stránku |
| 2 | **Počet slov na stránce přesně odpovídá zdroji** — text se nikde nemění ani nevypouští |
| 3 | Barevná sémantika je přiřazená podle varianty kapitoly, ne globálně |
| 4 | Každý oddíl má kotvu a je v bočním obsahu |
| 5 | Všechny vnitřní odkazy a kotvy někam vedou |
| 6 | Odkazované soubory (CSS, JS) existují |

Invariant č. 2 je ten hlavní. Je to jediná kontrola, která odpoví na otázku
*„nepřišel jsem o kus textu?"* — a zároveň ta, kterou by ruční kontrola nikdy neudělala
poctivě. Zjistí i rozdíl o jedno slovo a rovnou ho vyčíslí.

## Struktura

```
tools/
  build_site.py     generátor: .docx → statické HTML
  check_site.py     kontrolní sada, 6 invariantů, návratový kód 0/1
  markdown_min.py   minimální převod značkování
  model.py          datový model dokumentu
web/                vygenerovaný web — to, co jede na GitHub Pages
.github/workflows/
  pages.yml         nasazení web/ na Pages při každém pushi do main
```

## Nasazení

Web se nasazuje sám: workflow `pages.yml` publikuje na GitHub Pages obsah složky `web/`
(generátor ve `tools/` se nepublikuje). V repozitáři musí být v **Settings → Pages**
zdroj nastavený na **GitHub Actions**.

Bez CI to jde taky — stačí otevřít `web/index.html` dvojklikem, nebo obsah složky nahrát
na jakýkoli statický hosting. Soubor `web/.nojekyll` je potřeba nechat, aby GitHub Pages
obsah neproháněl Jekyllem.

## Co v repozitáři není a proč

**Zdrojové `.docx`, PDF sylabu, slovníku a vzorových zkoušek tady nejsou.** Jsou chráněné
autorským právem a nesmí se přeposílat. `.gitignore` proto blokuje `*.docx`, `*.pdf`
a `*.pptx` — aby se sem nedostaly ani při `git add -A`.

Praktický důsledek: `build_site.py` a invariant č. 2 v `check_site.py` se dají spustit
jen lokálně, kde zdrojové dokumenty leží v korenu projektu. **CI proto web jen publikuje,
nepřegenerovává ho.** Aby šly v CI ověřit i zbylé invarianty (3–6, které zdroje
nepotřebují), chybí `check_site.py` přepínač pro běh bez zdrojů — to je další krok.

---

## Autorská práva

Tento web je **neoficiální studijní materiál**. Není produktem ani publikací ISTQB®
ani CaSQB. ISTQB® je registrovaná ochranná známka International Software Testing
Qualifications Board. Oficiální sylabus, slovník a vzorové zkoušky jsou zdarma ke stažení
na [casqb.org/ke-stazeni](https://casqb.org/ke-stazeni).

Kód ve `tools/` je pod licencí MIT. Na textový obsah ve `web/` se MIT nevztahuje.
