---
name: appsource-release
description: Erstellt in einem AL-Go-Repo über GitHub Actions ein Release („Create release“) und reicht genau diese App-Version mit „Publish To AppSource“ im Microsoft Marketplace (Partner Center) ein. Prüft vorher Build, Tag, Version und Secrets, schlägt alle Workflow-Parameter vor, holt die Freigabe ein, startet und überwacht beide Läufe. Immer verwenden, wenn eine neue App-Version veröffentlicht, getaggt, als Release angelegt oder bei AppSource/Marketplace eingereicht werden soll — "Release erstellen", "neue Version veröffentlichen", "Create release", "Publish To AppSource", "Einreichung starten", "Submission", "in den Marketplace hochladen", "Go Live". Nicht für die Launch-Checkliste (dafür /appsource-launch).
---

# /appsource-release — Release erstellen und bei AppSource einreichen

Zwei AL-Go-Workflows hintereinander: erst wird aus dem jüngsten CI/CD-Build ein GitHub-Release
mit Tag, danach wird genau diese App-Datei als neue Einreichung an Partner Center geliefert.
Beide Schritte wirken nach außen (öffentlicher Tag, Microsoft-Validierung) und lassen sich nicht
sauber zurücknehmen. Deshalb: erst prüfen, dann Parameter zeigen, dann Freigabe, dann starten.

| Schritt | Workflow | Datei | Wirkung |
|---|---|---|---|
| 1 | Create release | `CreateRelease.yaml` | Release + Git-Tag, App-Dateien als Release-Asset, optional Versionserhöhung und Release-Branch |
| 2 | Publish To AppSource | `PublishToAppSource.yaml` | Lädt die App nach Partner Center und startet eine neue Einreichung |

„Create a new app“ (`CreateApp.yaml`) gehört **nicht** hierher: der Workflow legt einen neuen
App-Ordner im Repo an und erzeugt keine Version. Meint der Anwender damit eine neue Version,
ist „Create release“ gemeint — kurz klarstellen und so fortfahren.

Workflows immer über den **Dateinamen** ansprechen. Die Anzeigenamen in AL-Go beginnen teils
mit einem Leerzeichen (`' Create release'`), darüber findet `gh` sie nicht zuverlässig.

## Aufruf

```
/appsource-release               # Vorprüfung, Freigabe, Create release, Publish To AppSource
/appsource-release check         # nur Vorprüfung und Parametervorschlag; startet nichts
/appsource-release publish       # nur einreichen: ein vorhandenes Release an AppSource liefern
/appsource-release --branch release/1.0   # von einem anderen Branch als dem Default-Branch (Hotfix)
```

Angaben im Auftrag („als Prerelease“, „Tag 1.1.0“, „mit Go Live“, „danach auf 1.1 erhöhen“)
gehen den Vorschlägen vor.

## Ablauf

### Schritt 1: Vorprüfung (liest nur)

```
python3 <skill-dir>/scripts/release-preflight.py --project . \
    --out .dev/appsource-release/preflight.md --json .dev/appsource-release/preflight.json
```

Optionen: `--mode publish` (nur einreichen), `--release-type Prerelease|Draft`, `--branch <b>`.
Exit-Code 0 = startklar, 1 = Blocker, 2 = Prüfung selbst gescheitert (meist `gh` nicht angemeldet).

Das Skript liest die Eingabefelder direkt aus den Workflow-Dateien, weil AL-Go seine
Systemdateien regelmäßig aktualisiert. Meldet es fehlende oder zusätzliche Felder, die
Workflow-Datei lesen und die Parameter daran ausrichten, nicht an der Tabelle unten.

Bei einem **Blocker** nichts starten und nichts umgehen. Befund melden und den Weg nennen:

- Build gehört nicht zum aktuellen Stand des Branches, oder CI/CD läuft noch: Lauf abwarten
  (`dispatch-workflow.py --run-id <id> --wait`) und die Vorprüfung wiederholen. Einen CI/CD-Build
  nur auf Wunsch des Anwenders starten (dauert etwa 30 Minuten).
- Build nicht neuer als das letzte Release: es gibt nichts zu veröffentlichen.
- Tag existiert schon: mit dem Anwender einen anderen Tag festlegen.
- Kein `deliverToAppSource.productId`: AL-Go würde grün durchlaufen und nichts einreichen.
  Erst die Produkt-ID eintragen (siehe /appsource-launch, Punkt C.4).

Bei `check`: Report zeigen, hier enden.

### Schritt 2: Parameter festlegen

Vorschläge aus `preflight.json` (`proposal`) übernehmen und nur fragen, was offen ist. Eine
AskUserQuestion-Runde, höchstens diese Punkte, und nur die, die der Auftrag nicht schon beantwortet:

1. Tag und Name wie vorgeschlagen?
2. Version im Branch nach dem Release erhöhen? (nein / `+0.1` / `+1`)
3. Nach bestandener Validierung automatisch live schalten? (nein / ja)

**Create release** (`CreateRelease.yaml`)

| Feld | Vorschlag | Bedeutung |
|---|---|---|
| `buildVersion` | genaue Build-Version, z. B. `1.0.2.1` | Welcher CI/CD-Build zum Release wird. Die genaue Version statt `latest`, damit zwischen Prüfung und Start kein anderer Build hineinrutscht. |
| `tag` | erste drei Stellen des Builds, z. B. `1.0.2` | Git-Tag. Muss SemVer sein und darf noch nicht existieren. |
| `name` | wie beim letzten Release, z. B. `cdmTicker 1.0.2.1` | Titel des Releases. |
| `releaseType` | `Release` | `Prerelease` oder `Draft` nur auf Wunsch; ändert `appVersion` in Schritt 5. |
| `createReleaseBranch` | `false` | `true` legt `release/<Version>` an, sinnvoll wenn Hotfixes auf dieser Version geplant sind. |
| `updateVersionNumber` | leer | `+0.1`, `+1` oder `Major.Minor`: erhöht die Version im Branch nach dem Release. Bei geschütztem Branch entsteht ein Pull Request. |
| `skipUpdatingDependencies` | `false` | Nur zusammen mit `updateVersionNumber` von Belang. |
| `directCommit` | `false` | `true` scheitert an einem geschützten Branch. |
| `useGhTokenWorkflow` | `false` | Nur wenn das Secret `ghTokenWorkflow` existiert. Nötig, um einen älteren als den neuesten Build zu veröffentlichen. |

**Publish To AppSource** (`PublishToAppSource.yaml`)

| Feld | Vorschlag | Bedeutung |
|---|---|---|
| `appVersion` | `current` | `current` = Release mit dem höchsten SemVer-Tag (ohne Prerelease und Draft), `prerelease` = höchstes inklusive Prerelease, `draft` = höchstes überhaupt, `latest` = jüngster CI/CD-Build ohne Release, Versionsnummer wie `1.0.2.1` = Build-Artefakt genau dieser Version. |
| `projects` | `*` | Nur in Repos mit mehreren AL-Go-Projekten einschränken. |
| `GoLive` | `false` | `false`: der Lauf endet, sobald die Einreichung angelegt ist; live geschaltet wird von Hand im Partner Center. `true`: der Lauf wartet auf die Validierung und schaltet automatisch live, kann also Stunden dauern. |

`current` trifft das neue Release nur, wenn dessen Tag der höchste ist. Die Vorprüfung rechnet
das nach und setzt sonst die genaue Build-Version ein (typisch bei einem Hotfix auf einer älteren
Linie). Diesen Vorschlag nicht auf `current` zurückändern.

### Schritt 3: Freigabe

Vor dem ersten Start beide Parametersätze zusammen zeigen (Tabelle: Feld, Wert) und dazu:

- Es entsteht ein Release mit Tag `<tag>` aus Commit `<sha>`, App-Version `<version>`.
- Diese Version wird bei Partner Center eingereicht (Produkt-ID `<productId>`).
- AL-Go reicht mit `-Force` ein: **eine noch laufende Einreichung dieses Angebots wird abgebrochen**
  und ersetzt. Das lässt sich aus dem Repo nicht sehen, also ausdrücklich nennen.
- Partner Center nimmt keine niedrigere Version an als die dort vorhandene.

Dann auf ein klares Ja warten. Ein Ja gilt für beide Starts, solange Schritt 4 genau das
bestätigt, was freigegeben wurde. Weicht etwas ab (anderer Commit, anderes Asset, ein Job rot),
erneut fragen. `GoLive=true` braucht in jedem Fall ein eigenes, ausdrückliches Ja in dieser
Sitzung: es veröffentlicht ohne weiteren Halt für alle Kunden.

Hat der Anwender Parameter und Start schon im Auftrag freigegeben, die Zusammenfassung trotzdem
zeigen und dann ohne Rückfrage starten.

### Schritt 4: Create release starten und prüfen

```
python3 <skill-dir>/scripts/dispatch-workflow.py --workflow CreateRelease.yaml --ref <branch> --wait \
    -f buildVersion=<version> -f "name=<name>" -f tag=<tag> -f releaseType=Release \
    -f createReleaseBranch=false -f directCommit=false -f useGhTokenWorkflow=false
```

Leere Felder (`updateVersionNumber` ohne Wert) weglassen statt leer übergeben. Das Skript
liefert Run-ID und URL und meldet am Ende das Ergebnis je Job (Exit 0 = alles grün). Der Lauf
dauert einige Minuten; wenn möglich im Hintergrund laufen lassen. Bricht das Warten ab,
**nicht erneut starten**, sondern mit `--run-id <id> --wait` weiter beobachten — ein zweiter
Start scheitert am vergebenen Tag oder legt ein zweites Release an.

Danach das Release gegen die Freigabe prüfen:

```
gh release view <tag> --json tagName,name,isDraft,isPrerelease,targetCommitish,assets,url
```

- `targetCommitish` ist der Commit aus der Vorprüfung.
- Das Asset `expectedAsset` aus `preflight.json` (`<Projekt>-<Branch>-Apps-<Version>.zip`) ist vorhanden.
  Fehlt es, findet Schritt 5 nichts zum Einreichen.
- Alle Jobs sind `success` oder `skipped` — auch Zusatzjobs des Repos wie „Test App Release Gate“.
  Ist einer rot, nicht einreichen: das Release ist dann nicht in dem Zustand, den das Repo verlangt.
- Mit `updateVersionNumber`: den entstandenen Pull Request (`increment-version-number/…`) nennen,
  aber nicht selbst mergen.

### Schritt 5: Publish To AppSource starten und prüfen

```
python3 <skill-dir>/scripts/dispatch-workflow.py --workflow PublishToAppSource.yaml --ref <branch> --wait \
    -f appVersion=current -f "projects=*" -f GoLive=false
```

Denselben Branch wie in Schritt 4 verwenden: die Artefaktnamen enthalten den Branch, auf einem
anderen findet der Workflow die Dateien nicht. Mit `GoLive=true` `--timeout 360` setzen.

Ein grüner Lauf allein beweist die Einreichung nicht (ohne Produkt-ID endet er grün und tut
nichts). Im Log nachsehen:

```
gh run view <run-id> --log | grep -E "ProductId|Main App File|Library App Files|_[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\.app|Submitting to AppSource|New AppSource submission"
```

Erwartet: die Produkt-ID, unter „Main App File“ die Datei mit der freigegebenen Version, und
„New AppSource submission created“ (bei `GoLive=true` „… succeeded“). Steht dort „project is a
library project“, wurde nichts eingereicht.

Bei `publish` als Argument: Schritt 4 entfällt; Vorprüfung mit `--mode publish`, Freigabe wie in
Schritt 3 mit der Version des vorhandenen Releases.

### Schritt 6: Protokoll und Meldung

`.dev/appsource-release/<tag>.md` anlegen (bei Wiederholung ergänzen): Datum, Repo, Branch, Commit,
Build-Version, Tag, Release-URL, beide Run-URLs, die tatsächlich übergebenen Parameter, Ergebnis,
offene Punkte.

Dem Anwender melden, was jetzt wahr ist, und was bei ihm liegt:

- Release-Link und eingereichte Version.
- Die Einreichung ist **gestartet, nicht bestanden**. Microsoft validiert im Hintergrund; der
  Stand steht im Partner Center beim Angebot. Mit `GoLive=false` muss dort nach der Validierung
  „Go live“ gedrückt werden.
- Offene Folgepunkte: Versions-PR mergen, Listing-Änderungen (lösen eine eigene, manuelle
  Prüfung aus und laufen nicht über diesen Workflow).

## Wenn ein Lauf scheitert

Fehlertext mit `gh run view <run-id> --log-failed` holen. Häufige Fälle:

| Meldung | Ursache | Weg |
|---|---|---|
| „branch has changed since the last successful build“ | Branch ist weiter als der Build | CI/CD für den aktuellen Stand abwarten, Vorprüfung wiederholen |
| „No artifacts found for this project“ | Build-Artefakte abgelaufen oder nie gebaut | CI/CD laufen lassen |
| HTTP 422 `already_exists` beim Anlegen des Releases | Tag oder Release existiert | Anderen Tag mit dem Anwender festlegen |
| „Unable to locate current release“ / „Artifact … was not found on any release“ | Kein passendes Release, oder das Apps-Asset fehlt | `releaseType` und `appVersion` abgleichen, Assets prüfen |
| „The new version number (x) is lower than the existing version number (y) in Partner Center“ | Version zu niedrig | Version erhöhen (`updateVersionNumber` oder Workflow „Increment Version Number“), neu bauen, neues Release |
| „An AppSource submission already running … substate=…“ | Einreichung in einem Zustand, den AL-Go nicht abbrechen kann | Im Partner Center klären, dann Schritt 5 wiederholen |
| „No product found with ProductID=…“ | Produkt-ID falsch, oder der Dienstprinzipal hat keinen Zugriff auf das Partner-Center-Konto | `deliverToAppSource.productId` und Secret `appSourceContext` prüfen |
| „appSourceContext secret is missing“ oder Anmeldefehler | Secret fehlt oder ist abgelaufen | Anwender erneuert das Secret; den Inhalt nie ausgeben oder anfordern |

Ist Schritt 4 gelungen und Schritt 5 gescheitert, bleibt das Release bestehen. Nach der Korrektur
nur Schritt 5 wiederholen (`/appsource-release publish`), kein zweites Release anlegen.

## Regeln

- Ohne Freigabe wird nichts gestartet; `check` startet nie etwas.
- Keine Releases oder Tags löschen, um einen Fehlversuch zu bereinigen, ohne den Anwender zu
  fragen. Ein gelöschter Tag kann schon von anderen geholt worden sein.
- Secrets nur dem Namen nach prüfen. Werte nie lesen, ausgeben oder in Dateien schreiben.
- Den Versions-PR und andere Pull Requests nicht selbst mergen.
- Kein Subagent nötig: der Ablauf besteht aus zwei Skriptaufrufen und einer Freigabe.
