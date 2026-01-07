# API-Referenz - Bilderkennung Microservice v2.0

Vollständige REST-API Dokumentation für den Bilderkennung-Microservice.

---

## 🔗 Base URL

```
http://localhost:8090
```

---

## 📋 Endpunkte

### 1. Health Check

Prüft ob der Service läuft und gibt Status-Informationen zurück.

```http
GET /health
```

#### Response

```json
{
  "status": "ok",
  "version": "1.0.0",
  "clip_model": "ready",
  "ci4_integration": "disabled",
  "ci4_reachable": null
}
```

#### Status Codes
- `200 OK` - Service läuft normal

---

### 2. Bild klassifizieren

Klassifiziert ein hochgeladenes Bild und gibt detaillierte Analyse-Ergebnisse zurück.

```http
POST /classify
Content-Type: multipart/form-data
```

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | Bilddatei (JPEG, PNG, etc.) |

#### cURL Beispiel

```bash
curl -X POST http://localhost:8090/classify \
  -F "file=@/path/to/image.jpg"
```

#### Python Beispiel

```python
import requests

with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8090/classify',
        files={'file': f}
    )

result = response.json()
print(result['predicted'])
```

#### Response

```json
{
  "classification_id": "550e8400-e29b-41d4-a716-446655440000",
  "predicted": "arbeitsbericht",
  "confidence": 0.85,
  "scores": {
    "AR": 8.5,
    "TP": 2.3,
    "DOC": 3.1,
    "PHOTO": 0.5
  },
  "corners": {
    "points": [
      {"x": 45, "y": 120, "label": "top_left"},
      {"x": 890, "y": 118, "label": "top_right"},
      {"x": 892, "y": 450, "label": "bottom_right"},
      {"x": 43, "y": 452, "label": "bottom_left"}
    ],
    "detection_method": "contour_based",
    "confidence": 0.92
  },
  "ocr": {
    "text_length": 1245,
    "density": 0.000654,
    "word_count": 210,
    "line_count": 45,
    "raw_text": "Arbeitsbericht vom 07.01.2026..."
  },
  "clip": {
    "label": "document",
    "confidence": 0.89
  },
  "arbeitsbericht_debug": {
    "has_main_keyword": true,
    "keyword_hits": 5,
    "keyword_details": [
      {"keyword": "unterschrift", "position": 234},
      {"keyword": "fahrer", "position": 567}
    ],
    "text_length": 1245,
    "is_long_text": true,
    "main_keyword_position": 0
  },
  "typeplate_debug": {
    "legacy_score": 2.45,
    "digit_ratio": 0.15,
    "keywords": 2,
    "line_density": 0.00045,
    "text_features": {
      "digit_ratio": 0.15,
      "keyword_count": 2,
      "keyword_hits": ["serial", "model"],
      "has_serial_number": true,
      "has_model_number": true,
      "has_technical_specs": false
    },
    "color_uniformity": {
      "global_std": 35.2,
      "regional_std": 32.1,
      "dominant_color_ratio": 0.45,
      "uniformity_score": 0.0,
      "is_uniform": false,
      "color_components": {
        "l_std": 28.5,
        "a_std": 32.1,
        "b_std": 45.0
      }
    },
    "line_analysis": {
      "line_count": 24,
      "horizontal_count": 12,
      "vertical_count": 8,
      "has_rectangular_border": true,
      "line_score": 8.5,
      "border_completeness": 4,
      "orientation_ratio": 1.5
    }
  },
  "model_version": "1.0.0"
}
```

#### Response Fields

##### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| classification_id | string | Eindeutige UUID für diese Klassifizierung |
| predicted | string | Klassifizierungsergebnis (`arbeitsbericht`, `typeplate`, `document`, `photo`) |
| confidence | float | Konfidenz-Score 0.0-1.0 |
| scores | object | Detaillierte Scores pro Kategorie |
| corners | object | Erkannte 4 Eckpunkte |
| ocr | object | OCR-Ergebnisse |
| clip | object | CLIP-Model-Ergebnisse |
| arbeitsbericht_debug | object | Debug-Info für Arbeitsbericht-Erkennung |
| typeplate_debug | object | Debug-Info für Typenschild-Erkennung |
| model_version | string | Version des verwendeten Models |

##### Scores Object

| Field | Type | Description |
|-------|------|-------------|
| AR | float | Arbeitsbericht-Score |
| TP | float | Typeplate-Score |
| DOC | float | Document-Score |
| PHOTO | float | Photo-Score |

##### Corners Object

| Field | Type | Description |
|-------|------|-------------|
| points | array | Array von 4 Eckpunkten (x, y, label) |
| detection_method | string | Verwendete Methode (`contour_based`, `harris`, `image_bounds`) |
| confidence | float | Konfidenz der Eckpunkt-Erkennung 0.0-1.0 |

##### Corner Point Object

| Field | Type | Description |
|-------|------|-------------|
| x | integer | X-Koordinate |
| y | integer | Y-Koordinate |
| label | string | Position (`top_left`, `top_right`, `bottom_right`, `bottom_left`) |

#### Status Codes

- `200 OK` - Erfolgreich klassifiziert
- `400 Bad Request` - Ungültige Datei oder fehlende Parameter
- `500 Internal Server Error` - Server-Fehler

---

### 3. Feedback einreichen

Sendet User-Feedback für eine Klassifizierung (nur wenn CI4-Integration aktiviert).

```http
POST /feedback
Content-Type: application/json
```

#### Request Body

```json
{
  "classification_id": "550e8400-e29b-41d4-a716-446655440000",
  "corrected_class": "typeplate",
  "user_confidence": "high",
  "correction_reason": "Bild zeigt eindeutig ein Typenschild",
  "corrected_corners": [
    {"x": 50, "y": 125},
    {"x": 895, "y": 120},
    {"x": 890, "y": 455},
    {"x": 48, "y": 450}
  ]
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| classification_id | string | Yes | UUID der ursprünglichen Klassifizierung |
| corrected_class | string | No | Korrigierte Klasse (`arbeitsbericht`, `typeplate`, `document`, `photo`) |
| user_confidence | string | Yes | Nutzer-Konfidenz (`low`, `medium`, `high`) |
| correction_reason | string | No | Textuelle Begründung |
| corrected_corners | array | No | Korrigierte Eckpunkte (4 x/y Koordinaten) |

#### cURL Beispiel

```bash
curl -X POST http://localhost:8090/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "classification_id": "550e8400-e29b-41d4-a716-446655440000",
    "corrected_class": "typeplate",
    "user_confidence": "high",
    "correction_reason": "Korrekte Klassifizierung wäre Typenschild"
  }'
```

#### Response

**Erfolg (CI4 aktiviert):**
```json
{
  "status": "success",
  "message": "Feedback stored"
}
```

**Warnung (CI4 deaktiviert):**
```json
{
  "status": "warning",
  "message": "CI4 integration disabled, feedback not stored"
}
```

**Fehler:**
```json
{
  "status": "error",
  "message": "Failed to store feedback"
}
```

#### Status Codes

- `200 OK` - Feedback erfolgreich gespeichert (oder CI4 deaktiviert)
- `400 Bad Request` - Ungültige Daten
- `404 Not Found` - classification_id nicht gefunden
- `500 Internal Server Error` - Fehler beim Speichern

---

## 📊 Datentypen

### Klassifizierungstypen

| Wert | Beschreibung |
|------|--------------|
| `arbeitsbericht` | Arbeitsbericht-Dokument mit Keyword "Arbeitsbericht" |
| `typeplate` | Typenschild/Maschinenschild |
| `document` | Allgemeines Dokument |
| `photo` | Foto ohne relevanten Text |

### User Confidence Levels

| Wert | Beschreibung |
|------|--------------|
| `low` | Nutzer ist unsicher |
| `medium` | Mittlere Sicherheit |
| `high` | Nutzer ist sich sicher |

### Corner Detection Methods

| Wert | Beschreibung |
|------|--------------|
| `contour_based` | Kontur-basierte Erkennung (primär) |
| `harris` | Harris Corner Detection (fallback) |
| `image_bounds` | Bildränder (last resort) |

---

## ⚠️ Fehlerbehandlung

### Error Response Format

```json
{
  "error": "Python exception",
  "type": "ValueError",
  "message": "Leere Datei hochgeladen.",
  "traceback": "..."
}
```

### Häufige Fehler

#### 1. Leere Datei

**Request:**
```bash
curl -X POST http://localhost:8090/classify -F "file=@empty.jpg"
```

**Response (500):**
```json
{
  "error": "Python exception",
  "type": "ValueError",
  "message": "Leere Datei hochgeladen."
}
```

#### 2. Ungültiges Dateiformat

**Request:**
```bash
curl -X POST http://localhost:8090/classify -F "file=@document.pdf"
```

**Response (500):**
```json
{
  "error": "Python exception",
  "type": "UnidentifiedImageError",
  "message": "cannot identify image file"
}
```

#### 3. Fehlende Datei

**Request:**
```bash
curl -X POST http://localhost:8090/classify
```

**Response (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "file"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 🔧 Rate Limiting

Aktuell **kein Rate Limiting** implementiert.

**Empfehlung**: Implementiere Rate Limiting auf Reverse-Proxy-Ebene (nginx):

```nginx
limit_req_zone $binary_remote_addr zone=classify:10m rate=10r/s;

location /classify {
    limit_req zone=classify burst=20 nodelay;
    proxy_pass http://localhost:8090;
}
```

---

## 📝 Best Practices

### 1. Bildgröße optimieren

```python
from PIL import Image

# Vor Upload resizen
img = Image.open('large_image.jpg')
img.thumbnail((1920, 1920))  # Max 1920x1920
img.save('optimized.jpg', quality=85)
```

### 2. Batch-Processing

```python
import requests
import concurrent.futures

def classify_image(filepath):
    with open(filepath, 'rb') as f:
        response = requests.post(
            'http://localhost:8090/classify',
            files={'file': f}
        )
    return response.json()

# Parallel verarbeiten
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(classify_image, image_files)
```

### 3. Timeout setzen

```python
import requests

response = requests.post(
    'http://localhost:8090/classify',
    files={'file': open('image.jpg', 'rb')},
    timeout=30  # 30 Sekunden Timeout
)
```

### 4. Fehlerbehandlung

```python
import requests

try:
    response = requests.post(
        'http://localhost:8090/classify',
        files={'file': open('image.jpg', 'rb')},
        timeout=30
    )
    response.raise_for_status()

    result = response.json()

    # Validierung
    if 'predicted' not in result:
        raise ValueError("Invalid response format")

    print(f"Klassifiziert als: {result['predicted']}")

except requests.exceptions.Timeout:
    print("Request timeout - Service überlastet?")
except requests.exceptions.ConnectionError:
    print("Service nicht erreichbar")
except requests.exceptions.HTTPError as e:
    print(f"HTTP Fehler: {e}")
except ValueError as e:
    print(f"Ungültige Response: {e}")
```

---

## 🔐 Authentifizierung

Aktuell **keine Authentifizierung** implementiert.

**Für Produktion empfohlen**:

### API-Key Header

```python
import requests

headers = {
    'Authorization': 'Bearer your-secret-api-key'
}

response = requests.post(
    'http://localhost:8090/classify',
    files={'file': open('image.jpg', 'rb')},
    headers=headers
)
```

Implementierung siehe [README.md](README.md#authentifizierung).

---

## 📊 Performance

### Durchschnittliche Response-Zeiten

| Endpunkt | Durchschnitt | Max |
|----------|--------------|-----|
| GET /health | ~10ms | ~50ms |
| POST /classify | ~500ms | ~2s |
| POST /feedback | ~50ms | ~200ms |

**Faktoren die Performance beeinflussen**:
- Bildgröße (größere Bilder = langsamer)
- OCR-Textmenge (mehr Text = langsamer)
- CLIP-Model auf CPU vs GPU
- Systemauslastung

### Optimierungstipps

1. **GPU verwenden** (falls verfügbar):
   ```python
   # In classifier_service.py
   clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to("cuda")
   ```

2. **Bilder vorverarbeiten**:
   - Max 1920x1920 Pixel
   - JPEG mit 85% Qualität
   - Entferne EXIF-Daten

3. **Caching aktivieren**:
   ```python
   # In config.py
   PERFORMANCE["enable_caching"] = True
   ```

---

## 📖 Changelog

### v2.0.0 (2026-01-07)
- ✅ 4-Eckpunkte-Erkennung hinzugefügt
- ✅ Verbesserte Arbeitsbericht-Erkennung (Keyword "Arbeitsbericht")
- ✅ Farbuniformitäts-Analyse für Typenschilder
- ✅ Gerade-Linien-Analyse
- ✅ CI4-Integration (optional)
- ✅ Feedback-System

### v1.0.0 (vorher)
- ✅ Basis-Klassifizierung (Arbeitsbericht/Typeplate/Document/Photo)
- ✅ OCR mit Tesseract
- ✅ CLIP-Model-Integration

---

## 💬 Support

Bei Fragen zur API:
- Dokumentation: [README.md](README.md)
- CI4-Integration: [CI4_INTEGRATION_GUIDE.md](CI4_INTEGRATION_GUIDE.md)
- Logs: `journalctl -u ocr-classifier.service -f`
