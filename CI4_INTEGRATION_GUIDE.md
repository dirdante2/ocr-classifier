# CodeIgniter 4 Integration - Detaillierte Anleitung

Schritt-für-Schritt Anleitung zur Integration des Bilderkennung-Microservices in dein CodeIgniter 4 Projekt.

---

## 📋 Übersicht

Der Microservice kommuniziert mit deinem CI4-Projekt über REST-API Endpunkte. Die Integration ermöglicht:

✅ Persistente Speicherung von Klassifizierungen
✅ User-Feedback-System für kontinuierliches Lernen
✅ Ähnlichkeitssuche in vergangenen Klassifizierungen
✅ Adaptive Model-Gewichte basierend auf Feedback

---

## 🚀 Schnellstart (5 Minuten)

```bash
# 1. Datenbank-Migrations ausführen
cd /path/to/your/ci4/project
php spark migrate:create create_image_classification_tables

# 2. Controller erstellen
php spark make:controller ImageClassification --restful

# 3. Models erstellen
php spark make:model ClassificationModel
php spark make:model FeedbackModel

# 4. Routes hinzufügen (siehe unten)

# 5. Microservice konfigurieren
export CI4_ENABLED=true
export CI4_BASE_URL="http://localhost/api/v1"
systemctl restart ocr-classifier.service
```

---

## 📊 Schritt 1: Datenbank-Setup

### 1.1 Migration erstellen

Erstelle `app/Database/Migrations/YYYY-MM-DD-HHMMSS_CreateImageClassificationTables.php`:

```php
<?php

namespace App\Database\Migrations;

use CodeIgniter\Database\Migration;

class CreateImageClassificationTables extends Migration
{
    public function up()
    {
        // 1. Classifications Table
        $this->forge->addField([
            'id' => [
                'type' => 'VARCHAR',
                'constraint' => 36,
            ],
            'timestamp' => [
                'type' => 'TIMESTAMP',
                'null' => false,
            ],
            'image_hash' => [
                'type' => 'VARCHAR',
                'constraint' => 64,
                'null' => false,
            ],
            'predicted_class' => [
                'type' => 'VARCHAR',
                'constraint' => 50,
                'null' => false,
            ],
            'confidence' => [
                'type' => 'FLOAT',
                'null' => true,
            ],
            'score_AR' => [
                'type' => 'FLOAT',
                'null' => true,
            ],
            'score_TP' => [
                'type' => 'FLOAT',
                'null' => true,
            ],
            'score_DOC' => [
                'type' => 'FLOAT',
                'null' => true,
            ],
            'score_PHOTO' => [
                'type' => 'FLOAT',
                'null' => true,
            ],
            'features' => [
                'type' => 'JSON',
                'null' => false,
            ],
            'image_width' => [
                'type' => 'INT',
                'null' => true,
            ],
            'image_height' => [
                'type' => 'INT',
                'null' => true,
            ],
            'image_format' => [
                'type' => 'VARCHAR',
                'constraint' => 10,
                'null' => true,
            ],
            'model_version' => [
                'type' => 'VARCHAR',
                'constraint' => 20,
                'null' => true,
            ],
            'weights_version' => [
                'type' => 'VARCHAR',
                'constraint' => 20,
                'null' => true,
            ],
            'created_at' => [
                'type' => 'TIMESTAMP',
                'null' => true,
            ],
            'updated_at' => [
                'type' => 'TIMESTAMP',
                'null' => true,
            ],
        ]);

        $this->forge->addKey('id', true);
        $this->forge->addKey('timestamp');
        $this->forge->addKey('image_hash');
        $this->forge->addKey('predicted_class');
        $this->forge->createTable('classifications');

        // 2. Feedback Table
        $this->forge->addField([
            'id' => [
                'type' => 'INT',
                'constraint' => 11,
                'unsigned' => true,
                'auto_increment' => true,
            ],
            'classification_id' => [
                'type' => 'VARCHAR',
                'constraint' => 36,
                'null' => false,
            ],
            'timestamp' => [
                'type' => 'TIMESTAMP',
                'null' => false,
            ],
            'corrected_class' => [
                'type' => 'VARCHAR',
                'constraint' => 50,
                'null' => true,
            ],
            'user_confidence' => [
                'type' => 'ENUM',
                'constraint' => ['low', 'medium', 'high'],
                'null' => true,
            ],
            'correction_reason' => [
                'type' => 'TEXT',
                'null' => true,
            ],
            'corrected_corners' => [
                'type' => 'JSON',
                'null' => true,
            ],
            'user_id' => [
                'type' => 'VARCHAR',
                'constraint' => 50,
                'null' => true,
            ],
            'created_at' => [
                'type' => 'TIMESTAMP',
                'null' => true,
            ],
        ]);

        $this->forge->addKey('id', true);
        $this->forge->addKey('classification_id');
        $this->forge->addKey('timestamp');
        $this->forge->addForeignKey('classification_id', 'classifications', 'id', 'CASCADE', 'CASCADE');
        $this->forge->createTable('feedback');

        // 3. Image Features Table (für Ähnlichkeitssuche)
        $this->forge->addField([
            'id' => [
                'type' => 'INT',
                'constraint' => 11,
                'unsigned' => true,
                'auto_increment' => true,
            ],
            'classification_id' => [
                'type' => 'VARCHAR',
                'constraint' => 36,
                'null' => false,
            ],
            'perceptual_hash' => [
                'type' => 'VARCHAR',
                'constraint' => 64,
                'null' => true,
            ],
            'color_histogram' => [
                'type' => 'BLOB',
                'null' => true,
            ],
            'edge_histogram' => [
                'type' => 'BLOB',
                'null' => true,
            ],
            'text_features' => [
                'type' => 'JSON',
                'null' => true,
            ],
            'hash_bucket' => [
                'type' => 'VARCHAR',
                'constraint' => 16,
                'null' => true,
            ],
        ]);

        $this->forge->addKey('id', true);
        $this->forge->addKey('hash_bucket');
        $this->forge->addKey('perceptual_hash');
        $this->forge->addForeignKey('classification_id', 'classifications', 'id', 'CASCADE', 'CASCADE');
        $this->forge->createTable('image_features');

        // 4. Model Weights Table
        $this->forge->addField([
            'id' => [
                'type' => 'INT',
                'constraint' => 11,
                'unsigned' => true,
                'auto_increment' => true,
            ],
            'version' => [
                'type' => 'VARCHAR',
                'constraint' => 20,
                'null' => false,
            ],
            'timestamp' => [
                'type' => 'TIMESTAMP',
                'null' => false,
            ],
            'weights' => [
                'type' => 'JSON',
                'null' => false,
            ],
            'thresholds' => [
                'type' => 'JSON',
                'null' => false,
            ],
            'feedback_count' => [
                'type' => 'INT',
                'default' => 0,
            ],
            'accuracy_improvement' => [
                'type' => 'FLOAT',
                'null' => true,
            ],
            'is_active' => [
                'type' => 'BOOLEAN',
                'default' => false,
            ],
        ]);

        $this->forge->addKey('id', true);
        $this->forge->addKey('version');
        $this->forge->addKey('timestamp');
        $this->forge->addKey('is_active');
        $this->forge->createTable('model_weights');
    }

    public function down()
    {
        $this->forge->dropTable('feedback', true);
        $this->forge->dropTable('image_features', true);
        $this->forge->dropTable('model_weights', true);
        $this->forge->dropTable('classifications', true);
    }
}
```

### 1.2 Migration ausführen

```bash
cd /path/to/ci4/project
php spark migrate
```

---

## 🎯 Schritt 2: Models erstellen

### 2.1 ClassificationModel

`app/Models/ClassificationModel.php`:

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

    protected $useTimestamps = true;
    protected $createdField = 'created_at';
    protected $updatedField = 'updated_at';

    protected $validationRules = [
        'id' => 'required|max_length[36]',
        'image_hash' => 'required|max_length[64]',
        'predicted_class' => 'required|in_list[arbeitsbericht,typeplate,document,photo]',
    ];

    /**
     * Statistiken für Dashboard
     */
    public function getStatistics($days = 30)
    {
        $date = date('Y-m-d H:i:s', strtotime("-{$days} days"));

        return [
            'total' => $this->where('timestamp >=', $date)->countAllResults(),
            'by_class' => $this->select('predicted_class, COUNT(*) as count')
                ->where('timestamp >=', $date)
                ->groupBy('predicted_class')
                ->findAll(),
            'avg_confidence' => $this->selectAvg('confidence')
                ->where('timestamp >=', $date)
                ->first(),
        ];
    }

    /**
     * Suche Klassifizierungen mit Filter
     */
    public function search($filters = [])
    {
        $builder = $this->builder();

        if (!empty($filters['class'])) {
            $builder->where('predicted_class', $filters['class']);
        }

        if (!empty($filters['min_confidence'])) {
            $builder->where('confidence >=', $filters['min_confidence']);
        }

        if (!empty($filters['start_date'])) {
            $builder->where('timestamp >=', $filters['start_date']);
        }

        if (!empty($filters['end_date'])) {
            $builder->where('timestamp <=', $filters['end_date']);
        }

        return $builder->orderBy('timestamp', 'DESC')->findAll();
    }
}
```

### 2.2 FeedbackModel

`app/Models/FeedbackModel.php`:

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

    protected $useTimestamps = true;
    protected $createdField = 'created_at';

    protected $validationRules = [
        'classification_id' => 'required|max_length[36]',
        'corrected_class' => 'permit_empty|in_list[arbeitsbericht,typeplate,document,photo]',
        'user_confidence' => 'permit_empty|in_list[low,medium,high]',
    ];

    /**
     * Feedback mit Klassifizierungsdaten
     */
    public function getFeedbackWithClassification($limit = 50)
    {
        return $this->select('feedback.*, classifications.*')
            ->join('classifications', 'classifications.id = feedback.classification_id')
            ->orderBy('feedback.timestamp', 'DESC')
            ->limit($limit)
            ->findAll();
    }

    /**
     * Accuracy-Berechnung
     */
    public function calculateAccuracy($days = 30)
    {
        $date = date('Y-m-d H:i:s', strtotime("-{$days} days"));

        $feedbacks = $this->select('feedback.*, classifications.predicted_class')
            ->join('classifications', 'classifications.id = feedback.classification_id')
            ->where('feedback.timestamp >=', $date)
            ->findAll();

        if (empty($feedbacks)) {
            return null;
        }

        $correct = 0;
        $total = count($feedbacks);

        foreach ($feedbacks as $fb) {
            if ($fb['corrected_class'] === $fb['predicted_class']) {
                $correct++;
            }
        }

        return [
            'accuracy' => $correct / $total,
            'correct' => $correct,
            'total' => $total
        ];
    }
}
```

### 2.3 ModelWeightsModel

`app/Models/ModelWeightsModel.php`:

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
        'version', 'timestamp', 'weights', 'thresholds',
        'feedback_count', 'accuracy_improvement', 'is_active'
    ];

    protected $useTimestamps = false;

    /**
     * Aktiviert neue Gewichte und deaktiviert alte
     */
    public function activateWeights($weightsId)
    {
        // Alte deaktivieren
        $this->where('is_active', true)->set(['is_active' => false])->update();

        // Neue aktivieren
        return $this->update($weightsId, ['is_active' => true]);
    }

    /**
     * Gibt aktuelle Gewichte zurück
     */
    public function getActive()
    {
        return $this->where('is_active', true)->first();
    }
}
```

---

## 🔌 Schritt 3: Controller implementieren

`app/Controllers/Api/ImageClassificationController.php`:

```php
<?php

namespace App\Controllers\Api;

use CodeIgniter\RESTful\ResourceController;
use CodeIgniter\API\ResponseTrait;
use App\Models\ClassificationModel;
use App\Models\FeedbackModel;
use App\Models\ModelWeightsModel;

class ImageClassificationController extends ResourceController
{
    use ResponseTrait;

    protected $classificationModel;
    protected $feedbackModel;
    protected $weightsModel;
    protected $format = 'json';

    public function __construct()
    {
        $this->classificationModel = new ClassificationModel();
        $this->feedbackModel = new FeedbackModel();
        $this->weightsModel = new ModelWeightsModel();
    }

    /**
     * POST /api/v1/classifications
     */
    public function storeClassification()
    {
        $data = $this->request->getJSON(true);

        // Validierung
        if (!$this->classificationModel->insert($this->prepareClassificationData($data))) {
            return $this->failValidationErrors($this->classificationModel->errors());
        }

        return $this->respondCreated([
            'status' => 'success',
            'classification_id' => $data['classification_id']
        ]);
    }

    /**
     * POST /api/v1/feedback
     */
    public function storeFeedback()
    {
        $data = $this->request->getJSON(true);

        // Prüfen ob Klassifizierung existiert
        if (!$this->classificationModel->find($data['classification_id'])) {
            return $this->failNotFound('Classification not found');
        }

        if (!$this->feedbackModel->insert($this->prepareFeedbackData($data))) {
            return $this->failValidationErrors($this->feedbackModel->errors());
        }

        return $this->respondCreated([
            'status' => 'success',
            'message' => 'Feedback stored'
        ]);
    }

    /**
     * POST /api/v1/similar-images
     */
    public function findSimilar()
    {
        $data = $this->request->getJSON(true);
        $limit = $data['limit'] ?? 10;

        // Vereinfachte Ähnlichkeitssuche
        // TODO: Implementiere echte Feature-basierte Suche
        $results = $this->classificationModel
            ->orderBy('timestamp', 'DESC')
            ->limit($limit)
            ->findAll();

        return $this->respond(['results' => $results]);
    }

    /**
     * GET /api/v1/model-weights/latest
     */
    public function getLatestWeights()
    {
        $weights = $this->weightsModel->getActive();

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
     */
    public function updateWeights()
    {
        $data = $this->request->getJSON(true);

        $weightsData = [
            'version' => $data['version'] ?? '1.0.0',
            'weights' => json_encode($data['weights']),
            'thresholds' => json_encode($data['thresholds']),
            'timestamp' => date('Y-m-d H:i:s'),
            'is_active' => false  // Wird später aktiviert
        ];

        $weightsId = $this->weightsModel->insert($weightsData);

        if (!$weightsId) {
            return $this->failValidationErrors($this->weightsModel->errors());
        }

        // Neue Gewichte aktivieren
        $this->weightsModel->activateWeights($weightsId);

        return $this->respondCreated([
            'status' => 'success',
            'message' => 'Weights updated',
            'weights_id' => $weightsId
        ]);
    }

    /**
     * GET /api/v1/health
     */
    public function health()
    {
        return $this->respond([
            'status' => 'ok',
            'timestamp' => date('Y-m-d H:i:s'),
            'database' => $this->checkDatabase()
        ]);
    }

    // Helper Methods

    private function prepareClassificationData($data)
    {
        return [
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
    }

    private function prepareFeedbackData($data)
    {
        return [
            'classification_id' => $data['classification_id'],
            'timestamp' => $data['timestamp'] ?? date('Y-m-d H:i:s'),
            'corrected_class' => $data['user_correction']['corrected_class'] ?? null,
            'user_confidence' => $data['user_correction']['confidence'] ?? null,
            'correction_reason' => $data['user_correction']['reason'] ?? null,
            'corrected_corners' => isset($data['corrected_corners']) ? json_encode($data['corrected_corners']) : null,
        ];
    }

    private function checkDatabase()
    {
        try {
            $db = \Config\Database::connect();
            return $db->connID ? 'connected' : 'disconnected';
        } catch (\Exception $e) {
            return 'error';
        }
    }
}
```

---

## 🛣️ Schritt 4: Routes konfigurieren

`app/Config/Routes.php`:

```php
<?php

// ... existing routes ...

// API v1 Routes
$routes->group('api/v1', ['namespace' => 'App\Controllers\Api'], function($routes) {
    // Image Classification
    $routes->post('classifications', 'ImageClassificationController::storeClassification');
    $routes->post('feedback', 'ImageClassificationController::storeFeedback');
    $routes->post('similar-images', 'ImageClassificationController::findSimilar');

    // Model Weights
    $routes->get('model-weights/latest', 'ImageClassificationController::getLatestWeights');
    $routes->post('model-weights', 'ImageClassificationController::updateWeights');

    // Health Check
    $routes->get('health', 'ImageClassificationController::health');
});
```

---

## 🔐 Schritt 5: Authentifizierung (Optional)

Wenn du die API absichern möchtest:

### Filter erstellen

`app/Filters/ApiAuthFilter.php`:

```php
<?php

namespace App\Filters;

use CodeIgniter\HTTP\RequestInterface;
use CodeIgniter\HTTP\ResponseInterface;
use CodeIgniter\Filters\FilterInterface;

class ApiAuthFilter implements FilterInterface
{
    public function before(RequestInterface $request, $arguments = null)
    {
        $authHeader = $request->getHeaderLine('Authorization');

        if (empty($authHeader)) {
            return service('response')
                ->setJSON(['error' => 'Missing Authorization header'])
                ->setStatusCode(401);
        }

        // Bearer Token Validierung
        if (!str_starts_with($authHeader, 'Bearer ')) {
            return service('response')
                ->setJSON(['error' => 'Invalid Authorization format'])
                ->setStatusCode(401);
        }

        $token = substr($authHeader, 7);

        // Token validieren (z.B. gegen Datenbank)
        $apiKey = env('API_KEY', 'your-secret-key');

        if ($token !== $apiKey) {
            return service('response')
                ->setJSON(['error' => 'Invalid API key'])
                ->setStatusCode(401);
        }

        return $request;
    }

    public function after(RequestInterface $request, ResponseInterface $response, $arguments = null)
    {
        // Nach-Verarbeitung falls nötig
    }
}
```

### Filter registrieren

`app/Config/Filters.php`:

```php
<?php

public $aliases = [
    // ... existing filters ...
    'apiauth' => \App\Filters\ApiAuthFilter::class,
];

public $filters = [
    'apiauth' => [
        'before' => [
            'api/*'  // Alle API-Routes schützen
        ]
    ]
];
```

### Microservice konfigurieren

```bash
export CI4_API_KEY="your-secret-key"
systemctl restart ocr-classifier.service
```

---

## ✅ Schritt 6: Testen

### Test-Script erstellen

`tests/api_test.php`:

```php
<?php

// CI4 Health Check
$ch = curl_init('http://localhost/api/v1/health');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
echo "CI4 Health: " . $response . "\n";
curl_close($ch);

// Microservice Health Check
$ch = curl_init('http://localhost:8090/health');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
echo "Microservice Health: " . $response . "\n";
curl_close($ch);

// Test Classification
$file = '/path/to/test-image.jpg';
$ch = curl_init('http://localhost:8090/classify');
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, [
    'file' => new CURLFile($file)
]);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
curl_close($ch);

$result = json_decode($response, true);
echo "Classification: " . $result['predicted'] . "\n";
echo "Classification ID: " . $result['classification_id'] . "\n";

// Prüfen ob in DB gespeichert
// ...
```

---

## 📊 Schritt 7: Dashboard (Optional)

Erstelle ein Admin-Dashboard um Klassifizierungen anzuzeigen:

`app/Controllers/Admin/DashboardController.php`:

```php
<?php

namespace App\Controllers\Admin;

use App\Controllers\BaseController;
use App\Models\ClassificationModel;
use App\Models\FeedbackModel;

class DashboardController extends BaseController
{
    public function index()
    {
        $classificationModel = new ClassificationModel();
        $feedbackModel = new FeedbackModel();

        $data = [
            'statistics' => $classificationModel->getStatistics(30),
            'accuracy' => $feedbackModel->calculateAccuracy(30),
            'recent_classifications' => $classificationModel
                ->orderBy('timestamp', 'DESC')
                ->limit(20)
                ->findAll(),
            'recent_feedback' => $feedbackModel
                ->getFeedbackWithClassification(20)
        ];

        return view('admin/dashboard', $data);
    }
}
```

---

## 🎉 Fertig!

Dein CI4-Projekt ist nun vollständig mit dem Bilderkennung-Microservice integriert!

### Nächste Schritte:

1. **Tests durchführen** mit verschiedenen Bildtypen
2. **Monitoring einrichten** für API-Calls und Errors
3. **Frontend integrieren** für Bild-Upload und Feedback
4. **Performance optimieren** basierend auf Nutzung

### Hilfreiche Kommandos:

```bash
# CI4-Logs ansehen
tail -f /path/to/ci4/writable/logs/log-*.php

# Microservice-Logs ansehen
journalctl -u ocr-classifier.service -f

# Datenbank-Status prüfen
mysql> SELECT COUNT(*) FROM classifications;
mysql> SELECT predicted_class, COUNT(*) FROM classifications GROUP BY predicted_class;
```
