# features/line_analyzer.py
# Gerade-Linien-Analyse für Typenschild-Erkennung

import cv2
import numpy as np
from PIL import Image
from typing import Dict, List
from config import config


class LineAnalyzer:
    """
    Analysiert gerade Linien - Typenschilder haben oft rechteckige Rahmen
    und horizontale/vertikale Text-Ausrichtung.
    """

    def __init__(self):
        self.config = config.LINE_ANALYSIS

    def analyze_straight_lines(self, image: Image.Image) -> Dict:
        """
        Führt Linien-Analyse durch.

        Returns:
            {
                "line_count": 24,
                "horizontal_count": 12,
                "vertical_count": 8,
                "has_rectangular_border": True,
                "line_score": 8.5,
                "border_completeness": 4
            }
        """
        img_array = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Edge Detection
        edges = cv2.Canny(
            gray,
            self.config["canny_low"],
            self.config["canny_high"]
        )

        # Hough Line Transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.config["hough_threshold"],
            minLineLength=self.config["hough_min_line_length"],
            maxLineGap=self.config["hough_max_line_gap"]
        )

        if lines is None:
            return self._empty_result()

        # Linien klassifizieren
        h, w = img_array.shape[:2]
        horizontal_lines, vertical_lines = self._classify_lines(lines)

        # Rechteckiger Rand erkennen
        has_border, border_completeness = self._detect_rectangular_border(
            horizontal_lines, vertical_lines, h, w
        )

        # Score berechnen
        line_score = self._calculate_line_score(
            len(horizontal_lines),
            len(vertical_lines),
            has_border
        )

        return {
            "line_count": len(lines),
            "horizontal_count": len(horizontal_lines),
            "vertical_count": len(vertical_lines),
            "has_rectangular_border": has_border,
            "line_score": round(float(line_score), 2),
            "border_completeness": border_completeness,
            "orientation_ratio": round(
                len(horizontal_lines) / max(len(vertical_lines), 1), 2
            )
        }

    def _classify_lines(self, lines: np.ndarray) -> tuple:
        """Klassifiziert Linien als horizontal oder vertikal."""
        horizontal = []
        vertical = []
        angle_tol = self.config["angle_tolerance"]

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Winkel berechnen
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))

            # Normalisieren
            angle = angle % 180
            if angle > 90:
                angle -= 180

            # Klassifizieren
            if abs(angle) < angle_tol:  # Horizontal
                horizontal.append(line)
            elif abs(abs(angle) - 90) < angle_tol:  # Vertikal
                vertical.append(line)

        return horizontal, vertical

    def _detect_rectangular_border(
        self, h_lines: List, v_lines: List, height: int, width: int
    ) -> tuple:
        """Erkennt rechteckigen Rahmen."""
        threshold = self.config["edge_proximity_threshold"]

        has_top = any(self._is_near_edge(l, 'top', height, width, threshold) for l in h_lines)
        has_bottom = any(self._is_near_edge(l, 'bottom', height, width, threshold) for l in h_lines)
        has_left = any(self._is_near_edge(l, 'left', height, width, threshold) for l in v_lines)
        has_right = any(self._is_near_edge(l, 'right', height, width, threshold) for l in v_lines)

        completeness = sum([has_top, has_bottom, has_left, has_right])
        has_border = completeness >= 3

        return has_border, completeness

    def _is_near_edge(self, line, edge_type: str, h: int, w: int, threshold: int) -> bool:
        """Prüft ob Linie nahe am Bildrand ist."""
        x1, y1, x2, y2 = line[0]

        if edge_type == 'top':
            return min(y1, y2) < threshold
        elif edge_type == 'bottom':
            return max(y1, y2) > h - threshold
        elif edge_type == 'left':
            return min(x1, x2) < threshold
        elif edge_type == 'right':
            return max(x1, x2) > w - threshold

        return False

    def _calculate_line_score(self, h_count: int, v_count: int, has_border: bool) -> float:
        """Berechnet Line-Score für Typeplate-Erkennung."""
        score = 0.0

        # Horizontale Linien (max 3.0)
        score += min(h_count * 0.5, 3.0)

        # Vertikale Linien (max 3.0)
        score += min(v_count * 0.5, 3.0)

        # Rechteckiger Rand (bonus)
        if has_border:
            score += 4.0

        return score

    def _empty_result(self) -> Dict:
        """Leeres Ergebnis wenn keine Linien gefunden."""
        return {
            "line_count": 0,
            "horizontal_count": 0,
            "vertical_count": 0,
            "has_rectangular_border": False,
            "line_score": 0.0,
            "border_completeness": 0,
            "orientation_ratio": 0.0
        }
