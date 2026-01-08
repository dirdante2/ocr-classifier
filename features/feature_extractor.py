# features/feature_extractor.py
# Multi-modale Feature-Extraktion für Ähnlichkeitssuche

import cv2
import numpy as np
import imagehash
from PIL import Image
from typing import Dict, List, Optional
import torch
from config import config

import logging
logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Multi-modale Feature-Extraktion für Bild-Ähnlichkeit.

    Features:
    1. Perceptual Hash (8x8): Schneller Duplikat-Check
    2. LAB-Farb-Histogramm (32 bins): Visuelle Ähnlichkeit
    3. Edge-Orientierungs-Histogramm (32 bins): Strukturelle Ähnlichkeit
    4. CLIP-Embedding (512-dim): Semantische Ähnlichkeit
    5. Text-Features: Wortanzahl, Ziffern-Ratio, Durchschn. Wortlänge
    6. Layout-Features: Aspect-Ratio, Text-Dichte
    """

    def __init__(self, clip_model=None, clip_processor=None):
        """
        Initialisiert Feature-Extractor.

        Args:
            clip_model: Optional CLIP-Model (wird wiederverwendet)
            clip_processor: Optional CLIP-Processor
        """
        self.clip_model = clip_model
        self.clip_processor = clip_processor
        self.cfg = config.FEATURE_CONFIG

    def extract_features(
        self,
        image: Image.Image,
        ocr_text: str = "",
        ocr_data: Optional[Dict] = None
    ) -> Dict:
        """
        Extrahiert alle Features.

        Args:
            image: PIL Image
            ocr_text: OCR-extrahierter Text
            ocr_data: Optional OCR-Analyse-Daten

        Returns:
            {
                "perceptual_hash": "abc123...",
                "color_histogram": [0.1, 0.05, ...],  # 32 bins
                "edge_histogram": [0.08, 0.12, ...],  # 32 bins
                "clip_embedding": [0.45, -0.12, ...], # 512-dim
                "text_features": {...},
                "layout_features": {...}
            }
        """
        features = {}

        try:
            # 1. Perceptual Hash
            features['perceptual_hash'] = self._compute_perceptual_hash(image)

            # 2. Color Histogram (LAB)
            features['color_histogram'] = self._compute_color_histogram(image)

            # 3. Edge Orientation Histogram
            features['edge_histogram'] = self._compute_edge_histogram(image)

            # 4. CLIP Embedding
            if self.clip_model and self.clip_processor:
                features['clip_embedding'] = self._compute_clip_embedding(image)
            else:
                features['clip_embedding'] = None

            # 5. Text Features
            features['text_features'] = self._extract_text_features(ocr_text, ocr_data)

            # 6. Layout Features
            features['layout_features'] = self._extract_layout_features(image, ocr_text)

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            # Returniere leere Features bei Fehler
            features = self._empty_features()

        return features

    def _compute_perceptual_hash(self, image: Image.Image) -> str:
        """Berechnet Perceptual Hash (phash) - robust gegen kleine Änderungen."""
        hash_size = self.cfg["perceptual_hash_size"]
        phash = imagehash.phash(image, hash_size=hash_size)
        return str(phash)

    def _compute_color_histogram(self, image: Image.Image) -> List[float]:
        """
        Berechnet LAB-Farb-Histogramm.

        Returns:
            Normalisiertes Histogramm (32 bins)
        """
        bins = self.cfg["color_histogram_bins"]

        # Zu LAB konvertieren
        img_array = np.array(image.convert("RGB"))
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)

        # Histogramm für jeden Kanal
        hist_l = cv2.calcHist([lab], [0], None, [bins], [0, 256])
        hist_a = cv2.calcHist([lab], [1], None, [bins], [0, 256])
        hist_b = cv2.calcHist([lab], [2], None, [bins], [0, 256])

        # Zusammenführen und normalisieren
        hist_combined = np.concatenate([hist_l, hist_a, hist_b]).flatten()
        hist_normalized = hist_combined / (hist_combined.sum() + 1e-6)

        return hist_normalized.tolist()

    def _compute_edge_histogram(self, image: Image.Image) -> List[float]:
        """
        Berechnet Edge-Orientierungs-Histogramm.

        Returns:
            Histogramm der Kanten-Orientierungen (32 bins)
        """
        bins = self.cfg["edge_histogram_bins"]

        # Zu Graustufen
        img_array = np.array(image.convert("L"))

        # Sobel-Filter für Gradienten
        sobelx = cv2.Sobel(img_array, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(img_array, cv2.CV_64F, 0, 1, ksize=3)

        # Gradientenrichtung
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        orientation = np.arctan2(sobely, sobelx)

        # Nur starke Kanten berücksichtigen (> Schwellwert)
        threshold = np.percentile(magnitude, 75)
        strong_edges = magnitude > threshold

        # Histogramm der Orientierungen (nur starke Kanten)
        orientations_filtered = orientation[strong_edges]

        if len(orientations_filtered) > 0:
            hist, _ = np.histogram(orientations_filtered, bins=bins, range=(-np.pi, np.pi))
            hist_normalized = hist / (hist.sum() + 1e-6)
        else:
            hist_normalized = np.zeros(bins)

        return hist_normalized.tolist()

    def _compute_clip_embedding(self, image: Image.Image) -> Optional[List[float]]:
        """
        Berechnet CLIP-Embedding (512-dim).

        Returns:
            Embedding-Vektor oder None
        """
        try:
            # CLIP-Input vorbereiten
            inputs = self.clip_processor(images=image, return_tensors="pt")

            # Embedding extrahieren
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)

            # Normalisieren
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            return image_features.squeeze().cpu().numpy().tolist()

        except Exception as e:
            logger.error(f"CLIP embedding extraction failed: {e}")
            return None

    def _extract_text_features(self, text: str, ocr_data: Optional[Dict] = None) -> Dict:
        """Extrahiert Text-basierte Features."""
        if not text:
            return {
                "word_count": 0,
                "digit_ratio": 0.0,
                "avg_word_length": 0.0,
                "char_count": 0
            }

        words = text.split()
        word_count = len(words)
        char_count = len(text)
        digit_count = sum(c.isdigit() for c in text)
        digit_ratio = digit_count / max(char_count, 1)

        # Durchschnittliche Wortlänge
        avg_word_length = sum(len(w) for w in words) / max(word_count, 1)

        return {
            "word_count": word_count,
            "digit_ratio": round(digit_ratio, 3),
            "avg_word_length": round(avg_word_length, 2),
            "char_count": char_count
        }

    def _extract_layout_features(self, image: Image.Image, text: str) -> Dict:
        """Extrahiert Layout-Features."""
        width, height = image.size
        aspect_ratio = width / max(height, 1)

        # Text-Dichte (Zeichen pro Pixel)
        total_pixels = width * height
        text_density = len(text) / max(total_pixels, 1)

        return {
            "aspect_ratio": round(aspect_ratio, 3),
            "text_density": round(text_density, 6),
            "width": width,
            "height": height
        }

    def _empty_features(self) -> Dict:
        """Returniert leere Feature-Struktur bei Fehler."""
        return {
            "perceptual_hash": "",
            "color_histogram": [],
            "edge_histogram": [],
            "clip_embedding": None,
            "text_features": {},
            "layout_features": {}
        }

    def calculate_similarity(self, features1: Dict, features2: Dict) -> float:
        """
        Berechnet Ähnlichkeit zwischen zwei Feature-Vektoren.

        Gewichtung:
        - hash_similarity * 0.2
        - color_histogram_similarity * 0.2
        - edge_histogram_similarity * 0.2
        - clip_embedding_similarity * 0.4

        Args:
            features1, features2: Feature-Dictionaries

        Returns:
            Similarity score 0.0-1.0
        """
        weights = self.cfg["similarity_weights"]

        similarities = {}

        # 1. Perceptual Hash Similarity
        if features1.get('perceptual_hash') and features2.get('perceptual_hash'):
            hash_sim = self._hash_similarity(
                features1['perceptual_hash'],
                features2['perceptual_hash']
            )
            similarities['hash'] = hash_sim
        else:
            similarities['hash'] = 0.0

        # 2. Color Histogram Similarity
        if features1.get('color_histogram') and features2.get('color_histogram'):
            color_sim = self._histogram_similarity(
                features1['color_histogram'],
                features2['color_histogram']
            )
            similarities['color_hist'] = color_sim
        else:
            similarities['color_hist'] = 0.0

        # 3. Edge Histogram Similarity
        if features1.get('edge_histogram') and features2.get('edge_histogram'):
            edge_sim = self._histogram_similarity(
                features1['edge_histogram'],
                features2['edge_histogram']
            )
            similarities['edge_hist'] = edge_sim
        else:
            similarities['edge_hist'] = 0.0

        # 4. CLIP Embedding Similarity
        if features1.get('clip_embedding') and features2.get('clip_embedding'):
            clip_sim = self._cosine_similarity(
                features1['clip_embedding'],
                features2['clip_embedding']
            )
            similarities['clip_embedding'] = clip_sim
        else:
            similarities['clip_embedding'] = 0.0

        # Gewichtete Summe
        total_similarity = sum(
            similarities[key] * weights[key]
            for key in similarities
        )

        return round(total_similarity, 3)

    def _hash_similarity(self, hash1: str, hash2: str) -> float:
        """
        Berechnet Ähnlichkeit zwischen zwei Perceptual Hashes.

        Verwendet Hamming-Distanz.
        """
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)

            # Hamming-Distanz
            hamming_dist = h1 - h2

            # Max Distanz für 8x8 Hash = 64
            max_dist = len(hash1) * 4  # 4 Bits pro Hex-Zeichen

            # Zu Ähnlichkeit konvertieren (1.0 = identisch, 0.0 = maximal verschieden)
            similarity = 1.0 - (hamming_dist / max_dist)

            return max(0.0, similarity)

        except Exception as e:
            logger.error(f"Hash similarity calculation failed: {e}")
            return 0.0

    def _histogram_similarity(self, hist1: List[float], hist2: List[float]) -> float:
        """
        Berechnet Ähnlichkeit zwischen zwei Histogrammen.

        Verwendet Chi-Square-Distanz.
        """
        try:
            h1 = np.array(hist1)
            h2 = np.array(hist2)

            # Chi-Square-Distanz
            chi_square = np.sum((h1 - h2)**2 / (h1 + h2 + 1e-6))

            # Chi-Square in Ähnlichkeit konvertieren
            # Kleinere Distanz = höhere Ähnlichkeit
            similarity = np.exp(-chi_square / 2)

            return float(max(0.0, min(1.0, similarity)))

        except Exception as e:
            logger.error(f"Histogram similarity calculation failed: {e}")
            return 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Berechnet Cosine-Similarity zwischen zwei Vektoren.
        """
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)

            # Cosine Similarity
            dot_product = np.dot(v1, v2)
            norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)

            if norm_product == 0:
                return 0.0

            similarity = dot_product / norm_product

            # Auf [0, 1] normalisieren (Cosine ist in [-1, 1])
            normalized = (similarity + 1) / 2

            return float(max(0.0, min(1.0, normalized)))

        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0
