#!/usr/bin/env python3
"""Automatische AppSource-Readiness-Prüfung für ein AL-Go-Projekt.

Nur Standardbibliothek. Ausgabe: Markdown-Report (stdout oder --out).
Exit-Code 0 = keine Fehler, 1 = mindestens ein FAIL.
"""
import argparse, json, os, re, struct, sys, urllib.request, urllib.error, glob, hashlib, subprocess
from datetime import date

OK, FAIL, WARN, SKIP = "✅", "❌", "⚠️", "⬜"
results = []  # (section, id, status, message)

def add(section, cid, status, msg):
    results.append((section, cid, status, msg))

def load_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        return None

def png_size(path):
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        w, h = struct.unpack(">II", head[16:24])
        return w, h
    except Exception:
        return None

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "appsource-readiness/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)

def git_added_at(project, path):
    """Unix-Zeit des Commits, der die Datei angelegt hat; None ohne Git-Historie.
    Bewusst ohne --follow: Git würde eine byte-gleiche Kopie sonst dem Original zuordnen."""
    try:
        out = subprocess.run(["git", "-C", project, "log", "--diff-filter=A", "--format=%ct", "--", path],
                             capture_output=True, text=True, timeout=10).stdout.split()
        return int(out[-1]) if out else None
    except Exception:
        return None

def find_app_folder(project, explicit):
    if explicit:
        return os.path.join(project, explicit)
    s = load_json(os.path.join(project, ".AL-Go", "settings.json")) or {}
    folders = s.get("appFolders") or []
    if folders:
        return os.path.join(project, folders[0])
    for p in glob.glob(os.path.join(project, "*", "app.json")):
        a = load_json(p) or {}
        rng = a.get("idRanges") or []
        if any(r.get("from", 0) >= 50000 for r in rng):
            return os.path.dirname(p)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--app", default=None, help="App-Ordner relativ zum Projekt")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-web", action="store_true", help="keine HTTP-Prüfungen")
    args = ap.parse_args()
    project = os.path.abspath(args.project)

    app_dir = find_app_folder(project, args.app)
    if not app_dir or not os.path.exists(os.path.join(app_dir, "app.json")):
        print("Kein App-Ordner mit app.json gefunden.", file=sys.stderr)
        sys.exit(2)
    app = load_json(os.path.join(app_dir, "app.json")) or {}
    app_name = app.get("name", "")

    # ---------- C.1 Manifest ----------
    for key in ("name", "publisher", "brief", "description", "help", "EULA", "privacyStatement", "url", "contextSensitiveHelpUrl", "logo"):
        v = app.get(key)
        add("C.1", f"app.json.{key}", OK if v else FAIL, f"`{key}` {'gesetzt' if v else 'FEHLT'}")
    pub = app.get("publisher", "")
    add("C.1", "publisher-spelling", WARN if re.search(r"[-–]", pub) else OK,
        f"Publisher `{pub}` — muss zeichengleich zum Partner-Center-Anzeigenamen sein" + (" (enthält Bindestrich: prüfen!)" if re.search(r"[-–]", pub) else ""))
    ai = app.get("applicationInsightsConnectionString", "")
    add("C.1", "app-insights", OK if ai.startswith("InstrumentationKey=") else FAIL, "applicationInsightsConnectionString " + ("gesetzt" if ai else "FEHLT (AS0092)"))
    rep = app.get("resourceExposurePolicy", {})
    bad = [k for k in ("allowDebugging", "allowDownloadingSource", "includeSourceInSymbolFile") if rep.get(k, True)]
    add("C.1", "resource-exposure", OK if not bad else FAIL, "resourceExposurePolicy " + ("alles false" if not bad else f"offen: {', '.join(bad)}"))
    rng = app.get("idRanges") or []
    add("C.1", "id-range", OK if rng and all(r.get("from", 0) >= 50000 for r in rng) else FAIL,
        "idRanges " + (", ".join(f"{r.get('from')}-{r.get('to')}" for r in rng) if rng else "FEHLT"))
    cop = load_json(os.path.join(app_dir, "AppSourceCop.json")) or {}
    affixes = cop.get("mandatoryAffixes") or []
    add("C.1", "appsourcecop", OK if affixes else FAIL, "AppSourceCop.json mandatoryAffixes: " + (", ".join(affixes) if affixes else "FEHLT"))
    rulesets = glob.glob(os.path.join(app_dir, "*.ruleset.json"))
    if rulesets:
        rs = load_json(rulesets[0]) or {}
        rules = rs.get("rules") or []
        missing = [r.get("id") for r in rules if r.get("action") == "None" and not r.get("justification")]
        add("C.1", "ruleset-justification", OK if not missing else FAIL,
            f"Ruleset `{os.path.basename(rulesets[0])}`: {len(rules)} Regeln" + (f", ohne Begründung: {missing}" if missing else ", alle begründet"))
    else:
        add("C.1", "ruleset-justification", SKIP, "kein Ruleset im App-Ordner (ok, wenn keine Unterdrückungen nötig)")

    # ---------- B.3 Logo ----------
    logo = os.path.join(app_dir, app.get("logo", "")) if app.get("logo") else None
    if logo and os.path.exists(logo):
        sz = png_size(logo)
        if not sz:
            add("B.3", "logo", FAIL, f"Logo `{app.get('logo')}` ist kein PNG")
        else:
            w, h = sz
            good = w == h and 216 <= w <= 350
            add("B.3", "logo", OK if good else FAIL, f"Logo {w}×{h} px" + ("" if good else " — Vorgabe: quadratisch, 216–350 px"))
        # Duplikat-Prüfung: gleiches Logo wie eine andere App im Repo?
        try:
            own = hashlib.md5(open(logo, "rb").read()).hexdigest()
            dupes = []
            for other_json in glob.glob(os.path.join(project, "*", "app.json")):
                other_dir = os.path.dirname(other_json)
                if os.path.abspath(other_dir) == os.path.abspath(app_dir):
                    continue
                other = load_json(other_json) or {}
                other_logo = os.path.join(other_dir, other.get("logo", "")) if other.get("logo") else None
                if other_logo and os.path.exists(other_logo) and hashlib.md5(open(other_logo, "rb").read()).hexdigest() == own:
                    dupes.append((other.get("name") or os.path.basename(other_dir), other_logo))
            if dupes:
                # Original oder Kopie? Das ältere Logo laut Git-Historie gilt als Original.
                own_t = git_added_at(project, logo)
                newer_than_me = [n for n, pth in dupes if own_t is not None and (git_added_at(project, pth) or 0) > own_t]
                names = [n for n, _ in dupes]
                if own_t is not None and len(newer_than_me) == len(dupes):
                    add("B.3", "logo-unique", WARN, f"Logo wurde von {names} kopiert (diese App ist laut Git das Original) — die andere App braucht ein eigenes Logo")
                else:
                    add("B.3", "logo-unique", FAIL, f"Logo ist byte-identisch mit dem Logo von: {names} — jede App braucht ein eigenes Logo")
            else:
                add("B.3", "logo-unique", OK, "Logo ist keine Kopie eines anderen App-Logos im Repo")
        except Exception as e:
            add("B.3", "logo-unique", SKIP, f"Duplikat-Prüfung nicht möglich: {e}")
    else:
        add("B.3", "logo", FAIL, "Logo-Datei fehlt")
    shots = sorted(glob.glob(os.path.join(project, ".dev", "appsource-assets", "screenshots", "*.png")))
    if not shots:
        add("B.3", "screenshots", SKIP, "keine Screenshots unter `.dev/appsource-assets/screenshots/` (mind. 3 × 1280×720 PNG nötig)")
    else:
        wrong = [os.path.basename(p) for p in shots if png_size(p) != (1280, 720)]
        st = OK if len(shots) >= 3 and not wrong else FAIL
        add("B.3", "screenshots", st, f"{len(shots)} Screenshots" + (f", falsches Format: {wrong}" if wrong else "") + ("" if len(shots) >= 3 else " — mindestens 3 nötig"))

    # ---------- C.2 Entitlements / Translations ----------
    src = os.path.join(app_dir, "src")
    ent_files = [p for p in glob.glob(os.path.join(src, "**", "*.al"), recursive=True) if re.search(r"^\s*entitlement\s", open(p, encoding="utf-8", errors="ignore").read(), re.M)]
    if ent_files:
        txt = "\n".join(open(p, encoding="utf-8", errors="ignore").read() for p in ent_files)
        ids = re.findall(r"ObjectEntitlements\s*=|Id\s*=\s*'([^']+)'", txt)
        sids = [i for i in ids if i]
        guid = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
        svc = re.compile(r"^[a-z0-9]+\.[a-z0-9-]+\.[a-z0-9-]+$")
        placeholder = [s for s in sids if not guid.match(s) and not svc.match(s)]
        real_plans = [s for s in sids if svc.match(s)]
        st = FAIL if not real_plans else (WARN if placeholder else OK)
        add("C.2", "entitlements", st,
            f"{len(ent_files)} Entitlement-Datei(en), Partner-Center-Plan-IDs: {real_plans or 'KEINE'}" + (f" — Platzhalter (nicht einreichbar, falls der Plan verkauft wird): {placeholder}" if placeholder else ""))
    else:
        add("C.2", "entitlements", FAIL, "keine Entitlement-Objekte gefunden")
    xlf = glob.glob(os.path.join(app_dir, "Translations", "*.xlf"))
    langs = sorted({re.search(r"\.([a-z]{2}-[A-Z]{2})\.xlf$", p).group(1) for p in xlf if re.search(r"\.([a-z]{2}-[A-Z]{2})\.xlf$", p)})
    add("C.2", "translations", OK if langs else WARN, "Übersetzungen: " + (", ".join(langs) if langs else "keine Sprach-XLF (nur .g.xlf?)"))
    al_all = glob.glob(os.path.join(src, "**", "*.al"), recursive=True)
    tbc = [os.path.basename(p) for p in al_all if "ToBeClassified" in open(p, encoding="utf-8", errors="ignore").read()]
    add("C.2", "data-classification", OK if not tbc else FAIL, "DataClassification " + ("vollständig" if not tbc else f"ToBeClassified in: {tbc[:5]}"))
    pub_ifaces = []
    for p in al_all:
        t = open(p, encoding="utf-8", errors="ignore").read()
        if re.search(r"^\s*interface\s+\"?[^\"\n]+\"?\s*$", t, re.M) and not re.search(r"Access\s*=\s*Internal", t):
            pub_ifaces.append(os.path.basename(p))
    add("C.3", "public-interfaces", WARN if pub_ifaces else OK,
        "Interfaces ohne `Access = Internal` (nach Einreichung eingefroren): " + (", ".join(pub_ifaces) if pub_ifaces else "keine"))

    # ---------- C.4 AL-Go ----------
    algo = load_json(os.path.join(project, ".AL-Go", "settings.json")) or {}
    d = algo.get("deliverToAppSource") or {}
    app_folder_name = os.path.basename(os.path.normpath(app_dir))
    app_folders = algo.get("appFolders") or []
    main_folder = d.get("mainAppFolder")
    if not d.get("productId"):
        add("C.4", "deliverToAppSource", FAIL, "deliverToAppSource FEHLT")
    elif main_folder and os.path.normpath(main_folder) != app_folder_name:
        add("C.4", "deliverToAppSource", FAIL,
            f"deliverToAppSource.productId `{d.get('productId')}` gehört zu `{main_folder}`, nicht zu `{app_folder_name}` — eigenes Offer + eigene productId nötig (Multi-App: AL-Go `projects`-Layout oder eigenes Repo)")
    elif not main_folder and len(app_folders) > 1:
        add("C.4", "deliverToAppSource", WARN,
            f"deliverToAppSource ohne mainAppFolder bei {len(app_folders)} appFolders — AL-Go liefert dann alle Apps an productId `{d.get('productId')}`")
    else:
        add("C.4", "deliverToAppSource", OK,
            f"deliverToAppSource productId gesetzt, continuousDelivery={d.get('continuousDelivery')}, mainAppFolder={main_folder or app_folder_name}")
    gh = load_json(os.path.join(project, ".github", "AL-Go-Settings.json")) or {}
    ts = gh.get("trustedSigning") or {}
    add("C.4", "trustedSigning", OK if ts.get("Account") and ts.get("CertificateProfile") else FAIL,
        "trustedSigning " + (f"Account={ts.get('Account')}, Profile={ts.get('CertificateProfile')}" if ts else "FEHLT (unsignierte Apps werden abgelehnt)"))
    add("C.4", "publish-workflow", OK if os.path.exists(os.path.join(project, ".github", "workflows", "PublishToAppSource.yaml")) else FAIL, "Workflow PublishToAppSource.yaml")

    # ---------- C.2 Test-App ----------
    ivt_ids = {(x.get("id") or "").lower() for x in (app.get("internalsVisibleTo") or []) if x.get("id")}
    test_folders = algo.get("testFolders") or []
    linked = []   # (folder, name, n_test_codeunits, in_testFolders)
    for tj in glob.glob(os.path.join(project, "*", "app.json")):
        tdir = os.path.dirname(tj)
        if os.path.abspath(tdir) == os.path.abspath(app_dir):
            continue
        t = load_json(tj) or {}
        if (t.get("id") or "").lower() not in ivt_ids:
            continue
        n_tests = 0
        for al in glob.glob(os.path.join(tdir, "**", "*.al"), recursive=True):
            txt = open(al, encoding="utf-8", errors="ignore").read()
            if re.search(r"Subtype\s*=\s*Test\s*;", txt):
                n_tests += 1
        tname = os.path.basename(os.path.normpath(tdir))
        linked.append((tname, t.get("name") or tname, n_tests, tname in [os.path.normpath(f) for f in test_folders]))
    if not ivt_ids:
        add("C.2", "test-app", WARN, "app.json hat kein `internalsVisibleTo` — keine Test-App verknüpft (Projektregel: jede App hat eine Test-App)")
    elif not linked:
        add("C.2", "test-app", FAIL, f"internalsVisibleTo zeigt auf {sorted(ivt_ids)}, aber kein Ordner im Repo hat diese App-ID")
    else:
        problems = []
        for folder, name, n, in_tf in linked:
            if not in_tf:
                problems.append(f"`{folder}` fehlt in .AL-Go testFolders")
            if n == 0:
                problems.append(f"`{folder}` enthält keine Test-Codeunit (Subtype = Test)")
        desc = ", ".join(f"`{f}` ({n} Test-Codeunits)" for f, _, n, _ in linked)
        add("C.2", "test-app", FAIL if problems else OK, "Test-App: " + desc + (" — " + "; ".join(problems) if problems else ""))

    # ---------- B.4 Links ----------
    links = {"help": app.get("help"), "EULA": app.get("EULA"), "privacyStatement": app.get("privacyStatement"), "url": app.get("url"), "contextSensitiveHelpUrl": app.get("contextSensitiveHelpUrl")}
    pages = {}
    for k, u in links.items():
        if not u:
            continue
        if not u.startswith("https://"):
            add("B.4", f"link-{k}", FAIL, f"{k}: `{u}` ist nicht https"); continue
        if args.no_web:
            add("B.4", f"link-{k}", SKIP, f"{k}: `{u}` (nicht geprüft, --no-web)"); continue
        code, body = fetch(u)
        pages[k] = body or ""
        add("B.4", f"link-{k}", OK if code == 200 else FAIL, f"{k}: `{u}` → HTTP {code}")
    if not args.no_web and pages:
        priv = pages.get("privacyStatement", "")
        add("B.4", "privacy-names-app", OK if app_name and app_name.lower() in priv.lower() else FAIL,
            "Datenschutzseite nennt die App " + ("namentlich" if app_name.lower() in priv.lower() else "NICHT — Pflicht laut Microsoft"))
        helpb = pages.get("help", "")
        contacts = set(re.findall(r"mailto:[^\"'\s>]+|tel:[^\"'\s>]+", helpb, re.I))
        chat = bool(re.search(r"chat|ticket|support-?portal|helpdesk", helpb, re.I))
        n = len(contacts) + (1 if chat else 0)
        add("B.4", "support-contacts", OK if n > 2 else WARN, f"Hilfeseite: {len(contacts)} Mail/Telefon-Kontakte{' + Chat/Ticket' if chat else ''} — Support braucht > 2 Kontaktwege")
        for k, body in pages.items():
            text = re.sub(r"<[^>]+>", " ", body)
            hits = sorted(set(re.findall(r"\b(BC|D365|NAV|MSDYN365BC)\b", text)))
            hits = [h for h in hits if not (h == "NAV" and "Navigation" in text and text.count("NAV") <= 1)]
            add("B.2", f"branding-{k}", OK if not hits else WARN, f"Branding auf {k}: " + ("keine verbotenen Abkürzungen" if not hits else f"Abkürzungen gefunden: {hits}"))

    # ---------- Report ----------
    counts = {s: sum(1 for r in results if r[2] == s) for s in (OK, FAIL, WARN, SKIP)}
    lines = [f"# AppSource-Readiness-Report — {app_name}", "",
             f"Projekt: `{project}` · App-Ordner: `{os.path.relpath(app_dir, project)}` · Version {app.get('version')} · Stand {date.today().isoformat()}", "",
             f"**{counts[OK]} ✅ · {counts[FAIL]} ❌ · {counts[WARN]} ⚠️ · {counts[SKIP]} ⬜**", "",
             "| Teil | Prüfung | Status | Befund |", "|---|---|---|---|"]
    for sec, cid, st, msg in sorted(results, key=lambda r: (r[0], r[1])):
        lines.append(f"| {sec} | `{cid}` | {st} | {msg} |")
    lines += ["", "Nicht automatisch prüfbar (manuell in `checklist.md` pflegen): Partner-Center-Konto, Payout/Steuer, Identity Validation, Offer-Texte, Kategorien, Leads, Notes for certification, Projekt-Review, Generalprobe, Go-to-Market."]
    report = "\n".join(lines) + "\n"
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report geschrieben: {args.out}  ({counts[OK]} ✅ / {counts[FAIL]} ❌ / {counts[WARN]} ⚠️ / {counts[SKIP]} ⬜)")
    else:
        print(report)
    sys.exit(1 if counts[FAIL] else 0)

if __name__ == "__main__":
    main()
