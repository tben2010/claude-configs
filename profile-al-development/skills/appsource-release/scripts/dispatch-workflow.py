#!/usr/bin/env python3
"""Startet einen GitHub-Actions-Workflow per workflow_dispatch und liefert die Run-ID.

`gh workflow run` gibt je nach gh-Version keine Run-ID zurück. Dieses Skript merkt sich
die Läufe vor dem Start, startet, und sucht danach den neuen Lauf. Mit --wait wartet es
auf das Ende und meldet das Ergebnis je Job.

Beispiel:
  dispatch-workflow.py --workflow CreateRelease.yaml --ref main --wait \
      -f tag=1.0.2 -f "name=cdmTicker 1.0.2.1" -f releaseType=Release

  dispatch-workflow.py --run-id 123456789 --wait      # nur auf einen laufenden Lauf warten

Ausgabe: eine JSON-Zeile je Ereignis (dispatched, waiting, completed).
Exit-Code 0 = gestartet bzw. erfolgreich beendet, 1 = Lauf gescheitert, 2 = Start gescheitert,
3 = Zeitlimit beim Warten erreicht (der Lauf läuft weiter).
"""
import argparse, json, re, subprocess, sys, time


def gh(args, cwd, check=True):
    p = subprocess.run(["gh"] + args, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[:500])
    return (p.stdout or "") + (p.stderr or "")


def runs(workflow, cwd):
    out = subprocess.run(["gh", "run", "list", "--workflow", workflow, "--limit", "20",
                          "--json", "databaseId,status,url,event,createdAt"], cwd=cwd, capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else []


def emit(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="Wurzel des Repos (Standard: aktueller Ordner)")
    ap.add_argument("--workflow", help="Dateiname des Workflows, z. B. CreateRelease.yaml")
    ap.add_argument("--ref", help="Branch, auf dem der Workflow startet")
    ap.add_argument("-f", "--field", action="append", default=[], metavar="feld=wert", help="Eingabefeld, mehrfach möglich")
    ap.add_argument("--run-id", help="Nichts starten, nur diesen Lauf beobachten")
    ap.add_argument("--wait", action="store_true", help="Auf das Ende des Laufs warten")
    ap.add_argument("--timeout", type=int, default=45, help="Höchste Wartezeit in Minuten (Standard 45)")
    ap.add_argument("--interval", type=int, default=20, help="Abfrageabstand in Sekunden (Standard 20)")
    a = ap.parse_args()

    run_id, url = a.run_id, None
    if not run_id:
        if not a.workflow or not a.ref:
            ap.error("--workflow und --ref sind nötig, wenn kein --run-id angegeben ist")
        for f in a.field:
            if "=" not in f:
                ap.error(f"Feld ohne '=': {f}")
        before = {r["databaseId"] for r in runs(a.workflow, a.project)}
        cmd = ["workflow", "run", a.workflow, "--ref", a.ref]
        for f in a.field:
            cmd += ["-f", f]
        try:
            out = gh(cmd, a.project)
        except RuntimeError as e:
            emit(event="error", message=f"Start gescheitert: {e}")
            return 2
        m = re.search(r"/actions/runs/(\d+)", out)
        if m:
            run_id = m.group(1)
        else:
            for _ in range(20):  # bis zu 60 s, GitHub legt den Lauf mit Verzögerung an
                time.sleep(3)
                new = [r for r in runs(a.workflow, a.project) if r["databaseId"] not in before and r["event"] == "workflow_dispatch"]
                if new:
                    run_id = str(max(r["databaseId"] for r in new))
                    break
        if not run_id:
            emit(event="error", message="Workflow gestartet, aber der neue Lauf wurde nicht gefunden. Mit `gh run list --workflow " + a.workflow + "` nachsehen; nicht erneut starten.")
            return 2
        info = json.loads(gh(["run", "view", str(run_id), "--json", "url,status"], a.project))
        url = info["url"]
        emit(event="dispatched", runId=int(run_id), url=url, workflow=a.workflow, ref=a.ref, fields=a.field)

    if not a.wait:
        return 0

    deadline = time.time() + a.timeout * 60
    last = None
    while True:
        try:
            info = json.loads(gh(["run", "view", str(run_id), "--json", "status,conclusion,url,jobs"], a.project))
        except (RuntimeError, json.JSONDecodeError):
            info = None  # kurzer Aussetzer der API: weiter warten
        if info:
            jobs = [{"name": j["name"], "status": j["status"], "conclusion": j.get("conclusion") or ""} for j in info.get("jobs", [])]
            if info["status"] == "completed":
                emit(event="completed", runId=int(run_id), url=info["url"], conclusion=info["conclusion"], jobs=jobs)
                failed = [j["name"] for j in jobs if j["conclusion"] not in ("success", "skipped", "neutral")]
                return 0 if info["conclusion"] == "success" and not failed else 1
            state = ", ".join(f"{j['name']}={j['conclusion'] or j['status']}" for j in jobs)
            if state != last:
                emit(event="waiting", runId=int(run_id), jobs=state)
                last = state
        if time.time() > deadline:
            emit(event="timeout", runId=int(run_id), message=f"Nach {a.timeout} Minuten noch nicht fertig. Der Lauf läuft weiter; mit --run-id {run_id} --wait weiter beobachten.")
            return 3
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
