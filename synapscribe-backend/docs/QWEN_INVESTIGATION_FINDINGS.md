# Not Giving Up on Qwen2.5-Omni-3B: A Complete Investigation

**Date:** December 2-3, 2025
**Status:** Active Investigation
**Goal:** Determine optimal approach for ASR/TTS with Qwen2.5-Omni-3B

---

## Executive Summary

We spent significant effort attempting to implement direct ASR/TTS inference with Qwen2.5-Omni-3B using the transformers library. While we successfully validated that **vLLM's chat completions API works perfectly with audio input** and maintains audio context across conversation turns, we encountered critical issues when trying to implement standalone ASR/TTS endpoints via direct model inference.

**Key Finding:** The investigation revealed that Qwen2.5-Omni's preview transformers branch is incompatible with our production environment, leading us to question whether we even need separate ASR/TTS endpoints at all.

---

## Timeline of Investigation

### Phase 1: Initial Implementation Attempt

**Date:** December 2, 2025 (Morning)

**Goal:** Implement direct inference service for ASR and TTS using Qwen2.5-Omni-3B

**Implementation:**
- Created `services/direct_inference/app.py` with FastAPI
- Used standard transformers library
- Implemented speculative processor API:
  ```python
  # ASR attempt
  inputs = processor(audio=[audio], sampling_rate=16000, return_tensors="pt")

  # TTS attempt
  inputs = processor(text=request.input, return_tensors="pt")
  ```

**Result:** FAILURE
- **TTS:** Hung for >9 minutes, never completed
- **ASR:** Hung indefinitely, never completed
- User had to Ctrl+C to abort both requests

**Symptoms:**
```
# TTS test
curl -X POST http://localhost:8001/v1/audio/speech \
  -d '{"input": "Hello world"}' --output test.mp3
# Ran for 9+ minutes, returned 0 bytes
```

---

### Phase 2: Root Cause Analysis

**Hypothesis 1:** Wrong processor API usage

**Investigation:**
- Searched for Qwen2.5-Omni documentation
- Found HuggingFace model card: https://huggingface.co/Qwen/Qwen2.5-Omni-3B
- Discovered the processor API we were using was completely wrong

**Actual Requirements Discovered:**

1. **Special transformers version required:**
   ```bash
   pip uninstall transformers
   pip install git+https://github.com/huggingface/transformers@v4.51.3-Qwen2.5-Omni-preview
   pip install qwen-omni-utils[decord] -U
   ```

2. **Different model/processor classes:**
   ```python
   from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
   from qwen_omni_utils import process_mm_info
   ```

3. **Conversation-based API pattern:**
   ```python
   # ASR (correct)
   conversation = [
       {"role": "user", "content": [{"type": "audio", "audio": audio_array}]}
   ]
   text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
   audios, images, videos = process_mm_info(conversation, use_audio_in_video=False)
   inputs = processor(text=text, audio=audios, images=images, videos=videos,
                      return_tensors="pt", padding=True)
   text_ids = model.generate(**inputs, return_audio=False)

   # TTS (correct) - requires system prompt
   conversation = [
       {
           "role": "system",
           "content": [{"type": "text", "text": "You are Qwen, a virtual human..."}]
       },
       {"role": "user", "content": text_to_synthesize}
   ]
   text_ids, audio = model.generate(**inputs)  # Returns both text and audio
   ```

**Findings:**
- Our initial implementation was using a non-existent API
- Qwen2.5-Omni requires a preview branch of transformers
- The API is conversation-based, not direct audio-in/audio-out

---

### Phase 3: Correct API Implementation

**Date:** December 2, 2025 (Evening)

**Changes Made:**
1. Updated `services/direct_inference/app.py` with correct API
2. Updated `requirements.txt` to use preview transformers
3. Deployed to EC2

**Deployment Commands:**
```bash
# Uploaded corrected files
scp -i "qwen-test-login.pem" \
  services/direct_inference/app.py \
  services/direct_inference/requirements.txt \
  ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com:/home/ubuntu/services/direct_inference/

# On EC2
source /home/ubuntu/venv/bin/activate
pip uninstall transformers -y
pip install git+https://github.com/huggingface/transformers@v4.51.3-Qwen2.5-Omni-preview
pip install qwen-omni-utils[decord] -U
```

**Result:** PARTIAL FAILURE

**Issue 1: Dependency Conflict**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
This behaviour is the source of the following dependency conflicts.
vllm 0.11.1 requires transformers<5,>=4.56.0, but you have transformers 4.52.0.dev0 which is incompatible.
```

**Analysis:**
- Preview transformers version: **4.52.0.dev0**
- vLLM requires: **>=4.56.0**
- The "preview" branch is actually **OLDER** than what vLLM needs
- This creates an unresolvable conflict

**Issue 2: SystemD Service Path Wrong**
```
Dec 02 23:51:48 qwen-inference.service: Changing to the requested working directory failed:
No such file or directory
```
- Service file still pointed to `/home/ubuntu/synapscribe/services/direct_inference`
- Correct path: `/home/ubuntu/services/direct_inference`

**Issue 3: Performance Still Terrible**
```bash
# TTS test
curl -X POST http://localhost:8001/v1/audio/speech \
  -d '{"input": "Hello world, this is a test."}' --output test-output.mp3
# Took 23 seconds, created 103-byte file (error response, not audio)

# ASR test
curl -X POST http://localhost:8001/v1/audio/transcriptions \
  -F "file=@/home/ubuntu/test-audio/query_30sec.mp3"
# Hung indefinitely again, user had to Ctrl+C
```

**Even with the "correct" API, performance was still unacceptable.**

---

## Critical Findings

### Finding 1: Preview Transformers Incompatibility

The Qwen2.5-Omni preview transformers branch (v4.51.3-Qwen2.5-Omni-preview) is:

1. **Older than production requirements**
   - Version: 4.52.0.dev0
   - vLLM requires: >=4.56.0
   - Creates version conflict

2. **Not production-ready**
   - Still in preview/development
   - Requires additional `qwen-omni-utils` package
   - Not in official transformers release

3. **Breaks vLLM compatibility**
   - Cannot have both preview transformers and working vLLM
   - Would require downgrading vLLM (risky)

### Finding 2: Performance Issues Persist

Even with the correct API:
- TTS took **23+ seconds** for short text (should be <5s)
- ASR **hung indefinitely** (should be <5s for 30s audio)
- Output files were invalid (103 bytes = error response)

**Possible reasons:**
- Model not optimized for direct inference
- Preview branch has performance bugs
- API not production-ready
- Wrong generation parameters still

### Finding 3: vLLM Chat Completions Work Perfectly

Throughout this investigation, one thing remained consistently successful:

**vLLM's chat completions endpoint with audio input works flawlessly:**

```bash
# This WORKS
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-Omni-3B",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "audio_url", "audio_url": {"url": "file:///path/to/audio.mp3"}},
          {"type": "text", "text": "What is this about?"}
        ]
      }
    ]
  }'
```

**Validated capabilities:**
- ✅ Audio context loading
- ✅ Multi-turn conversation with audio persistence
- ✅ Fast response times (<3s)
- ✅ No dependency conflicts
- ✅ Production-ready

---

## The Critical Question

**User's insight (December 3, 2025):**

> "If the Qwen model can handle audio context persistence and audio Q&A works, then why do we need ASR and TTS? Doesn't the Qwen model take audio query input and stream audio response output?"

This is a **brilliant observation** that challenges our entire approach.

### What We Know

**vLLM Chat Completions API can:**
1. ✅ Accept audio input (validated)
2. ✅ Maintain audio context across turns (validated)
3. ✅ Generate text responses (validated)
4. ❓ Generate audio output? (NOT YET TESTED)

### What We Need to Investigate

**Question 1: Can vLLM chat completions do ASR?**

Instead of a dedicated `/v1/audio/transcriptions` endpoint, can we just:
```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "audio_url", "audio_url": {"url": "file:///audio.mp3"}},
        {"type": "text", "text": "Transcribe this audio word-for-word."}
      ]
    }
  ]
}
```

**Hypothesis:** Yes, this should work since the model can understand audio

**Question 2: Can vLLM chat completions return audio output?**

This is the critical unknown:
- Qwen2.5-Omni is an **any-to-any** model (text/audio/image/video → text/audio)
- But does vLLM's API expose the audio generation capability?
- Or does it only return text even when the model generates audio internally?

**To test:**
```bash
# Check vLLM API documentation for audio output
# Try requesting audio response format
# See if there's a way to get audio tokens/waveform back
```

### Potential Architectural Simplification

**If vLLM can return audio output:**

```
┌─────────────────────────────────────┐
│ Frontend                             │
│  ↓ audio query                       │
│  ↑ audio response                    │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│ vLLM (port 8000)                     │
│  • Chat completions with audio I/O   │
│  • Does ASR via prompt engineering   │
│  • Returns audio directly            │
│  • NO NEED for direct inference!     │
└──────────────────────────────────────┘
```

**Benefits:**
- ✅ Single service (simpler architecture)
- ✅ No dependency conflicts
- ✅ No direct inference complexity
- ✅ Production-ready (vLLM is battle-tested)
- ✅ Consistent API

**If vLLM cannot return audio output:**

We need TTS, but ASR might still work via prompting:

```
┌─────────────────────────────────────┐
│ vLLM (port 8000)                     │
│  • Chat completions for Q&A          │
│  • ASR via prompt: "transcribe this" │
└──────────────────────────────────────┘
                  +
┌──────────────────────────────────────┐
│ Direct Inference (port 8001)         │
│  • TTS only (Whisper/gTTS/Coqui)     │
└──────────────────────────────────────┘
```

---

## Tested Solutions Summary

### Solution 1: Direct Inference with Standard Transformers
**Status:** ❌ Failed
**Duration:** 2-3 hours
**Reason:** Wrong API, model hung indefinitely

### Solution 2: Direct Inference with Preview Transformers
**Status:** ❌ Failed
**Duration:** 3-4 hours
**Reason:** Dependency conflict with vLLM, performance still terrible

### Solution 3: vLLM Chat Completions Only (Proposed)
**Status:** 🔍 Under Investigation
**Hypothesis:** Use vLLM for everything via prompt engineering
**Benefits:** Simplest, no conflicts, production-ready

### Solution 4: Hybrid with Proven Models (Backup Plan)
**Status:** ⏸️ Ready to Deploy
**Components:** Whisper (ASR) + gTTS (TTS) + vLLM (Q&A)
**Benefits:** Known performance, no research needed, can deploy today

---

## Lessons Learned

### 1. Preview Branches Are Risky

The Qwen2.5-Omni preview transformers taught us:
- Preview != Production-ready
- Version numbers can be misleading (4.52 dev < 4.56 release)
- Always check dependency compatibility before committing
- Official documentation may not reflect real-world constraints

### 2. Performance Testing Is Critical

Even with "correct" API:
- Implementation can still have performance issues
- Must validate with real workloads
- Preview code may have optimization gaps

### 3. Simpler Is Often Better

The user's question revealed:
- We may have over-engineered the solution
- Sometimes the existing tool (vLLM) can do everything
- Prompt engineering > Complex service architecture

### 4. Validate Assumptions Early

We spent hours on direct inference before testing:
- Can vLLM do ASR via prompting?
- Does vLLM expose audio output?
- Do we even need separate endpoints?

**Better approach:** Test the simplest solution first

---

## Next Steps

### Immediate: Answer The Critical Question

**Test 1: ASR via vLLM Chat Completions**
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-Omni-3B",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "audio_url", "audio_url": {"url": "file:///home/ubuntu/test-audio/query_30sec.mp3"}},
        {"type": "text", "text": "Please transcribe this audio word-for-word with proper punctuation."}
      ]
    }]
  }'
```

**Expected:** If this works, we don't need dedicated ASR endpoint

**Test 2: Audio Output from vLLM**
- Check vLLM documentation for audio response format
- Test if vLLM can return audio tokens/waveform
- Check Qwen2.5-Omni integration with vLLM

**Expected:** If vLLM can return audio, we don't need TTS either

### Decision Tree

```
Can vLLM do ASR via prompt?
├─ YES
│  └─ Can vLLM return audio output?
│     ├─ YES → Use vLLM only! ✅
│     └─ NO → vLLM (ASR+Q&A) + Direct TTS
└─ NO
   └─ Need dedicated ASR/TTS
      └─ Use Whisper + gTTS (proven solution)
```

---

## Conclusion

We haven't given up on Qwen2.5-Omni-3B—we've **learned** from it:

1. **vLLM integration works perfectly** for audio Q&A
2. **Direct inference via preview transformers is not viable** in our environment
3. **There may be a simpler solution** using vLLM for everything
4. **We have a proven backup plan** (Whisper + gTTS) if needed

The investigation continues with a focus on **architectural simplification** rather than complex workarounds.

**Current Status:** Investigating whether vLLM chat completions can handle all ASR/TTS needs via prompt engineering and audio output support.

**If successful:** We can eliminate the direct inference service entirely and use vLLM for everything.

**If not:** We deploy the proven Whisper + gTTS solution and move forward with Phase 0.

---

## FINAL FINDINGS: Model Capability vs. API Limitation

**Date:** December 2-3, 2025
**Status:** Investigation Complete

### Test Results

#### Test 1: ASR via vLLM Chat Completions - ✅ SUCCESS

**Hypothesis:** Can vLLM transcribe audio via prompt engineering instead of dedicated ASR endpoint?

**Test Executed:**
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/opt/models/qwen-omni",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "audio_url", "audio_url": {"url": "file:///home/ubuntu/test-audio/query_30sec.mp3"}},
        {"type": "text", "text": "Please transcribe this audio word-for-word with proper punctuation."}
      ]
    }]
  }'
```

**Result:** CONFIRMED WORKING! 🎉

**Transcription Quality:**
> "When we fit into all of this. Well it's taken us eighteen lectures. Humans have made guest appearances, maybe in the form of scientists. But now, at last, humans are waiting in the wings, though I'm afraid you're going to have to still wait two more lectures before they make a full entrance with trumpets blaring. But perhaps this long delay is actually helpful, and it can tell us something about the nature of big history. It's a reminder that the story is not all."

**Performance Metrics:**
- ⏱️ **Response time:** ~2 seconds for 30s audio (excellent!)
- ✅ **Quality:** Coherent, properly punctuated transcription
- ✅ **Format:** Standard OpenAI chat completions response
- 📊 **Token usage:** 790 prompt tokens (audio), 103 completion tokens (text)

**Key Finding:** vLLM successfully transcribes audio via prompt engineering! **No need for separate `/v1/audio/transcriptions` endpoint.**

#### Test 2: TTS via vLLM Chat Completions - ❌ NOT EXPOSED BY API

**Hypothesis:** Can vLLM generate and return audio in responses?

**Research Conducted:**
1. ✅ Checked vLLM documentation (https://docs.vllm.ai/)
2. ✅ Searched for audio output/generation features
3. ✅ Examined API response structure from successful ASR test
4. ✅ Reviewed Qwen2.5-Omni model capabilities on HuggingFace

**Critical Finding - Model vs. API Limitation:**

### The Model CAN Generate Audio

**Qwen2.5-Omni Model Capability (from HuggingFace):**
- ✅ **Model DOES have native audio generation** capability
- ✅ Uses "Thinker-Talker" architecture designed for multimodal I/O
- ✅ Can "generate text and natural speech responses in a streaming manner"
- ✅ Supports text/image/audio/video → **text/audio output**
- ✅ Model architecture includes audio generation components

**From HuggingFace Documentation:**
> "We propose Thinker-Talker architecture, an end-to-end multimodal model designed to perceive diverse modalities, including text, images, audio, and video, while simultaneously generating text and natural speech responses in a streaming manner."

### But vLLM Doesn't Expose It

**vLLM API Limitation:**
- ❌ **vLLM does NOT expose audio generation** in its API
- 📋 OpenAI-compatible endpoints focus on audio INPUT only (transcription/translation)
- 🔍 No API parameters to request audio output
- 📦 The `audio` field exists in response structure but is always `null`

**Evidence from API Response:**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "transcribed text here",
      "audio": null  // Field exists but always null
    }
  }]
}
```

### Why This Matters

**This is an API limitation, NOT a model limitation.**

The Qwen2.5-Omni model has the capability to generate audio responses natively, but vLLM's inference server doesn't currently expose this functionality through its API. This is why we need a separate TTS service for Phase 0.

**Architectural Impact:**
- We're not "giving up" on Qwen2.5-Omni's audio generation
- We're working around a **temporary infrastructure limitation**
- If/when vLLM adds audio output support, we can eliminate the TTS service entirely
- For now, gTTS provides a pragmatic, production-ready solution

### Final Architecture Decision

**Hybrid Approach (vLLM + gTTS):**

```
┌─────────────────────────────────────┐
│ Frontend                             │
│  ↓ audio query                       │
│  ↑ audio response                    │
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
┌─────▼─────────┐  ┌────▼──────────────┐
│ vLLM          │  │ TTS Service       │
│ (port 8000)   │  │ (port 8001)       │
│               │  │                   │
│ • ASR via     │  │ • gTTS only       │
│   prompting   │  │                   │
│ • Q&A with    │  │                   │
│   audio ctx   │  └───────────────────┘
│ • Text output │
└───────────────┘
```

**Benefits:**
1. ✅ **Simplified from original plan:** Only need TTS, not ASR
2. ✅ **Leverages vLLM strength:** Use it for both ASR and Q&A via prompting
3. ✅ **Production-ready:** gTTS is battle-tested, fast, reliable
4. ✅ **No version conflicts:** Removed heavy transformers/torch from TTS service
5. ✅ **Fast deployment:** gTTS requires no model downloads
6. ✅ **Future-proof:** Can swap gTTS for vLLM audio when/if vLLM adds support

**What We Eliminated:**
- ❌ Separate ASR endpoint (vLLM does this via prompting)
- ❌ Whisper model (don't need it anymore)
- ❌ Complex direct inference service (simplified to TTS-only)
- ❌ Transformers version conflicts (removed from TTS service)

### Success Metrics

- ✅ **ASR via vLLM:** ~2 seconds for 30s audio (VALIDATED)
- 🎯 **TTS via gTTS:** < 2 seconds for short text (to be validated in deployment)
- ✅ **No dependency conflicts:** Removed problematic preview transformers
- ✅ **Architectural simplification:** From complex hybrid to simple vLLM+gTTS
- ✅ **Phase 0 ready:** Can complete validation and move to Phase 1

---

## Appendix: Technical Details

### Preview Transformers Installation

```bash
pip uninstall transformers -y
pip install git+https://github.com/huggingface/transformers@v4.51.3-Qwen2.5-Omni-preview
pip install qwen-omni-utils[decord] -U
```

**Version installed:** 4.52.0.dev0
**Conflict with:** vLLM 0.11.1 (requires >=4.56.0)

### Correct Qwen2.5-Omni API Usage

```python
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
from qwen_omni_utils import process_mm_info

# Load model
model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
    'Qwen/Qwen2.5-Omni-3B',
    torch_dtype=torch.bfloat16,
    device_map='auto',
    trust_remote_code=True
)
processor = Qwen2_5OmniProcessor.from_pretrained(
    'Qwen/Qwen2.5-Omni-3B',
    trust_remote_code=True
)

# ASR
conversation = [{"role": "user", "content": [{"type": "audio", "audio": audio_array}]}]
text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
audios, images, videos = process_mm_info(conversation, use_audio_in_video=False)
inputs = processor(text=text, audio=audios, images=images, videos=videos, return_tensors="pt", padding=True)
text_ids = model.generate(**inputs, return_audio=False)
transcript = processor.batch_decode(text_ids, skip_special_tokens=True)[0]

# TTS
system_prompt = "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."
conversation = [
    {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
    {"role": "user", "content": text_to_synthesize}
]
text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
audios, images, videos = process_mm_info(conversation)
inputs = processor(text=text, audio=audios, images=images, videos=videos, return_tensors="pt", padding=True)
text_ids, audio = model.generate(**inputs, speaker="Chelsie")  # or "Ethan"
audio_array = audio.reshape(-1).detach().cpu().numpy()
```

### Performance Benchmarks

| Operation | Expected | Actual (Standard) | Actual (Preview) | Status |
|-----------|----------|-------------------|------------------|--------|
| ASR (30s audio) | <5s | Never completed | Never completed | ❌ |
| TTS (short text) | <5s | Never completed | 23s (error) | ❌ |
| Chat w/ audio | <3s | - | - | ✅ (vLLM) |
| Audio context | <5s overhead | - | - | ✅ (vLLM) |

### Error Messages

**Dependency Conflict:**
```
vllm 0.11.1 requires transformers<5,>=4.56.0,
but you have transformers 4.52.0.dev0 which is incompatible.
```

**SystemD Service:**
```
qwen-inference.service: Changing to the requested working directory failed:
No such file or directory
```

**TTS Output:**
```
% Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   144  100   103  100    41      4      1  0:00:41  0:00:23  0:00:18    26
```
(103 bytes = error JSON, not audio)
