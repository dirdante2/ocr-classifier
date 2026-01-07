# Quick Start Guide - Bilderkennung Microservice

5-Minuten Schnellstart für den selbstlernenden Bilderkennung-Service.

## ✅ Voraussetzungen prüfen

```bash
# Service-Status
systemctl status ocr-classifier.service

# Python-Umgebung
/opt/ocr-env/bin/python --version  # Should be Python 3.11+

# Tesseract OCR
tesseract --version  # Should be 5.x
```

## 🚀 Ersten Test durchführen

### 1. Service ist bereit?

```bash
# Health Check (sollte "ok" zurückgeben)
python3 << 'PYTHON'
import requests
r = requests.get('http://localhost:8090/health')
print(r.json())
PYTHON
```

### 2. Test-Bild klassifizieren

```bash
# Python-Test-Script erstellen
cat > /tmp/test_classify.py << 'PYTHON'
import requests

# Bild klassifizieren
with open('/path/to/your/image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8090/classify',
        files={'file': f}
    )

result = response.json()

print(f"✅ Klassifizierung: {result['predicted']}")
print(f"✅ Konfidenz: {result['confidence']}")
print(f"✅ Eckpunkte erkannt: {result['corners']['detection_method']}")

# Details
print(f"\nScores:")
print(f"  - Arbeitsbericht: {result['scores']['AR']}")
print(f"  - Typenschild: {result['scores']['TP']}")
print(f"  - Dokument: {result['scores']['DOC']}")
print(f"  - Foto: {result['scores']['PHOTO']}")

if result['predicted'] == 'arbeitsbericht':
    print(f"\n✓ Keyword gefunden: {result['arbeitsbericht_debug']['has_main_keyword']}")
    print(f"  Keywords: {result['arbeitsbericht_debug']['keyword_hits']}")
PYTHON

# Ausführen
python3 /tmp/test_classify.py
```

## 📚 Was ist implementiert?

✅ **4-Eckpunkte-Erkennung**
- Automatische Dokumentenrand-Erkennung
- Hybrid-Algorithmus (Contour + Harris)
- Perspektiv-Transformation möglich

✅ **Arbeitsbericht-Erkennung**
- Keyword: "Arbeitsbericht" (case-insensitive)
- Zusatz-Keywords: unterschrift, fahrer, fahrzeug, etc.
- Schwellwert: AR >= 5.0

✅ **Typenschild-Erkennung (verbessert)**
- Farbuniformitäts-Analyse (LAB-Farbraum)
- Gerade-Linien-Erkennung (Hough)
- Rechteckiger Rand-Detektion

✅ **CI4-Integration (optional)**
- REST-API Anbindung
- Feedback-System
- Model-Gewichte Sync

## 🔧 Konfiguration anpassen

### Schwellwerte ändern

```bash
# config.py bearbeiten
nano /root/config.py

# Beispiel-Änderungen:
# THRESHOLDS["arbeitsbericht"] = 4.0  # Sensibler
# THRESHOLDS["typeplate"] = 4.0       # Strenger

# Service neu starten
systemctl restart ocr-classifier.service
```

### CI4-Integration aktivieren

```bash
# Environment-Variablen setzen
cat >> /etc/environment << 'ENV'
CI4_ENABLED=true
CI4_BASE_URL=http://your-ci4-server/api/v1
CI4_API_KEY=your-secret-key
ENV

# Service neu starten
systemctl restart ocr-classifier.service

# Status prüfen
python3 -c "import requests; print(requests.get('http://localhost:8090/health').json())"
```

## 📖 Weitere Dokumentation

- **[README.md](README.md)** - Vollständige Dokumentation
- **[API_REFERENCE.md](API_REFERENCE.md)** - API-Details
- **[CI4_INTEGRATION_GUIDE.md](CI4_INTEGRATION_GUIDE.md)** - CI4-Setup

## 🐛 Troubleshooting

### Service startet nicht

```bash
journalctl -u ocr-classifier.service -n 50 --no-pager
```

### CLIP-Model fehlt

```bash
source /opt/ocr-env/bin/activate
python3 -c "from transformers import CLIPModel; CLIPModel.from_pretrained('openai/clip-vit-base-patch32')"
```

### Langsam

```bash
# config.py:
# PERFORMANCE["lazy_feature_extraction"] = True
systemctl restart ocr-classifier.service
```

## 💡 Nächste Schritte

1. **CI4-Integration einrichten** (siehe CI4_INTEGRATION_GUIDE.md)
2. **Feedback-System testen**
3. **Monitoring aufsetzen**
4. **Produktiv nehmen**

---

**Service-Port**: 8090
**Logs**: `journalctl -u ocr-classifier.service -f`
**Config**: `/root/config.py`
