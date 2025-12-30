# Lessons Learned

Notes from dogfooding sessions to avoid repeating mistakes.

---

## Session: 2024-12-31

### 1. Python Version Compatibility

**Problem:** Python 3.14 is too new and causes `pydantic-core` build failures.

**Solution:** Use Python 3.12 for the virtual environment:
```bash
python3.12 -m venv venv
```

**Lesson:** Always check Python version compatibility before creating venv. Stick to stable releases (3.11, 3.12) for projects with compiled dependencies.

---

### 2. gRPC DNS Resolution on macOS

**Problem:** Google Ads API calls fail with:
```
DNS resolution failed for googleads.googleapis.com: C-ares status is not ARES_SUCCESS
```

**Solution:** Set the `GRPC_DNS_RESOLVER` environment variable:
```bash
export GRPC_DNS_RESOLVER=native
```

**Lesson:** macOS has issues with gRPC's default c-ares DNS resolver. Always use native resolver for Google Ads API calls.

---

### 3. Typer CLI Version Compatibility

**Problem:** Typer 0.9.x has compatibility issues with newer Click versions, causing:
- `--help` crashes with `TypeError: Parameter.make_metavar() missing 1 required positional argument`
- Options not being recognized properly

**Solution:** Upgrade typer to 0.12+:
```bash
pip install "typer>=0.12"
```

**Lesson:** Pin typer to a version that's compatible with the Click version in use. Note: `instructor` package pins typer<0.10.0, which may cause conflicts.

---

### 4. Environment Setup Checklist

Before running the CLI, ensure:

1. **Virtual environment with correct Python:**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. **Dependencies installed:**
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Environment variables set:**
   ```bash
   export GRPC_DNS_RESOLVER=native
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

4. **Google Ads credentials:** Ensure `google-ads.yaml` exists with valid credentials.

---

### 5. Required Environment Variables

| Variable | Purpose | Required For |
|----------|---------|--------------|
| `GRPC_DNS_RESOLVER=native` | Fix macOS DNS issues | Google Ads API |
| `ANTHROPIC_API_KEY` | Claude API authentication | Persona/Ad generation |

---

### 6. Quick Start Script

Create a `run.sh` for easy startup:
```bash
#!/bin/bash
source venv/bin/activate
export GRPC_DNS_RESOLVER=native
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Warning: ANTHROPIC_API_KEY not set"
fi

python cli.py "$@"
```

---

### 7. Testing Commands (in order)

```bash
# 1. Test Google Ads connection
python cli.py test-connection

# 2. List available configs
python cli.py list-examples

# 3. Generate personas (requires ANTHROPIC_API_KEY)
python cli.py generate-personas -c examples/saas_config.json

# 4. Generate ad copy
python cli.py generate-ads -c examples/saas_config.json

# 5. Generate upsell script
python cli.py generate-upsell -c examples/saas_config.json

# 6. Full workflow
python cli.py run-workflow -c examples/saas_config.json
```

---

### 8. Use `uv` Instead of `pip`

**Problem:** `pip install` is slow, especially with many dependencies.

**Solution:** Use `uv` for faster package management:
```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv with specific Python
uv venv --python 3.12 venv

# Install dependencies (much faster)
source venv/bin/activate
uv pip install -r requirements.txt
```

**Benchmark:** `uv pip install` completed 85 packages in ~300ms vs several minutes with pip.

---

### 9. Instructor Package Version

**Problem:** `instructor==0.2.4` (old) doesn't have `from_anthropic()` method.

**Solution:** Upgrade to instructor 1.0+:
```bash
uv pip install "instructor>=1.0.0"
```

**Note:** Newer instructor also brings updated `openai` and `pydantic` versions.

---

### 10. Pydantic Schema Constraints

**Problem:** LLM outputs often exceed `max_length` constraints, causing validation failures.

**Examples encountered:**
- `purchase_driver: max_length=100` → LLM generates 120+ chars
- `transition: max_length=300` → LLM generates 350+ chars
- `headlines: max_length=30` per item → LLM generates 35+ char headlines

**Solution:** Either:
1. Increase constraints to be more lenient (e.g., 100 → 150)
2. Update prompts to explicitly emphasize character limits
3. Add retry logic with error context passed back to LLM

**Files affected:**
- `src/generators/persona_generator.py` - PersonaSchema
- `src/generators/upsell_generator.py` - UpsellScript
- `src/generators/ad_copy_generator.py` - AdCopySchema

---

### 11. Claude Model Availability

**Problem:** Some API keys only have access to certain models.

**Example:** `claude-3-5-sonnet-20240620` returns 404 but `claude-3-haiku-20240307` works.

**Solution:**
- Use `claude-3-haiku-20240307` for cost-effective generation
- Check API key permissions if model returns 404
- Consider using `claude-3-5-sonnet-latest` alias when Sonnet access is confirmed

---

### 12. Ad Copy Validation Rules

**Problem:** Google Ads has strict copy requirements:
- Headlines: max 30 characters
- Descriptions: max 90 characters
- Blocked words: "guarantee", "free", "100%", "risk-free"

**Solution:** Updated prompts in `prompts/setup/generate_polarity_ads.yaml` with:
1. **STRICT RULES** section with bold warnings about rejection
2. Examples showing character counts: `"Grow Your Business" (18)`
3. Explicit blocklist with variants: `"free"`, `"guarantee"`, `"risk-free"`
4. Clearer structure and shorter example descriptions

**Result:** Haiku now generates valid copy (may need 2-3 retries but succeeds)

---

## Future Notes

Add lessons from future sessions below...
