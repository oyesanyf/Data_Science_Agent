# OpenAI-First Architecture with Rate Limit Protection

## 📋 Overview

The Data Science Agent uses a **resilient, OpenAI-first architecture** with intelligent fallback mechanisms to ensure reliable operation even under high load or rate limiting.

**Key Features:**
- ✅ **OpenAI Primary** - Fast, reliable, cost-effective
- ✅ **Circuit Breaker** - Prevents cascading failures
- ✅ **Exponential Backoff** - Handles transient rate limits
- ✅ **Automatic Fallback** - Seamless Gemini fallback if needed
- ✅ **Self-Healing** - Automatic recovery after cooldown

---

## 🏗️ Architecture Design

### Model Selection Strategy

```
┌─────────────────────────────────────────────────┐
│           LLM Model Selection Flow              │
└─────────────────────────────────────────────────┘

1. Check USE_GEMINI environment variable
   │
   ├─ NO (default) ──────────────────────────────┐
   │                                              │
   └─ YES → Check Circuit Breaker                │
      │                                          │
      ├─ OPEN (tripped) ──────────────────────┐ │
      │                                        │ │
      └─ CLOSED → Try Gemini                  │ │
         │                                     │ │
         ├─ SUCCESS → Use Gemini              │ │
         │                                     │ │
         └─ FAILURE → Record failure ─────────┘ │
                                                 │
                                                 ▼
                                    ┌─────────────────────────┐
                                    │  Use OpenAI (Primary)   │
                                    │  OPENAI_MODEL env var   │
                                    │  Default: gpt-4o-mini   │
                                    └─────────────────────────┘
```

### Component Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Data Science Agent                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              LLM Model Selection Layer                   │ │
│  │                  (_get_llm_model)                        │ │
│  │                                                          │ │
│  │  ┌────────────────┐    ┌─────────────────────────────┐ │ │
│  │  │ Circuit Breaker│────│   OpenAI (Primary)          │ │ │
│  │  │  - 3 failures  │    │   - gpt-4o-mini (default)   │ │ │
│  │  │  - 5 min cool  │    │   - gpt-4o (quality)        │ │ │
│  │  │  - Auto-reset  │    │   - Consistent LiteLlm wrap│ │ │
│  │  └────────────────┘    └─────────────────────────────┘ │ │
│  │          │                        ▲                     │ │
│  │          ▼                        │                     │ │
│  │  ┌────────────────┐              │                     │ │
│  │  │ Gemini (Opt-in)│──── Failure ─┘                     │ │
│  │  │  - USE_GEMINI  │                                    │ │
│  │  │  - gemini-2.0  │                                    │ │
│  │  └────────────────┘                                    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           Rate Limit Protection Layer                    │ │
│  │             (Exponential Backoff)                        │ │
│  │                                                          │ │
│  │  Attempt 1 ──► Fail (429) ──► Wait 0.5s                │ │
│  │  Attempt 2 ──► Fail (429) ──► Wait 1.0s                │ │
│  │  Attempt 3 ──► Fail (429) ──► Wait 2.0s                │ │
│  │  Attempt 4 ──► Fail (429) ──► Wait 4.0s                │ │
│  │  Attempt 5 ──► Success ✅                               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                 44 Data Science Tools                    │ │
│  │   (AutoML, Sklearn, Visualization, SHAP, Export, etc.)  │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Details

### 1. Circuit Breaker Pattern

**Purpose**: Prevent cascading failures when Gemini is rate-limited

**Behavior**:
- Tracks consecutive Gemini failures
- Opens circuit after 3 failures
- Disables Gemini for 5 minutes (cooldown)
- Automatically resets after cooldown
- Falls back to OpenAI immediately

**Class**: `GeminiCircuitBreaker`

```python
class GeminiCircuitBreaker:
    def __init__(self, failure_threshold=3, cooldown_minutes=5):
        self.failure_threshold = 3      # Trip after 3 failures
        self.cooldown_minutes = 5       # 5-minute cooldown
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False            # Open = circuit tripped
    
    def record_failure(self):
        """Record failure and potentially trip circuit."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            # Disable Gemini for cooldown period
    
    def can_use_gemini(self) -> bool:
        """Check if Gemini can be used."""
        if not self.is_open:
            return True
        # Auto-reset after cooldown
        if time_since_failure > cooldown:
            self.is_open = False
            return True
        return False
```

**States**:
- **CLOSED** (normal) - Gemini available
- **OPEN** (tripped) - Gemini disabled, using OpenAI
- **HALF-OPEN** (recovering) - Testing if Gemini recovered

**Example Flow**:
```
T+0s:  Gemini call fails (rate limit)       Failure count: 1
T+1s:  Gemini call fails (rate limit)       Failure count: 2
T+2s:  Gemini call fails (rate limit)       Failure count: 3
       🔴 CIRCUIT BREAKER OPEN
       → Fallback to OpenAI for 5 minutes

T+2s-T+302s: All calls use OpenAI

T+302s: Circuit breaker auto-resets
        ✅ CIRCUIT BREAKER CLOSED
        → Gemini available again
```

### 2. Exponential Backoff

**Purpose**: Handle transient rate limits gracefully

**Decorator**: `@with_backoff`

```python
@with_backoff(max_retries=4, base_delay=0.5, factor=2.0)
def call_llm():
    return llm.generate(...)
```

**Parameters**:
- `max_retries`: 4 attempts
- `base_delay`: 0.5 seconds initial
- `factor`: 2.0 (exponential growth)

**Delay Progression**:
```
Attempt 1: Immediate (0s)
Attempt 2: 0.5s delay
Attempt 3: 1.0s delay
Attempt 4: 2.0s delay
Attempt 5: 4.0s delay
```

**Retriable Errors**:
- `"rate limit"`
- `"too many requests"`
- `"429"`
- `"temporarily unavailable"`
- `"overloaded"`
- `"resource_exhausted"`
- `"quota"`

**Example**:
```
12:00:00 - LLM call attempt 1
12:00:00 - ⚠️ Rate limit hit (429). Retrying in 0.5s...
12:00:00.5 - LLM call attempt 2
12:00:00.5 - ⚠️ Rate limit hit (429). Retrying in 1.0s...
12:00:01.5 - LLM call attempt 3
12:00:01.5 - ✅ Success!
```

### 3. OpenAI-First Model Selection

**Function**: `_get_llm_model()`

**Logic**:
1. **Check USE_GEMINI** environment variable
   - If `false` (default) → Return OpenAI immediately
   - If `true` → Continue to step 2

2. **Check Circuit Breaker**
   - If OPEN → Return OpenAI (Gemini disabled)
   - If CLOSED → Continue to step 3

3. **Try Gemini Initialization**
   - If SUCCESS → Return Gemini, reset failure count
   - If FAILURE → Record failure, return OpenAI

**Consistency**:
- Always returns `LiteLlm` instance (never raw model name)
- Ensures type consistency for agent framework
- Prevents runtime type mismatches

---

## ⚙️ Configuration

### Environment Variables

#### Required

```bash
# OpenAI API Key (required)
export OPENAI_API_KEY="sk-your-api-key-here"
```

#### Recommended Settings

```bash
# OpenAI Model (default: gpt-4o-mini)
export OPENAI_MODEL="gpt-4o-mini"      # Fast & cheap (recommended)
# OR
export OPENAI_MODEL="gpt-4o"           # Best quality
# OR
export OPENAI_MODEL="gpt-3.5-turbo"    # Fastest

# Disable Gemini (recommended for stability)
export USE_GEMINI="false"

# LiteLLM settings
export LITELLM_MAX_RETRIES="4"
export LITELLM_TIMEOUT_SECONDS="60"
export LITELLM_LOG="DEBUG"            # For detailed logging
```

#### Optional: Enable Gemini Fallback

```bash
# Only if you want Gemini as fallback (not recommended for production)
export USE_GEMINI="true"
export GENAI_MODEL="gemini-2.0-flash-exp"
```

### Model Comparison

| Model | Speed | Cost | Quality | Recommended |
|-------|-------|------|---------|-------------|
| **gpt-4o-mini** | ⚡⚡⚡ Fast | 💰 Cheap | ⭐⭐⭐ Good | ✅ **Yes** (default) |
| **gpt-4o** | ⚡⚡ Medium | 💰💰 Moderate | ⭐⭐⭐⭐⭐ Excellent | ✅ Yes (quality) |
| **gpt-3.5-turbo** | ⚡⚡⚡⚡ Very Fast | 💰 Very Cheap | ⭐⭐ Basic | ⚠️ Simple tasks only |
| **gemini-2.0-flash-exp** | ⚡⚡⚡ Fast | 💰 Free* | ⭐⭐⭐ Good | ❌ No (rate limits) |

*Gemini has strict rate limits that can cause failures.

---

## 🚀 Usage

### Default Usage (OpenAI Only - Recommended)

```bash
# Set API key
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-4o-mini"
export USE_GEMINI="false"

# Start server
uv run python main.py
```

**Expected Logs**:
```
🔵 OpenAI configured: gpt-4o-mini
✅ Using OpenAI (Gemini disabled)
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### With Gemini Fallback (Optional)

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-4o-mini"
export USE_GEMINI="true"
export GENAI_MODEL="gemini-2.0-flash-exp"

uv run python main.py
```

**Expected Logs**:
```
🔵 OpenAI configured: gpt-4o-mini
🟢 Gemini configured: gemini-2.0-flash-exp (circuit breaker: CLOSED)
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### Circuit Breaker in Action

```bash
# Gemini hits rate limit 3 times
12:00:00 - 🟢 Using Gemini
12:00:05 - ⚠️ Gemini rate limit hit (attempt 1/3)
12:00:10 - ⚠️ Gemini rate limit hit (attempt 2/3)
12:00:15 - ⚠️ Gemini rate limit hit (attempt 3/3)
12:00:15 - 🔴 Gemini circuit breaker OPEN: 3 failures. Disabling for 5 minutes.
12:00:15 - 🔵 Falling back to OpenAI: gpt-4o-mini

# All subsequent calls use OpenAI for 5 minutes
12:00:30 - ✅ Using OpenAI (Gemini circuit breaker OPEN)
12:01:00 - ✅ Using OpenAI (Gemini circuit breaker OPEN)
12:02:00 - ✅ Using OpenAI (Gemini circuit breaker OPEN)

# After 5 minutes, circuit breaker auto-resets
12:05:15 - ✅ Gemini circuit breaker CLOSED: Cooldown period elapsed.
12:05:20 - 🟢 Gemini available again
```

---

## 📊 Benefits

### 1. Reliability

**Before**:
```
Gemini rate limit → ❌ Agent fails → User error
```

**After**:
```
Gemini rate limit → ⚠️ Automatic fallback → ✅ OpenAI continues → User unaffected
```

### 2. Cost Optimization

- **gpt-4o-mini**: $0.15 per 1M input tokens, $0.60 per 1M output tokens
- **gpt-4o**: $2.50 per 1M input tokens, $10.00 per 1M output tokens
- **gemini-2.0-flash-exp**: Free (with strict rate limits)

**Recommendation**: Use `gpt-4o-mini` for best cost/performance ratio.

### 3. Performance

| Scenario | OpenAI-First | Gemini-First |
|----------|--------------|--------------|
| No rate limits | ✅ Fast | ✅ Fast |
| Gemini rate limited | ✅ Fast (fallback) | ❌ Slow (retries) |
| OpenAI rate limited | ✅ Handled (backoff) | ❌ Fails |
| Both rate limited | ✅ Retries with backoff | ❌ Complete failure |

### 4. Predictability

- Consistent response times (OpenAI SLA)
- No surprise rate limit errors
- Graceful degradation under load
- Automatic recovery

---

## 🔍 Monitoring & Debugging

### Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| `🔵 OpenAI configured: gpt-4o-mini` | OpenAI initialized | None (normal) |
| `✅ Using OpenAI (Gemini disabled)` | Using OpenAI only | None (normal) |
| `🟢 Gemini configured: ...` | Gemini available | None (normal) |
| `⚠️ Rate limit hit. Retrying in...` | Transient rate limit | None (auto-retry) |
| `🔴 Gemini circuit breaker OPEN` | Gemini disabled (3 failures) | Check Gemini quota |
| `⚠️ Gemini circuit breaker OPEN (rate limit protection)` | Using OpenAI fallback | None (auto-recovery) |
| `✅ Gemini circuit breaker CLOSED` | Gemini recovered | None (normal) |
| `❌ LLM call failed` | Non-retriable error | Check API keys |

### Health Check

```python
# Check circuit breaker status
from data_science.agent import _gemini_circuit_breaker

print(f"Circuit breaker status: {'OPEN' if _gemini_circuit_breaker.is_open else 'CLOSED'}")
print(f"Failure count: {_gemini_circuit_breaker.failure_count}")
print(f"Can use Gemini: {_gemini_circuit_breaker.can_use_gemini()}")
```

### Metrics to Track

1. **OpenAI Success Rate** - Should be >99%
2. **Gemini Success Rate** - May vary (rate limits)
3. **Circuit Breaker Trips** - Monitor frequency
4. **Average Response Time** - Track performance
5. **Retry Count** - Track rate limit occurrences

---

## 🏆 Best Practices

### Production Deployment

1. ✅ **Use OpenAI only** (`USE_GEMINI=false`)
2. ✅ **Set LITELLM_MAX_RETRIES=4** (exponential backoff)
3. ✅ **Use gpt-4o-mini** (cost-effective)
4. ✅ **Monitor API usage** (OpenAI dashboard)
5. ✅ **Set up alerts** (for rate limit errors)
6. ✅ **Review logs regularly** (check for issues)

### Development

1. ✅ **Test with OpenAI** (primary path)
2. ✅ **Test circuit breaker** (simulate failures)
3. ✅ **Monitor retry behavior** (check logs)
4. ⚠️ **Avoid Gemini** (unless absolutely needed)

### Cost Optimization

1. **Use gpt-4o-mini** for routine tasks (80% of cases)
2. **Use gpt-4o** only when quality matters
3. **Set shorter time_limits** for AutoGluon (reduce tokens)
4. **Enable caching** (LiteLLM feature)
5. **Monitor token usage** (OpenAI dashboard)

---

## 🐛 Troubleshooting

### Issue: "API Key Set: NO"

**Cause**: OpenAI API key not configured

**Solution**:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### Issue: Constant Rate Limits

**Cause**: High request volume or low quota

**Solution**:
1. Check OpenAI usage dashboard
2. Upgrade OpenAI tier
3. Increase LITELLM_MAX_RETRIES
4. Add delays between requests

### Issue: Circuit Breaker Stuck OPEN

**Cause**: Gemini repeatedly failing

**Solution**:
```bash
# Disable Gemini completely
export USE_GEMINI="false"

# Restart server
uv run python main.py
```

### Issue: Slow Responses

**Cause**: Multiple retries due to rate limits

**Solution**:
1. Switch to gpt-4o-mini (faster)
2. Reduce concurrent requests
3. Check network latency
4. Monitor OpenAI status page

---

## 📚 Related Documentation

- [README.md](README.md) - Project overview
- [INSTALLATION.md](INSTALLATION.md) - Setup guide
- [OPENAI_SETUP.md](OPENAI_SETUP.md) - OpenAI API configuration
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - Deployment guide
- [SECURITY.md](SECURITY.md) - Security best practices

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-15 | Initial OpenAI-first architecture |
| | | - Circuit breaker implementation |
| | | - Exponential backoff |
| | | - Consistent LiteLlm wrapping |
| | | - Auto-recovery mechanism |

---

## 📞 Support

For issues related to rate limiting or model selection:
1. Check logs for circuit breaker messages
2. Verify environment variables are set correctly
3. Test with OpenAI only first
4. Open GitHub issue with logs if problem persists

---

<div align="center">

**🚀 Resilient, Fast, Reliable - OpenAI-First Architecture 🚀**

[Back to README](README.md) | [Installation](INSTALLATION.md) | [Configuration](README.md#configuration)

</div>

---

Last updated: 2025-01-15  
Architecture version: 1.0

