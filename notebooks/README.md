# Phase 0 Validation Notebooks

This directory contains Jupyter notebooks for validating Qwen2.5-Omni-3B model capabilities on EC2 g5.2xlarge.

---

## Notebooks

### 1. `phase0_validation.ipynb`

**Purpose:** Critical validation tests to determine if model meets MVP requirements

**Tests:**
1. **Audio Context Loading (CRITICAL)** - Can the model load 25-min audio as persistent context? (16K context)
2. **Query with Audio Context** - Can we ask questions about the loaded audio?
3. **ASR Performance** - How accurate is speech recognition?
4. **TTS Performance** - How natural is the generated speech?
5. **GPU Memory Monitoring** - Does memory usage stay under 22GB (90% of 24GB)?

**Note:** Tests optimized for 16K context window (supports lectures ≤25 minutes, provides 2x performance vs 32K)

**Decision Point:** If Test #1 fails, we need fallback plan (ASR upfront + text context)

**Output:** Results saved to `/home/ubuntu/phase0-results/`

---

### 2. `phase0_benchmarks.ipynb`

**Purpose:** Comprehensive performance benchmarks for production readiness

**Benchmarks:**
1. **ASR Latency** - Measure transcription speed (30s, 5min, 20min audio)
2. **Audio Context Loading** - Test loading times (10min, 20min, 25min lectures - 16K context optimized)
3. **TTS Latency** - Measure speech synthesis speed (short, medium, long)
4. **End-to-End Q&A** - Full pipeline latency (voice → answer → audio)
5. **GPU Memory Profiling** - Track memory usage patterns
6. **Concurrent Throughput** - Test concurrent request handling

**Note:** Benchmarks optimized for 16K context window (25-min max lecture, 2x performance vs 32K)

**Output:** Results saved to `/home/ubuntu/phase0-results/benchmarks/`

---

## Prerequisites

### On EC2 Instance

1. **Phase 0 setup completed** (run `setup_phase0.sh`)
2. **Virtual environment activated**
3. **vLLM service running**
4. **Test audio files added** to `/home/ubuntu/test-audio/`

---

## Running the Notebooks

### Option A: VS Code Remote SSH (Recommended)

1. **Install VS Code Remote SSH extension** (see `scripts/VS_CODE_REMOTE_SSH.md`)
2. **Connect to EC2** via Remote SSH
3. **Open notebooks** in VS Code
4. **Select kernel:** `/home/ubuntu/venv/bin/python`
5. **Run cells** interactively

**Advantages:**
- Full IDE experience on EC2
- No file copying needed
- Edit files directly on server
- Terminal access in same window

---

### Option B: Copy Files and Use Jupyter

#### Step 1: Copy notebooks to EC2

From your local machine:

```bash
# Copy notebooks
scp -i qwen-test-login.pem notebooks/*.ipynb ubuntu@ec2-18-232-121-236.compute-1.amazonaws.com:/home/ubuntu/notebooks/
```

#### Step 2: SSH into EC2

```bash
ssh -i qwen-test-login.pem ubuntu@ec2-18-232-121-236.compute-1.amazonaws.com
```

#### Step 3: Activate virtual environment

```bash
source /home/ubuntu/venv/bin/activate
```

#### Step 4: Start Jupyter Notebook

```bash
cd /home/ubuntu/notebooks
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```

#### Step 5: Access Jupyter

The command will output a URL like:
```
http://127.0.0.1:8888/?token=abc123...
```

**On your local machine**, create SSH tunnel:
```bash
ssh -i qwen-test-login.pem -L 8888:localhost:8888 ubuntu@ec2-18-232-121-236.compute-1.amazonaws.com
```

Then open in your browser:
```
http://localhost:8888/?token=abc123...
```

---

## Test Audio Files Required

Before running notebooks, add test audio to `/home/ubuntu/test-audio/`:

**Required files:**
- `query_30sec.mp3` - 30-second voice query
- `lecture_5min.mp3` - 5-minute lecture segment
- `lecture_10min.mp3` - 10-minute lecture
- `lecture_20min.mp3` - 20-minute lecture
- `lecture_25min.mp3` - 25-minute lecture (max for 16K context)

**Sources:**
- Your own lecture recordings
- [LibriVox](https://librivox.org/) - Free public domain audiobooks
- [OpenSLR](https://www.openslr.org/) - Speech datasets
- YouTube (with appropriate permissions)

**Converting audio:**
```bash
# Convert to MP3
ffmpeg -i input.mp4 -vn -acodec mp3 output.mp3

# Trim to specific duration (25 minutes = 1500 seconds, max for 16K context)
ffmpeg -i input.mp3 -t 1500 -c copy lecture_25min.mp3

# Extract audio segment (from 1:00 to 1:30)
ffmpeg -i input.mp3 -ss 00:01:00 -t 00:00:30 -c copy query_30sec.mp3
```

---

## Verifying Setup

Before running notebooks:

### 1. Check virtual environment

```bash
source /home/ubuntu/venv/bin/activate
python --version  # Should show Python 3.x
which python      # Should show /home/ubuntu/venv/bin/python
```

### 2. Check vLLM service

```bash
# Check status
sudo systemctl status vllm

# Check endpoint
curl http://localhost:8000/health

# View logs
tail -f /var/log/vllm.log
```

### 3. Check test audio

```bash
ls -lh /home/ubuntu/test-audio/
# Should show your .mp3 files
```

### 4. Check GPU

```bash
nvidia-smi
# Should show model loaded in GPU memory
```

---

## Interpreting Results

### Validation Results (`phase0_validation.ipynb`)

**Test 1: Audio Context Loading (CRITICAL)**
- ✅ **PASS** → Proceed with Phase 1 (use audio context directly)
- ❌ **FAIL** → Implement fallback (ASR upfront + text context)

**Other Tests:**
- ASR, TTS, GPU memory should meet success criteria
- Document any failures in `docs/PHASE0_REPORT.md`

---

### Benchmark Results (`phase0_benchmarks.ipynb`)

**Success Criteria:**

| Metric | Target | Notes |
|--------|--------|-------|
| ASR Latency | <0.5x real-time | 25-min audio in <12.5min |
| Context Load | <10 seconds | For 25-min audio (16K context) |
| TTS Latency | <3 seconds | For 50-word response |
| E2E Q&A | <10 seconds | Voice query → audio answer |
| GPU Memory | <22GB (90%) | Peak usage |
| Throughput | >2 req/sec | Concurrent ASR requests |

**If targets not met:**
- Document performance gaps
- Identify optimization opportunities
- Consider infrastructure changes

---

## Troubleshooting

### Virtual Environment Not Active

**Symptom:**
```
ModuleNotFoundError: No module named 'vllm'
```

**Fix:**
```bash
source /home/ubuntu/venv/bin/activate
```

---

### vLLM Endpoint Not Responding

**Symptom:**
```
❌ vLLM endpoint not responding!
```

**Fix:**
```bash
# Check status
sudo systemctl status vllm

# View logs
tail -f /var/log/vllm.log

# Restart if needed
sudo systemctl restart vllm

# Wait 2-3 minutes for startup
sleep 120
curl http://localhost:8000/health
```

---

### Test Audio Files Missing

**Symptom:**
```
❌ Test audio file not found: /home/ubuntu/test-audio/lecture_30min.mp3
```

**Fix:**
Add real audio files to `/home/ubuntu/test-audio/` (see "Test Audio Files Required" section)

---

### GPU Out of Memory

**Symptom:**
```
RuntimeError: CUDA out of memory
```

**Fix:**
```bash
# Check current usage
nvidia-smi

# Restart vLLM to clear memory
sudo systemctl restart vllm

# Wait for restart
sleep 120
```

---

### Jupyter Kernel Crashes

**Symptom:**
Kernel dies during notebook execution

**Fix:**
```bash
# Check system resources
free -h
df -h

# Check vLLM logs for errors
tail -100 /var/log/vllm.log

# Restart vLLM if needed
sudo systemctl restart vllm
```

---

## Next Steps After Validation

1. **Review all results** in `/home/ubuntu/phase0-results/`
2. **Document findings** in `docs/PHASE0_REPORT.md`
3. **Make Go/No-Go decision** for Phase 1
4. **If GO:** Proceed with Phase 1 infrastructure setup
5. **If NO-GO:** Implement fallback plan and re-validate

---

## Results Location

All results are saved to:
```
/home/ubuntu/phase0-results/
├── test1_audio_context.json      # Critical test result
├── test2_query_context.json
├── test3_asr.json
├── test4_tts.json
├── test4_tts_output.wav          # TTS sample
└── benchmarks/
    ├── asr_latency.json
    ├── context_loading.json
    ├── tts_latency.json
    ├── tts_short_sample.wav
    ├── tts_medium_sample.wav
    ├── tts_long_sample.wav
    ├── e2e_qa_latency.json
    ├── e2e_response_sample.wav
    ├── gpu_memory_profile.json
    └── concurrent_throughput.json
```

---

## Contact

For issues with notebooks:
1. Check vLLM logs: `tail -f /var/log/vllm.log`
2. Check service status: `sudo systemctl status vllm`
3. Verify GPU: `nvidia-smi`
4. Check virtual environment: `which python`
