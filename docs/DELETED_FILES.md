# Deleted Files Documentation

**Date**: December 4, 2025
**Purpose**: Record of files removed during project cleanup

## Summary

This document catalogs all files removed during the December 4, 2025 cleanup operation. These files served their purpose during development phases but are no longer needed for production operation.

## Deleted Script Files

### setup_phase0.sh
- **Purpose**: Automated EC2 setup for Phase 0 model validation
- **What it did**:
  - Installed system dependencies (Python 3.11, ffmpeg, NVIDIA drivers)
  - Created virtual environment
  - Downloaded Qwen2.5-Omni-3B model
  - Configured initial vLLM systemd service
  - Created test directories
- **Why deleted**: Phase 0 complete; EC2 instance already configured; settings incorporated into production systemd services
- **Alternative**: See systemd service files in /etc/systemd/system/

### fix_vllm_asr.sh
- **Purpose**: Fixed vLLM ASR by adding allowed-local-media-path
- **What it did**: Added --allowed-local-media-path /home/ubuntu/test-audio to vLLM service configuration
- **Why deleted**: Fix incorporated into /etc/systemd/system/vllm.service
- **Alternative**: See vLLM service configuration

### fix_vllm_memory.sh
- **Purpose**: Optimized vLLM memory usage
- **What it did**: Adjusted GPU memory utilization and batching parameters
- **Why deleted**: Optimal settings incorporated into production vLLM service
- **Alternative**: See vLLM service configuration with --gpu-memory-utilization 0.85

### fix_vllm_local_audio.sh
- **Purpose**: Configure local audio file access
- **What it did**: Set up file path permissions for audio processing
- **Why deleted**: Configuration complete in systemd service
- **Alternative**: See vLLM service configuration

### optimize_vllm_16k.sh
- **Purpose**: Optimize vLLM for 16K context length
- **What it did**: Set --max-model-len 16384 with optimized batching
- **Why deleted**: Production settings incorporated into systemd service
- **Alternative**: See /etc/systemd/system/vllm.service

## Deleted Directories

### /home/ubuntu/services/ (EC2 - Outside synapscribe/)
- **Purpose**: Phase 0 testing services
- **What it contained**:
  - Initial direct_inference implementation
  - Test scripts and configurations
- **Why deleted**: Duplicate of /home/ubuntu/synapscribe/services/ which contains the production implementation
- **Alternative**: Use /home/ubuntu/synapscribe/services/ for all service code

### test-audio/ (Local only)
- **Purpose**: Test audio files for ASR and TTS validation
- **What it contained**: query_30sec.mp3, lecture_5min/10min/20min/25min.mp3 (~30MB)
- **Why removed from local**: Files only needed on EC2 where services run
- **Alternative**: Access files on EC2 at /home/ubuntu/test-audio/

## Archived Files (docs/archive/)

### Phase 0 Artifacts
The following were archived rather than deleted for historical reference:

- notebooks/phase0_benchmarks.ipynb - Performance benchmarks
- notebooks/phase0_validation.ipynb - Model validation results
- phase0-results/ - Test results and output files
- phase0-results/benchmarks/ - Performance data

**Location**: /home/ubuntu/synapscribe/docs/archive/phase0/
**Reason**: Historical performance data useful for future comparisons

## Files Retained

### Core Application Files
- /home/ubuntu/synapscribe/services/agentcore/ - Production AgentCore service
- /home/ubuntu/synapscribe/services/direct_inference/ - Production gTTS service
- /home/ubuntu/synapscribe/docs/ - Current documentation
- /home/ubuntu/test-audio/ - Test audio files (EC2 only)

### System Configuration
- /etc/systemd/system/vllm.service - vLLM systemd service
- /etc/systemd/system/gtts.service - gTTS systemd service
- /etc/systemd/system/agentcore.service - AgentCore systemd service

### SSH Key (IMPORTANT)
- qwen-test-login.pem - Keep secured locally, DO NOT commit to GitHub
- Add to .gitignore
