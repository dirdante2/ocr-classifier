# Datei-Übersicht - Bilderkennung Microservice

Vollständige Übersicht aller Projekt-Dateien und deren Zweck.

## 📁 Projektstruktur

```
/root/ocr-classifier
├── 📄 Dokumentation
│   ├── README.md                      # Hauptdokumentation
│   ├── API_REFERENCE.md               # API-Referenz
│   ├── CI4_INTEGRATION_GUIDE.md       # CI4-Integrationsanleitung
│   ├── QUICKSTART.md                  # 5-Minuten Schnellstart
│   └── FILES_OVERVIEW.md              # Diese Datei
│
├── 🚀 Hauptservice
│   ├── classifier_service.py          # FastAPI Microservice (v2.0)
│   └── config.py                      # Zentrale Konfiguration
│
├── 🧠 ML-Modelle & Analyzer
│   └── models/
│       ├── __init__.py
│       ├── corner_detector.py         # 4-Eckpunkte-Erkennung
│       └── ocr_analyzer.py            # OCR + Arbeitsbericht-Erkennung
│
├── 🔍 Feature-Extraction
│   └── features/
│       ├── __init__.py
│       ├── color_analyzer.py          # LAB-Farbuniformität
│       └── line_analyzer.py           # Hough-Linien-Analyse
│
├── 💾 Datenbank-Integration
│   └── database/
│       ├── __init__.py
│       ├── ci4_client.py              # REST-API Client für CI4
│       └── schemas.py                 # Pydantic Data Models
│
├── 🎓 Learning (zukünftig)
│   └── learning/
│       └── __init__.py                # Adaptive Gewichtsanpassung
│
└── 📦 Legacy/Backup
    └── classifier_service.py.backup   # Backup der alten Version
```

## 📄 Detaillierte Dateibeschreibungen

### Dokumentation

#### [README.md](README.md) (26 KB)
- **Zweck**: Hauptdokumentation des Projekts
- **Inhalt**:
  - Installation & Setup
  - Konfiguration
  - API-Endpunkte
  - CI4-Integration Übersicht
  - Architektur-Beschreibung
  - Troubleshooting
- **Zielgruppe**: Entwickler, DevOps

#### [API_REFERENCE.md](API_REFERENCE.md) (13 KB)
- **Zweck**: Vollständige REST-API Dokumentation
- **Inhalt**:
  - Alle Endpunkte (GET /health, POST /classify, POST /feedback)
  - Request/Response-Formate
  - Beispiele (cURL, Python, PHP)
  - Error-Handling
  - Performance-Tipps
- **Zielgruppe**: API-Konsumenten, Frontend-Entwickler

#### [CI4_INTEGRATION_GUIDE.md](CI4_INTEGRATION_GUIDE.md) (25 KB)
- **Zweck**: Schritt-für-Schritt CI4-Integrationsanleitung
- **Inhalt**:
  - Datenbank-Migrations (SQL)
  - CI4-Models (ClassificationModel, FeedbackModel, etc.)
  - CI4-Controller (ImageClassificationController)
  - Routes-Konfiguration
  - Authentifizierung
  - Test-Scripte
  - Dashboard-Beispiel
- **Zielgruppe**: CI4-Entwickler

#### [QUICKSTART.md](QUICKSTART.md) (3 KB)
- **Zweck**: 5-Minuten Schnellstart
- **Inhalt**:
  - Voraussetzungen prüfen
  - Erster Test
  - Konfiguration anpassen
  - Troubleshooting
- **Zielgruppe**: Alle (Quick Reference)

#### [FILES_OVERVIEW.md](FILES_OVERVIEW.md) (Diese Datei)
- **Zweck**: Übersicht aller Dateien
- **Zielgruppe**: Neue Entwickler im Projekt

---

### Hauptservice

#### [classifier_service.py](classifier_service.py) (~10 KB, v2.0)
- **Zweck**: FastAPI Hauptservice
- **Funktionen**:
  - Bild-Upload-Handling
  - OCR-Analyse (Tesseract)
  - CLIP-Klassifizierung
  - Corner-Detection
  - Farbuniformitäts-Analyse
  - Linien-Analyse
  - Score-Berechnung
  - Klassifizierungs-Entscheidung
  - CI4-Integration (optional)
- **Endpunkte**:
  - `GET /health` - Health Check
  - `POST /classify` - Bildklassifizierung
  - `POST /feedback` - Feedback einreichen
- **Dependencies**: FastAPI, PIL, PyTesseract, Transformers, OpenCV

#### [config.py](config.py) (~5 KB)
- **Zweck**: Zentrale Konfigurationsdatei
- **Konfiguriert**:
  - Klassifizierungs-Schwellwerte (arbeitsbericht, typeplate, etc.)
  - Scoring-Gewichte (adaptive)
  - Corner-Detection-Parameter
  - Farbanalyse-Parameter (LAB)
  - Linien-Analyse-Parameter (Hough)
  - OCR-Keywords
  - CI4-Konfiguration (URL, API-Key, Enabled)
  - Feature-Extraction-Parameter
  - Learning-Parameter
  - Performance-Einstellungen
- **Methoden**:
  - `update_weights()` - Gewichte dynamisch anpassen
  - `update_thresholds()` - Schwellwerte anpassen
  - `to_dict()` - Export als Dictionary

---

### ML-Modelle & Analyzer

#### [models/corner_detector.py](models/corner_detector.py) (~8 KB)
- **Zweck**: 4-Eckpunkte-Erkennung für Dokumente/Typenschilder
- **Algorithmus**: Hybrid-Ansatz
  1. **Primär**: Kontur-basiert (`cv2.findContours` + `cv2.approxPolyDP`)
  2. **Fallback**: Harris Corner Detection (`cv2.goodFeaturesToTrack`)
  3. **Last Resort**: Bildbegrenzung
- **Klasse**: `CornerDetector`
- **Hauptmethode**: `detect_4_corners(image) -> dict`
- **Output**:
  - 4 geordnete Eckpunkte [TL, TR, BR, BL]
  - Detection-Methode
  - Konfidenz-Score
- **Zusatz-Features**:
  - Perspektiv-Transformations-Matrix
  - Perspektiv-Transformation anwenden

#### [models/ocr_analyzer.py](models/ocr_analyzer.py) (~7 KB)
- **Zweck**: OCR-Analyse + Arbeitsbericht-Erkennung
- **Klasse**: `OCRAnalyzer`
- **Hauptmethoden**:
  - `analyze(image)` - Vollständige OCR-Analyse
  - `detect_arbeitsbericht(text)` - Arbeitsbericht-Keyword-Erkennung
  - `analyze_typeplate_features(text)` - Typenschild-Text-Features
  - `detect_date_patterns(text)` - Datumserkennun

g
  - `get_text_statistics(text)` - Detaillierte Text-Statistiken
- **Keywords**:
  - **Arbeitsbericht**: "arbeitsbericht" (Haupt), "unterschrift", "fahrer", etc.
  - **Typeplate**: "serial", "model", "voltage", "hz", etc.
- **Features**:
  - Ziffern-Ratio
  - Keyword-Matching mit Positionen
  - Technische Spezifikationen-Erkennung (Voltage, Frequency, Power)

---

### Feature-Extraction

#### [features/color_analyzer.py](features/color_analyzer.py) (~4 KB)
- **Zweck**: Farbuniformitäts-Analyse für Typenschilder
- **Klasse**: `ColorAnalyzer`
- **Methode**: LAB-Farbraum-Analyse
- **Algorithmus**:
  1. RGB → LAB Konvertierung
  2. Globale Standardabweichung (L, A, B Kanäle)
  3. Regionale Analyse (5x5 Grid)
  4. Dominante Farbe via K-Means (k=3)
- **Output**:
  - `global_std` - Globale Standardabweichung
  - `regional_std` - Durchschn. regionale StdDev
  - `dominant_color_ratio` - Anteil der dominanten Farbe
  - `uniformity_score` - Score für Typeplate-Erkennung
  - `is_uniform` - Boolean Flag

#### [features/line_analyzer.py](features/line_analyzer.py) (~4 KB)
- **Zweck**: Gerade-Linien-Analyse
- **Klasse**: `LineAnalyzer`
- **Methode**: Hough Line Transform
- **Algorithmus**:
  1. Canny Edge Detection
  2. HoughLinesP (probabilistische Hough)
  3. Linien-Klassifizierung (horizontal/vertikal)
  4. Rechteckiger Rand-Erkennung
- **Output**:
  - `line_count` - Anzahl erkannter Linien
  - `horizontal_count`, `vertical_count` - Nach Orientierung
  - `has_rectangular_border` - Boolean
  - `border_completeness` - 0-4 (Anzahl erkannter Seiten)
  - `line_score` - Score für Typeplate-Erkennung

---

### Datenbank-Integration

#### [database/ci4_client.py](database/ci4_client.py) (~4 KB)
- **Zweck**: REST-API Client für CodeIgniter 4
- **Klasse**: `CI4Client`
- **Konfiguration**: Aus `config.CI4_CONFIG`
- **Methoden**:
  - `store_classification(data)` - Klassifizierung speichern
  - `store_feedback(id, feedback)` - Feedback speichern
  - `find_similar_images(features, limit)` - Ähnlichkeitssuche
  - `get_model_weights()` - Aktuelle Gewichte laden
  - `update_model_weights(weights, thresholds)` - Gewichte aktualisieren
  - `health_check()` - CI4-Erreichbarkeit prüfen
- **Error-Handling**: Logged alle Fehler, gibt None/[] zurück
- **Singleton**: `ci4_client` Instanz global verfügbar

#### [database/schemas.py](database/schemas.py) (~2 KB)
- **Zweck**: Pydantic Data Models für API-Validierung
- **Schemas**:
  - `CornerPoint` - Einzelner Eckpunkt (x, y, label)
  - `CornersResponse` - Eckpunkte-Response
  - `ScoresResponse` - Klassifizierungs-Scores
  - `ClassificationResponse` - Haupt-Response
  - `FeedbackRequest` - Feedback-Request
  - `ClassificationData` - CI4-Speicherformat
  - `FeedbackData` - CI4-Feedback-Format
- **Verwendung**: FastAPI Request/Response-Validierung

---

### Learning (Zukünftig)

#### [learning/](learning/)
- **Status**: Vorbereitet für zukünftige Implementierung
- **Geplant**:
  - `scoring_engine.py` - Adaptive Gewichtsanpassung basierend auf Feedback
  - `feedback_processor.py` - Feedback-Analyse und Batch-Processing
  - Gradient-basierte Weight-Adjustments
  - Threshold-Optimierung (ROC-Analyse)

---

### Legacy/Backup

#### [classifier_service.py.backup](classifier_service.py.backup)
- **Zweck**: Backup der vorherigen Service-Version (v1.x)
- **Verwendet für**: Rollback falls nötig
- **Unterschiede zu v2.0**:
  - Keine Eckpunkte-Erkennung
  - Nur Arbeitsbericht (nicht "Arbeitsschein")
  - Keine Farbuniformitäts-Analyse
  - Keine Linien-Analyse
  - Keine CI4-Integration

---

## 🔧 Konfigurationsdateien (System)

### /etc/systemd/system/ocr-classifier.service
```ini
[Unit]
Description=OCR + Image Classifier Microservice (FastAPI)
After=network.target

[Service]
WorkingDirectory=/root
Environment="PATH=/opt/ocr-env/bin:/usr/bin"
ExecStart=/opt/ocr-env/bin/uvicorn classifier_service:app --host 0.0.0.0 --port 8090
Restart=always

[Install]
WantedBy=multi-user.target
```

### /opt/ocr-env/
- Python Virtual Environment
- Alle Dependencies installiert
- Models gecacht in `/root/.cache/huggingface/`

---

## 📊 Dateigröße-Übersicht

| Datei | Größe | Zeilen | Zweck |
|-------|-------|--------|-------|
| README.md | 26 KB | ~700 | Hauptdoku |
| CI4_INTEGRATION_GUIDE.md | 25 KB | ~900 | CI4-Setup |
| API_REFERENCE.md | 13 KB | ~550 | API-Docs |
| classifier_service.py | ~10 KB | ~380 | Hauptservice |
| models/corner_detector.py | ~8 KB | ~300 | Eckpunkte |
| models/ocr_analyzer.py | ~7 KB | ~250 | OCR |
| config.py | ~5 KB | ~180 | Config |
| features/color_analyzer.py | ~4 KB | ~150 | Farben |
| features/line_analyzer.py | ~4 KB | ~150 | Linien |
| database/ci4_client.py | ~4 KB | ~150 | CI4-Client |
| QUICKSTART.md | 3 KB | ~140 | Quick-Start |
| database/schemas.py | ~2 KB | ~50 | Schemas |

**Total Code**: ~55 KB / ~2500 Zeilen
**Total Docs**: ~67 KB / ~2300 Zeilen

---

## 🎯 Wichtigste Dateien für verschiedene Aufgaben

### Als Entwickler (neue Features):
1. `classifier_service.py` - Hauptlogik
2. `config.py` - Parameter anpassen
3. `models/` - Neue Analyzer hinzufügen

### Als CI4-Entwickler:
1. `CI4_INTEGRATION_GUIDE.md` - Setup-Anleitung
2. `database/ci4_client.py` - API-Schnittstelle
3. `API_REFERENCE.md` - Endpunkt-Details

### Als DevOps:
1. `README.md` - Installation
2. `QUICKSTART.md` - Quick-Check
3. `/etc/systemd/system/ocr-classifier.service` - Service-Config

### Als API-Nutzer:
1. `API_REFERENCE.md` - API-Docs
2. `QUICKSTART.md` - Erste Schritte
3. `README.md` - Troubleshooting

---

## 📝 Änderungshistorie

**v2.0.0** (2026-01-07):
- ✅ Alle Kern-Features implementiert
- ✅ Vollständige Dokumentation erstellt
- ✅ CI4-Integration vorbereitet
- ✅ Service läuft stabil

**v1.0.0** (vorher):
- ✅ Basis-Service mit CLIP + OCR
- ⚠️ Eingeschränkte Features
