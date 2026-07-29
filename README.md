# AI Usage Monitor

Ein kompaktes, lokales Dashboard für die persönlichen Nutzungskontingente von
ChatGPT und Claude. Die Anwendung läuft vollständig im Browser, speichert
Einstellungen nur im Local Storage und kennzeichnet simulierte sowie manuelle
Werte unmissverständlich.

## Machbarkeit und Datenlage

Stand: 29. Juli 2026.

OpenAI stellt eine offizielle
[Usage API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage)
für die Nutzung der API-Organisation bereit. Anthropic bietet analog einen
[Messages Usage Report](https://platform.claude.com/docs/en/api/admin/usage_report/retrieve_messages)
für API-Organisationen an. Beide Admin-Schnittstellen betreffen API-Verbrauch
und -Kosten. Sie stellen **nicht** das persönliche Restkontingent der
ChatGPT- bzw. Claude-Web-App bereit, das in den jeweiligen Usage-Einstellungen
angezeigt wird.

Deshalb enthält diese Version keine erfundene „Live Usage API“. Persönliche
Usage-Daten kommen wahlweise aus:

- klar gekennzeichneten Mock-Daten,
- manueller Eingabe oder
- einer lokal ausgewählten JSON-Datei.

Nur der allgemeine Dienststatus wird live über die öffentlichen, offiziellen
Statuspage-Endpunkte von
[OpenAI](https://status.openai.com/api/v2/status.json) und
[Claude](https://status.claude.com/api/v2/status.json) abgefragt. Scheitert
diese Abfrage durch Offlinebetrieb, Timeout oder CORS, bleibt das Dashboard
benutzbar und zeigt „Keine Daten“.

### Denkbare spätere Live-Anbindung

Eine Browser-Erweiterung oder ein Userscript könnte die vom Benutzer bereits
geöffnete und authentifizierte Usage-Seite auslesen und ausschließlich die
sichtbaren Prozent-/Reset-Werte an `localhost` übergeben. Das sollte mit
minimalen Host-Berechtigungen, expliziter Zustimmung und einem geprüften
Nachrichtenformat umgesetzt werden. Passwörter, Session-Cookies und Tokens
dürfen weder ausgelesen noch gespeichert werden. DOM-Scraping bleibt
wartungsintensiv, weil Änderungen an den Anbieter-Seiten den Adapter brechen
können.

## Architekturentscheidung

Für die aktuelle Version ist kein NestJS-Backend erforderlich:

- manuelle Werte und Einstellungen passen in den lokalen Browser-Speicher,
- der JSON-Import wird vollständig clientseitig verarbeitet,
- die öffentlichen Statusseiten benötigen keine geheimen Schlüssel,
- es gibt keine zentrale Datenbank oder geheime Serverkonfiguration.

Ein lokales Backend wäre erst sinnvoll, wenn später eine Erweiterung über eine
stabile localhost-Schnittstelle kommuniziert, verschlüsselte lokale Dateien
verwaltet werden oder CORS die Statusabfrage dauerhaft verhindert.

Die Vue-Komponenten kennen die Herkunft der Daten nicht. Pro Dienst wählt ein
Adapter einen `MockUsageProvider` oder `ManualUsageProvider` und ergänzt den
öffentlichen Status:

```text
Ansicht
  └─ useAIUsage
      ├─ ChatGPTUsageProvider
      │   ├─ MockUsageProvider | ManualUsageProvider
      │   └─ offizieller OpenAI-Dienststatus
      └─ ClaudeUsageProvider
          ├─ MockUsageProvider | ManualUsageProvider
          └─ offizieller Claude-Dienststatus
```

## Installation und Start

Voraussetzung: Node.js 22 oder neuer.

```bash
npm install
npm run dev
```

Danach ist das Dashboard unter
[http://localhost:5173](http://localhost:5173) erreichbar.

Produktions-Build und Typprüfung:

```bash
npm run typecheck
npm run build
npm run preview
```

Unter Windows PowerShell kann je nach Execution Policy `npm.cmd` statt `npm`
erforderlich sein:

```powershell
npm.cmd install
npm.cmd run dev
```

## Bedienung

Beim ersten Start sind Demo-Daten aktiv. Über das Zahnrad lassen sich:

- automatische Aktualisierung und Intervall einstellen,
- Mock-Daten deaktivieren,
- manuelle Werte für beide Dienste hinterlegen,
- einzelne Dienste ausblenden,
- die kompakte Ansicht aktivieren,
- JSON-Daten importieren und
- alle lokal gespeicherten Werte zurücksetzen.

Nach dem Deaktivieren der Mock-Daten erscheinen die manuellen Werte. Ohne
manuelle Eingabe zeigt der Dienst ausdrücklich „Keine Usage-Daten“.

### JSON-Import

Eine Beispieldatei liegt unter
[`public/examples/usage.json`](public/examples/usage.json). Das Schema:

```json
{
  "services": [
    {
      "id": "chatgpt",
      "plan": "Plus",
      "remainingPercentage": 40,
      "resetAt": "2026-07-29T21:30:00+02:00",
      "usageText": "Optionaler Hinweis"
    }
  ]
}
```

Der Import akzeptiert nur `chatgpt` und `claude`; Prozentwerte werden auf den
Bereich 0 bis 100 validiert. Importierte Werte gelten als **manuell**, nicht als
live.

## Datenkennzeichnung

| Badge | Bedeutung |
| --- | --- |
| `Demo` | simulierte Entwicklungsdaten |
| `Manuell` | Eingabe oder lokaler JSON-Import |
| `Erweiterung` | reserviert für eine spätere Browser-Erweiterung |
| `Live` | reserviert für eine künftig belegte offizielle Usage-Quelle |

Der daneben gezeigte Punkt „Online / Eingeschränkt / Störung“ beschreibt nur
den allgemeinen Dienststatus, nicht die Verfügbarkeit des persönlichen
Kontingents.

## Projektstruktur

```text
src/
├── assets/
│   └── main.css
├── components/
│   ├── DashboardHeader.vue
│   ├── ResetCountdown.vue
│   ├── ServiceCard.vue
│   ├── ServiceStatus.vue
│   └── UsageProgress.vue
├── composables/
│   ├── useAIUsage.ts
│   ├── useResetCountdown.ts
│   ├── useSettings.ts
│   └── useUsageRefresh.ts
├── services/
│   ├── chatgpt/ChatGPTUsageProvider.ts
│   ├── claude/ClaudeUsageProvider.ts
│   ├── manual/ManualUsageProvider.ts
│   ├── mock/MockUsageProvider.ts
│   ├── status/statusPageClient.ts
│   └── usage.types.ts
├── views/
│   ├── DashboardView.vue
│   └── SettingsView.vue
├── App.vue
└── main.ts
```

## Datenschutz und Sicherheit

- Keine eigenen externen Server.
- Keine API-Schlüssel, Logins, Passwörter oder Session-Cookies.
- Einstellungen liegen unter `ai-usage-monitor:settings` im Local Storage.
- Netzwerkzugriffe erfolgen nur zu den zwei offiziellen Statusseiten.
- Der Dokument-Sichtbarkeitsstatus pausiert Hintergrund-Polling bei
  inaktivem Tab.
