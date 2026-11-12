#!/usr/bin/env python3
"""Vorprüfung für "Create release" + "Publish To AppSource" in einem AL-Go-Repo.

Liest nur (lokale Dateien, git, gh). Startet nichts und ändert nichts.
Nur Standardbibliothek; braucht die GitHub-CLI `gh` mit Anmeldung.

Ausgabe: Markdown-Report (stdout oder --out), optional die Rohdaten als JSON (--json).
Exit-Code 0 = startklar, 1 = mindestens ein Blocker, 2 = Prüfung selbst gescheitert.
"""
import argparse, glob, json, os, re, subprocess, sys
from datetime import datetime, timezone
from urllib.parse import quote

EXPECTED = {
    "CreateRelease": ["buildVersion", "name", "tag", "releaseType", "createReleaseBranch",
                      "releaseBranchPrefix", "updateVersionNumber", "skipUpdatingDependencies",
                      "directCommit", "useGhTokenWorkflow"],
    "PublishToAppSource": ["appVersion", "projects", "GoLive"],
}

blockers, warnings, notes = [], [], []


class CheckError(Exception):
    pass


def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise CheckError(f"{' '.join(cmd[:4])} …: {(p.stderr or p.stdout).strip()[:300]}")
    return p.stdout.strip() if p.returncode == 0 else None


def gh_json(args, cwd, check=True):
    out = run(["gh"] + args, cwd=cwd, check=check)
    if out is None or out == "":
        return None
    return json.loads(out)


def load_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def find_workflow(root, stem):
    for ext in (".yaml", ".yml"):
        p = os.path.join(root, ".github", "workflows", stem + ext)
        if os.path.isfile(p):
            return p
    return None


def parse_dispatch_inputs(path):
    """Liest die workflow_dispatch-Inputs (Name, default, type, options) ohne YAML-Bibliothek."""
    inputs, wd_indent, in_indent, key_indent, cur, in_options = {}, None, None, None, None, False
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if wd_indent is None:
                if s.startswith("workflow_dispatch:"):
                    wd_indent = indent
                continue
            if in_indent is None:
                if indent <= wd_indent:
                    break
                if s.startswith("inputs:"):
                    in_indent = indent
                continue
            if indent <= in_indent:
                break
            if key_indent is None:
                key_indent = indent
            if indent == key_indent and s.endswith(":"):
                cur = s[:-1].strip().strip("'\"")
                inputs[cur] = {"options": []}
                in_options = False
            elif cur and s.startswith("- ") and in_options:
                inputs[cur]["options"].append(s[2:].strip().strip("'\""))
            elif cur and ":" in s:
                k, v = s.split(":", 1)
                k = k.strip()
                in_options = (k == "options")
                if not in_options:
                    inputs[cur][k] = v.strip().strip("'\"")
    return inputs


def semver_key(tag):
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+](.*))?$", tag or "")
    if not m:
        return None
    # ohne Zusatz (1.0.0) ist höher als mit Zusatz (1.0.0-beta)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if m.group(4) else 1, m.group(4) or "")


def vtuple(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return None


def discover_projects(root, repo_settings):
    projects = []
    if isinstance(repo_settings.get("projects"), list) and repo_settings["projects"]:
        projects = list(repo_settings["projects"])
    else:
        if os.path.isfile(os.path.join(root, ".AL-Go", "settings.json")):
            projects.append(".")
        for pattern in ("*/.AL-Go/settings.json", "*/*/.AL-Go/settings.json"):
            for p in sorted(glob.glob(os.path.join(root, pattern))):
                rel = os.path.relpath(os.path.dirname(os.path.dirname(p)), root)
                if not rel.startswith(".") and rel not in projects:
                    projects.append(rel.replace(os.sep, "/"))
    return projects


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="Wurzel des AL-Go-Repos (Standard: aktueller Ordner)")
    ap.add_argument("--branch", help="Branch, von dem veröffentlicht wird (Standard: Default-Branch des Repos)")
    ap.add_argument("--mode", choices=["full", "publish"], default="full",
                    help="full = Release erstellen und einreichen (Standard); publish = nur ein vorhandenes Release einreichen")
    ap.add_argument("--release-type", choices=["Release", "Prerelease", "Draft"], default="Release",
                    help="Art des Releases; bestimmt, welches appVersion-Schlüsselwort passt")
    ap.add_argument("--out", help="Markdown-Report in diese Datei schreiben")
    ap.add_argument("--json", dest="json_out", help="Rohdaten zusätzlich als JSON in diese Datei schreiben")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    data = {"checkedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": a.mode}
    full = a.mode == "full"
    keyword = {"Release": "current", "Prerelease": "prerelease", "Draft": "draft"}[a.release_type]

    # --- Repository -------------------------------------------------------------------
    repo = gh_json(["repo", "view", "--json", "nameWithOwner,defaultBranchRef"], root)
    nwo = repo["nameWithOwner"]
    branch = a.branch or repo["defaultBranchRef"]["name"]
    refname = branch.replace("/", "_")
    data.update(repository=nwo, branch=branch)

    # --- Workflows und ihre Eingabefelder ---------------------------------------------
    wf = {}
    for stem, expected in EXPECTED.items():
        path = find_workflow(root, stem)
        if not path:
            blockers.append(f"Workflow-Datei `.github/workflows/{stem}.yaml` fehlt — das Repo ist kein AL-Go-AppSource-Repo oder die Systemdateien sind unvollständig.")
            wf[stem] = {"file": None, "inputs": {}}
            continue
        inputs = parse_dispatch_inputs(path)
        wf[stem] = {"file": os.path.basename(path), "inputs": inputs}
        have = {k.lower(): k for k in inputs}
        missing = [e for e in expected if e.lower() not in have]
        extra = [k for k in inputs if k.lower() not in [e.lower() for e in expected]]
        if missing:
            warnings.append(f"`{wf[stem]['file']}` kennt die erwarteten Eingabefelder nicht mehr: {', '.join(missing)}. AL-Go-Vorlage hat sich geändert — Felder im Workflow nachlesen, bevor gestartet wird.")
        if extra:
            warnings.append(f"`{wf[stem]['file']}` hat zusätzliche Eingabefelder: {', '.join(extra)}. Im Workflow nachlesen, ob sie gesetzt werden müssen.")
    data["workflows"] = wf

    def actual(stem, name):
        """Schreibweise des Feldes so, wie sie im Workflow steht (z. B. GoLive)."""
        for k in wf[stem]["inputs"]:
            if k.lower() == name.lower():
                return k
        return None

    # --- AL-Go-Einstellungen und Projekte ---------------------------------------------
    repo_settings = load_json(os.path.join(root, ".github", "AL-Go-Settings.json")) or {}
    if repo_settings.get("type") != "AppSource App":
        warnings.append(f"`.github/AL-Go-Settings.json`: type ist `{repo_settings.get('type')}`, erwartet `AppSource App`.")
    repo_name = repo_settings.get("repoName") or nwo.split("/")[1]
    projects = []
    for proj in discover_projects(root, repo_settings):
        pdir = root if proj == "." else os.path.join(root, proj)
        ps = load_json(os.path.join(pdir, ".AL-Go", "settings.json")) or {}
        d2a = ps.get("deliverToAppSource") or {}
        product_id = ps.get("AppSourceProductId") or d2a.get("productId") or ""
        main_folder = ps.get("AppSourceMainAppFolder") or d2a.get("mainAppFolder") or (ps.get("appFolders") or [None])[0]
        app = load_json(os.path.join(pdir, main_folder, "app.json")) if main_folder else None
        projects.append({
            "project": proj,
            "artifactProject": repo_name if proj == "." else proj.replace("\\", "_").replace("/", "_"),
            "productId": product_id,
            "mainAppFolder": main_folder,
            "appName": (app or {}).get("name"),
            "appJsonVersion": (app or {}).get("version"),
            "repoVersion": ps.get("repoVersion") or repo_settings.get("repoVersion"),
        })
    deliver = [p for p in projects if p["productId"]]
    if not projects:
        blockers.append("Kein AL-Go-Projekt gefunden (`.AL-Go/settings.json` fehlt).")
    elif not deliver:
        blockers.append("Kein Projekt hat `deliverToAppSource.productId`. AL-Go behandelt es dann als Library-Projekt: „Publish To AppSource“ läuft grün durch, reicht aber nichts ein.")
    data["projects"] = projects

    # --- Secrets (nur Namen) ----------------------------------------------------------
    secrets = gh_json(["secret", "list", "--json", "name"], root, check=False)
    if secrets is None:
        warnings.append("Secret-Namen nicht lesbar (fehlende Berechtigung). `appSourceContext` von Hand prüfen.")
    else:
        names = [s["name"].lower() for s in secrets]
        if "appsourcecontext" not in names:
            hint = " `AZURE_CREDENTIALS` ist vorhanden, das Secret kann also im Azure Key Vault liegen." if "azure_credentials" in names else " Es kann auch als Organisations-Secret hinterlegt sein."
            warnings.append("Secret `appSourceContext` steht nicht in den Repo-Secrets." + hint)
        data["secretNames"] = sorted(s["name"] for s in secrets)

    # --- Stand des Branches, lokal und auf GitHub -------------------------------------
    b = gh_json(["api", f"repos/{nwo}/branches/{quote(branch, safe='')}"], root)
    head = b["commit"]["sha"]
    data["remoteHead"] = head
    local_head = run(["git", "rev-parse", "HEAD"], cwd=root, check=False)
    local_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, check=False)
    dirty = run(["git", "status", "--porcelain"], cwd=root, check=False)
    if dirty:
        warnings.append("Der lokale Arbeitsordner hat ungespeicherte Änderungen. Sie sind nicht Teil des Builds, der veröffentlicht wird.")
    if local_head and local_head != head:
        warnings.append(f"Lokaler Stand ({local_branch} @ {local_head[:7]}) weicht von `{branch}` auf GitHub ({head[:7]}) ab. Veröffentlicht wird der Stand auf GitHub.")
    rules = gh_json(["api", f"repos/{nwo}/rules/branches/{quote(branch, safe='')}"], root, check=False)
    protected = bool(rules) or bool(b.get("protected"))
    data["branchProtected"] = protected

    # --- Builds (CI/CD) ----------------------------------------------------------------
    cicd = find_workflow(root, "CICD")
    runs = gh_json(["run", "list", "--workflow", os.path.basename(cicd) if cicd else "CICD.yaml", "--branch", branch,
                    "--limit", "15", "--json", "databaseId,status,conclusion,headSha,createdAt,url"], root, check=False) or []
    active = [r for r in runs if r["status"] != "completed"]
    on_head = [r for r in runs if r["headSha"] == head]
    if not full:
        pass  # beim reinen Einreichen kommen die Dateien aus dem Release, nicht aus dem Build
    elif active:
        blockers.append(f"Auf `{branch}` läuft noch ein CI/CD-Build ({active[0]['url']}). Erst abwarten, sonst wird der vorherige Build veröffentlicht oder der Start scheitert.")
    elif on_head and on_head[0]["conclusion"] != "success":
        blockers.append(f"Der CI/CD-Build für den aktuellen Stand von `{branch}` ist `{on_head[0]['conclusion']}` ({on_head[0]['url']}).")
    for stem in EXPECTED:
        if wf[stem]["file"] and (full or stem == "PublishToAppSource"):
            busy = gh_json(["run", "list", "--workflow", wf[stem]["file"], "--limit", "5", "--json", "status,url"], root, check=False) or []
            busy = [r for r in busy if r["status"] != "completed"]
            if busy:
                blockers.append(f"`{wf[stem]['file']}` läuft gerade ({busy[0]['url']}). Erst das Ergebnis abwarten.")

    # --- Build-Artefakte: jüngstes Apps-Artefakt je Projekt ----------------------------
    wanted = {p["artifactProject"]: None for p in (deliver or projects)}
    for page in range(1, 6):
        res = gh_json(["api", f"repos/{nwo}/actions/artifacts?per_page=100&page={page}"], root)
        arts = res.get("artifacts", [])
        for art in arts:
            if art.get("expired"):
                continue
            for proj in wanted:
                if wanted[proj] is None:
                    m = re.match(rf"^{re.escape(proj)}-{re.escape(refname)}-Apps-(\d+\.\d+\.\d+\.\d+)$", art["name"])
                    if m:
                        wanted[proj] = {"name": art["name"], "version": m.group(1), "sha": art["workflow_run"]["head_sha"],
                                        "createdAt": art["created_at"], "expiresAt": art.get("expires_at")}
        if not arts or all(wanted.values()):
            break
    for p in projects:
        p["build"] = wanted.get(p["artifactProject"])
    for p in ((deliver or projects) if full else []):
        bld = p["build"]
        if not bld:
            blockers.append(f"Kein nicht abgelaufenes Apps-Artefakt für `{p['artifactProject']}` auf `{branch}`. Erst einen CI/CD-Build laufen lassen.")
        elif bld["sha"] != head:
            blockers.append(f"Der jüngste Build {bld['version']} gehört zu {bld['sha'][:7]}, `{branch}` steht aber bei {head[:7]}. „Create release“ bricht dann ab („branch has changed since the last successful build“). Erst den CI/CD-Build für den aktuellen Stand abwarten.")

    # --- Releases und Tags -------------------------------------------------------------
    releases = gh_json(["api", f"repos/{nwo}/releases?per_page=100"], root) or []
    tags = [t["name"] for t in (gh_json(["api", f"repos/{nwo}/tags?per_page=100"], root, check=False) or [])]
    rel = [{"tag": r["tag_name"], "name": r["name"], "draft": r["draft"], "prerelease": r["prerelease"],
            "publishedAt": r.get("published_at"), "assets": [x["name"] for x in r.get("assets", [])]} for r in releases]
    sortable = [r for r in rel if semver_key(r["tag"])]
    if len(sortable) != len(rel):
        warnings.append("Nicht alle Release-Tags sind SemVer. AL-Go sortiert dann nach GitHub-Reihenfolge; `appVersion=current` ist damit unzuverlässig.")
    sortable.sort(key=lambda r: semver_key(r["tag"]), reverse=True)
    # So wählt AL-Go (Deliver.ps1) das Release je appVersion-Schlüsselwort aus:
    pick = {"current": [r for r in sortable if not r["draft"] and not r["prerelease"]],
            "prerelease": [r for r in sortable if not r["draft"]],
            "draft": sortable}

    def apps_version(release):
        for asset in (release or {}).get("assets", []):
            m = re.search(r"-Apps-(\d+\.\d+\.\d+\.\d+)\.zip$", asset)
            if m:
                return m.group(1)
        return None

    def asset_name(artifact_project, version):
        # GitHub-Release-Assets: Leerzeichen werden zu Punkten, Sonderzeichen entfallen (wie in CreateRelease.yaml)
        return quote(f"{artifact_project}-{refname}-Apps-{version}.zip".replace(" ", "."), safe="").replace("%", "")

    last = pick["current"][0] if pick["current"] else None
    last_version = apps_version(last)
    data.update(releases=rel[:20], lastRelease=last, lastReleaseVersion=last_version)

    # --- Vorschlag ---------------------------------------------------------------------
    proposal = None
    lead = next((p for p in deliver if p.get("build")), None)
    if not full:
        target = pick[keyword][0] if pick[keyword] else None
        if not target:
            blockers.append(f"Kein Release gefunden, das `appVersion={keyword}` liefern würde. Erst „Create release“ ausführen.")
        else:
            tv = apps_version(target)
            for p in deliver:
                want = [x for x in target["assets"] if re.match(rf"^{re.escape(asset_name(p['artifactProject'], '0').rsplit('-Apps-', 1)[0])}-Apps-.+\.zip$", x)]
                if not want:
                    blockers.append(f"Release `{target['tag']}` hat kein Apps-Asset für `{p['artifactProject']}` auf `{branch}`. „Publish To AppSource“ findet dann nichts zum Einreichen.")
            if any("testapps" in x.lower() for x in target["assets"]):
                notes.append(f"Release `{target['tag']}` enthält noch ein TestApps-Asset. Für AppSource werden nur Apps und Dependencies geliefert; das Asset selbst sollte trotzdem nicht am Release hängen.")
            publish = {"appVersion": keyword,
                       "projects": "*" if len(projects) == 1 else ",".join(p["project"] for p in deliver),
                       "GoLive": "false"}
            proposal = {"ref": branch, "version": tv, "tag": target["tag"], "releaseName": target["name"],
                        "expectedAsset": next((x for x in target["assets"] if "-Apps-" in x), None),
                        "createRelease": {},
                        "publishToAppSource": {actual("PublishToAppSource", k): v for k, v in publish.items() if actual("PublishToAppSource", k)}}
    elif lead:
        version = lead["build"]["version"]
        versions = {p["build"]["version"] for p in deliver if p.get("build")}
        tag = ".".join(version.split(".")[:3])
        if last_version and vtuple(version) <= vtuple(last_version):
            blockers.append(f"Der jüngste Build ({version}) ist nicht neuer als das letzte Release `{last['tag']}` ({last_version}). Es gibt nichts Neues zu veröffentlichen, und Partner Center lehnt niedrigere Versionen ab.")
        if tag in tags or any(r["tag"] == tag for r in rel):
            blockers.append(f"Der Tag `{tag}` existiert schon (Build {version}). GitHub legt kein zweites Release mit demselben Tag an. Mit dem Anwender einen anderen Tag festlegen.")
        name = f"{lead['appName'] or repo_name} {version}"
        if last and last_version and last["name"] and last_version in last["name"]:
            name = last["name"].replace(last_version, version)
        elif last and last["name"] and last["tag"] in last["name"]:
            name = last["name"].replace(last["tag"], tag)
        highest = pick[keyword][0] if pick[keyword] else None
        is_highest = (highest is None) or (semver_key(tag) is not None and semver_key(tag) > semver_key(highest["tag"]))
        app_version = keyword
        if not is_highest:
            app_version = version
            notes.append(f"`{tag}` wäre nicht der höchste Release-Tag (höchster: `{highest['tag']}`). `appVersion={keyword}` würde das falsche Release liefern, deshalb steht im Vorschlag die genaue Build-Version (sie wird aus den Build-Artefakten geholt, solange diese nicht abgelaufen sind).")
        build_version = version if len(versions) == 1 else "latest"
        if len(versions) > 1:
            notes.append("Die Projekte haben unterschiedliche Build-Versionen, deshalb `buildVersion=latest`.")
        create = {"buildVersion": build_version, "name": name, "tag": tag, "releaseType": a.release_type,
                  "createReleaseBranch": "false", "updateVersionNumber": "", "skipUpdatingDependencies": "false",
                  "directCommit": "false", "useGhTokenWorkflow": "false"}
        publish = {"appVersion": app_version,
                   "projects": "*" if len(projects) == 1 else ",".join(p["project"] for p in deliver),
                   "GoLive": "false"}
        proposal = {
            "ref": branch, "version": version, "tag": tag, "commit": lead["build"]["sha"],
            "expectedAsset": asset_name(lead["artifactProject"], version),
            "createRelease": {actual("CreateRelease", k): v for k, v in create.items() if actual("CreateRelease", k)},
            "publishToAppSource": {actual("PublishToAppSource", k): v for k, v in publish.items() if actual("PublishToAppSource", k)},
        }
        if protected:
            notes.append(f"`{branch}` ist geschützt. `directCommit` bleibt `false`; eine Versionserhöhung (`updateVersionNumber`) kommt als Pull Request.")
        for p in deliver:
            if p.get("build") and p["appJsonVersion"] and p["build"]["version"].split(".")[:2] != p["appJsonVersion"].split(".")[:2]:
                notes.append(f"`{p['mainAppFolder']}/app.json` steht auf {p['appJsonVersion']}, der Build ist {p['build']['version']} (repoVersion {p['repoVersion'] or 'Standard'}).")
    data.update(proposal=proposal, blockers=blockers, warnings=warnings, notes=notes)

    # --- Report ------------------------------------------------------------------------
    L = [f"# Vorprüfung AppSource-Release — {nwo}" + ("" if full else " (nur einreichen)"), "",
         f"Geprüft am {data['checkedAt']} · Branch `{branch}` @ `{head[:7]}`", "",
         f"**Ergebnis: {'❌ nicht startklar' if blockers else '✅ startklar'}** ({len(blockers)} Blocker, {len(warnings)} Warnungen)", ""]
    if blockers:
        L += ["## Blocker", ""] + [f"- ❌ {x}" for x in blockers] + [""]
    if warnings:
        L += ["## Warnungen", ""] + [f"- ⚠️ {x}" for x in warnings] + [""]
    L += ["## Projekte", "", "| Projekt | App | productId | jüngster Build | Commit |", "|---|---|---|---|---|"]
    for p in projects:
        bld = p.get("build") or {}
        L.append(f"| `{p['project']}` | {p['appName'] or '?'} | {p['productId'] or '— (Library)'} | {bld.get('version', '—')} | {bld.get('sha', '')[:7] or '—'} |")
    L += ["", "## Letztes Release", ""]
    L.append(f"`{last['tag']}` „{last['name']}“ vom {last['publishedAt']} · App-Version {last_version or '?'} · Assets: {', '.join(last['assets']) or '—'}" if last else "Noch kein Release vorhanden.")
    L.append("")
    if proposal and not full:
        L += [f"## Einzureichendes Release", "",
              f"`{proposal['tag']}` „{proposal['releaseName']}“ · App-Version {proposal['version'] or '?'} · Asset `{proposal['expectedAsset']}`", "",
              f"## Vorschlag „Publish To AppSource“ (`{wf['PublishToAppSource']['file']}`, Branch `{branch}`)", "", "| Feld | Wert |", "|---|---|"]
        L += [f"| `{k}` | `{v}` |" for k, v in proposal["publishToAppSource"].items()]
        L.append("")
    elif proposal:
        L += [f"## Vorschlag „Create release“ (`{wf['CreateRelease']['file']}`, Branch `{branch}`)", "", "| Feld | Wert |", "|---|---|"]
        L += [f"| `{k}` | {('`' + v + '`') if v else '(leer)'} |" for k, v in proposal["createRelease"].items()]
        L += ["", f"Erwartetes Release-Asset: `{proposal['expectedAsset']}` · Commit `{proposal['commit'][:7]}`", "",
              f"## Vorschlag „Publish To AppSource“ (`{wf['PublishToAppSource']['file']}`, Branch `{branch}`)", "", "| Feld | Wert |", "|---|---|"]
        L += [f"| `{k}` | `{v}` |" for k, v in proposal["publishToAppSource"].items()]
        L.append("")
    if notes:
        L += ["## Hinweise", ""] + [f"- {x}" for x in notes] + [""]
    report = "\n".join(L)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(report)
    if a.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(a.json_out)), exist_ok=True)
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(report)
    return 1 if blockers else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckError as e:
        print(f"Vorprüfung gescheitert: {e}", file=sys.stderr)
        sys.exit(2)
    except FileNotFoundError as e:
        print(f"Vorprüfung gescheitert: {e} (ist `gh` installiert?)", file=sys.stderr)
        sys.exit(2)
