"""Épreuve du site racine : la page d'accueil renvoie vers /pucia/, sans erreur.

Usage : python3 essais/eprouver.py [adresse]   (par défaut http://127.0.0.1:8765)
"""
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ADRESSE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765").rstrip("/")
CAPTURES = Path(__file__).parent / "captures"
ECRANS = {"mobile": (375, 667), "bureau": (1440, 900)}
PLAN = "Sitemap: https://pucia-protocol.github.io/pucia/sitemap.xml"


def lire(chemin: str) -> tuple[int, str]:
    with urllib.request.urlopen(ADRESSE + chemin, timeout=20) as reponse:
        return reponse.status, reponse.read().decode("utf-8")


def eprouver_fichiers(echecs: list[str]) -> None:
    code, robots = lire("/robots.txt")
    if code != 200 or PLAN not in robots:
        echecs.append("robots.txt absent ou sans le plan du site")
    cles = [f for f in Path(__file__).parent.parent.glob("*.txt") if f.name != "robots.txt"]
    if len(cles) != 1:
        echecs.append(f"un seul fichier de clé attendu, trouvé {len(cles)}")
        return
    code, contenu = lire("/" + cles[0].name)
    if code != 200 or contenu.strip() != cles[0].stem:
        echecs.append("fichier de clé IndexNow absent ou différent de son nom")


def eprouver_redirection(echecs: list[str]) -> None:
    CAPTURES.mkdir(exist_ok=True)
    with sync_playwright() as p:
        for moteur in (p.chromium, p.webkit):
            navigateur = moteur.launch()
            for nom, (largeur, hauteur) in ECRANS.items():
                page = navigateur.new_page(viewport={"width": largeur, "height": hauteur})
                erreurs: list[str] = []
                page.on("console", lambda m, e=erreurs: e.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda x, e=erreurs: e.append(str(x)))
                page.goto(ADRESSE + "/", wait_until="load")
                page.wait_for_url("**/pucia/", timeout=15000)
                page.wait_for_load_state("networkidle")
                titre = page.title()
                # La capture de WebKit injecte une feuille de style que la politique de
                # sécurité de /pucia/ refuse : on ne compte que les erreurs d'avant la capture.
                avant = len(erreurs)
                page.screenshot(path=str(CAPTURES / f"{moteur.name}-{nom}.png"))
                del erreurs[avant:]
                if "PUCIA" not in titre:
                    echecs.append(f"{moteur.name} {nom} : arrivée sur une page inattendue ({titre!r})")
                if erreurs:
                    echecs.append(f"{moteur.name} {nom} : {len(erreurs)} erreur(s) : {erreurs[:2]}")
                print(f"  {moteur.name:9} {nom:7} -> {page.url}  erreurs : {len(erreurs)}")
                page.close()
            navigateur.close()


def main() -> int:
    echecs: list[str] = []
    eprouver_fichiers(echecs)
    eprouver_redirection(echecs)
    for echec in echecs:
        print("ÉCHEC :", echec)
    print(f"{len(echecs)} échec(s) sur {ADRESSE}")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
