# OpenAI Configuration Setup

The agent now uses **OpenAI by default** instead of Gemini to avoid rate limit issues.

## How It Works

Based on Google ADK's official documentation, the agent uses `LiteLlm` from `google.adk.models.lite_llm` which provides a unified interface to 100+ LLMs including OpenAI.

**Key Points:**
- LiteLlm **automatically reads** `OPENAI_API_KEY` from environment variables
- Model format: `"gpt-4o-mini"` or `"openai/gpt-4o"` (both work)
- No additional configuration needed beyond the API key

## Setup Steps

### 1. Create `.env` file

Create a `.env` file in the project root with:

```bash
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=your-openai-api-key-here

# Optional: Choose specific OpenAI model (default: gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini
# Or use: gpt-4o, gpt-3.5-turbo

# Web Interface
SERVE_WEB_INTERFACE=true
```

### 2. Get your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key and paste it in your `.env` file

### 3. Install Dependencies

```bash
uv sync
```

### 4. Start the Server

```bash
$env:SERVE_WEB_INTERFACE='true'; uv run python main.py
```

## Model Options

| Model | Description | Cost | Best For |
|-------|-------------|------|----------|
| **gpt-4o** (default) | Latest, most capable | $$$ | Complex tasks, best quality |
| **gpt-4o-mini** | Fast, affordable | $ | Most tasks, good balance |
| **gpt-3.5-turbo** | Fastest, cheapest | ¢ | Simple tasks, high volume |

## Switch Back to Gemini

If you want to use Gemini instead, set in `.env`:

```bash
USE_GEMINI=true
GENAI_MODEL=gemini-2.0-flash-exp
GOOGLE_API_KEY=your-google-api-key
```

## Troubleshooting

### "No API key provided"

Make sure `OPENAI_API_KEY` is set in your `.env` file.

### "Insufficient quota"

You need to add credit to your OpenAI account at https://platform.openai.com/account/billing

### Rate limits

OpenAI has generous rate limits:
- **Free tier**: 200 requests/day
- **Paid tier**: 10,000+ requests/day

Much better than Gemini's 250K tokens/minute limit!

