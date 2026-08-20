# Sliplane-Deployment

Der erste Slice verwendet ausschließlich synthetische Daten. PostgreSQL läuft
als privater Service auf demselben Sliplane-Server wie die Anwendung. Für diesen
disposable Entwicklungsstand entstehen dadurch keine zusätzlichen Kosten für
eine Managed Database.

## 1. Projekt und Server

1. In Sliplane das Projekt `Personalkostencontrolling` anlegen.
2. Einen Server namens `personalkosten-dev` in Deutschland erstellen.
3. PostgreSQL, Streamlit und den Basic-Auth-Proxy auf diesem Server betreiben.

Die Ressourcenmetriken des Servers müssen beobachtet werden. PDF-Verarbeitung,
Streamlit und PostgreSQL teilen sich CPU und Arbeitsspeicher.

## 2. Privater PostgreSQL-Service

Im Projekt einen weiteren Service anlegen:

| Einstellung | Wert |
| --- | --- |
| Deploy Source | vorkonfiguriertes PostgreSQL oder Registry |
| Image bei Registry | `docker.io/library/postgres:18.6` |
| Service Name | `personalkosten-postgres` |
| Expose Service | aus |
| Volume | `/var/lib/postgresql` |

Umgebungsvariablen des PostgreSQL-Service:

```text
POSTGRES_DB=personalkosten_dev
POSTGRES_USER=personalkosten
POSTGRES_PASSWORD=<starkes zufälliges Passwort>
```

`POSTGRES_PASSWORD` wird in Sliplane als Secret markiert. Der Service darf nicht
öffentlich exponiert werden. PostgreSQL 18 verwendet standardmäßig das
versionsspezifische `PGDATA` `/var/lib/postgresql/18/docker`; deshalb wird das
übergeordnete Verzeichnis `/var/lib/postgresql` eingebunden. Das Volume ersetzt
kein Backup.

Für Slice 1 ist Datenverlust akzeptiert, weil ausschließlich synthetische Daten
verwendet werden. Vor einer Freigabe für echte Daten ist auf Sliplane Managed
PostgreSQL mit Point-in-Time-Recovery zu wechseln oder ein geprüftes separates
Backup- und Restore-Konzept umzusetzen.

## 3. Interne Datenbankverbindung

Nach dem Start zeigt Sliplane in den Service-Einstellungen den internen Hostnamen
des PostgreSQL-Service an. Dieser Hostname wird in der privaten Streamlit-App
verwendet, niemals `localhost` und niemals eine öffentliche IP.

`DATABASE_URL` der Streamlit-App:

```text
postgresql+psycopg://personalkosten:<URL-kodiertes Passwort>@<interner Host>:5432/personalkosten_dev
```

Die vollständige URI wird als Sliplane Secret gespeichert und weder committed
noch in Logs ausgegeben. Sonderzeichen im Passwort müssen URL-kodiert sein.
Innerhalb des privaten Sliplane-Netzes ist kein öffentlicher Datenbankport und
keine externe TLS-Verbindung erforderlich.

## 4. Private Streamlit-App

Die Anwendung wird aus
`dhbw-cas/Personalkostencontrolling`, Branch `main`, deployt.

Service-Einstellungen:

| Einstellung | Wert |
| --- | --- |
| Deploy Source | GitHub |
| Build | Railpack |
| Expose Service | aus |
| Healthcheck | `/_stcore/health` |
| CMD Override | leer |
| `DATABASE_URL` | interne PostgreSQL-URI, als Secret |

`railpack.json` führt vor jedem App-Start `alembic upgrade head` aus und startet
Streamlit anschließend auf `0.0.0.0:$PORT`.

Im Deploy-Log müssen nacheinander diese Vorgänge erkennbar sein:

```text
alembic upgrade head
python -m streamlit run streamlit_app.py ...
```

Ein fehlgeschlagenes Alembic-Upgrade verhindert den Start der neuen
Anwendungsversion.

## 5. Oeffentlicher Basic-Auth-Proxy

Die Streamlit-App bleibt privat. Der öffentliche Zugang erfolgt vorläufig über
den offiziellen Sliplane Basic-Auth-Proxy:

1. `sliplane/basic-auth-proxy` auf GitHub forken.
2. Den Fork als dritten Service auf demselben Sliplane-Server deployen. Für
   dieses Projekt wird `convertedfox/basic-auth-proxy` verwendet.
3. Nur den Proxy als öffentlichen HTTP-Service auf Port 8080 exponieren.
4. Den Proxy-Healthcheck auf `/health` setzen.
5. Kein Volume hinzufügen.
6. Die folgenden Werte als Secrets beziehungsweise Umgebungsvariablen setzen.

```text
HTTP_BASIC_AUTH_USER=<Benutzername>
HTTP_BASIC_AUTH_PASSWORD=<starkes Passwort>
PRIVATE_WEBSITE_URL=<vollständige interne URL inklusive Protokoll und Port>
```

Die Zugangsdaten dürfen nicht in diesem Repository gespeichert werden.

## 6. Abnahme

Nach dem Deployment werden geprüft:

- PostgreSQL ist ausschließlich intern erreichbar.
- Das Volume ist unter `/var/lib/postgresql` eingebunden.
- Alembic legt die drei Tabellen des ersten Slices an.
- App-Healthcheck `/_stcore/health` ist grün.
- Proxy-Healthcheck `/health` ist grün.
- Zugriff ohne Basic Auth wird abgewiesen.
- Anmeldung über den Proxy öffnet die Streamlit-App.
- Ein synthetisches 1049-ZIP kann gespeichert werden.
- Der Import erscheint im Datenbestand.
- Derselbe Upload wird beim zweiten Speicherversuch abgewiesen.
- In den Logs erscheinen keine Uploadinhalte, DataFrames oder Zugangsdaten.

Die Anwendung ist damit technisch erreichbar, aber noch nicht für echte
personenbezogene Daten freigegeben. Dafür folgen insbesondere Managed
PostgreSQL oder ein belastbares Backupkonzept, Anwendungs-Authentifizierung,
Rollen, Aufbewahrungsregeln und eine fachliche Datenschutzabnahme.
