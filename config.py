# config.py
# Zentrale Konfiguration mit adaptiven Gewichten für selbstlernendes System

import os
from typing import Dict, Any

class ClassificationConfig:
    """Zentrale Konfiguration für Klassifizierungs-Service."""

    # Version tracking
    VERSION = "1.0.0"

    # Klassifizierungs-Schwellwerte (adaptive)
    THRESHOLDS = {
        "arbeitsbericht": 5.0,  # Muss Keyword "Arbeitsbericht" enthalten
        "typeplate": 3.0,
        "document": 1.5,
        "photo": 0.0  # Fallback-Klasse
    }

    # Scoring-Gewichte (werden durch Learning angepasst)
    WEIGHTS = {
        "AR": {  # Arbeitsbericht
            "text_length_divisor": 500,
            "text_length_factor": 1.5,
            "keyword_multiplier": 2.0,
            "clip_bonus": 1.0,
            "min_text_length": 500  # Typisch für Arbeitsberichte
        },
        "TP": {  # Typeplate
            "clip_factor": 4.0,
            "keyword_multiplier": 1.5,
            "digit_ratio_factor": 10.0,
            "line_density_factor": 80.0,
            "color_uniformity_factor": 5.0,  # NEU
            "rect_score_factor": 3.0  # NEU
        },
        "DOC": {  # Document
            "text_length_divisor": 300,
            "clip_factor": 2.0
        },
        "PHOTO": {  # Photo
            "low_text_threshold": 20,
            "low_text_bonus": 2.0,
            "clip_factor": 2.0
        }
    }

    # Eckpunkt-Erkennung Parameter
    CORNER_DETECTION = {
        "method": "contour_based",  # primary method
        "fallback_method": "harris",
        # Contour detection
        "canny_low": 50,
        "canny_high": 150,
        "gaussian_blur_ksize": 5,
        "morphology_ksize": 5,
        "approx_epsilon": 0.02,  # Polygon approximation accuracy
        "min_area_ratio": 0.1,  # Minimum 10% of image area
        # Harris corner detection
        "harris_quality": 0.01,
        "harris_min_distance": 10,
        "harris_max_corners": 100
    }

    # Farbuniformität-Analyse Parameter
    COLOR_ANALYSIS = {
        "lab_std_threshold_high": 15.0,  # < 15 = sehr uniform
        "lab_std_threshold_medium": 25.0,  # < 25 = mäßig uniform
        "dominant_color_threshold": 0.6,  # > 60% = dominante Farbe
        "grid_divisions": 5,  # 5x5 Grid für regionale Analyse
        "kmeans_clusters": 3,  # K-Means für dominante Farben
        "kmeans_iterations": 10
    }

    # Linien-Erkennung Parameter
    LINE_ANALYSIS = {
        "hough_threshold": 80,
        "hough_min_line_length": 50,
        "hough_max_line_gap": 10,
        "angle_tolerance": 5.0,  # Grad für horizontal/vertikal Klassifizierung
        "edge_proximity_threshold": 20,  # Pixel-Abstand zum Rand
        "canny_low": 50,
        "canny_high": 150
    }

    # OCR & Text-Analyse
    OCR_CONFIG = {
        "tesseract_lang": "deu+eng",
        "arbeitsbericht_keywords": [
            "arbeitsbericht",  # HAUPTKEYWORD
            "unterschrift",
            "auftraggeber",
            "fahrer",
            "fahrzeug",
            "stempel",
            "kontakt",
            "fahrzeit",
            "arbeitszeit",
            "kunde",
            "auftragsnummer"
        ],
        "typeplate_keywords": [
            "serial", "serial no", "model", "made in", "type", "product",
            "rated", "voltage", "v", "w", "hz", "kw", "class", "refrigerant",
            "gas", "carrier", "castel", "built", "manufactured", "mpa", "pressure"
        ]
    }

    # Configuration API
    CONFIG_API_KEY = os.getenv("CONFIG_API_KEY", "")

    # CI4 Integration
    CI4_CONFIG = {
        "base_url": os.getenv("CI4_BASE_URL", "http://localhost/api/v1"),
        "api_key": os.getenv("CI4_API_KEY", ""),
        "timeout": 10,  # Sekunden
        "retry_attempts": 3,
        "retry_delay": 1,  # Sekunden
        "enabled": os.getenv("CI4_ENABLED", "false").lower() == "true"
    }

    # Feature-Extraktion
    FEATURE_CONFIG = {
        "perceptual_hash_size": 8,  # 8x8 = 64-bit hash
        "color_histogram_bins": 32,
        "edge_histogram_bins": 32,
        "clip_embedding_dim": 512,
        "similarity_weights": {
            "hash": 0.2,
            "color_hist": 0.2,
            "edge_hist": 0.2,
            "clip_embedding": 0.4
        }
    }

    # Learning System
    LEARNING_CONFIG = {
        "learning_rate": 0.1,  # Schrittweite für Gewichtsanpassung
        "reinforce_factor": 0.05,  # Bei korrekter Prediction
        "penalize_factor": -0.1,  # Bei falscher Prediction
        "reward_factor": 0.1,  # Bei Korrektur zur richtigen Klasse
        "threshold_recalc_interval": 50,  # Alle N Feedbacks
        "min_feedback_for_update": 10,  # Minimum Feedbacks vor Anwendung
        "weight_update_interval": 50  # Gewichte an CI4 senden
    }

    # Performance & Caching
    PERFORMANCE = {
        "enable_caching": True,
        "cache_ttl": 3600,  # Sekunden (1 Stunde)
        "max_cache_size": 1000,  # Anzahl gecachte Items
        "lazy_feature_extraction": True,  # Nur bei Bedarf extrahieren
        "async_feature_extraction": True  # Im Hintergrund extrahieren
    }

    @classmethod
    def get_arbeitsbericht_keywords(cls) -> list:
        """Gibt Arbeitsbericht-Keywords zurück."""
        return cls.OCR_CONFIG["arbeitsbericht_keywords"]

    @classmethod
    def get_typeplate_keywords(cls) -> list:
        """Gibt Typeplate-Keywords zurück."""
        return cls.OCR_CONFIG["typeplate_keywords"]

    @classmethod
    def update_weights(cls, new_weights: Dict[str, Any]):
        """
        Aktualisiert Gewichte (wird von Learning-System aufgerufen).

        Args:
            new_weights: Dictionary mit neuen Gewichten
        """
        for category, weights in new_weights.items():
            if category in cls.WEIGHTS:
                cls.WEIGHTS[category].update(weights)

    @classmethod
    def update_thresholds(cls, new_thresholds: Dict[str, float]):
        """
        Aktualisiert Klassifizierungs-Schwellwerte.

        Args:
            new_thresholds: Dictionary mit neuen Schwellwerten
        """
        cls.THRESHOLDS.update(new_thresholds)

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Exportiert Konfiguration als Dictionary."""
        return {
            "version": cls.VERSION,
            "thresholds": cls.THRESHOLDS,
            "weights": cls.WEIGHTS,
            "corner_detection": cls.CORNER_DETECTION,
            "color_analysis": cls.COLOR_ANALYSIS,
            "line_analysis": cls.LINE_ANALYSIS,
            "ocr_config": cls.OCR_CONFIG,
            "feature_config": cls.FEATURE_CONFIG,
            "learning_config": cls.LEARNING_CONFIG
        }


# Singleton-Instanz
config = ClassificationConfig()
