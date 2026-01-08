# Configuration API Documentation

## Overview

The Configuration API provides full programmatic access to the OCR classifier service configuration. This enables CI4 to manage the service through a web interface, allowing administrators to adjust classification behavior without code changes or service restarts.

## Features

- ✅ Complete read/write access to all configuration parameters
- ✅ Thread-safe operations with atomic file writes
- ✅ Pydantic validation for all changes
- ✅ Automatic backup and corruption recovery
- ✅ API key authentication
- ✅ JSON schema export for auto-generating UIs
- ✅ Configuration diff and rollback capabilities
- ✅ Integration with adaptive learning system
- ✅ CI4 synchronization support

## Authentication

All configuration endpoints (except `/config/schema`) require authentication via API key.

### Header Format

```
X-Config-API-Key: your-secure-api-key
```

### Setting the API Key

The API key is configured via environment variable in the systemd service file:

```ini
Environment="CONFIG_API_KEY=your-secure-api-key"
```

Current key: `ocr-config-secure-key-2026` (change this in production!)

## Base URL

```
https://ocr.dorfmecklenburg.eu/config
```

## Endpoints

### 1. GET /config

Get complete configuration with metadata.

**Authentication**: Required

**Query Parameters**:
- `include_runtime` (boolean, optional): Include runtime learning adjustments. Default: false

**Response**:
```json
{
  "config": {
    "version": "1.0.0",
    "THRESHOLDS": {
      "arbeitsbericht": 5.0,
      "typeplate": 3.0,
      "document": 1.5,
      "photo": 0.0
    },
    "WEIGHTS": { ... },
    "CORNER_DETECTION": { ... },
    ...
  },
  "metadata": {
    "version": "1.0.0",
    "last_modified": 1704672000.123,
    "ci4_enabled": false,
    "has_runtime_overrides": true,
    "config_file_exists": true
  }
}
```

**Example**:
```bash
curl -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  https://ocr.dorfmecklenburg.eu/config
```

---

### 2. GET /config/weights

Get current classification weights (includes runtime learning adjustments).

**Authentication**: Required

**Response**:
```json
{
  "AR": {
    "text_length_divisor": 500,
    "text_length_factor": 1.5,
    "keyword_multiplier": 2.0,
    "clip_bonus": 1.0,
    "min_text_length": 500
  },
  "TP": { ... },
  "DOC": { ... },
  "PHOTO": { ... }
}
```

**Example**:
```bash
curl -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  https://ocr.dorfmecklenburg.eu/config/weights
```

---

### 3. GET /config/thresholds

Get current classification thresholds.

**Authentication**: Required

**Response**:
```json
{
  "arbeitsbericht": 5.0,
  "typeplate": 3.0,
  "document": 1.5,
  "photo": 0.0
}
```

**Example**:
```bash
curl -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  https://ocr.dorfmecklenburg.eu/config/thresholds
```

---

### 4. GET /config/schema

Get Pydantic JSON schema for all configuration options.

**Authentication**: Not required (public endpoint)

**Response**: Complete JSON schema with field types, constraints, descriptions, and defaults

**Use Case**: CI4 can use this to dynamically generate configuration forms

**Example**:
```bash
curl https://ocr.dorfmecklenburg.eu/config/schema
```

---

### 5. PUT /config

Update configuration (full or partial).

**Authentication**: Required

**Query Parameters**:
- `dry_run` (boolean, optional): Validate only without applying. Default: false

**Request Body**: JSON configuration (full or partial)

**Response**:
```json
{
  "status": "updated",
  "warnings": [
    "Weights changed by 35.2% - may affect classification accuracy"
  ],
  "config": { ... },
  "learning_reset_required": true,
  "ci4_synced": false
}
```

**Important Notes**:
- Validates all values before applying
- Updates are atomic (all or nothing)
- Automatically backs up current config
- **WARNING**: Changing weights or thresholds resets the learning system!

**Example - Update thresholds**:
```bash
curl -X PUT -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "THRESHOLDS": {
      "arbeitsbericht": 6.0,
      "typeplate": 3.5
    }
  }' \
  https://ocr.dorfmecklenburg.eu/config
```

**Example - Dry run validation**:
```bash
curl -X PUT -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"THRESHOLDS": {"arbeitsbericht": 10.0}}' \
  "https://ocr.dorfmecklenburg.eu/config?dry_run=true"
```

---

### 6. POST /config/reload

Reload configuration from file.

**Authentication**: Required

**Query Parameters**:
- `clear_runtime` (boolean, optional): Clear runtime learning adjustments. Default: true

**Response**:
```json
{
  "status": "reloaded",
  "learning_cleared": true,
  "config": { ... }
}
```

**WARNING**: `clear_runtime=true` discards all adaptive learning progress!

**Example**:
```bash
curl -X POST -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  "https://ocr.dorfmecklenburg.eu/config/reload?clear_runtime=false"
```

---

### 7. POST /config/reset

Reset configuration to factory defaults.

**Authentication**: Required

**Response**:
```json
{
  "status": "reset",
  "config": { ... },
  "ci4_synced": false
}
```

**WARNING**: This clears:
- All custom configuration
- config.json file
- All learning progress
- Syncs defaults to CI4 (if enabled)

**Example**:
```bash
curl -X POST -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  https://ocr.dorfmecklenburg.eu/config/reset
```

---

### 8. GET /config/diff

Compare current configuration to a baseline.

**Authentication**: Required

**Query Parameters**:
- `compare_to` (string, required): Baseline to compare against
  - `defaults` - Factory defaults
  - `file` - Config file on disk
  - `ci4` - CI4 database (requires CI4 enabled)

**Response**:
```json
{
  "baseline": "Factory Defaults",
  "has_differences": true,
  "diff": {
    "THRESHOLDS": {
      "old": {"arbeitsbericht": 5.0},
      "new": {"arbeitsbericht": 6.0}
    }
  },
  "current": { ... },
  "baseline_config": { ... }
}
```

**Example**:
```bash
curl -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  "https://ocr.dorfmecklenburg.eu/config/diff?compare_to=defaults"
```

---

### 9. POST /config/sync-from-ci4

Pull latest configuration from CI4 database.

**Authentication**: Required

**Query Parameters**:
- `persist` (boolean, optional): Save to config file. Default: true

**Requirements**: CI4 integration must be enabled

**Response**:
```json
{
  "status": "synced",
  "persisted": true,
  "config": { ... }
}
```

**Example**:
```bash
curl -X POST -H "X-Config-API-Key: ocr-config-secure-key-2026" \
  "https://ocr.dorfmecklenburg.eu/config/sync-from-ci4?persist=true"
```

---

## Configuration Structure

The complete configuration is organized into sections:

### THRESHOLDS
Classification score thresholds for each class.

```json
{
  "arbeitsbericht": 5.0,
  "typeplate": 3.0,
  "document": 1.5,
  "photo": 0.0
}
```

### WEIGHTS
Scoring weights for each classification class (AR, TP, DOC, PHOTO).

### CORNER_DETECTION
4-corner detection parameters (contour-based + Harris fallback).

### COLOR_ANALYSIS
LAB color space uniformity analysis parameters.

### LINE_ANALYSIS
Hough transform line detection parameters.

### OCR_CONFIG
Tesseract configuration and keyword lists.

### CI4_CONFIG
CI4 integration settings (base URL, API key, timeouts).

### FEATURE_CONFIG
Feature extraction parameters (perceptual hash, histograms, CLIP embeddings).

### LEARNING_CONFIG
Adaptive learning system parameters (learning rate, update intervals).

### PERFORMANCE
Caching and performance settings.

---

## Error Responses

### 400 Bad Request
Invalid configuration data (validation failed).

```json
{
  "detail": "Invalid configuration: Thresholds must be non-negative"
}
```

### 403 Forbidden
Invalid or missing API key.

```json
{
  "detail": "Invalid configuration API key"
}
```

### 404 Not Found
Resource not found (e.g., config file doesn't exist for reload).

```json
{
  "detail": "No config file exists"
}
```

### 500 Internal Server Error
Server-side error during processing.

```json
{
  "detail": "Failed to update configuration: ..."
}
```

### 503 Service Unavailable
API not configured (missing CONFIG_API_KEY).

```json
{
  "detail": "Configuration API is not enabled. Set CONFIG_API_KEY environment variable."
}
```

---

## CI4 Integration Guide

### Step 1: Fetch Configuration Schema

Use the schema to auto-generate your configuration UI:

```javascript
const schema = await fetch('https://ocr.dorfmecklenburg.eu/config/schema')
  .then(r => r.json());

// schema contains field types, constraints, descriptions
// Use this to build forms dynamically
```

### Step 2: Load Current Configuration

```javascript
const response = await fetch('https://ocr.dorfmecklenburg.eu/config', {
  headers: {'X-Config-API-Key': 'ocr-config-secure-key-2026'}
});

const data = await response.json();
const config = data.config;
const metadata = data.metadata;
```

### Step 3: Update Configuration

```javascript
const updates = {
  THRESHOLDS: {
    arbeitsbericht: 6.0,
    typeplate: 3.5
  }
};

const response = await fetch('https://ocr.dorfmecklenburg.eu/config', {
  method: 'PUT',
  headers: {
    'X-Config-API-Key': 'ocr-config-secure-key-2026',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(updates)
});

const result = await response.json();

if (result.learning_reset_required) {
  alert('Warning: Learning system will be reset!');
}

if (result.warnings.length > 0) {
  console.warn('Configuration warnings:', result.warnings);
}
```

### Step 4: Show Configuration Drift

Visualize how far the current config has drifted from defaults:

```javascript
const diff = await fetch(
  'https://ocr.dorfmecklenburg.eu/config/diff?compare_to=defaults',
  {headers: {'X-Config-API-Key': 'ocr-config-secure-key-2026'}}
).then(r => r.json());

if (diff.has_differences) {
  // Show diff UI
  Object.entries(diff.diff).forEach(([section, changes]) => {
    console.log(`${section} changed:`, changes);
  });
}
```

---

## Required CI4 Database Changes

To fully integrate with the Configuration API, add this table to your CI4 database:

```sql
CREATE TABLE model_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    version VARCHAR(50),
    config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    INDEX idx_created_at (created_at)
);
```

This table stores base configuration separately from the existing `model_weights` table (which stores learning adjustments).

**CI4 Endpoints to Implement**:

1. `POST /api/v1/config/base` - Store base config
2. `GET /api/v1/config/base/latest` - Retrieve latest base config

---

## Safety Features

### Thread Safety
- All configuration operations use async locks
- No race conditions between API requests, learning system, and classification

### Data Integrity
- Pydantic validation before any changes
- Atomic file writes with automatic backups
- Corruption recovery (backup → CI4 → defaults)
- Safety warnings for large changes (>50% weight shift)

### Learning System Protection
- Base config changes automatically trigger learning reset
- Runtime learning state kept separate from persisted config
- No accidental overwriting of learned weights

### Audit Trail
- All changes logged to `config_audit.jsonl`
- Includes timestamp, action type, and full diff
- Useful for debugging and compliance

---

## File Locations

- **Configuration file**: `/root/ocr-classifier/config.json`
- **Backup file**: `/root/ocr-classifier/config.json.backup`
- **Audit log**: `/root/ocr-classifier/config_audit.jsonl`

---

## Troubleshooting

### Config API returns 503

**Cause**: `CONFIG_API_KEY` environment variable not set.

**Solution**: Add to `/etc/systemd/system/ocr-classifier.service`:
```ini
Environment="CONFIG_API_KEY=your-key-here"
```

Then reload:
```bash
systemctl daemon-reload
systemctl restart ocr-classifier.service
```

### Changes not persisting after restart

**Cause**: File permissions or disk full.

**Solution**: Check file permissions and disk space:
```bash
ls -l /root/ocr-classifier/config.json
df -h
```

### Learning system keeps resetting

**Cause**: Config file contains weights that override learning adjustments.

**Solution**: Don't persist learning weights to config file. Only use config file for base configuration. Learning weights sync to CI4 automatically every 50 feedbacks.

### Config file corrupted

**Automatic Recovery**: The system will automatically attempt:
1. Load from `config.json.backup`
2. Pull from CI4 (if enabled)
3. Use hardcoded defaults

**Manual Recovery**:
```bash
# Restore from backup
cp /root/ocr-classifier/config.json.backup /root/ocr-classifier/config.json

# Or reset to defaults via API
curl -X POST -H "X-Config-API-Key: your-key" \
  https://ocr.dorfmecklenburg.eu/config/reset
```

---

## Best Practices

1. **Always use dry_run first**: Test configuration changes with `?dry_run=true` before applying

2. **Monitor warnings**: Pay attention to warning messages about large changes

3. **Backup before major changes**: The system auto-backups, but consider manual backups for major changes

4. **Test in development**: Test configuration changes in a development environment first

5. **Document changes**: Use CI4 UI to document why configuration was changed

6. **Gradual adjustments**: Make small, incremental changes rather than large jumps

7. **Monitor impact**: After configuration changes, monitor classification accuracy via `/learning/stats`

---

## Example Workflows

### Workflow 1: Adjust Typeplate Threshold

```bash
# 1. Get current configuration
curl -H "X-Config-API-Key: KEY" https://ocr.../config/thresholds

# 2. Test change with dry-run
curl -X PUT -H "X-Config-API-Key: KEY" -H "Content-Type: application/json" \
  -d '{"THRESHOLDS": {"typeplate": 3.5}}' \
  "https://ocr.../config?dry_run=true"

# 3. Apply if validation passes
curl -X PUT -H "X-Config-API-Key: KEY" -H "Content-Type: application/json" \
  -d '{"THRESHOLDS": {"typeplate": 3.5}}' \
  https://ocr.../config

# 4. Monitor classification accuracy
curl https://ocr.../learning/stats
```

### Workflow 2: Reset After Bad Configuration

```bash
# 1. Reset to defaults
curl -X POST -H "X-Config-API-Key: KEY" \
  https://ocr.../config/reset

# 2. Verify reset
curl -H "X-Config-API-Key: KEY" \
  "https://ocr.../config/diff?compare_to=defaults"

# 3. Restart service to ensure clean state
systemctl restart ocr-classifier.service
```

---

## Security Considerations

1. **Change the default API key** in production
2. **Use HTTPS** for all API requests (already configured with nginx)
3. **Restrict API key** to authorized CI4 administrators only
4. **Monitor audit log** for unauthorized changes
5. **Backup configuration** regularly via CI4
6. **Limit network access** to config endpoints (firewall rules)

---

## Support

For issues or questions about the Configuration API:

1. Check this documentation
2. Review audit logs: `/root/ocr-classifier/config_audit.jsonl`
3. Check service logs: `journalctl -u ocr-classifier.service -n 100`
4. Test with `/config/schema` to ensure API is responding
