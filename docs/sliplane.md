# Sliplane-Deployment

Der erste Slice verwendet eine disposable Entwicklungsdatenbank und
ausschließlich synthetische Daten.

## 1. Projekt und Server

1. In Sliplane ein Projekt für das Personalkostencontrolling anlegen.
2. Einen Server in der gewünschten Region erstellen.
3. Die PostgreSQL-Datenbank in derselben Region anlegen.

## 2. PostgreSQL

In Sliplane unter **Databases** eine Datenbank erstellen und nach dem
Provisioning ihre Connection URI verwenden.

Anforderungen:

- TLS bleibt mit `sslmode=verify-full` aktiviert.
- `sslrootcert=system` bleibt in der URI erhalten.
- Die URI wird niemals committed oder in Logs ausgegeben.
- Die Access-Control-Liste erlaubt nur die Entwickler-IP und die öffentliche
  Ausgangs-IP des Sliplane-Servers.
- `0.0.0.0/0` und `::/0` werden nicht dauerhaft freigeschaltet.

Die von Sliplane gelieferte `postgres://`-URI kann unverändert als
`DATABASE_URL` gesetzt werden. Die Anwendung normalisiert das Schema intern zu
`postgresql+psycopg://`.

## 3. Private Streamlit-App

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
| `DATABASE_URL` | Sliplane Connection URI, als Secret |

`railpack.json` führt vor jedem App-Start `alembic upgrade head` aus und startet
Streamlit anschließend auf `0.0.0.0:$PORT`.

Im Deploy-Log müssen nacheinander diese Vorgänge erkennbar sein:

```text
alembic upgrade head
python -m streamlit run streamlit_app.py ...
```

Ein fehlgeschlagenes Alembic-Upgrade verhindert damit den Start der neuen
Anwendungsversion.

## 4. Oeffentlicher Basic-Auth-Proxy

Die Streamlit-App bleibt privat. Der öffentliche Zugang erfolgt vorläufig über
den offiziellen Sliplane Basic-Auth-Proxy:

1. `sliplane/basic-auth-proxy` auf GitHub forken.
2. Den Fork als zweiten Service auf demselben Sliplane-Server deployen.
3. Nur den Proxy öffentlich exponieren.
4. Den Proxy-Healthcheck auf `/health` setzen.
5. Die folgenden Werte als Secrets beziehungsweise Umgebungsvariablen setzen.

```text
HTTP_BASIC_AUTH_USER=<Benutzername>
HTTP_BASIC_AUTH_PASSWORD=<starkes Passwort>
PRIVATE_WEBSITE_URL=<vollständige interne URL inklusive Protokoll und Port>
```

Die Zugangsdaten dürfen nicht in diesem Repository gespeichert werden.

## 5. Abnahme

Nach dem Deployment werden geprüft:

- App-Healthcheck `/_stcore/health` ist grün.
- Proxy-Healthcheck `/health` ist grün.
- Zugriff ohne Basic Auth wird abgewiesen.
- Anmeldung über den Proxy öffnet die Streamlit-App.
- Ein synthetisches 1049-ZIP kann gespeichert werden.
- Der Import erscheint im Datenbestand.
- Derselbe Upload wird beim zweiten Speicherversuch abgewiesen.
- In den Logs erscheinen keine Uploadinhalte, DataFrames oder Zugangsdaten.

Die Anwendung ist damit technisch erreichbar, aber noch nicht für echte
personenbezogene Daten freigegeben. Dafür folgen insbesondere
Anwendungs-Authentifizierung, Rollen, Aufbewahrungsregeln und eine fachliche
Datenschutzabnahme.
