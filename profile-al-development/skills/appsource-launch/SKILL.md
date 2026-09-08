---
name: appsource-launch
description: Erzeugt und pflegt die AppSource-Launch-Checkliste (Marketing + Technik + Einreichung) für eine Business-Central-App. Prüft automatisch, was aus Repo und Website ableitbar ist, und legt Vorlagen für Listing-Texte und Zertifizierungsnotizen an. Verwenden bei "AppSource", "Marketplace", "Partner Center", "Listing", "Launch", "veröffentlichen".
---

# /appsource-launch — AppSource-Launch-Checkliste

Du bist Engineering Manager für den Launch einer Business-Central-App auf Microsoft AppSource.
Ziel ist ein Ordner `.dev/appsource-launch/` im Projekt mit einer **gefüllten, geprüften
Checkliste** und den Vorlagen, die der Anwender für das Partner Center braucht.

Die Checkliste stammt aus dem Launch der cdm "AI Requirements Bridge" (Juli/August 2026) und
den Microsoft-Marketing-Anforderungen (Marketing validation checklist, Offer listing, Listing
guidelines). Sie trennt **einmalige Publisher-Aufgaben** von **Aufgaben je App** und enthält
einen **Go-to-Market-Block** nach dem Go Live.

## Aufruf

```
/appsource-launch                 # Erstanlage oder Aktualisierung
/appsource-launch verify          # nur die automatischen Prüfungen ausführen
/appsource-launch --app "<Ordner>" # App-Ordner explizit angeben (Multi-App-Projekte)
```

## Ausgabe

```
.dev/appsource-launch/
├── checklist.md                 # gefüllte Checkliste, Status je Punkt
├── listing-texts.md             # Offer-Name, Summary, Description, Keywords, Screenshot-Plan
├── notes-for-certification.md   # Testanleitung für den Microsoft-Validator
└── verify-report.md             # Ergebnis der automatischen Prüfungen (bei jedem Lauf neu)
```

## Ablauf

### Schritt 1: Kontext einsammeln (kein Subagent nötig)

1. App-Ordner bestimmen: `$ARGUMENTS --app`, sonst `appFolders[0]` aus `.AL-Go/settings.json`,
   sonst der Ordner mit `app.json` und `idRanges` ≥ 50000.
2. Aus `app.json` lesen: `name`, `publisher`, `version`, `brief`, `description`, `help`,
   `EULA`, `privacyStatement`, `url`, `contextSensitiveHelpUrl`, `logo`,
   `applicationInsightsConnectionString`, `idRanges`, `resourceExposurePolicy`.
3. Aus `.AL-Go/settings.json` lesen: `deliverToAppSource`, `rulesetFile`,
   `appSourceCopMandatoryAffixes`. Aus `.github/AL-Go-Settings.json`: `trustedSigning`.
4. Falls `.dev/appsource-launch/checklist.md` bereits existiert: **Status-Häkchen übernehmen**,
   die der Anwender manuell gesetzt hat. Nie eine manuell gepflegte Checkliste überschreiben,
   ohne die Häkchen zu mergen.

### Schritt 2: Automatische Prüfungen

Skript ausführen (Python 3, nur Standardbibliothek, keine Abhängigkeiten):

```
python3 <skill-dir>/scripts/verify-readiness.py --project . [--app "<Ordner>"] --out .dev/appsource-launch/verify-report.md
```

Das Skript prüft u. a.: Pflichtfelder in app.json, Publisher-Schreibweise, Logo-Format
(PNG, 216–350 px quadratisch), AppSourceCop + Affix, Ruleset-Begründungen, Entitlements
mit echter Service-ID, Translations, `resourceExposurePolicy`, App-Insights-String,
`deliverToAppSource`, `trustedSigning`, Erreichbarkeit aller Links (https, kein 404),
ob die Datenschutzseite die App namentlich nennt, ob die Support-Seite mehr als zwei
Kontaktwege hat, Branding-Verstöße ("BC", "D365", "NAV") auf den Seiten, und Screenshots
unter `.dev/appsource-assets/screenshots/` (PNG 1280×720, mindestens 3).

Bei `verify` als Argument: Report ausgeben, Schritt 3–5 überspringen.

### Schritt 3: Fehlende Fakten beim Anwender erfragen

Genau **eine** AskUserQuestion-Runde mit den Punkten, die weder Repo noch Website liefern:

- Offer-ID und Produkt-ID (GUID) im Partner Center — falls noch kein Offer existiert: "noch nicht angelegt".
- Listing-Typ: Get it now (transactable) / Free trial / Contact me / Free.
- Plan(e) und Preismodell (pro Benutzer, monatlich/jährlich, Free Trial ja/nein).
- Zielmärkte und Sprachen.
- Primäre Kategorie und Industrie.
- Wer Leads im Partner Center (Referrals → Leads) bearbeitet, bzw. ob ein CRM angebunden ist.

### Schritt 4: Dateien erzeugen

1. `templates/checklist.md` laden, Platzhalter `{{…}}` mit den Werten aus Schritt 1 und 3 füllen.
2. Jeden Punkt, den `verify-report.md` als bestanden meldet, auf ✅ setzen; gescheiterte Punkte
   auf ❌ mit dem Befund aus dem Report; nicht prüfbare Punkte auf ⬜.
3. Manuell gesetzte Häkchen aus einer bestehenden Checkliste übernehmen (Schritt 1.4).
4. `templates/listing-texts.md` und `templates/notes-for-certification.md` nur anlegen, wenn
   sie noch nicht existieren (der Anwender schreibt dort hinein). Platzhalter füllen.

### Schritt 5: Zusammenfassung

Dem Anwender melden:
- Anzahl ✅ / ❌ / ⬜ je Teil (A Publisher, B Marketing, C Technik, D Einreichung, E Go-to-Market).
- Die **Blocker** (❌ in B–D) als Liste mit dem konkreten Befund.
- Die drei nächsten sinnvollen Schritte, Long-Lead-Punkte zuerst (Identity Validation,
  Marketing-Assets, Partner-Center-Offer).

## Regeln

- Keine Secrets in Dateien (Client Secrets, Connection Strings sind ok, da nicht geheim).
- Marketing-Änderungen lösen bei Microsoft eine **manuelle** Revalidierung aus. In der
  Zusammenfassung darauf hinweisen, wenn ein Hotfix ansteht.
- Das Preismodell eines Plans ist nach Veröffentlichung nicht änderbar. Vor der ersten
  Einreichung explizit bestätigen lassen.
- Ein AL-Interface ohne `Access`-Property ist nach der ersten Einreichung eingefrorene API.
  Der Punkt C.3 darf nie automatisch auf ✅ gesetzt werden; nur der Anwender bestätigt ihn.
