import io
import os
import pdfplumber
import re
import pandas as pd
from datetime import datetime

FOLDER_PATH = ".data/12_2025"  # Ordner mit PDFs, kann angepasst werden
EXPORT_PATH = ".data/export"  # Ordner, wohin die fertigen Exporte gespeichert werden
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # timestamp für Dateinamen
filename = f"PDF_Extract_{timestamp}.xlsx"

# Katalog der Standorte mit präzisen Adressen
STANDORTE = {
    "Florianstr. 15": "Horb am Neckar",
    "Coblitzallee 1-9": "Mannheim",
    "Erzbergstr. 121": "Karlsruhe",
    "Lohrtalweg 14": "Mosbach",
    "Schloß 2": "Bad Mergentheim",
    "Hangstr. 46-50": "Lörrach",
    "Friedrichstr. 14": "Stuttgart (Präsidium)",
    "Herdweg 21": "Stuttgart (DHBW)",
    "Friedrich-Ebert-Str. 30": "Villingen-Schwenningen",
    "Marienstr. 20": "Heidenheim",
    "Marienplatz 2": "Ravensburg",
    "Fallenbrunnen 2": "Friedrichshafen",
    "Bildungscampus 4": "Heilbronn (DHBW)",
    "Bildungscampus 23": "Heilbronn (CAS)",
}


def _extract_periods_from_filename(filename: str):
    """
    Extrahiert A- und B-Monat aus Dateinamen wie:
    - 7002 10-2025A+11-2025B .pdf
    - 7002_10-2025A+11-2025B__.pdf
    """
    # Suche robust nach "...MM-YYYYA+MM-YYYYB..." unabhängig von Trennzeichen
    match = re.search(r"(\d{2})-\d{4}\s*A\s*\+\s*(\d{2})-\d{4}\s*B", filename)
    if not match:
        return None, None

    try:
        month_a = int(match.group(1))
        month_b = int(match.group(2))
        return month_a, month_b
    except ValueError:
        return None, None


def extract_data(pdf_path):
    """
    Öffnet deine einzelne PDF, extrahiert das Datum des Anschreibens und die Tabelleneinträge,
    und gibt ein pandas DataFrame mit den Spalten Position, Datum des Anschreibens, Betrag zurück.
    """
    try:
        # PDF einlesen
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            print(f"\n=== Verarbeite: {os.path.basename(pdf_path)} ===")

        # Datum des Anschreibens extrahieren (z.B. '05.09.2024')
        date_match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
        if not date_match:
            print(f"Warnung: Datum des Anschreibens nicht gefunden in {pdf_path}")
            letter_date = None
        else:
            letter_date = date_match.group(1)
            print(f"Datum gefunden: {letter_date}")

        # VERBESSERTE Tabelleneinträge-Extraktion
        # Wichtig: Nur Beträge mit LEERZEICHEN vor dem € sind Tabellenwerte!
        # Pattern sucht nach: Position + Betrag mit Leerzeichen + € am Zeilenende
        pattern_tabelle = r"^(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+€\s*$"

        rows = []

        # Verarbeite Zeilen einzeln
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Suche nach Tabelleneinträgen
            match = re.search(pattern_tabelle, line, re.MULTILINE)
            if match:
                position = match.group(1).strip()
                # Bereinige Fußnoten (z.B. "1)")
                position = re.sub(r"\s*\d+\)\s*$", "", position)
                amount_str = match.group(2)

                # Konvertiere Betrag zu float
                amount = float(amount_str.replace(".", "").replace(",", "."))

                rows.append({"Position": position, "Betrag (€)": amount})
                print(f"  ✓ Gefunden: {position} | {amount_str} €")

        # Standort aus dem Katalog finden
        standort = None
        for adresse, ort in STANDORTE.items():
            # Flexible Suche
            pattern = r"\b" + re.escape(adresse.split()[0]) + r"(?:\s*\d*-?\d*)?"
            if re.search(pattern, text):
                # Genauere Überprüfung für Adressen mit Hausnummern
                if len(adresse.split()) > 1:
                    hausnummer = adresse.split()[1]
                    if hausnummer in text or re.search(
                        r"\b" + re.escape(adresse) + r"\b", text
                    ):
                        standort = ort
                        break
                else:
                    standort = ort
                    break

        print(f"Standort: {standort if standort else 'Nicht gefunden'}")

        # Verwendungszweck finden
        pattern_verwendungszweck = (
            r"\d{13}\s+Erst\.\:\s+\d{2}/\d{4}\s*[A-Z]\s+\+\s+\d{2}/\d{4}\s*[A-Z]"
        )
        verwendungszweck_match = re.search(pattern_verwendungszweck, text)
        verwendungszweck = (
            verwendungszweck_match.group(0) if verwendungszweck_match else ""
        )

        # Füge Metadaten zu allen Zeilen hinzu
        source_filename = os.path.basename(pdf_path)
        month_a, month_b = _extract_periods_from_filename(source_filename)
        if month_a is None or month_b is None:
            print(
                f"Warnung: Keine A/B-Periode im Dateinamen erkannt: {source_filename}"
            )

        for row in rows:
            position_value = row.get("Position", "")
            position_lower = str(position_value).lower()
            if "vergütung" in position_lower:
                buchungsperiode = month_a
            elif "besoldung" in position_lower:
                buchungsperiode = month_b
            else:
                # Fachlicher Fallback: A-Periode
                buchungsperiode = month_a

            row["Standort"] = standort if standort else ""
            row["Datum des Anschreibens"] = letter_date
            row["Quelldatei"] = source_filename
            row["Abrechnungsstelle"] = str(source_filename)[
                :4
            ]  # Nimm die ersten 4 Zeichen des Dateinamens
            row["Verwendungszweck"] = verwendungszweck
            row["Buchungsperiode"] = buchungsperiode

        print(f"\nGefundene Positionen: {len(rows)}")

        return rows

    except Exception as e:
        print(f"Fehler bei der Verarbeitung von {pdf_path}: {str(e)}")
        return []


def process_all_pdfs(FOLDER_PATH, progress_callback=None):
    """
    Verarbeitet alle PDFs in einem Ordner und gibt ein kombiniertes DataFrame zurück.
    """
    all_rows = []

    # Alle PDF-Dateien im Ordner (rekursiv) finden
    pdf_files = []
    for root, _, files in os.walk(FOLDER_PATH):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"Keine PDF-Dateien im Ordner {FOLDER_PATH} gefunden.")
        return pd.DataFrame()

    # Jede PDF-Datei verarbeiten
    total_files = len(pdf_files)
    for index, pdf_path in enumerate(pdf_files, start=1):
        if progress_callback:
            progress_callback(index, total_files, pdf_path)
        rows = extract_data(pdf_path)
        all_rows.extend(rows)

    # Kombiniertes DataFrame erstellen
    if all_rows:
        df = pd.DataFrame(all_rows)
        # Sortiere nach Quelldatei
        df = df.sort_values(["Quelldatei", "Position"])
        return df
    else:
        print("Keine Daten gefunden.")
        return pd.DataFrame()


def export_to_excel(df, filename):
    """
    Exportiert das DataFrame in eine Excel-Datei mit mehreren Arbeitsblättern.
    """
    try:
        # Stelle sicher, dass das Export-Verzeichnis existiert
        os.makedirs(EXPORT_PATH, exist_ok=True)

        # Konstruiere den vollständigen Pfad zur Excel-Datei
        full_path = os.path.join(EXPORT_PATH, filename)

        _write_excel(df, full_path)

        print(f"Excel-Datei '{filename}' wurde erfolgreich erstellt.")
        return True

    except Exception as e:
        print(f"Fehler beim Export in Excel: {str(e)}")
        return False


def export_to_excel_bytes(df):
    """
    Exportiert das DataFrame in eine Excel-Datei (Bytes) mit mehreren Arbeitsblättern.
    """
    buffer = io.BytesIO()
    _write_excel(df, buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _write_excel(df, target):
    """
    Schreibt die Excel-Datei entweder in einen Pfad oder in ein file-like Objekt.
    """
    total = df["Betrag (€)"].sum()
    ordered_columns = [
        "Position",
        "Betrag (€)",
        "Standort",
        "Datum des Anschreibens",
        "Quelldatei",
        "Abrechnungsstelle",
        "Verwendungszweck",
        "Buchungsperiode",
    ]
    export_columns = [col for col in ordered_columns if col in df.columns]
    df_export = df[export_columns] if export_columns else df

    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Tabellenpositionen", index=False)

        summary_data = {
            "Metrik": [
                "Anzahl Positionen",
                "Gesamtsumme (€)",
                "Anzahl Standorte",
                "Anzahl Dateien",
            ],
            "Wert": [
                len(df),
                f"{total:,.2f}",
                df["Standort"].nunique(),
                df["Quelldatei"].nunique(),
            ],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Zusammenfassung", index=False)

        if "Standort" in df.columns:
            standort_summary = (
                df.groupby("Standort")["Betrag (€)"].agg(["count", "sum"]).reset_index()
            )
            standort_summary.columns = [
                "Standort",
                "Anzahl Positionen",
                "Gesamtbetrag (€)",
            ]
            standort_summary.to_excel(
                writer, sheet_name="Standort-Übersicht", index=False
            )

if __name__ == "__main__":
    # Alle PDFs verarbeiten und kombiniertes DataFrame erstellen
    df = process_all_pdfs(FOLDER_PATH)

    if not df.empty:
        print("\n" + "=" * 80)
        print("EXTRAHIERTE TABELLENPOSITIONEN:")
        print("=" * 80)

        # Zeige die Daten schön formatiert
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        pd.set_option("display.max_colwidth", 50)

        print(
            df[
                ["Position", "Betrag (€)", "Standort", "Datum des Anschreibens"]
            ].to_string(index=False)
        )

        # Zusammenfassung
        print("\n" + "=" * 80)
        print("ZUSAMMENFASSUNG:")
        print("=" * 80)
        print(f"Anzahl Positionen: {len(df)}")

        # Prüfe ob die Summe mit dem "verbleibenden Betrag" übereinstimmt
        verbleibend = df[
            df["Position"].str.contains("verbleibender Betrag", case=False)
        ]["Betrag (€)"].values
        if len(verbleibend) > 0:
            print(f"\nVerbleibender Betrag laut Dokument: {verbleibend[0]:,.2f} €")

        # Excel Export über eigene Funktion
        export_to_excel(df, filename)

    else:
        print("Keine Daten zum Exportieren vorhanden.")
