# AppSource-Launch-Checkliste — {{APP_NAME}}

Publisher: **{{PUBLISHER}}** · Version: {{VERSION}} · Offer: `{{OFFER_ID}}` · Produkt-ID: `{{PRODUCT_ID}}`
Listing-Typ: {{LISTING_TYPE}} · Plan/Preis: {{PLAN_PRICING}} · Märkte: {{MARKETS}} · Sprachen: {{LANGUAGES}}
Erzeugt von `/appsource-launch` am {{DATE}}. Automatische Prüfung: `verify-report.md`.

Legende: ✅ erledigt/geprüft · ❌ Prüfung fehlgeschlagen (Befund im Report) · ⬜ offen/manuell · 🔁 bei jedem Release

Quellen: Marketing validation checklist (BC), Offer listing (BC), Listing guidelines, Sell BC apps through Marketplace —
alle unter https://learn.microsoft.com (Suchbegriffe siehe Skill-Doku).

---

## A. Einmalig je Publisher

### A.1 Konto und Firmierung
- ⬜ Partner-Center-Konto mit Marketplace-Programm, Publisher-Vereinbarung akzeptiert.
- ⬜ Affix bei Microsoft registriert: `{{AFFIX}}`.
- ⬜ Publisher-Anzeigename im Partner Center zeichengleich zu app.json: `{{PUBLISHER}}`.
- ⬜ Billing-Profil (Azure), Handelsregister und Impressum mit identischer Firmierung und Adresse.
- ⬜ Payout- und Steuerprofil (W-8, Bankverbindung, Auszahlungswährung) — nur für transactable Angebote. Validierung bis 48 h.
- ⬜ Mindestens zwei Owner auf dem Publisher-Konto.

### A.2 Signing und Automatisierung
- ⬜ Azure Artifact Signing: Account, Identity Validation (Long-Lead: 1–20 Werktage, Ausweisprüfung), Certificate Profile.
- ⬜ Service Principal für Signing + GitHub-Secret `AZURE_CREDENTIALS`.
- ⬜ Entra-App für die Partner-Center-API, im Partner Center als **Manager** zugeordnet, GitHub-Secret `AppSourceContext`.
- ⬜ Ablaufdaten der Client-Secrets im Kalender (Standard 24 Monate).

### A.3 Website-Grundgerüst
- ⬜ URL-Struktur für App-Seiten (Landingpage, Help, EULA), zentrale Datenschutzerklärung.
- ⬜ Datenschutzerklärung beschreibt AppSource-Apps und deren externe Dienste (KI-Anbieter, Telemetrie).

---

## B. Je App — Marketing und Listing (Partner Center)

> Marketing-Validierung ist manuell und läuft nur bei neuen oder geänderten Listing-Daten. Für Hotfixes keine Marketing-Änderungen mitschicken.

### B.1 Positionierung und Geschäftsmodell
- ⬜ Zielgruppe und Nutzenversprechen in zwei Sätzen (Basis für Summary, Description, Screenshots, Video).
- ⬜ Listing-Typ festgelegt: {{LISTING_TYPE}}.
- ⬜ Plan(e) und Preis: {{PLAN_PRICING}}. Pro Benutzer, monatlich/jährlich, optional Min/Max-Benutzer, optional Free Trial (1 Monat). **Nach Veröffentlichung nicht änderbar.**
- ⬜ Märkte ({{MARKETS}}) und Sprachen ({{LANGUAGES}}) — müssen zum Absatz „Supported countries/languages" in der Description passen.
- ⬜ Kategorien (1 primär, 1 sekundär, je ≤ 2 Subkategorien) und Industrien (≤ 2): {{CATEGORY}}.
- ⬜ Leads: landen immer im Partner Center unter Referrals → Leads, aber ohne Benachrichtigung. Zuständig: {{LEAD_OWNER}}. Optional CRM/HTTPS-Endpunkt anbinden.

### B.2 Texte (→ `listing-texts.md`)
- ⬜ Offer-Name (≤ 200 Zeichen, keine Emojis), identisch zur Website.
- ⬜ Search results summary (≤ 100 Zeichen, ein Satz, Suchbegriffe enthalten).
- ⬜ Description (≤ 5.000 Zeichen, HTML): 2–3 Absätze, Nutzen zuerst, Zielgruppe, Bullets, dann **Supported editions / countries / languages** auf Englisch. Bis 3 Sprachen mit identischem Inhalt.
- ⬜ 3 Search keywords, „Products your app works with".
- ⬜ Branding: Erstnennung „Microsoft Dynamics 365 Business Central", dann „Dynamics 365 Business Central", dann „Business Central". Nie „BC", „D365", „NAV". Keine Microsoft-Logos in eigenen Bildern.
- ⬜ Offenlegungen in der Description: KI-Nutzung, externe Dienste, Lizenzvoraussetzungen.

### B.3 Medien
- ⬜ Logo PNG 216–350 px quadratisch, flach, ohne Text, Hintergrund nicht weiß/schwarz/blau. (`{{LOGO_PATH}}`)
- ⬜ Mindestens 3, max. 5 Screenshots PNG 1280 × 720 mit Caption, lesbar, Demodaten ohne Kundenbezug. Ablage: `.dev/appsource-assets/screenshots/`.
- ⬜ Optional bis 4 Videos (YouTube/Vimeo, Thumbnail 1280 × 720, ≥ 3 Min., englische Untertitel bei nicht-englischem Ton, keine Wettbewerber).
- ⬜ Optional bis 3 PDF-Dokumente (Broschüre, Whitepaper, Präsentation).

### B.4 Pflicht-Links und Seiten
- ⬜ Help-Link: Doku, Erste Schritte, FAQ. `{{HELP_URL}}`
- ⬜ Support-Link: > 2 Kontaktwege, ohne Login, Antwortzeit genannt. Darf Sektion der Hilfeseite sein.
- ⬜ Privacy-Link nennt die App namentlich. `{{PRIVACY_URL}}`
- ⬜ EULA/Terms. `{{EULA_URL}}`
- ⬜ Landingpage mit Call-to-Action „Get it from Microsoft AppSource". `{{LANDING_URL}}`
- ⬜ Alle Links https, kein 404, identisch in app.json und Partner Center.

### B.5 Kontakte und Validierungshilfen
- ⬜ Support-Kontakt und Engineering-Kontakt im Partner Center (Telefon nur Ziffern/Leerzeichen).
- ⬜ Notes for certification (→ `notes-for-certification.md`): Setup-Schritte, Demodaten, Testkonto, wie externe Dienste ohne eigenen Key getestet werden.
- ⬜ Preview audience / Hide key gesetzt, Listing vor Go Live selbst geprüft.
- ⬜ Optional Publisher Attestation (Microsoft 365 App Compliance).

---

## C. Je App — Technische Vorbereitung

### C.1 Analyzer und Manifest
- ⬜ AppSourceCop mit `mandatoryAffixes: ["{{AFFIX}}"]`; Test-App ausgenommen. Build diagnosefrei; akzeptierte Diagnosen nur mit Begründung im Ruleset.
- ⬜ Aktuelle Plattform/Application und Runtime.
- ⬜ app.json: `publisher` zeichengleich zum Partner Center; `brief`, `description`, Links; `logo`; eigene App-Insights-Ressource; `resourceExposurePolicy` alles false; registrierter `idRanges`-Bereich ({{ID_RANGE}}).

### C.2 Lizenzierung und Pflicht-Features
- ⬜ Entitlements (Plan / Unlicensed / Internal) mit der echten Service-ID des Plans (`<publisher-tenant>.<offer>.<plan>`).
- ⬜ Lizenz-Guard auf allen schreibenden Prozeduren und Page-Aktionen; Permission-Sets vollständig.
- ⬜ Assisted Setup + Checklist; Retention Policy für Log-Tabellen; Copilot-Capability in Install und Upgrade (falls KI); Learn-More-URL auf die Hilfeseite.
- ⬜ Übersetzungen (mind. en-US), Source-Texte Englisch.
- ⬜ DataClassification auf allen Feldern (AS0016).

### C.3 Vor dem API-Freeze (nur manuell bestätigen)
- ⬜ Projekt-Review; alle „vor Submission fixen"-Punkte geschlossen.
- ⬜ Alles nur intern Genutzte auf `Access = Internal`. Ein Interface ohne `Access` ist nach der ersten Einreichung eingefrorene API (AS0026/AS0066).
- ⬜ Generalprobe der Kundenpfade in der Cloud-Sandbox (AppSource-Range nur via VS-Code-Dev-Publish, PTE0001).

### C.4 AL-Go-Anbindung
- ⬜ `deliverToAppSource` mit `productId`, `mainAppFolder`, `continuousDelivery: false`. `includeDependencies` nur bewusst setzen.
- ⬜ `trustedSigning`-Block vorhanden; CI-Guards in PR-Handler, CICD, CreateRelease.

---

## D. Einreichen und Go Live

- ⬜ Marketing-Teile (B) vollständig vor der ersten Einreichung; werden zusammen mit der Technik validiert.
- 🔁 Create Release → Publish To AppSource manuell von `main` (vom Release-Branch: „unable to locate apps folder").
- 🔁 Fehlerbilder: `unauthorized_client` → Partner-Center-Zuordnung der Entra-App; „submission already running … substate=Submitted" → nur eine Submission gleichzeitig.
- 🔁 Validierungsergebnisse im Partner Center und in Application Insights (Submission-Trace) lesen.
- 🔁 Listing mit Hide Key als Preview prüfen.
- 🔁 Go Live manuell im Partner Center (Button startet die Validierungs-Queue).
- ⬜ Nach Go Live: AppSource-URL notieren und auf Website, Landingpage, Signaturen verlinken.

---

## E. Nach dem Launch — Vermarktung und Betrieb

### E.1 Sofort nach Go Live
- ⬜ „Get it from Microsoft AppSource"-Badge auf Landingpage und Website.
- ⬜ Launch-Kommunikation: Blog/News, LinkedIn (Firma + persönlich), Newsletter an Kunden und Partner, optional Presse.
- ⬜ Demo-Video veröffentlichen und ins Listing nachtragen (nach Go Live, wegen Revalidierung).
- ⬜ Preisliste/Angebotsvorlage für Direktvertrieb und Partner.

### E.2 Programme und Reichweite
- ⬜ ISV Success / Marketplace Rewards im Partner Center aktivieren.
- ⬜ Co-sell-ready (Solution-Beschreibung, Referenzen, Bill of Materials).
- ⬜ Reseller/Partner: Private Pläne oder Multiparty Private Offers.
- ⬜ Events: Directions EMEA, Days of Knowledge, BC TechDays, lokale Usergroups.
- ⬜ Referenzkunde → Case Study (auch als PDF ins Listing).

### E.3 Laufender Betrieb
- 🔁 Bewertungen und Reviews auf AppSource beobachten und beantworten.
- 🔁 Leads im Partner Center (Referrals → Leads) wöchentlich abarbeiten oder automatisch weiterleiten.
- 🔁 Telemetrie (Application Insights) auswerten: Installationen, Fehler, Feature-Nutzung.
- 🔁 Listing bei größeren Releases aktualisieren — getrennt von Hotfix-Releases.
- 🔁 Hilfe/FAQ aus Support-Fällen pflegen; Support-Antwortzeiten einhalten.
- 🔁 Jährlich Preise, Märkte, Kategorien und Wettbewerb prüfen.
- 🔁 Baseline-Regel: öffentliche Signaturen nur über `ObsoleteState = Pending` + neues internes Interface ändern.
