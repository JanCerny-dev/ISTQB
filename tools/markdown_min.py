# -*- coding: utf-8 -*-
"""Minimální převodník Markdownu na HTML.

Pokrývá jen konstrukce, které se skutečně vyskytují v ZDROJE.md:
nadpisy, odstavce, tabulky se zarovnáním, odrážkové a číslované seznamy,
citace, vodorovné linky a inline zvýraznění, kód a odkazy.

Není to obecný Markdown — je to záměrně malý převodník bez závislostí.
"""

from __future__ import annotations

import html
import re

_ODKAZ = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_TUCNE = re.compile(r"\*\*([^*]+)\*\*")
_KURZIVA = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
_KOD = re.compile(r"`([^`]+)`")


def inline(text: str) -> str:
    """Escapuje HTML a přeloží inline značky. Kód se chrání před dalšími pravidly."""
    schranka: list[str] = []

    def uloz(shoda: re.Match) -> str:
        schranka.append(f"<code>{html.escape(shoda.group(1))}</code>")
        return f"\x00{len(schranka) - 1}\x00"

    text = _KOD.sub(uloz, text)
    text = html.escape(text, quote=False)
    text = _ODKAZ.sub(
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        text,
    )
    text = _TUCNE.sub(r"<strong>\1</strong>", text)
    text = _KURZIVA.sub(r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: schranka[int(m.group(1))], text)
    return text


def _zarovnani(bunka: str) -> str:
    bunka = bunka.strip()
    if bunka.startswith(":") and bunka.endswith(":"):
        return ' style="text-align:center"'
    if bunka.endswith(":"):
        return ' style="text-align:right"'
    return ""


def _radek_tabulky(radek: str) -> list[str]:
    return [b.strip() for b in radek.strip().strip("|").split("|")]


def prevod(zdroj: str) -> str:
    radky = zdroj.replace("\r\n", "\n").split("\n")
    vystup: list[str] = []
    i = 0
    n = len(radky)

    while i < n:
        radek = radky[i]
        holy = radek.strip()

        if not holy:
            i += 1
            continue

        if re.fullmatch(r"-{3,}", holy):
            vystup.append("<hr>")
            i += 1
            continue

        nadpis = re.match(r"^(#{1,6})\s+(.*)$", holy)
        if nadpis:
            # Nadpis úrovně # se ze zdroje odebírá a stává se z něj <h1> stránky,
            # takže ## začíná na h2 a hierarchie nadpisů nepřeskakuje úroveň.
            uroven = max(2, min(len(nadpis.group(1)), 6))
            vystup.append(f"<h{uroven}>{inline(nadpis.group(2))}</h{uroven}>")
            i += 1
            continue

        # tabulka
        if holy.startswith("|") and i + 1 < n and re.search(r"\|\s*:?-{2,}", radky[i + 1]):
            hlavicka = _radek_tabulky(holy)
            zarovnani = [_zarovnani(b) for b in _radek_tabulky(radky[i + 1])]
            i += 2
            telo: list[list[str]] = []
            while i < n and radky[i].strip().startswith("|"):
                telo.append(_radek_tabulky(radky[i].strip()))
                i += 1
            vystup.append('<div class="tabulka-obal"><table>')
            vystup.append("<thead><tr>")
            for j, bunka in enumerate(hlavicka):
                z = zarovnani[j] if j < len(zarovnani) else ""
                vystup.append(f"<th{z}>{inline(bunka)}</th>")
            vystup.append("</tr></thead><tbody>")
            for r in telo:
                vystup.append("<tr>")
                for j, bunka in enumerate(r):
                    z = zarovnani[j] if j < len(zarovnani) else ""
                    vystup.append(f"<td{z}>{inline(bunka)}</td>")
                vystup.append("</tr>")
            vystup.append("</tbody></table></div>")
            continue

        # citace
        if holy.startswith(">"):
            kusy: list[str] = []
            while i < n and radky[i].strip().startswith(">"):
                kusy.append(radky[i].strip().lstrip(">").strip())
                i += 1
            vystup.append(f'<blockquote><p>{inline(" ".join(k for k in kusy if k))}</p></blockquote>')
            continue

        # seznamy
        odrazka = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", radek)
        if odrazka:
            cislovany = bool(re.fullmatch(r"\d+\.", odrazka.group(2)))
            znacka = "ol" if cislovany else "ul"
            polozky: list[str] = []
            while i < n:
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", radky[i])
                if m and bool(re.fullmatch(r"\d+\.", m.group(2))) == cislovany:
                    polozky.append(m.group(3).strip())
                    i += 1
                elif radky[i].startswith("  ") and radky[i].strip() and polozky:
                    polozky[-1] += " " + radky[i].strip()
                    i += 1
                else:
                    break
            vystup.append(f"<{znacka}>")
            vystup.extend(f"<li>{inline(p)}</li>" for p in polozky)
            vystup.append(f"</{znacka}>")
            continue

        # odstavec
        kusy = []
        while i < n and radky[i].strip() and not re.match(
            r"^\s*(#{1,6}\s|[-*]\s|\d+\.\s|>|\|)", radky[i]
        ) and not re.fullmatch(r"-{3,}", radky[i].strip()):
            kusy.append(radky[i].strip())
            i += 1
        if kusy:
            vystup.append(f'<p>{inline(" ".join(kusy))}</p>')
        else:
            i += 1

    return "\n".join(vystup)
