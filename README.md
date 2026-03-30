# Rag evaluation with RAGAS
1. Create a file `litellm_config.yaml`:
```
model_list:
  - model_name: ggml-org/gpt-oss-120b-GGUF
    litellm_params:
      model: model_name
      api_base: ip
      api_key: key
```

2. Start the server:
```
litellm --config litellm_config.yaml --port 4000
```
3. Start the program:
```
uv run python evals.py
```