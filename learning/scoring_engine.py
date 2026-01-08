# learning/scoring_engine.py
# Adaptive Gewichtsanpassung basierend auf User-Feedback

import logging
from typing import Dict, List, Tuple
from datetime import datetime
from collections import Counter
import numpy as np
from config import config

logger = logging.getLogger(__name__)


class AdaptiveScoringEngine:
    """
    Gradient-Descent-inspirierte Gewichtsanpassung.

    Strategie:
    - Bei korrekter Vorhersage: Gewichte leicht verstärken (+5%)
    - Bei falscher Vorhersage:
      - Falsche Klasse: Gewichte reduzieren (-10%)
      - Richtige Klasse: Gewichte verstärken (+10%)
    - Alle 50 Feedbacks: Schwellwerte neu berechnen
    """

    def __init__(self):
        self.feedback_history: List[Dict] = []
        self.learning_rate = config.LEARNING_CONFIG["learning_rate"]
        self.feedback_count = 0
        self.weights_version = 1

    def adjust_weights_from_feedback(
        self,
        classification_data: dict,
        feedback: dict
    ) -> dict:
        """
        Passt Gewichte basierend auf einzelnem Feedback an.

        Args:
            classification_data: Original-Klassifizierung
            feedback: User-Korrektur

        Returns:
            Updated weights dictionary
        """
        predicted = classification_data['prediction']['class']
        correct = feedback['user_correction']['corrected_class']
        scores = classification_data['prediction']['scores']

        # Feedback speichern
        feedback_entry = {
            'predicted': predicted,
            'correct': correct,
            'scores': scores,
            'timestamp': datetime.now().isoformat(),
            'confidence': classification_data['prediction']['confidence']
        }
        self.feedback_history.append(feedback_entry)
        self.feedback_count += 1

        logger.info(f"Feedback #{self.feedback_count}: Predicted={predicted}, Correct={correct}")

        # Gewichte anpassen
        if predicted == correct:
            # Korrekte Vorhersage → Verstärken
            logger.info("Correct prediction - reinforcing weights")
            self._reinforce_weights(predicted, scores, factor=config.LEARNING_CONFIG["reinforce_factor"])
        else:
            # Falsche Vorhersage → Penalisieren + Belohnen
            logger.info(f"Incorrect prediction - penalizing {predicted}, rewarding {correct}")
            self._penalize_weights(predicted, scores, factor=config.LEARNING_CONFIG["penalize_factor"])
            self._reinforce_weights(correct, scores, factor=config.LEARNING_CONFIG["reward_factor"])

        # Alle 50 Feedbacks: Schwellwerte optimieren
        if self.feedback_count % config.LEARNING_CONFIG["threshold_recalc_interval"] == 0:
            logger.info("Recalculating thresholds based on feedback history")
            self._recalculate_thresholds()
            self.weights_version += 1

        return config.WEIGHTS

    def _reinforce_weights(self, class_name: str, scores: dict, factor: float):
        """
        Verstärkt Gewichte für eine Klasse.

        Args:
            class_name: Klassen-Name (arbeitsbericht, typeplate, document, photo)
            scores: Score-Dictionary (AR, TP, DOC, PHOTO)
            factor: Verstärkungsfaktor (z.B. 0.05 = 5% Erhöhung)
        """
        # Mapping von Klassennamen zu Score-Keys
        class_to_key = {
            'arbeitsbericht': 'AR',
            'typeplate': 'TP',
            'document': 'DOC',
            'photo': 'PHOTO'
        }

        if class_name not in class_to_key:
            logger.warning(f"Unknown class name: {class_name}")
            return

        key = class_to_key[class_name]

        # Gewichte der entsprechenden Klasse erhöhen
        if key in config.WEIGHTS:
            for weight_key in config.WEIGHTS[key]:
                if isinstance(config.WEIGHTS[key][weight_key], (int, float)):
                    old_value = config.WEIGHTS[key][weight_key]
                    new_value = old_value * (1 + factor)
                    config.WEIGHTS[key][weight_key] = new_value
                    logger.debug(f"Reinforced {key}.{weight_key}: {old_value:.3f} → {new_value:.3f}")

    def _penalize_weights(self, class_name: str, scores: dict, factor: float):
        """
        Reduziert Gewichte für eine Klasse.

        Args:
            class_name: Klassen-Name
            scores: Score-Dictionary
            factor: Penalisierungs-Faktor (z.B. -0.1 = 10% Reduktion)
        """
        class_to_key = {
            'arbeitsbericht': 'AR',
            'typeplate': 'TP',
            'document': 'DOC',
            'photo': 'PHOTO'
        }

        if class_name not in class_to_key:
            logger.warning(f"Unknown class name: {class_name}")
            return

        key = class_to_key[class_name]

        # Gewichte reduzieren (aber nicht unter Minimum)
        MIN_WEIGHT = 0.1  # Vermeide dass Gewichte zu klein werden

        if key in config.WEIGHTS:
            for weight_key in config.WEIGHTS[key]:
                if isinstance(config.WEIGHTS[key][weight_key], (int, float)):
                    old_value = config.WEIGHTS[key][weight_key]
                    new_value = max(old_value * (1 + factor), MIN_WEIGHT)
                    config.WEIGHTS[key][weight_key] = new_value
                    logger.debug(f"Penalized {key}.{weight_key}: {old_value:.3f} → {new_value:.3f}")

    def _recalculate_thresholds(self):
        """
        Berechnet optimale Schwellwerte basierend auf Feedback-Historie.

        Verwendet einfache Statistik-basierte Optimierung:
        - Berechnet Score-Verteilungen für jede Klasse
        - Setzt Schwellwerte basierend auf Median/Quantilen
        """
        if len(self.feedback_history) < config.LEARNING_CONFIG["min_feedback_for_update"]:
            logger.info("Not enough feedback for threshold recalculation")
            return

        # Gruppiere Feedback nach korrekter Klasse
        class_scores = {
            'arbeitsbericht': [],
            'typeplate': [],
            'document': [],
            'photo': []
        }

        for entry in self.feedback_history:
            correct_class = entry['correct']
            scores = entry['scores']

            # Mapping von Klasse zu Score-Key
            class_to_score_key = {
                'arbeitsbericht': 'AR',
                'typeplate': 'TP',
                'document': 'DOC',
                'photo': 'PHOTO'
            }

            if correct_class in class_to_score_key:
                score_key = class_to_score_key[correct_class]
                if score_key in scores:
                    class_scores[correct_class].append(scores[score_key])

        # Berechne neue Schwellwerte (25. Perzentil)
        # Damit werden 75% der korrekten Vorhersagen erkannt
        for class_name, scores in class_scores.items():
            if len(scores) >= 5:  # Mindestens 5 Samples
                scores_array = np.array(scores)
                # 25. Perzentil als Schwellwert (konservativ)
                new_threshold = np.percentile(scores_array, 25)

                old_threshold = config.THRESHOLDS.get(class_name, 0.0)

                # Nur anpassen wenn Änderung signifikant (>10%)
                if abs(new_threshold - old_threshold) / max(old_threshold, 0.1) > 0.1:
                    config.THRESHOLDS[class_name] = round(float(new_threshold), 2)
                    logger.info(
                        f"Updated threshold for {class_name}: "
                        f"{old_threshold:.2f} → {new_threshold:.2f}"
                    )

    def get_statistics(self) -> dict:
        """
        Gibt Statistiken über das Learning zurück.

        Returns:
            {
                "total_feedback": 123,
                "accuracy": 0.85,
                "class_distribution": {...},
                "confusion_matrix": {...},
                "weights_version": 3
            }
        """
        if not self.feedback_history:
            return {
                "total_feedback": 0,
                "accuracy": 0.0,
                "class_distribution": {},
                "weights_version": self.weights_version
            }

        # Genauigkeit berechnen
        correct_predictions = sum(
            1 for entry in self.feedback_history
            if entry['predicted'] == entry['correct']
        )
        accuracy = correct_predictions / len(self.feedback_history)

        # Klassen-Verteilung
        predicted_classes = [entry['predicted'] for entry in self.feedback_history]
        correct_classes = [entry['correct'] for entry in self.feedback_history]

        class_distribution = {
            'predicted': dict(Counter(predicted_classes)),
            'correct': dict(Counter(correct_classes))
        }

        # Einfache Confusion-Matrix
        confusion = {}
        for entry in self.feedback_history:
            key = f"{entry['predicted']} -> {entry['correct']}"
            confusion[key] = confusion.get(key, 0) + 1

        return {
            "total_feedback": len(self.feedback_history),
            "accuracy": round(accuracy, 3),
            "class_distribution": class_distribution,
            "confusion_matrix": confusion,
            "weights_version": self.weights_version,
            "current_thresholds": config.THRESHOLDS.copy(),
            "recent_feedback": self.feedback_history[-10:]  # Letzte 10 Feedbacks
        }

    def reset_learning(self):
        """Reset Learning-Historie (für Testing oder Rollback)."""
        logger.warning("Resetting learning history")
        self.feedback_history = []
        self.feedback_count = 0
        # Gewichte NICHT zurücksetzen - nur Historie


# Singleton-Instanz
scoring_engine = AdaptiveScoringEngine()
