# models/corner_detector.py
# 4-Eckpunkte-Erkennung mit Hybrid-Ansatz (Contour + Harris Fallback)

import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Optional
from config import config

class CornerDetector:
    """
    Hybrid Corner Detector für Dokumente und Typenschilder.

    Methoden:
    1. Contour-based (primär): Beste Wahl für rechteckige Objekte
    2. Harris corners (fallback): Für Fälle ohne klare Konturen
    3. Image bounds (last resort): Bildränder als Fallback
    """

    def __init__(self):
        self.config = config.CORNER_DETECTION

    def detect_4_corners(self, image: np.ndarray) -> Dict:
        """
        Erkennt 4 Eckpunkte eines Dokuments/Typenschilds.

        Args:
            image: Numpy array (RGB oder BGR)

        Returns:
            {
                "points": [
                    {"x": 45, "y": 120, "label": "top_left"},
                    {"x": 890, "y": 118, "label": "top_right"},
                    {"x": 892, "y": 450, "label": "bottom_right"},
                    {"x": 43, "y": 452, "label": "bottom_left"}
                ],
                "detection_method": "contour_based",
                "confidence": 0.92
            }
        """
        # Methode 1: Kontur-basiert (primär)
        corners, confidence = self._detect_corners_contour(image)
        if corners is not None and len(corners) == 4:
            ordered = self._order_points_clockwise(corners)
            return self._format_response(ordered, "contour_based", confidence)

        # Methode 2: Harris Corner Detection (fallback)
        corners, confidence = self._detect_corners_harris(image)
        if corners is not None and len(corners) >= 4:
            selected = self._select_best_4_corners(corners, image.shape)
            if selected is not None:
                ordered = self._order_points_clockwise(selected)
                return self._format_response(ordered, "harris", confidence)

        # Methode 3: Bildbegrenzung (last resort)
        corners = self._get_image_bounds(image.shape)
        return self._format_response(corners, "image_bounds", 0.1)

    def _detect_corners_contour(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        """
        Kontur-basierte Eckpunkt-Erkennung.

        Returns:
            (corners, confidence) oder (None, 0.0)
        """
        # Zu Graustufen konvertieren
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()

        # Preprocessing
        blurred = cv2.GaussianBlur(
            gray,
            (self.config["gaussian_blur_ksize"], self.config["gaussian_blur_ksize"]),
            0
        )

        # Edge Detection
        edges = cv2.Canny(
            blurred,
            self.config["canny_low"],
            self.config["canny_high"]
        )

        # Morphological Closing (um Lücken zu schließen)
        kernel_size = self.config["morphology_ksize"]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        # Konturen finden
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None, 0.0

        # Nach Fläche filtern (mindestens 10% des Bildes)
        h, w = image.shape[:2]
        min_area = (h * w) * self.config["min_area_ratio"]
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]

        if not valid_contours:
            return None, 0.0

        # Größte Kontur wählen
        largest = max(valid_contours, key=cv2.contourArea)

        # Zu Polygon approximieren
        epsilon = self.config["approx_epsilon"] * cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, epsilon, True)

        # Überprüfen ob es ein Viereck ist
        if len(approx) == 4:
            # Konfidenz basierend auf Flächen-Verhältnis
            contour_area = cv2.contourArea(approx)
            image_area = h * w
            area_ratio = contour_area / image_area

            # Hohe Konfidenz wenn Kontur zwischen 30% und 95% der Bildfläche
            if 0.3 <= area_ratio <= 0.95:
                confidence = min(area_ratio, 0.95)
            else:
                confidence = 0.5

            return approx.reshape(4, 2), confidence

        return None, 0.0

    def _detect_corners_harris(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        """
        Harris Corner Detection (fallback).

        Returns:
            (corners, confidence) oder (None, 0.0)
        """
        # Zu Graustufen
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()

        gray = gray.astype(np.float32)

        # Shi-Tomasi Corner Detection (Verbesserung von Harris)
        corners = cv2.goodFeaturesToTrack(
            gray,
            maxCorners=self.config["harris_max_corners"],
            qualityLevel=self.config["harris_quality"],
            minDistance=self.config["harris_min_distance"]
        )

        if corners is None or len(corners) < 4:
            return None, 0.0

        corners = corners.reshape(-1, 2).astype(int)

        # Konfidenz basierend auf Anzahl der gefundenen Ecken
        confidence = min(len(corners) / 20.0, 0.8)  # Max 0.8

        return corners, confidence

    def _select_best_4_corners(self, corners: np.ndarray, image_shape: Tuple) -> Optional[np.ndarray]:
        """
        Wählt beste 4 Ecken aus mehreren Harris-Ecken.

        Strategie: Convex Hull → Approximation zu Viereck
        """
        if len(corners) < 4:
            return None

        # Convex Hull berechnen
        hull = cv2.convexHull(corners)

        # Zu Viereck approximieren
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)

        if len(approx) >= 4:
            # Falls mehr als 4 Punkte, wähle die äußersten 4
            points = approx.reshape(-1, 2)

            # Berechne Distanz zum Bildzentrum
            h, w = image_shape[:2]
            center = np.array([w/2, h/2])
            distances = np.linalg.norm(points - center, axis=1)

            # Wähle 4 Punkte mit größter Distanz (äußere Ecken)
            indices = np.argsort(distances)[-4:]
            return points[indices]

        return None

    def _get_image_bounds(self, image_shape: Tuple) -> np.ndarray:
        """
        Gibt Bildränder als Fallback-Eckpunkte zurück.
        """
        h, w = image_shape[:2]
        return np.array([
            [0, 0],      # top_left
            [w-1, 0],    # top_right
            [w-1, h-1],  # bottom_right
            [0, h-1]     # bottom_left
        ])

    def _order_points_clockwise(self, pts: np.ndarray) -> np.ndarray:
        """
        Ordnet 4 Punkte im Uhrzeigersinn: [TL, TR, BR, BL].

        Args:
            pts: Numpy array (4, 2)

        Returns:
            Geordnetes numpy array (4, 2)
        """
        # Sortiere nach y-Koordinate
        sorted_pts = pts[np.argsort(pts[:, 1])]

        # Obere 2 Punkte
        top_pts = sorted_pts[:2]
        # Sortiere nach x (links hat kleineres x)
        top_pts = top_pts[np.argsort(top_pts[:, 0])]
        tl, tr = top_pts

        # Untere 2 Punkte
        bottom_pts = sorted_pts[2:]
        # Sortiere nach x
        bottom_pts = bottom_pts[np.argsort(bottom_pts[:, 0])]
        bl, br = bottom_pts

        return np.array([tl, tr, br, bl])

    def _format_response(self, corners: np.ndarray, method: str, confidence: float) -> Dict:
        """
        Formatiert Eckpunkte als API-Response.

        Args:
            corners: Numpy array (4, 2) - geordnet [TL, TR, BR, BL]
            method: Erkennungsmethode
            confidence: Konfidenz-Score 0.0-1.0

        Returns:
            Dictionary mit formatierten Daten
        """
        labels = ["top_left", "top_right", "bottom_right", "bottom_left"]

        points = []
        for i, (x, y) in enumerate(corners):
            points.append({
                "x": int(x),
                "y": int(y),
                "label": labels[i]
            })

        return {
            "points": points,
            "detection_method": method,
            "confidence": round(float(confidence), 3)
        }

    def get_perspective_transform_matrix(self, corners: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """
        Berechnet Perspektiv-Transformations-Matrix.

        Args:
            corners: 4 Eckpunkte
            target_size: (width, height) der Ziel-Größe

        Returns:
            3x3 Transformations-Matrix
        """
        width, height = target_size

        # Ziel-Eckpunkte (Rechteck)
        dst_points = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ], dtype=np.float32)

        # Perspektiv-Transformation berechnen
        matrix = cv2.getPerspectiveTransform(
            corners.astype(np.float32),
            dst_points
        )

        return matrix

    def apply_perspective_transform(self, image: np.ndarray, corners: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """
        Wendet Perspektiv-Transformation an.

        Args:
            image: Eingabebild
            corners: 4 Eckpunkte
            target_size: (width, height)

        Returns:
            Transformiertes Bild
        """
        matrix = self.get_perspective_transform_matrix(corners, target_size)

        warped = cv2.warpPerspective(
            image,
            matrix,
            target_size,
            flags=cv2.INTER_LINEAR
        )

        return warped
