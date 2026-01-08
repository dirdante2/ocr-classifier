# learning/feedback_processor.py
# Verarbeitet User-Feedback und koordiniert Learning

import logging
from typing import Dict, Optional
from learning.scoring_engine import scoring_engine
from features.feature_extractor import FeatureExtractor
from database.ci4_client import ci4_client
from config import config

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """
    Verarbeitet User-Feedback und koordiniert Learning.

    Workflow:
    1. Original-Klassifizierung von CI4 laden
    2. Feedback an CI4 speichern
    3. Gewichte anpassen (scoring_engine)
    4. Bei Bedarf: Gewichte an CI4 zurückschreiben
    """

    def __init__(self, clip_model=None, clip_processor=None):
        """
        Initialisiert Feedback-Prozessor.

        Args:
            clip_model: Optional CLIP-Model
            clip_processor: Optional CLIP-Processor
        """
        self.scoring_engine = scoring_engine
        self.feature_extractor = FeatureExtractor(clip_model, clip_processor)

    def process_feedback(
        self,
        classification_id: str,
        feedback_data: dict
    ) -> dict:
        """
        Verarbeitet Feedback und triggert Learning.

        Args:
            classification_id: UUID der Klassifizierung
            feedback_data: Feedback-Dictionary

        Returns:
            {
                "status": "success" | "error",
                "message": "...",
                "weights_updated": True/False,
                "feedback_count": 51,
                "current_accuracy": 0.87
            }
        """
        try:
            # 1. Original-Klassifizierung von CI4 laden
            if ci4_client.enabled:
                original = ci4_client.get_classification(classification_id)

                if not original:
                    return {
                        "status": "error",
                        "message": "Classification not found in CI4"
                    }
            else:
                # CI4 disabled - kann keine Original-Klassifizierung laden
                logger.warning("CI4 disabled - cannot load original classification for learning")
                return {
                    "status": "warning",
                    "message": "CI4 integration disabled, feedback not processed for learning"
                }

            # 2. Feedback an CI4 speichern
            feedback_stored = ci4_client.store_feedback(classification_id, feedback_data)

            if not feedback_stored:
                logger.warning("Failed to store feedback in CI4")

            # 3. Gewichte anpassen
            updated_weights = self.scoring_engine.adjust_weights_from_feedback(
                original,
                feedback_data
            )

            # 4. Bei genug Feedbacks: Gewichte an CI4 senden
            feedback_count = self.scoring_engine.feedback_count
            weight_update_interval = config.LEARNING_CONFIG["weight_update_interval"]

            weights_updated = False
            if feedback_count % weight_update_interval == 0:
                logger.info(f"Updating weights in CI4 (feedback count: {feedback_count})")
                update_result = ci4_client.update_model_weights(
                    updated_weights,
                    config.THRESHOLDS
                )

                weights_updated = update_result is not None

            # 5. Statistiken abrufen
            stats = self.scoring_engine.get_statistics()

            return {
                "status": "success",
                "message": "Feedback processed and weights adjusted",
                "weights_updated": weights_updated,
                "feedback_count": feedback_count,
                "current_accuracy": stats.get("accuracy", 0.0),
                "weights_version": stats.get("weights_version", 1)
            }

        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
            return {
                "status": "error",
                "message": f"Feedback processing failed: {str(e)}"
            }

    def get_learning_statistics(self) -> dict:
        """
        Gibt detaillierte Learning-Statistiken zurück.

        Returns:
            Statistiken vom scoring_engine
        """
        return self.scoring_engine.get_statistics()

    def reset_learning(self):
        """
        Reset Learning-Historie (Admin-Funktion).

        ACHTUNG: Löscht alle Feedback-Historie!
        """
        logger.warning("Resetting all learning history")
        self.scoring_engine.reset_learning()

        return {
            "status": "success",
            "message": "Learning history reset"
        }


# Singleton-Instanz (wird beim Import erstellt, aber CLIP-Model wird später gesetzt)
feedback_processor = None


def initialize_feedback_processor(clip_model=None, clip_processor=None):
    """
    Initialisiert Feedback-Prozessor mit CLIP-Model.

    Sollte beim Start des Services aufgerufen werden.
    """
    global feedback_processor
    feedback_processor = FeedbackProcessor(clip_model, clip_processor)
    logger.info("FeedbackProcessor initialized")
    return feedback_processor
