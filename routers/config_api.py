# routers/config_api.py
# Configuration API endpoints

import os
import logging
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, Dict, Any

from config_manager import config_manager
from config_schemas import FullConfigSchema, ConfigMetadata
from config import ClassificationConfig

logger = logging.getLogger(__name__)

router = APIRouter(tags=["configuration"])


# Authentication dependency
async def verify_api_key(x_config_api_key: str = Header(...)) -> bool:
    """
    Verify configuration API key.

    Args:
        x_config_api_key: API key from header

    Returns:
        True if valid

    Raises:
        HTTPException: If invalid or not configured
    """
    expected = os.getenv("CONFIG_API_KEY")

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Configuration API is not enabled. Set CONFIG_API_KEY environment variable."
        )

    if x_config_api_key != expected:
        raise HTTPException(
            status_code=403,
            detail="Invalid configuration API key"
        )

    return True


@router.get("", response_model=Dict[str, Any])
async def get_full_config(
    include_runtime: bool = False,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get complete configuration.

    Args:
        include_runtime: Include runtime learning adjustments (default: False)

    Returns:
        Complete configuration with metadata
    """
    try:
        config = await config_manager.get_config()
        metadata = config_manager.get_metadata()

        return {
            "config": config,
            "metadata": metadata.dict()
        }

    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weights", response_model=Dict[str, Any])
async def get_weights(authenticated: bool = Depends(verify_api_key)):
    """
    Get current weights (base + runtime learning adjustments).

    Returns:
        Current weights configuration
    """
    try:
        return await config_manager.get_config("WEIGHTS")
    except Exception as e:
        logger.error(f"Failed to get weights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thresholds", response_model=Dict[str, float])
async def get_thresholds(authenticated: bool = Depends(verify_api_key)):
    """
    Get current classification thresholds.

    Returns:
        Current thresholds configuration
    """
    try:
        return await config_manager.get_config("THRESHOLDS")
    except Exception as e:
        logger.error(f"Failed to get thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_config_schema():
    """
    Get configuration JSON schema.
    No authentication required - useful for CI4 UI generation.

    Returns:
        Pydantic JSON schema
    """
    try:
        return FullConfigSchema.schema()
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=Dict[str, Any])
async def update_config(
    config_update: Dict[str, Any],
    dry_run: bool = False,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Update configuration.

    Args:
        config_update: Configuration updates (full or partial)
        dry_run: If True, validate only without applying changes

    Returns:
        Updated configuration with warnings and status

    WARNING: Updating weights will reset the learning system!
    """
    try:
        # Safety validation
        warnings = await config_manager.validate_safety(config_update)

        if dry_run:
            return {
                "status": "validated",
                "warnings": warnings,
                "changes": config_update
            }

        # Apply update
        learning_reset = "WEIGHTS" in config_update or "THRESHOLDS" in config_update
        updated_config = await config_manager.update_config(config_update, persist=True)

        # Reset learning system if weights changed
        if learning_reset:
            logger.warning("Learning system needs reset due to base config change")
            # Note: Learning system reset will be triggered in classifier_service.py
            # via feedback_processor.reset_learning()

        # Sync to CI4 if enabled
        ci4_synced = False
        if ClassificationConfig.CI4_CONFIG.get("enabled"):
            try:
                from database.ci4_client import ci4_client
                await ci4_client.update_base_config(config_update)
                ci4_synced = True
                logger.info("Configuration synced to CI4")
            except Exception as e:
                logger.error(f"Failed to sync to CI4: {e}")
                warnings.append(f"CI4 sync failed: {str(e)}")

        return {
            "status": "updated",
            "warnings": warnings,
            "config": updated_config,
            "learning_reset_required": learning_reset,
            "ci4_synced": ci4_synced
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload", response_model=Dict[str, Any])
async def reload_config(
    clear_runtime: bool = True,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Reload configuration from file.

    Args:
        clear_runtime: If True, discard runtime learning adjustments (default: True)

    Returns:
        Reloaded configuration

    WARNING: clear_runtime=True will lose all adaptive learning progress!
    """
    try:
        config = await config_manager.reload(clear_runtime=clear_runtime)

        return {
            "status": "reloaded",
            "learning_cleared": clear_runtime,
            "config": config
        }

    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=Dict[str, Any])
async def reset_config(authenticated: bool = Depends(verify_api_key)):
    """
    Reset configuration to factory defaults.

    Returns:
        Default configuration

    WARNING: This clears all customizations, learning progress, and syncs defaults to CI4!
    """
    try:
        defaults = await config_manager.reset_to_defaults()

        # Sync to CI4 if enabled
        ci4_synced = False
        if ClassificationConfig.CI4_CONFIG.get("enabled"):
            try:
                from database.ci4_client import ci4_client
                await ci4_client.update_model_weights(
                    defaults.get("WEIGHTS", {}),
                    defaults.get("THRESHOLDS", {})
                )
                ci4_synced = True
                logger.info("Default configuration synced to CI4")
            except Exception as e:
                logger.error(f"Failed to sync defaults to CI4: {e}")

        return {
            "status": "reset",
            "config": defaults,
            "ci4_synced": ci4_synced
        }

    except Exception as e:
        logger.error(f"Failed to reset configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff", response_model=Dict[str, Any])
async def get_config_diff(
    compare_to: str = "defaults",
    authenticated: bool = Depends(verify_api_key)
):
    """
    Compare current configuration to a baseline.

    Args:
        compare_to: Baseline to compare against ("defaults", "file", "ci4")

    Returns:
        Comparison result showing differences
    """
    try:
        current = await config_manager.get_config()

        if compare_to == "defaults":
            baseline = config_manager._get_defaults()
            baseline_name = "Factory Defaults"

        elif compare_to == "file":
            baseline = await config_manager._load_from_file()
            if not baseline:
                raise HTTPException(status_code=404, detail="No config file exists")
            baseline_name = "Config File"

        elif compare_to == "ci4":
            if not ClassificationConfig.CI4_CONFIG.get("enabled"):
                raise HTTPException(status_code=400, detail="CI4 integration not enabled")

            try:
                from database.ci4_client import ci4_client
                ci4_data = await ci4_client.get_model_weights()
                if not ci4_data:
                    raise HTTPException(status_code=404, detail="No weights in CI4")

                baseline = {
                    "WEIGHTS": ci4_data.get("weights", {}),
                    "THRESHOLDS": ci4_data.get("thresholds", {})
                }
                baseline_name = "CI4 Database"

            except ImportError:
                raise HTTPException(status_code=503, detail="CI4 client not available")

        else:
            raise HTTPException(status_code=400, detail=f"Invalid compare_to value: {compare_to}")

        diff = config_manager._calculate_diff(baseline, current)

        return {
            "baseline": baseline_name,
            "has_differences": bool(diff),
            "diff": diff,
            "current": current,
            "baseline_config": baseline
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-from-ci4", response_model=Dict[str, Any])
async def sync_from_ci4(
    persist: bool = True,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Pull latest configuration from CI4 database.

    Args:
        persist: If True, save to config file (default: True)

    Returns:
        Synced configuration
    """
    if not ClassificationConfig.CI4_CONFIG.get("enabled"):
        raise HTTPException(status_code=400, detail="CI4 integration not enabled")

    try:
        from database.ci4_client import ci4_client

        # Get weights from CI4
        ci4_data = await ci4_client.get_model_weights()
        if not ci4_data:
            raise HTTPException(status_code=404, detail="No weights available in CI4")

        update = {
            "WEIGHTS": ci4_data.get("weights", {}),
            "THRESHOLDS": ci4_data.get("thresholds", {})
        }

        # Apply update
        updated_config = await config_manager.update_config(update, persist=persist)

        return {
            "status": "synced",
            "persisted": persist,
            "config": updated_config
        }

    except ImportError:
        raise HTTPException(status_code=503, detail="CI4 client not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync from CI4: {e}")
        raise HTTPException(status_code=500, detail=str(e))
