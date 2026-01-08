# config_schemas.py
# Pydantic validation schemas for configuration API

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional


class WeightsARConfig(BaseModel):
    """Arbeitsbericht weights configuration."""
    text_length_divisor: float = Field(gt=0, le=10000, description="Text length divisor for scoring")
    text_length_factor: float = Field(gt=0, le=100, description="Text length weight factor")
    keyword_multiplier: float = Field(gt=0, le=100, description="Keyword match multiplier")
    clip_bonus: float = Field(ge=0, le=100, description="CLIP model bonus factor")
    min_text_length: int = Field(ge=0, le=100000, description="Minimum expected text length")


class WeightsTPConfig(BaseModel):
    """Typeplate weights configuration."""
    clip_factor: float = Field(gt=0, le=100, description="CLIP model weight factor")
    keyword_multiplier: float = Field(gt=0, le=100, description="Keyword match multiplier")
    digit_ratio_factor: float = Field(gt=0, le=1000, description="Digit ratio importance")
    line_density_factor: float = Field(gt=0, le=1000, description="Line density weight")
    color_uniformity_factor: float = Field(gt=0, le=100, description="Color uniformity weight")
    rect_score_factor: float = Field(gt=0, le=100, description="Rectangle/corner detection weight")


class WeightsDOCConfig(BaseModel):
    """Document weights configuration."""
    text_length_divisor: float = Field(gt=0, le=10000, description="Text length divisor")
    clip_factor: float = Field(gt=0, le=100, description="CLIP model weight factor")


class WeightsPHOTOConfig(BaseModel):
    """Photo weights configuration."""
    low_text_threshold: int = Field(ge=0, le=1000, description="Threshold for low text detection")
    low_text_bonus: float = Field(ge=0, le=100, description="Bonus for low text content")
    clip_factor: float = Field(gt=0, le=100, description="CLIP model weight factor")


class WeightsConfig(BaseModel):
    """Complete weights configuration for all classes."""
    AR: WeightsARConfig
    TP: WeightsTPConfig
    DOC: WeightsDOCConfig
    PHOTO: WeightsPHOTOConfig


class ThresholdsConfig(BaseModel):
    """Classification thresholds configuration."""
    arbeitsbericht: float = Field(ge=0, le=1000, description="Arbeitsbericht classification threshold")
    typeplate: float = Field(ge=0, le=1000, description="Typeplate classification threshold")
    document: float = Field(ge=0, le=1000, description="Document classification threshold")
    photo: float = Field(ge=0, le=1000, description="Photo classification threshold (fallback)")

    @validator('*')
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Thresholds must be non-negative')
        return v


class CornerDetectionConfig(BaseModel):
    """Corner detection parameters."""
    method: str = Field(default="contour_based", description="Primary detection method")
    fallback_method: str = Field(default="harris", description="Fallback detection method")
    canny_low: int = Field(ge=0, le=500, description="Canny edge detection low threshold")
    canny_high: int = Field(ge=0, le=500, description="Canny edge detection high threshold")
    gaussian_blur_ksize: int = Field(ge=1, le=31, description="Gaussian blur kernel size (odd)")
    morphology_ksize: int = Field(ge=1, le=31, description="Morphology kernel size (odd)")
    approx_epsilon: float = Field(ge=0.001, le=0.5, description="Polygon approximation accuracy")
    min_area_ratio: float = Field(ge=0.0, le=1.0, description="Minimum contour area ratio")
    harris_quality: float = Field(ge=0.001, le=1.0, description="Harris corner quality level")
    harris_min_distance: int = Field(ge=1, le=100, description="Minimum distance between corners")
    harris_max_corners: int = Field(ge=4, le=1000, description="Maximum corners to detect")

    @validator('gaussian_blur_ksize', 'morphology_ksize')
    def validate_odd(cls, v):
        if v % 2 == 0:
            raise ValueError('Kernel size must be odd')
        return v


class ColorAnalysisConfig(BaseModel):
    """Color uniformity analysis parameters."""
    lab_std_threshold_high: float = Field(ge=0, le=100, description="LAB std threshold for high uniformity")
    lab_std_threshold_medium: float = Field(ge=0, le=100, description="LAB std threshold for medium uniformity")
    dominant_color_threshold: float = Field(ge=0.0, le=1.0, description="Dominant color ratio threshold")
    grid_divisions: int = Field(ge=2, le=20, description="Grid divisions for regional analysis")
    kmeans_clusters: int = Field(ge=2, le=10, description="K-means cluster count")
    kmeans_iterations: int = Field(ge=1, le=100, description="K-means max iterations")


class LineAnalysisConfig(BaseModel):
    """Line detection parameters."""
    hough_threshold: int = Field(ge=1, le=500, description="Hough transform threshold")
    hough_min_line_length: int = Field(ge=1, le=1000, description="Minimum line length")
    hough_max_line_gap: int = Field(ge=0, le=200, description="Maximum gap between line segments")
    angle_tolerance: float = Field(ge=0, le=45, description="Angle tolerance for horizontal/vertical")
    edge_proximity_threshold: int = Field(ge=0, le=200, description="Pixel distance to edge")
    canny_low: int = Field(ge=0, le=500, description="Canny low threshold")
    canny_high: int = Field(ge=0, le=500, description="Canny high threshold")


class OCRConfig(BaseModel):
    """OCR and text analysis configuration."""
    tesseract_lang: str = Field(default="deu+eng", description="Tesseract language config")
    arbeitsbericht_keywords: List[str] = Field(min_items=1, description="Arbeitsbericht detection keywords")
    typeplate_keywords: List[str] = Field(min_items=1, description="Typeplate detection keywords")


class CI4Config(BaseModel):
    """CI4 integration configuration."""
    base_url: str = Field(description="CI4 API base URL")
    api_key: str = Field(default="", description="CI4 API key (empty if disabled)")
    timeout: int = Field(ge=1, le=300, description="Request timeout in seconds")
    retry_attempts: int = Field(ge=0, le=10, description="Number of retry attempts")
    retry_delay: int = Field(ge=0, le=60, description="Delay between retries in seconds")
    enabled: bool = Field(description="Enable/disable CI4 integration")


class FeatureConfig(BaseModel):
    """Feature extraction configuration."""
    perceptual_hash_size: int = Field(ge=4, le=64, description="Perceptual hash size (n x n)")
    color_histogram_bins: int = Field(ge=8, le=256, description="Color histogram bins")
    edge_histogram_bins: int = Field(ge=8, le=256, description="Edge histogram bins")
    clip_embedding_dim: int = Field(ge=128, le=2048, description="CLIP embedding dimensions")
    similarity_weights: Dict[str, float] = Field(description="Similarity metric weights")

    @validator('similarity_weights')
    def validate_weights_sum(cls, v):
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(f'Similarity weights must sum to 1.0, got {total}')
        return v


class LearningConfig(BaseModel):
    """Learning system configuration."""
    learning_rate: float = Field(ge=0.001, le=1.0, description="Learning rate for weight adjustments")
    reinforce_factor: float = Field(ge=0, le=1.0, description="Reinforcement for correct predictions")
    penalize_factor: float = Field(ge=-1.0, le=0, description="Penalty for incorrect predictions")
    reward_factor: float = Field(ge=0, le=1.0, description="Reward for corrections")
    threshold_recalc_interval: int = Field(ge=1, le=1000, description="Threshold recalculation interval")
    min_feedback_for_update: int = Field(ge=1, le=100, description="Minimum feedback before applying updates")
    weight_update_interval: int = Field(ge=1, le=1000, description="CI4 sync interval for weights")


class PerformanceConfig(BaseModel):
    """Performance and caching configuration."""
    enable_caching: bool = Field(description="Enable feature caching")
    cache_ttl: int = Field(ge=60, le=86400, description="Cache TTL in seconds")
    max_cache_size: int = Field(ge=10, le=100000, description="Maximum cache entries")
    lazy_feature_extraction: bool = Field(description="Extract features only when needed")
    async_feature_extraction: bool = Field(description="Extract features asynchronously")


class FullConfigSchema(BaseModel):
    """Complete configuration schema for validation."""
    version: str = Field(default="1.0.0", description="Configuration version")
    THRESHOLDS: Optional[ThresholdsConfig] = None
    WEIGHTS: Optional[WeightsConfig] = None
    CORNER_DETECTION: Optional[CornerDetectionConfig] = None
    COLOR_ANALYSIS: Optional[ColorAnalysisConfig] = None
    LINE_ANALYSIS: Optional[LineAnalysisConfig] = None
    OCR_CONFIG: Optional[OCRConfig] = None
    CI4_CONFIG: Optional[CI4Config] = None
    FEATURE_CONFIG: Optional[FeatureConfig] = None
    LEARNING_CONFIG: Optional[LearningConfig] = None
    PERFORMANCE: Optional[PerformanceConfig] = None

    class Config:
        extra = "forbid"  # Reject unknown fields


class ConfigMetadata(BaseModel):
    """Metadata about configuration state."""
    version: str
    last_modified: Optional[float] = None
    ci4_enabled: bool
    has_runtime_overrides: bool = False
    config_file_exists: bool = False
