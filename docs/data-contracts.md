# Datenvertraege

## 1049 LBV-PDF-Extraktor

Der Dashboard-Adapter akzeptiert ausschließlich ein nicht leeres
`pandas.DataFrame` mit diesen Spalten in dieser Reihenfolge:

| Spalte | Eingabe | Persistenz |
| --- | --- | --- |
| `Position` | Text, erforderlich | `TEXT NOT NULL` |
| `Betrag (€)` | Zahl mit maximal zwei Nachkommastellen | `NUMERIC(18, 2) NOT NULL` |
| `Standort` | Text oder leer | `TEXT NOT NULL` |
| `Datum des Anschreibens` | `TT.MM.JJJJ` oder leer | `DATE NULL` |
| `Quelldatei` | PDF-Basisname, erforderlich | `TEXT NOT NULL` |
| `Abrechnungsstelle` | Text oder leer | `TEXT NOT NULL` |
| `Verwendungszweck` | Text oder leer | `TEXT NOT NULL` |
| `Buchungsperiode` | Monatszahl 1 bis 12 oder leer | `SMALLINT NULL` |

`Buchungsperiode` enthält im aktuellen Tool kein Jahr. Ein Jahr wird weder
abgeleitet noch geraten.

Der aktuelle Extraktor erzeugt Beträge zunächst als `float`. Der Mapper wandelt
sie deshalb ausschließlich über `Decimal(str(value))` um und lehnt Werte mit
mehr als zwei Nachkommastellen ab.

## Dateiprovenienz

`import_files` beschreibt die hochgeladene ZIP-Datei:

- Originaldateiname
- SHA256 der unveränderten Uploadbytes
- Dateigröße in Bytes
- Quelltyp `lbv_1049`

Die ZIP- und PDF-Binärdaten werden nicht dauerhaft gespeichert. Der Name der
enthaltenen PDF bleibt je Position in `lbv_1049_rows.quelldatei` erhalten.

Eine eindeutige Constraint auf `(source_type, sha256)` verhindert parallele
Doppelimporte. `row_number` wird nach der finalen DataFrame-Reihenfolge neu und
fortlaufend ab 1 vergeben.

## Offene Datenvertraege

1067 und 1052 werden erst in späteren Migrationen modelliert. Für 1052 gilt
bereits als überprüfte Randbedingung:

- Das SAP-Template besitzt 38 Zielspalten.
- Das rohe `target_df` entspricht nicht den finalen Workbook-Zeilen.
- Persistiert werden müssen später die vorbereiteten Output-DataFrames je
  Tabellenblatt.
