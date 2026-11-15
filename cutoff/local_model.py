"""Run an open-weight model locally (Apple Silicon / MPS), optionally with a LoRA adapter from Adaption."""
import json
import re
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load(base: str, adapter: str | None = None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(base)
    if adapter:
        # Adaption trains Qwen 3.5 through its multimodal class, so the LoRA weights are named
        # model.language_model.layers.*. Loading the text-only class leaves every adapter weight unmatched
        # (PEFT only warns), which silently gives you the base model.
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText
        model = AutoModelForImageTextToText.from_pretrained(base, dtype=torch.float16, device_map="mps")
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = PeftModel.from_pretrained(model, adapter)
        if any("missing adapter keys" in str(w.message) for w in caught):
            raise RuntimeError("adapter weights did not match the base model; refusing to run as the plain base")
    else:
        model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.float16, device_map="mps")
    model.eval()
    return tok, model


def generate(prompt: str, base: str, adapter: str | None = None, max_new_tokens: int = 1500) -> str:
    import torch

    tok, model = load(base, adapter)
    msgs = [{"role": "user", "content": prompt}]
    try:
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False)
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)


def parse_rules(text: str) -> list[dict] | None:
    """Pull {"rules": [...]} out of a model answer; None when it is not valid."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        rules = json.loads(m.group(0))["rules"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    need = {"kind", "symbol", "note", "source_quote"}
    return [r for r in rules if isinstance(r, dict) and need <= r.keys()] if isinstance(rules, list) else None
