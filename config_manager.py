# config_manager.py
# Thread-safe configuration manager with file persistence

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from copy import deepcopy

from config_schemas import FullConfigSchema, ConfigMetadata
from config import ClassificationConfig

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Thread-safe configuration manager with layered configuration support.

    Configuration layers (lowest to highest priority):
    1. Hardcoded defaults (in config.py)
    2. config.json file (persisted user config)
    3. CI4 weights (loaded at startup)
    4. Runtime learning adjustments (in-memory only)
    5. Environment variables (immutable)
    """

    def __init__(self, config_file: Path = Path("/root/ocr-classifier/config.json")):
        self.config_file = config_file
        self._lock = asyncio.Lock()
        self._runtime_overrides = {}  # Learning system writes here
        self._audit_log_file = config_file.parent / "config_audit.jsonl"

    async def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Get configuration with all layers merged.

        Args:
            section: Optional section name (e.g., "WEIGHTS", "THRESHOLDS")

        Returns:
            Complete config dict or specific section
        """
        async with self._lock:
            # Start with hardcoded defaults
            config = self._get_defaults()

            # Layer 2: Merge file config (if exists)
            file_config = await self._load_from_file()
            if file_config:
                config = self._deep_merge(config, file_config)

            # Layer 3 & 4: Merge runtime overrides (from CI4 + learning)
            if self._runtime_overrides:
                config = self._deep_merge(config, self._runtime_overrides)

            # Layer 5: Environment variables already applied in config.py

            if section:
                return config.get(section, {})
            return config

    async def update_config(self, updates: Dict[str, Any], persist: bool = True) -> Dict[str, Any]:
        """
        Update configuration atomically.

        Args:
            updates: Dictionary with config updates (full or partial)
            persist: If True, save to file. If False, runtime-only (for learning system)

        Returns:
            Updated configuration

        Raises:
            ValidationError: If updates are invalid
        """
        async with self._lock:
            # Get current config
            current = await self.get_config()

            # Merge updates
            updated = self._deep_merge(current, updates)

            # Validate with Pydantic
            try:
                FullConfigSchema(**updated)
            except Exception as e:
                logger.error(f"Config validation failed: {e}")
                raise ValueError(f"Invalid configuration: {e}")

            if persist:
                # Save to file (atomic write with backup)
                await self._atomic_write(updated)

                # Log change
                await self._log_change("update_persisted", current, updated)

                # Apply to singleton (for backwards compatibility)
                self._apply_to_singleton(updated)
            else:
                # Runtime-only override (for learning system)
                self._runtime_overrides = self._deep_merge(self._runtime_overrides, updates)
                await self._log_change("update_runtime", current, updated)

            return await self.get_config()

    async def reload(self, clear_runtime: bool = True) -> Dict[str, Any]:
        """
        Reload configuration from file.

        Args:
            clear_runtime: If True, discard runtime overrides (learning progress)

        Returns:
            Reloaded configuration
        """
        async with self._lock:
            if clear_runtime:
                self._runtime_overrides = {}
                logger.warning("Runtime overrides cleared - learning progress lost")

            file_config = await self._load_from_file()
            if file_config:
                self._apply_to_singleton(file_config)

            await self._log_change("reload", {}, file_config or {})
            return await self.get_config()

    async def reset_to_defaults(self) -> Dict[str, Any]:
        """
        Reset configuration to hardcoded defaults.
        Clears both file and runtime overrides.

        Returns:
            Default configuration
        """
        async with self._lock:
            defaults = self._get_defaults()

            # Clear runtime overrides
            self._runtime_overrides = {}

            # Save defaults to file
            await self._atomic_write(defaults)

            # Apply to singleton
            self._apply_to_singleton(defaults)

            await self._log_change("reset_to_defaults", {}, defaults)
            return defaults

    async def validate_safety(self, new_config: Dict[str, Any]) -> List[str]:
        """
        Check if configuration changes are safe.

        Args:
            new_config: Proposed new configuration

        Returns:
            List of warning messages
        """
        warnings = []
        current = await self.get_config()

        # Check weights changes
        if "WEIGHTS" in new_config and "WEIGHTS" in current:
            change_pct = self._calculate_change_percentage(
                current["WEIGHTS"],
                new_config["WEIGHTS"]
            )
            if change_pct > 50:
                warnings.append(
                    f"Weights changed by {change_pct:.1f}% - may significantly affect classification accuracy"
                )

        # Check thresholds changes
        if "THRESHOLDS" in new_config and "THRESHOLDS" in current:
            for key in current["THRESHOLDS"]:
                old_val = current["THRESHOLDS"].get(key, 0)
                new_val = new_config["THRESHOLDS"].get(key, 0)
                if old_val > 0:
                    change = abs(new_val - old_val) / old_val * 100
                    if change > 100:
                        warnings.append(
                            f"Threshold '{key}' changed by {change:.1f}% - classification behavior will change significantly"
                        )

        return warnings

    async def clear_runtime_overrides(self):
        """Clear runtime overrides (called when base config changes)."""
        async with self._lock:
            self._runtime_overrides = {}
            logger.info("Runtime overrides cleared")

    def get_metadata(self) -> ConfigMetadata:
        """Get configuration metadata."""
        return ConfigMetadata(
            version=ClassificationConfig.VERSION,
            last_modified=self.config_file.stat().st_mtime if self.config_file.exists() else None,
            ci4_enabled=ClassificationConfig.CI4_CONFIG.get("enabled", False),
            has_runtime_overrides=bool(self._runtime_overrides),
            config_file_exists=self.config_file.exists()
        )

    # Private methods

    def _get_defaults(self) -> Dict[str, Any]:
        """Get hardcoded default configuration from config.py."""
        return {
            "version": ClassificationConfig.VERSION,
            "THRESHOLDS": deepcopy(ClassificationConfig.THRESHOLDS),
            "WEIGHTS": deepcopy(ClassificationConfig.WEIGHTS),
            "CORNER_DETECTION": deepcopy(ClassificationConfig.CORNER_DETECTION),
            "COLOR_ANALYSIS": deepcopy(ClassificationConfig.COLOR_ANALYSIS),
            "LINE_ANALYSIS": deepcopy(ClassificationConfig.LINE_ANALYSIS),
            "OCR_CONFIG": deepcopy(ClassificationConfig.OCR_CONFIG),
            "CI4_CONFIG": deepcopy(ClassificationConfig.CI4_CONFIG),
            "FEATURE_CONFIG": deepcopy(ClassificationConfig.FEATURE_CONFIG),
            "LEARNING_CONFIG": deepcopy(ClassificationConfig.LEARNING_CONFIG),
            "PERFORMANCE": deepcopy(ClassificationConfig.PERFORMANCE)
        }

    async def _load_from_file(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from file with corruption recovery.

        Returns:
            Config dict or None if file doesn't exist
        """
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)

            # Validate
            FullConfigSchema(**data)
            logger.info(f"Loaded configuration from {self.config_file}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Config file corrupted (JSON error): {e}")
            return await self._recover_from_corruption()

        except Exception as e:
            logger.error(f"Config file invalid: {e}")
            return await self._recover_from_corruption()

    async def _recover_from_corruption(self) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover from corrupted config file.

        Returns:
            Recovered config or None
        """
        # Try backup file
        backup = self.config_file.with_suffix('.json.backup')
        if backup.exists():
            try:
                logger.info("Attempting recovery from backup file")
                with open(backup, 'r') as f:
                    data = json.load(f)
                FullConfigSchema(**data)
                logger.info("Successfully recovered from backup")
                return data
            except Exception as e:
                logger.error(f"Backup file also corrupted: {e}")

        logger.warning("Using hardcoded defaults - all custom config lost")
        return None

    async def _atomic_write(self, config: Dict[str, Any]):
        """
        Write configuration to file atomically with backup.

        Args:
            config: Configuration to write
        """
        temp_file = self.config_file.with_suffix('.json.tmp')
        backup_file = self.config_file.with_suffix('.json.backup')

        try:
            # Write to temp file first
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # Backup existing config
            if self.config_file.exists():
                self.config_file.rename(backup_file)

            # Atomic rename
            temp_file.rename(self.config_file)
            logger.info(f"Configuration saved to {self.config_file}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            # Cleanup temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise

    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            updates: Updates to merge

        Returns:
            Merged dictionary
        """
        result = deepcopy(base)

        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursive merge for nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Replace value (including arrays)
                result[key] = deepcopy(value)

        return result

    def _apply_to_singleton(self, config: Dict[str, Any]):
        """Apply configuration to ClassificationConfig singleton."""
        if "THRESHOLDS" in config:
            ClassificationConfig.THRESHOLDS.update(config["THRESHOLDS"])

        if "WEIGHTS" in config:
            ClassificationConfig.update_weights(config["WEIGHTS"])

        # Update other sections
        for key in ["CORNER_DETECTION", "COLOR_ANALYSIS", "LINE_ANALYSIS",
                    "OCR_CONFIG", "FEATURE_CONFIG", "LEARNING_CONFIG", "PERFORMANCE"]:
            if key in config:
                setattr(ClassificationConfig, key, config[key])

    def _calculate_change_percentage(self, old_weights: Dict, new_weights: Dict) -> float:
        """Calculate percentage change in weights."""
        total_change = 0
        count = 0

        for category in old_weights:
            if category not in new_weights:
                continue

            for key in old_weights[category]:
                if key not in new_weights[category]:
                    continue

                old_val = old_weights[category][key]
                new_val = new_weights[category][key]

                if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                    if old_val != 0:
                        change = abs(new_val - old_val) / abs(old_val) * 100
                        total_change += change
                        count += 1

        return total_change / count if count > 0 else 0

    async def _log_change(self, action: str, old_config: Dict, new_config: Dict):
        """
        Log configuration change to audit file.

        Args:
            action: Action type (update_persisted, update_runtime, reload, reset)
            old_config: Previous configuration
            new_config: New configuration
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "changes": self._calculate_diff(old_config, new_config)
        }

        try:
            with open(self._audit_log_file, 'a') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _calculate_diff(self, old: Dict, new: Dict) -> Dict[str, Any]:
        """Calculate differences between two configs."""
        diff = {}

        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            if key not in old:
                diff[key] = {"added": new[key]}
            elif key not in new:
                diff[key] = {"removed": old[key]}
            elif old[key] != new[key]:
                diff[key] = {"old": old[key], "new": new[key]}

        return diff


# Global instance
config_manager = ConfigurationManager()
