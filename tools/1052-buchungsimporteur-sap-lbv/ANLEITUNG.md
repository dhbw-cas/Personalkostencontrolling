# 📋 SAP LBV Buchungsimporteur - Benutzeranleitung

Eine einfache Anleitung zur Verwendung des SAP LBV Buchungsimporteurs für Benutzer ohne Programmiererfahrung.

## 🎯 Was macht das Programm?

Dieses Tool wandelt Excel-Dateien mit Buchungsdaten in das spezielle SAP LBV-Format um:
- **Eingabe**: Ihre Excel-Datei mit Buchungsdaten (z.B. Vergütungen, Besoldung)
- **Ausgabe**: SAP-konforme Excel-Datei für den Import ins System
- **Automatisch**: Jede Eingabezeile wird zu zwei SAP-Buchungszeilen (Haben/Soll)

## 🚀 Schnellstart

### Schritt 1: Programm öffnen
1. Öffnen Sie die **Eingabeaufforderung** (CMD) oder **PowerShell**
2. Navigieren Sie zum Projektordner:
   ```cmd
   cd "C:\Ihr\Pfad\zum\Projekt\1052 - Buchungsimporteur SAP LBV"
   ```

### Alternative: Streamlit-App starten
```cmd
uv run streamlit run streamlit_app.py
```

Oder direkt:
```cmd
uv run buchungsimporteur-app
```

In der App koennen Sie eine Excel-Datei hochladen, optional eine JSON-Konfiguration
auswaehlen und die Ausgabedatei direkt herunterladen.

### Schritt 2: Excel-Datei transformieren
```cmd
uv run buchungsimporteur transform "MeineQuelldatei.xlsx" "MeineZieldatei.xlsx"
```

**Beispiel:**
```cmd
uv run buchungsimporteur transform "Buchungen_Januar.xlsx" "SAP_Import_Januar.xlsx"
```

## 📁 Dateiformat-Anforderungen

### Ihre Eingabe-Excel muss folgende Spalten haben:
- **Spalte A**: Belegtyp (z.B. "Vergütung", "Besoldung")
- **Spalte B**: Betrag (z.B. "1500.00")
- **Spalte D**: Rechnungsdatum (korrigiert von C auf D)
- **Spalte F**: Referenz/Abrechnungsstelle 
- **Spalte G**: Verwendungszweck/Text

### Das Programm erstellt automatisch:
- ✅ Doppelte Buchungszeilen (Haben + Soll) für jeden Eintrag
- ✅ Korrekte SAP-Kontierung (Hauptbuch 440000/48500199)
- ✅ Fortlaufende Nummerierung und Gruppierung
- ✅ Alle 38 SAP-Spalten (A bis AL)

## 🔧 Erweiterte Nutzung

### Mit ausführlicher Ausgabe (zeigt Details an):
```cmd
uv run buchungsimporteur transform "quelldatei.xlsx" "zieldatei.xlsx" --verbose
```

### Datei vorab prüfen (ohne zu transformieren):
```cmd
uv run buchungsimporteur validate "quelldatei.xlsx"
```

### Hilfe anzeigen:
```cmd
uv run buchungsimporteur --help
```

## 📊 Beispiel-Transformation

**Eingabe (1 Zeile):**
| A (Position) | B (Betrag) | D (Rechnungsdatum) | F (Stelle) | G (Zweck) |
|--------------|------------|-------------------|------------|-----------|
| Vergütung    | 2500.00    | 01.01.2025        | LBV-KA     | Gehalt    |

**Ausgabe (2 Zeilen):**
| Belegnummer | Zeileart | Soll/Haben | Hauptbuch | Betrag | GrpId |
|-------------|----------|------------|-----------|--------|-------|
| Vergütung   | K        | H          | 440000    | 2500.00| 1     |
| Vergütung   | S        | S          | 48500199  | 2500.00| 1     |

## ⚠️ Häufige Probleme & Lösungen

### Problem: "Befehl nicht gefunden"
**Lösung:** Stellen Sie sicher, dass Sie im richtigen Projektverzeichnis sind:
```cmd
cd "Vollständiger\Pfad\zum\Projekt"
```

### Problem: "Datei nicht gefunden"
**Lösung:** Verwenden Sie vollständige Pfade oder stellen Sie sicher, dass die Datei existiert:
```cmd
uv run buchungsimporteur transform "C:\Meine Dateien\quelldatei.xlsx" "C:\Ausgabe\zieldatei.xlsx"
```

### Problem: Umlaute in Dateinamen
**Lösung:** Verwenden Sie Anführungszeichen um Dateinamen:
```cmd
uv run buchungsimporteur transform "Buchungen März.xlsx" "SAP Import März.xlsx"
```

### Problem: Spalten fehlen in der Eingabedatei
**Lösung:** Überprüfen Sie, ob Ihre Excel-Datei die benötigten Spalten A, B, D, F, G enthält.

## 📋 Checkliste vor der Nutzung

- [ ] Eingabedatei ist eine gültige Excel-Datei (.xlsx)
- [ ] Datei enthält Daten in den Spalten A, B, D, F, G
- [ ] Sie haben Schreibrechte im Zielordner
- [ ] Eingabeaufforderung ist im Projektverzeichnis geöffnet

## 💡 Tipps

1. **Backup erstellen**: Erstellen Sie immer eine Kopie Ihrer Originaldatei
2. **Testlauf**: Probieren Sie das Tool zuerst mit wenigen Testdaten
3. **Dateinamen**: Verwenden Sie aussagekräftige Namen für Ihre Ausgabedateien
4. **Überprüfung**: Kontrollieren Sie die Ausgabedatei vor dem SAP-Import

## 📞 Support

Bei Problemen oder Fragen wenden Sie sich an den Administrator oder überprüfen Sie:
- Sind alle Dateipfade korrekt?
- Ist die Eingabedatei im richtigen Format?
- Haben Sie die neueste Version des Tools?

---

**Viel Erfolg mit dem SAP LBV Buchungsimporteur!** 🎉
