# database/ci4_client.py
# REST-API Client für CI4-Kommunikation

import requests
import logging
from typing import Dict, List, Optional
from config import config

logger = logging.getLogger(__name__)


class CI4Client:
    """
    REST-API Client für CodeIgniter 4 Backend.

    Handles:
    - Klassifizierungs-Speicherung
    - Feedback-Speicherung
    - Ähnlichkeitssuche
    - Model-Gewichte Sync
    """

    def __init__(self):
        self.cfg = config.CI4_CONFIG
        self.base_url = self.cfg["base_url"].rstrip('/')
        self.timeout = self.cfg["timeout"]
        self.enabled = self.cfg["enabled"]

        self.session = requests.Session()
        if self.cfg["api_key"]:
            self.session.headers.update({
                "Authorization": f"Bearer {self.cfg['api_key']}"
            })

    def store_classification(self, data: Dict) -> Optional[Dict]:
        """
        Speichert Klassifizierungsergebnis in CI4.

        Args:
            data: Classification data dictionary

        Returns:
            Response dict oder None bei Fehler/Deaktiviert
        """
        if not self.enabled:
            logger.debug("CI4 integration disabled, skipping store_classification")
            return None

        try:
            response = self.session.post(
                f"{self.base_url}/classifications",
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to store classification in CI4: {e}")
            return None

    def store_feedback(self, classification_id: str, feedback: Dict) -> Optional[Dict]:
        """
        Speichert User-Feedback in CI4.

        Args:
            classification_id: UUID der Klassifizierung
            feedback: Feedback data

        Returns:
            Response dict oder None
        """
        if not self.enabled:
            logger.debug("CI4 integration disabled, skipping store_feedback")
            return None

        try:
            payload = {
                "classification_id": classification_id,
                **feedback
            }

            response = self.session.post(
                f"{self.base_url}/feedback",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to store feedback in CI4: {e}")
            return None

    def find_similar_images(self, features: Dict, limit: int = 10) -> List[Dict]:
        """
        Findet ähnliche Bilder basierend auf Features.

        Args:
            features: Feature dictionary
            limit: Max Anzahl Ergebnisse

        Returns:
            List of similar classifications
        """
        if not self.enabled:
            return []

        try:
            response = self.session.post(
                f"{self.base_url}/similar-images",
                json={"features": features, "limit": limit},
                timeout=self.timeout * 2  # Längere Timeout für Suche
            )
            response.raise_for_status()
            return response.json().get("results", [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to find similar images: {e}")
            return []

    def get_model_weights(self) -> Optional[Dict]:
        """
        Lädt aktuelle Model-Gewichte von CI4.

        Returns:
            Weights dict oder None
        """
        if not self.enabled:
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/model-weights/latest",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get model weights: {e}")
            return None

    def update_model_weights(self, weights: Dict, thresholds: Dict) -> Optional[Dict]:
        """
        Aktualisiert Model-Gewichte in CI4.

        Args:
            weights: Updated weights
            thresholds: Updated thresholds

        Returns:
            Response dict oder None
        """
        if not self.enabled:
            return None

        try:
            payload = {
                "weights": weights,
                "thresholds": thresholds,
                "version": config.VERSION
            }

            response = self.session.post(
                f"{self.base_url}/model-weights",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update model weights: {e}")
            return None

    def get_classification(self, classification_id: str) -> Optional[Dict]:
        """
        Lädt einzelne Klassifizierung von CI4.

        Args:
            classification_id: UUID der Klassifizierung

        Returns:
            Classification dict oder None
        """
        if not self.enabled:
            logger.debug("CI4 integration disabled, skipping get_classification")
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/classifications/{classification_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get classification: {e}")
            return None

    def update_base_config(self, config_data: Dict) -> Optional[Dict]:
        """
        Speichert Basis-Konfiguration in CI4 (Config API only).
        Separate from learning weights.

        Args:
            config_data: Base configuration dictionary

        Returns:
            Response dict oder None
        """
        if not self.enabled:
            return None

        try:
            payload = {
                "config": config_data,
                "version": config.VERSION,
                "updated_by": "config_api"
            }

            response = self.session.post(
                f"{self.base_url}/config/base",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update base config in CI4: {e}")
            return None

    def get_base_config(self) -> Optional[Dict]:
        """
        Lädt Basis-Konfiguration von CI4.
        Separate from learning weights.

        Returns:
            Base configuration dict oder None
        """
        if not self.enabled:
            return None

        try:
            response = self.session.get(
                f"{self.base_url}/config/base/latest",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get base config from CI4: {e}")
            return None

    def health_check(self) -> bool:
        """
        Prüft ob CI4-API erreichbar ist.

        Returns:
            True wenn erreichbar
        """
        if not self.enabled:
            return False

        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200

        except requests.exceptions.RequestException:
            return False


# Singleton-Instanz
ci4_client = CI4Client()
