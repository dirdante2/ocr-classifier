# features/color_analyzer.py
# Farbuniformitäts-Analyse für Typenschild-Erkennung

import cv2
import numpy as np
from PIL import Image
from typing import Dict
from config import config


class ColorAnalyzer:
    """
    Analysiert Farbuniformität - Typenschilder haben oft uniforme Hintergründe.

    Verwendet LAB-Farbraum für perzeptuell uniforme Messungen.
    """

    def __init__(self):
        self.config = config.COLOR_ANALYSIS

    def analyze_color_uniformity(self, image: Image.Image) -> Dict:
        """
        Führt Farbuniformitäts-Analyse durch.

        Returns:
            {
                "global_std": 12.3,
                "regional_std": 14.5,
                "dominant_color_ratio": 0.67,
                "uniformity_score": 5.0,
                "is_uniform": True
            }
        """
        img_array = np.array(image.convert("RGB"))

        # Zu LAB konvertieren (perzeptuell uniform)
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)

        # 1. Globale Uniformität (Standardabweichung)
        l_std = np.std(lab[:, :, 0])  # Lightness
        a_std = np.std(lab[:, :, 1])  # Green-Red
        b_std = np.std(lab[:, :, 2])  # Blue-Yellow

        global_std = (l_std + a_std + b_std) / 3.0

        # 2. Regionale Analyse (Grid)
        regional_std = self._analyze_regional_uniformity(lab)

        # 3. Dominante Farbe
        dominant_ratio = self._calculate_dominant_color_ratio(img_array)

        # 4. Scoring
        uniformity_score = self._calculate_uniformity_score(
            global_std, regional_std, dominant_ratio
        )

        is_uniform = (
            global_std < self.config["lab_std_threshold_medium"] and
            dominant_ratio > self.config["dominant_color_threshold"]
        )

        return {
            "global_std": round(float(global_std), 2),
            "regional_std": round(float(regional_std), 2),
            "dominant_color_ratio": round(float(dominant_ratio), 3),
            "uniformity_score": round(float(uniformity_score), 2),
            "is_uniform": bool(is_uniform),
            "color_components": {
                "l_std": round(float(l_std), 2),
                "a_std": round(float(a_std), 2),
                "b_std": round(float(b_std), 2)
            }
        }

    def _analyze_regional_uniformity(self, lab_image: np.ndarray) -> float:
        """Analysiert Uniformität in Grid-Regionen."""
        h, w = lab_image.shape[:2]
        grid_size = self.config["grid_divisions"]

        cell_h = h // grid_size
        cell_w = w // grid_size

        cell_stds = []

        for i in range(grid_size):
            for j in range(grid_size):
                y1, y2 = i * cell_h, (i + 1) * cell_h
                x1, x2 = j * cell_w, (j + 1) * cell_w

                cell = lab_image[y1:y2, x1:x2]
                cell_std = np.std(cell)
                cell_stds.append(cell_std)

        return np.mean(cell_stds)

    def _calculate_dominant_color_ratio(self, rgb_image: np.ndarray) -> float:
        """Berechnet Dominanz-Ratio der häufigsten Farbe (K-Means)."""
        pixels = rgb_image.reshape(-1, 3).astype(np.float32)

        # K-Means Clustering
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            self.config["kmeans_iterations"],
            1.0
        )

        k = self.config["kmeans_clusters"]
        _, labels, centers = cv2.kmeans(
            pixels, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS
        )

        # Dominanz-Ratio berechnen
        label_counts = np.bincount(labels.flatten())
        max_count = np.max(label_counts)
        total_count = len(labels)

        return max_count / total_count

    def _calculate_uniformity_score(
        self, global_std: float, regional_std: float, dominant_ratio: float
    ) -> float:
        """Berechnet Uniformitäts-Score für Typeplate-Erkennung."""
        score = 0.0

        # Globale Uniformität
        if global_std < self.config["lab_std_threshold_high"]:
            score += 3.0
        elif global_std < self.config["lab_std_threshold_medium"]:
            score += 1.5

        # Dominante Farbe
        if dominant_ratio > self.config["dominant_color_threshold"]:
            score += 2.0

        # Regionale Konsistenz
        if regional_std < self.config["lab_std_threshold_high"]:
            score += 1.0

        return score
