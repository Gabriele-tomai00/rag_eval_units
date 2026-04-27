# RAG Evaluation

Evaluate a RAG (Retrieval Augmented Generation) system with custom metrics

## Quick Start

### 1. Set Your API Key

Choose your LLM provider:

```bash
# OpenAI (default)
export OPENAI_API_KEY="your-openai-key"

# Or use Anthropic Claude
export ANTHROPIC_API_KEY="your-anthropic-key"

# Or use Google Gemini
export GOOGLE_API_KEY="your-google-key"
```

### 2. Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

Or using `pip`:

```bash
pip install -e .
```

### 3. Run the Evaluation

Using `uv`:

```bash
uv run python evals.py
```

Or using `pip`:

```bash
python evals.py
```

## Project Structure

```
rag_eval/
├── README.md           # This file
├── pyproject.toml      # Project configuration
├── rag.py              # Your RAG application code
├── evals.py            # Evaluation workflow
├── __init__.py         # Makes this a Python package
└── evals/              # Evaluation-related data
    ├── datasets/       # Test datasets
    ├── experiments/    # Experiment results
    └── logs/           # Evaluation logs and traces
```

## Customization

### Modify the LLM Provider

In `evals.py`, update the LLM configuration:

```python
from ragas.llms import llm_factory

# Use Anthropic Claude
llm = llm_factory("claude-3-5-sonnet-20241022", provider="anthropic")

# Use Google Gemini
llm = llm_factory("gemini-1.5-pro", provider="google")

# Use local Ollama
llm = llm_factory("mistral", provider="ollama", base_url="http://localhost:11434")
```
### Evals
```
python evals.py
```
or
```
uv run python evals.py
```
## Parameters
| Flag | Long form | Default | Description |
|------|-----------|---------|-------------|
| `-t` | `--type` | *(required)* | `1` sentence splitting, `2` markdown structure splitting, `3` hybrid markdown + sentence |
| `-n` | `--no_answare` | false | Use questions without expected answer |
| `-k` | `--top_k` | `5` | Number of top-k chunks retrieved |
| `-c` | `--chunk_size` | `512` | Chunk size of the index: `128`, `256`, `512`, `1024` (ignored for `-t 2`) |
| `-a` | `--all` | false | Enable all RAGAS metrics (slower) |
| `-o` | `--name_file_output` | *(auto)* | Output file name without extension |

## Examples
```
python evals.py -t 1 -k 4 -c 256
python evals.py -t 2 -k 10
python evals.py -t 3 -c 1024 -a
python evals.py -t 1 -n -k 5
```

### Customize Test Cases

Edit the `load_dataset()` function in `evals.py` to add or modify test cases.

### Change Evaluation Metrics

Update the `my_metric` definition in `evals.py` to use different grading criteria.

## Documentation

Visit https://docs.ragas.io for more information.
