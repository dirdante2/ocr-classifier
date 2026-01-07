# models/ocr_analyzer.py
# OCR-Analyse mit verbesserter Arbeitsbericht-Erkennung

import re
from typing import Tuple, Dict
from PIL import Image
import pytesseract
from config import config


class OCRAnalyzer:
    """
    OCR-basierte Textanalyse für Dokumentklassifizierung.

    Hauptfunktionen:
    - Arbeitsbericht-Erkennung mit Keyword "Arbeitsbericht"
    - Textdichte-Messung
    - Keyword-Matching für verschiedene Dokument-Typen
    """

    def __init__(self):
        self.config = config.OCR_CONFIG
        self.arbeitsbericht_keywords = self.config["arbeitsbericht_keywords"]
        self.typeplate_keywords = self.config["typeplate_keywords"]

    def analyze(self, image: Image.Image) -> Dict:
        """
        Führt vollständige OCR-Analyse durch.

        Args:
            image: PIL Image

        Returns:
            {
                "text": "Vollständiger OCR-Text",
                "text_length": 1234,
                "text_density": 0.0005,
                "word_count": 245,
                "line_count": 18
            }
        """
        # OCR durchführen
        text = pytesseract.image_to_string(image, lang=self.config["tesseract_lang"])

        # Text-Metriken berechnen
        text_length = len(text.strip())
        total_pixels = image.size[0] * image.size[1]
        text_density = text_length / max(total_pixels, 1)

        # Weitere Metriken
        words = text.split()
        word_count = len(words)
        line_count = len([line for line in text.split('\n') if line.strip()])

        return {
            "text": text,
            "text_length": text_length,
            "text_density": text_density,
            "word_count": word_count,
            "line_count": line_count
        }

    def detect_arbeitsbericht(self, text: str) -> Tuple[float, Dict]:
        """
        Erkennt ob Text ein "Arbeitsbericht" ist.

        Strategie:
        - Hauptkeyword "arbeitsbericht" MUSS vorhanden sein (+5.0)
        - Zusätzliche Keywords erhöhen Score (+2.0 pro Treffer)
        - Textlänge > 500 Zeichen typisch für Arbeitsberichte (+1.5)

        Args:
            text: OCR-extrahierter Text

        Returns:
            (score, debug_info)
        """
        t_low = text.lower()

        # Hauptkeyword prüfen (case-insensitive)
        has_main_keyword = "arbeitsbericht" in t_low

        # Zusatz-Keywords zählen (ohne Hauptkeyword)
        additional_keywords = self.arbeitsbericht_keywords[1:]  # Skip "arbeitsbericht"
        keyword_hits = []

        for kw in additional_keywords:
            if kw in t_low:
                # Position im Text finden
                pos = t_low.index(kw)
                keyword_hits.append({
                    "keyword": kw,
                    "position": pos
                })

        # Textlänge prüfen
        text_length = len(text.strip())
        is_long_text = text_length > config.WEIGHTS["AR"]["min_text_length"]

        # Scoring
        score = 0.0

        if has_main_keyword:
            # Nur wenn Hauptkeyword vorhanden ist, zählt der Rest
            score += 5.0  # Starker Indikator
            score += len(keyword_hits) * 2.0  # Zusatz-Keywords
            score += is_long_text * 1.5  # Längerer Text

        # Debug-Info
        debug_info = {
            "has_main_keyword": has_main_keyword,
            "keyword_hits": len(keyword_hits),
            "keyword_details": keyword_hits,
            "text_length": text_length,
            "is_long_text": is_long_text,
            "main_keyword_position": t_low.index("arbeitsbericht") if has_main_keyword else -1
        }

        return score, debug_info

    def analyze_typeplate_features(self, text: str) -> Dict:
        """
        Analysiert Typenschild-spezifische Text-Features.

        Returns:
            {
                "digit_ratio": 0.45,
                "keyword_count": 3,
                "keyword_hits": ["serial", "model", "voltage"],
                "has_serial_number": True,
                "has_model_number": True
            }
        """
        t_low = text.lower()

        # Ziffern-Ratio berechnen
        digit_count = sum(c.isdigit() for c in text)
        total_chars = len(text)
        digit_ratio = digit_count / max(total_chars, 1)

        # Typeplate-Keywords zählen
        keyword_hits = []
        for kw in self.typeplate_keywords:
            if kw in t_low:
                keyword_hits.append(kw)

        # Spezielle Muster erkennen
        has_serial_number = any(pattern in t_low for pattern in [
            "serial", "s/n", "ser.", "serial no"
        ])

        has_model_number = any(pattern in t_low for pattern in [
            "model", "type", "mod.", "model no"
        ])

        # Voltage/Power-Muster (z.B. "230V", "50Hz", "1.5kW")
        voltage_pattern = r'\d+\s*[vV]'
        frequency_pattern = r'\d+\s*[hH][zZ]'
        power_pattern = r'\d+\.?\d*\s*[kK]?[wW]'

        has_voltage = bool(re.search(voltage_pattern, text))
        has_frequency = bool(re.search(frequency_pattern, text))
        has_power = bool(re.search(power_pattern, text))

        return {
            "digit_ratio": digit_ratio,
            "keyword_count": len(keyword_hits),
            "keyword_hits": keyword_hits,
            "has_serial_number": has_serial_number,
            "has_model_number": has_model_number,
            "has_technical_specs": has_voltage or has_frequency or has_power,
            "technical_indicators": {
                "voltage": has_voltage,
                "frequency": has_frequency,
                "power": has_power
            }
        }

    def detect_date_patterns(self, text: str) -> bool:
        """
        Erkennt Datums-Muster im Text.

        Muster: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.
        """
        date_patterns = [
            r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
            r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
            r'\d{4}-\d{2}-\d{2}',        # YYYY-MM-DD
            r'\d{1,2}\.\s*\d{1,2}\.\s*\d{4}',  # DD. MM. YYYY
        ]

        for pattern in date_patterns:
            if re.search(pattern, text):
                return True

        return False

    def get_text_statistics(self, text: str) -> Dict:
        """
        Berechnet detaillierte Text-Statistiken.

        Returns:
            {
                "char_count": 1234,
                "word_count": 245,
                "line_count": 18,
                "avg_word_length": 5.7,
                "alpha_ratio": 0.75,
                "digit_ratio": 0.15,
                "space_ratio": 0.20,
                "punctuation_ratio": 0.05,
                "uppercase_ratio": 0.12,
                "has_date": True
            }
        """
        char_count = len(text)
        word_count = len(text.split())
        line_count = len([l for l in text.split('\n') if l.strip()])

        # Durchschnittliche Wortlänge
        words = text.split()
        avg_word_length = sum(len(w) for w in words) / max(word_count, 1)

        # Zeichen-Verhältnisse
        alpha_count = sum(c.isalpha() for c in text)
        digit_count = sum(c.isdigit() for c in text)
        space_count = sum(c.isspace() for c in text)
        punct_count = sum(c in '.,;:!?-()[]{}"\'' for c in text)
        upper_count = sum(c.isupper() for c in text)

        alpha_ratio = alpha_count / max(char_count, 1)
        digit_ratio = digit_count / max(char_count, 1)
        space_ratio = space_count / max(char_count, 1)
        punctuation_ratio = punct_count / max(char_count, 1)
        uppercase_ratio = upper_count / max(char_count, 1)

        # Datumserkennung
        has_date = self.detect_date_patterns(text)

        return {
            "char_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "avg_word_length": round(avg_word_length, 2),
            "alpha_ratio": round(alpha_ratio, 3),
            "digit_ratio": round(digit_ratio, 3),
            "space_ratio": round(space_ratio, 3),
            "punctuation_ratio": round(punctuation_ratio, 3),
            "uppercase_ratio": round(uppercase_ratio, 3),
            "has_date": has_date
        }
