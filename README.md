# Selbstlernender Bilderkennung-Microservice v2.0

Intelligenter OCR- und Bildklassifizierungs-Service mit maschinellem Lernen, spezialisiert auf die Erkennung von Arbeitsberichten, Typenschildern und Dokumenten.

## 🎯 Features

### Kernfunktionen
- ✅ **4-Eckpunkte-Erkennung** - Automatische Erkennung der Dokumentenränder
- ✅ **Arbeitsbericht-Erkennung** - Präzises Keyword-basiertes Matching
- ✅ **Typenschild-Erkennung** - Verbessert durch Farbuniformität und Linienanalyse
- ✅ **Multi-Model-Ansatz** - Kombination aus OCR, CLIP und Computer Vision
- ✅ **CI4-Integration** - Optionale REST-API Anbindung für Datenpersistenz
- ✅ **Feedback-System** - Lernfähig durch User-Korrekturen

### Technologie-Stack
- **FastAPI** - Moderne Python Web-Framework
- **Tesseract OCR** - Texterkennung (Deutsch + Englisch)
- **CLIP (OpenAI)** - Vision-Language Model für semantische Klassifizierung
- **OpenCV** - Computer Vision (Eckpunkte, Linien, Farben)
- **PyTorch** - Deep Learning Backend

---

## 📋 Inhaltsverzeichnis

1. [Installation](#installation)
2. [Konfiguration](#konfiguration)
3. [API-Dokumentation](#api-dokumentation)
4. [CI4-Integration](#ci4-integration)
5. [Architektur](#architektur)
6. [Verwendung](#verwendung)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Installation

### Voraussetzungen

```bash
# System-Pakete
apt install python3-venv tesseract-ocr tesseract-ocr-deu -y

# Python Virtual Environment
python3 -m venv /opt/ocr-env
source /opt/ocr-env/bin/activate

# Python-Abhängigkeiten
/opt/ocr-env/bin/pip install fastapi uvicorn pillow pytesseract \
    transformers torch opencv-python-headless pydantic requests
```

### Service-Installation

1. **Code deployen** (bereits in `/root/`)
   ```bash
   cd /root
   ls -la  # Sollte classifier_service.py, config.py, models/, features/, etc. zeigen
   ```

2. **Systemd Service einrichten**

   Erstelle `/etc/systemd/system/ocr-classifier.service`:
   ```ini
   [Unit]
   Description=OCR + Image Classifier Microservice (FastAPI)
   After=network.target

   [Service]
   WorkingDirectory=/root
   Environment="PATH=/opt/ocr-env/bin:/usr/bin"
   ExecStart=/opt/ocr-env/bin/uvicorn classifier_service:app --host 0.0.0.0 --port 8090
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. **Service starten**
   ```bash
   systemctl daemon-reload
   systemctl enable ocr-classifier.service
   systemctl start ocr-classifier.service
   systemctl status ocr-classifier.service
   ```

---

## ⚙️ Konfiguration

### Umgebungsvariablen

Erstelle `/root/.env` (optional):

```bash
# CI4 Integration (standardmäßig deaktiviert)
CI4_ENABLED=false
CI4_BASE_URL=http://localhost/api/v1
CI4_API_KEY=your-api-key-here

# Service-Port (Standard: 8090)
PORT=8090
```

### Konfigurationsdatei

Alle Parameter sind in [`config.py`](config.py) konfigurierbar:

```python
from config import config

# Schwellwerte anpassen
config.THRESHOLDS["arbeitsbericht"] = 5.0
config.THRESHOLDS["typeplate"] = 3.0

# Gewichte anpassen
config.WEIGHTS["TP"]["color_uniformity_factor"] = 6.0

# CI4-Konfiguration
config.CI4_CONFIG["base_url"] = "http://your-server/api/v1"
config.CI4_CONFIG["enabled"] = True
```

---

## 📡 API-Dokumentation

### Endpunkte

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "clip_model": "ready",
  "ci4_integration": "disabled",
  "ci4_reachable": null
}
```

---

#### 2. Bildklassifizierung
```http
POST /classify
Content-Type: multipart/form-data
```

**Request:**
```bash
curl -X POST http://localhost:8090/classify \
  -F "file=@/path/to/image.jpg"
```

**Response:**
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
      "is_uniform": false
    },
    "line_analysis": {
      "line_count": 24,
      "horizontal_count": 12,
      "vertical_count": 8,
      "has_rectangular_border": true,
      "line_score": 8.5,
      "border_completeness": 4
    }
  },
  "model_version": "1.0.0"
}
```

**Klassifizierungs-Typen:**
- `arbeitsbericht` - Arbeitsbericht mit Keyword "Arbeitsbericht"
- `typeplate` - Typenschild/Maschinenschild
- `document` - Allgemeines Dokument
- `photo` - Foto ohne Text

---

#### 3. Feedback einreichen
```http
POST /feedback
Content-Type: application/json
```

**Request:**
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

**Response:**
```json
{
  "status": "success",
  "message": "Feedback stored"
}
```

**Hinweis:** Feedback-Endpunkt benötigt aktivierte CI4-Integration.

---

## 🔗 CI4-Integration

### Übersicht

Der Microservice kann optional mit einem CodeIgniter 4 Backend kommunizieren für:
- Persistente Speicherung von Klassifizierungen
- User-Feedback-System
- Ähnlichkeitssuche
- Adaptive Model-Gewichte

### Schritt 1: CI4-Datenbank-Schema

Erstelle folgende Tabellen in deiner CI4-Datenbank:

#### `classifications` Tabelle
```sql
CREATE TABLE classifications (
    id VARCHAR(36) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    image_hash VARCHAR(64) NOT NULL,

    -- Prediction
    predicted_class VARCHAR(50) NOT NULL,
    confidence FLOAT,
    score_AR FLOAT,
    score_TP FLOAT,
    score_DOC FLOAT,
    score_PHOTO FLOAT,

    -- Features (JSON)
    features JSON NOT NULL,

    -- Image Metadata
    image_width INT,
    image_height INT,
    image_format VARCHAR(10),

    -- Model Version
    model_version VARCHAR(20),
    weights_version VARCHAR(20),

    -- Indexes
    INDEX idx_timestamp (timestamp),
    INDEX idx_image_hash (image_hash),
    INDEX idx_predicted_class (predicted_class),
    INDEX idx_created (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `feedback` Tabelle
```sql
CREATE TABLE feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classification_id VARCHAR(36) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- User Correction
    corrected_class VARCHAR(50),
    user_confidence ENUM('low', 'medium', 'high'),
    correction_reason TEXT,

    -- Corner Correction
    corrected_corners JSON,

    -- Tracking
    user_id VARCHAR(50),

    FOREIGN KEY (classification_id) REFERENCES classifications(id) ON DELETE CASCADE,
    INDEX idx_classification (classification_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `image_features` Tabelle (für Ähnlichkeitssuche)
```sql
CREATE TABLE image_features (
    id INT AUTO_INCREMENT PRIMARY KEY,
    classification_id VARCHAR(36) NOT NULL,

    -- Feature Vectors
    perceptual_hash VARCHAR(64),
    color_histogram BLOB,
    edge_histogram BLOB,
    text_features JSON,

    -- Hash Bucketing für schnelle Suche
    hash_bucket VARCHAR(16),

    FOREIGN KEY (classification_id) REFERENCES classifications(id) ON DELETE CASCADE,
    INDEX idx_hash_bucket (hash_bucket),
    INDEX idx_perceptual_hash (perceptual_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### `model_weights` Tabelle
```sql
CREATE TABLE model_weights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    weights JSON NOT NULL,
    thresholds JSON NOT NULL,

    -- Learning Stats
    feedback_count INT DEFAULT 0,
    accuracy_improvement FLOAT,

    -- Status
    is_active BOOLEAN DEFAULT FALSE,

    INDEX idx_version (version),
    INDEX idx_timestamp (timestamp),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Schritt 2: CI4-Controller erstellen

Erstelle `app/Controllers/ImageClassificationController.php`:

```php
<?php

namespace App\Controllers;

use CodeIgniter\RESTful\ResourceController;
use CodeIgniter\API\ResponseTrait;

class ImageClassificationController extends ResourceController
{
    use ResponseTrait;

    protected $classificationModel;
    protected $feedbackModel;
    protected $imageFeaturesModel;
    protected $modelWeightsModel;

    public function __construct()
    {
        $this->classificationModel = new \App\Models\ClassificationModel();
        $this->feedbackModel = new \App\Models\FeedbackModel();
        $this->imageFeaturesModel = new \App\Models\ImageFeaturesModel();
        $this->modelWeightsModel = new \App\Models\ModelWeightsModel();
    }

    /**
     * POST /api/v1/classifications
     * Speichert Klassifizierungsergebnis
     */
    public function storeClassification()
    {
        $data = $this->request->getJSON(true);

        // Validierung
        $validation = \Config\Services::validation();
        $validation->setRules([
            'classification_id' => 'required|max_length[36]',
            'timestamp' => 'required',
            'image_hash' => 'required|max_length[64]',
            'prediction.class' => 'required|in_list[arbeitsbericht,typeplate,document,photo]',
            'prediction.confidence' => 'required|decimal',
        ]);

        if (!$validation->run($data)) {
            return $this->failValidationErrors($validation->getErrors());
        }

        // Daten vorbereiten
        $classificationData = [
            'id' => $data['classification_id'],
            'timestamp' => $data['timestamp'],
            'image_hash' => $data['image_hash'],
            'predicted_class' => $data['prediction']['class'],
            'confidence' => $data['prediction']['confidence'],
            'score_AR' => $data['prediction']['scores']['AR'] ?? null,
            'score_TP' => $data['prediction']['scores']['TP'] ?? null,
            'score_DOC' => $data['prediction']['scores']['DOC'] ?? null,
            'score_PHOTO' => $data['prediction']['scores']['PHOTO'] ?? null,
            'features' => json_encode($data['features']),
            'model_version' => $data['model_version'] ?? '1.0.0',
            'weights_version' => $data['weights_version'] ?? '1.0.0',
        ];

        try {
            $this->classificationModel->insert($classificationData);

            return $this->respondCreated([
                'status' => 'success',
                'classification_id' => $data['classification_id']
            ]);
        } catch (\Exception $e) {
            log_message('error', 'Failed to store classification: ' . $e->getMessage());
            return $this->failServerError('Failed to store classification');
        }
    }

    /**
     * POST /api/v1/feedback
     * Speichert User-Feedback
     */
    public function storeFeedback()
    {
        $data = $this->request->getJSON(true);

        // Validierung
        $validation = \Config\Services::validation();
        $validation->setRules([
            'classification_id' => 'required|max_length[36]',
            'user_correction.corrected_class' => 'permit_empty|in_list[arbeitsbericht,typeplate,document,photo]',
            'user_correction.confidence' => 'permit_empty|in_list[low,medium,high]',
        ]);

        if (!$validation->run($data)) {
            return $this->failValidationErrors($validation->getErrors());
        }

        // Prüfen ob Klassifizierung existiert
        $classification = $this->classificationModel->find($data['classification_id']);
        if (!$classification) {
            return $this->failNotFound('Classification not found');
        }

        // Feedback speichern
        $feedbackData = [
            'classification_id' => $data['classification_id'],
            'timestamp' => $data['timestamp'] ?? date('Y-m-d H:i:s'),
            'corrected_class' => $data['user_correction']['corrected_class'] ?? null,
            'user_confidence' => $data['user_correction']['confidence'] ?? null,
            'correction_reason' => $data['user_correction']['reason'] ?? null,
            'corrected_corners' => isset($data['corrected_corners']) ? json_encode($data['corrected_corners']) : null,
        ];

        try {
            $this->feedbackModel->insert($feedbackData);

            return $this->respondCreated([
                'status' => 'success',
                'message' => 'Feedback stored'
            ]);
        } catch (\Exception $e) {
            log_message('error', 'Failed to store feedback: ' . $e->getMessage());
            return $this->failServerError('Failed to store feedback');
        }
    }

    /**
     * POST /api/v1/similar-images
     * Findet ähnliche Bilder (vereinfachte Version)
     */
    public function findSimilar()
    {
        $data = $this->request->getJSON(true);
        $limit = $data['limit'] ?? 10;

        // Hier würde Ähnlichkeitslogik implementiert werden
        // Für jetzt: Einfache Abfrage nach ähnlichen Klassifizierungen

        $results = $this->classificationModel
            ->orderBy('timestamp', 'DESC')
            ->limit($limit)
            ->findAll();

        return $this->respond([
            'results' => $results
        ]);
    }

    /**
     * GET /api/v1/model-weights/latest
     * Gibt aktuelle Model-Gewichte zurück
     */
    public function getLatestWeights()
    {
        $weights = $this->modelWeightsModel
            ->where('is_active', true)
            ->orderBy('timestamp', 'DESC')
            ->first();

        if (!$weights) {
            return $this->respond([
                'weights' => [],
                'thresholds' => [],
                'version' => '1.0.0'
            ]);
        }

        return $this->respond([
            'weights' => json_decode($weights['weights'], true),
            'thresholds' => json_decode($weights['thresholds'], true),
            'version' => $weights['version'],
            'feedback_count' => $weights['feedback_count']
        ]);
    }

    /**
     * POST /api/v1/model-weights
     * Aktualisiert Model-Gewichte
     */
    public function updateWeights()
    {
        $data = $this->request->getJSON(true);

        // Alte Gewichte deaktivieren
        $this->modelWeightsModel->where('is_active', true)->set(['is_active' => false])->update();

        // Neue Gewichte speichern
        $weightsData = [
            'version' => $data['version'] ?? '1.0.0',
            'weights' => json_encode($data['weights']),
            'thresholds' => json_encode($data['thresholds']),
            'is_active' => true,
        ];

        try {
            $this->modelWeightsModel->insert($weightsData);

            return $this->respondCreated([
                'status' => 'success',
                'message' => 'Weights updated'
            ]);
        } catch (\Exception $e) {
            log_message('error', 'Failed to update weights: ' . $e->getMessage());
            return $this->failServerError('Failed to update weights');
        }
    }

    /**
     * GET /api/v1/health
     * Health Check
     */
    public function health()
    {
        return $this->respond([
            'status' => 'ok',
            'timestamp' => date('Y-m-d H:i:s')
        ]);
    }
}
```

### Schritt 3: CI4-Models erstellen

#### `app/Models/ClassificationModel.php`
```php
<?php

namespace App\Models;

use CodeIgniter\Model;

class ClassificationModel extends Model
{
    protected $table = 'classifications';
    protected $primaryKey = 'id';
    protected $useAutoIncrement = false;
    protected $returnType = 'array';
    protected $useSoftDeletes = false;
    protected $allowedFields = [
        'id', 'timestamp', 'image_hash', 'predicted_class', 'confidence',
        'score_AR', 'score_TP', 'score_DOC', 'score_PHOTO',
        'features', 'image_width', 'image_height', 'image_format',
        'model_version', 'weights_version'
    ];
    protected $useTimestamps = false;
}
```

#### `app/Models/FeedbackModel.php`
```php
<?php

namespace App\Models;

use CodeIgniter\Model;

class FeedbackModel extends Model
{
    protected $table = 'feedback';
    protected $primaryKey = 'id';
    protected $returnType = 'array';
    protected $useSoftDeletes = false;
    protected $allowedFields = [
        'classification_id', 'timestamp', 'corrected_class',
        'user_confidence', 'correction_reason', 'corrected_corners', 'user_id'
    ];
    protected $useTimestamps = false;
}
```

#### `app/Models/ModelWeightsModel.php`
```php
<?php

namespace App\Models;

use CodeIgniter\Model;

class ModelWeightsModel extends Model
{
    protected $table = 'model_weights';
    protected $primaryKey = 'id';
    protected $returnType = 'array';
    protected $useSoftDeletes = false;
    protected $allowedFields = [
        'version', 'weights', 'thresholds', 'feedback_count',
        'accuracy_improvement', 'is_active'
    ];
    protected $useTimestamps = false;
}
```

### Schritt 4: CI4-Routes konfigurieren

Füge zu `app/Config/Routes.php` hinzu:

```php
// API v1 Routes
$routes->group('api/v1', ['namespace' => 'App\Controllers'], function($routes) {
    // Image Classification
    $routes->post('classifications', 'ImageClassificationController::storeClassification');
    $routes->post('feedback', 'ImageClassificationController::storeFeedback');
    $routes->post('similar-images', 'ImageClassificationController::findSimilar');

    // Model Weights
    $routes->get('model-weights/latest', 'ImageClassificationController::getLatestWeights');
    $routes->post('model-weights', 'ImageClassificationController::updateWeights');

    // Health
    $routes->get('health', 'ImageClassificationController::health');
});
```

### Schritt 5: Microservice konfigurieren

Aktiviere CI4-Integration im Microservice:

```bash
# Environment-Variablen setzen
export CI4_ENABLED=true
export CI4_BASE_URL="http://your-ci4-server/api/v1"
export CI4_API_KEY="your-secret-api-key"  # Optional

# Service neu starten
systemctl restart ocr-classifier.service
```

Oder in `/root/config.py` direkt ändern:

```python
CI4_CONFIG = {
    "base_url": "http://your-ci4-server/api/v1",
    "api_key": "your-secret-api-key",
    "enabled": True
}
```

### Schritt 6: Testen

```bash
# 1. CI4 Health Check
curl http://your-ci4-server/api/v1/health

# 2. Bild klassifizieren (Microservice)
curl -X POST http://localhost:8090/classify \
  -F "file=@test.jpg"

# 3. Prüfen ob in CI4-DB gespeichert
# Über CI4-Admin oder direkt in MySQL:
mysql> SELECT * FROM classifications ORDER BY timestamp DESC LIMIT 1;

# 4. Feedback senden
curl -X POST http://localhost:8090/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "classification_id": "YOUR-UUID-HERE",
    "corrected_class": "typeplate",
    "user_confidence": "high"
  }'
```

---

## 🏗️ Architektur

### Modulstruktur
```
/root/
├── classifier_service.py      # FastAPI Hauptservice
├── config.py                  # Zentrale Konfiguration
│
├── models/                    # ML-Modelle & Analyzer
│   ├── __init__.py
│   ├── corner_detector.py    # 4-Eckpunkte-Erkennung
│   └── ocr_analyzer.py       # OCR + Arbeitsbericht-Erkennung
│
├── features/                  # Feature-Extraction
│   ├── __init__.py
│   ├── color_analyzer.py     # LAB-Farbuniformität
│   └── line_analyzer.py      # Hough-Linien-Analyse
│
├── database/                  # CI4-Integration
│   ├── __init__.py
│   ├── ci4_client.py         # REST-API Client
│   └── schemas.py            # Pydantic Data Models
│
└── learning/                  # Zukünftig: Adaptives Lernen
    └── __init__.py
```

### Datenfluss

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /classify (image)
       ▼
┌─────────────────────────────────────┐
│  FastAPI Service (classifier_service.py)   │
├─────────────────────────────────────┤
│  1. Image Loading                   │
│  2. OCR Analysis (Tesseract)        │
│  3. Corner Detection (OpenCV)       │
│  4. CLIP Classification              │
│  5. Color Uniformity (LAB)          │
│  6. Line Analysis (Hough)           │
│  7. Score Calculation               │
│  8. Classification Decision         │
│  9. [Optional] Store to CI4         │
└──────┬──────────────────────────────┘
       │ Response (JSON)
       ▼
┌─────────────┐
│   Client    │
└─────────────┘
```

### Klassifizierungslogik

```
Scores berechnen:
├── AR  = Arbeitsbericht Score (Keyword "arbeitsbericht" + Zusatz-Keywords)
├── TP  = Typeplate Score (CLIP + Keywords + Color + Lines)
├── DOC = Document Score (Text-Länge + CLIP)
└── PHOTO = Photo Score (wenig Text + CLIP)

Entscheidung:
if AR >= 5.0:
    → arbeitsbericht
elif TP > max(DOC, PHOTO) AND TP >= 3.0:
    → typeplate
elif DOC > PHOTO AND DOC >= 1.5:
    → document
else:
    → photo
```

---

## 💡 Verwendung

### Python-Client Beispiel

```python
import requests

# Bild klassifizieren
with open('arbeitsbericht.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8090/classify',
        files={'file': f}
    )

result = response.json()
print(f"Klassifizierung: {result['predicted']}")
print(f"Konfidenz: {result['confidence']}")
print(f"Eckpunkte: {result['corners']['points']}")

# Feedback senden (falls falsch klassifiziert)
if result['predicted'] != 'arbeitsbericht':
    feedback = {
        'classification_id': result['classification_id'],
        'corrected_class': 'arbeitsbericht',
        'user_confidence': 'high',
        'correction_reason': 'Bild enthält eindeutig einen Arbeitsbericht'
    }

    requests.post(
        'http://localhost:8090/feedback',
        json=feedback
    )
```

### PHP-Client Beispiel (für CI4)

```php
<?php
// In deinem CI4-Controller

public function uploadImage()
{
    $file = $this->request->getFile('image');

    if (!$file->isValid()) {
        return $this->fail('Invalid file');
    }

    // Zu Microservice senden
    $client = \Config\Services::curlrequest();

    $response = $client->request('POST', 'http://localhost:8090/classify', [
        'multipart' => [
            [
                'name' => 'file',
                'contents' => file_get_contents($file->getTempName()),
                'filename' => $file->getName()
            ]
        ]
    ]);

    $result = json_decode($response->getBody(), true);

    // Klassifizierung verarbeiten
    if ($result['predicted'] === 'arbeitsbericht') {
        // Arbeitsbericht-spezifische Logik
        $this->processArbeitsbericht($result);
    } elseif ($result['predicted'] === 'typeplate') {
        // Typenschild-spezifische Logik
        $this->processTypeplate($result);
    }

    return $this->respond($result);
}
```

---

## 🔧 Troubleshooting

### Service startet nicht

```bash
# Logs ansehen
journalctl -u ocr-classifier.service -n 100 --no-pager

# Häufige Probleme:
# 1. Python-Pakete fehlen
/opt/ocr-env/bin/pip install -r requirements.txt

# 2. Tesseract nicht installiert
apt install tesseract-ocr tesseract-ocr-deu -y

# 3. Permissions
chown -R root:root /root
chmod +x /root/classifier_service.py
```

### CLIP-Model lädt nicht

```bash
# Manuell vorladen
cd /root
source /opt/ocr-env/bin/activate
python3 -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"
```

### CI4-Integration funktioniert nicht

```bash
# 1. CI4-Erreichbarkeit testen
curl http://your-ci4-server/api/v1/health

# 2. Microservice-Logs prüfen
journalctl -u ocr-classifier.service -f | grep CI4

# 3. CI4-Logs prüfen
tail -f /path/to/ci4/writable/logs/log-*.php

# 4. Debug-Modus aktivieren
# In config.py:
CI4_CONFIG["timeout"] = 30  # Längere Timeout
```

### Langsame Performance

```bash
# 1. CLIP-Model auf GPU (falls verfügbar)
# In classifier_service.py:
# clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to("cuda")

# 2. Kleineres CLIP-Model verwenden
# In classifier_service.py ersetzen:
# clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16")

# 3. Lazy-Loading aktivieren
# In config.py:
PERFORMANCE["lazy_feature_extraction"] = True
```

---

## 📝 Lizenz

Proprietär - Nur für autorisierte Nutzung

---

## 📧 Support

Bei Fragen oder Problemen:
- Logs prüfen: `journalctl -u ocr-classifier.service`
- Service neu starten: `systemctl restart ocr-classifier.service`
- Konfiguration überprüfen: `/root/config.py`
