"""Transporte Responses + Pydantic, sem importação do motor/catálogo antigo."""
import json
import os
import time
import tomllib
from openai import OpenAI
from .norma import ROOT


def configuration():
    secrets = ROOT / ".streamlit" / "secrets.toml"
    config = {}
    if secrets.exists():
        try:
            config = tomllib.loads(secrets.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError):
            pass
    return os.environ.get("OPENAI_API_KEY") or config.get("OPENAI_API_KEY", ""), os.environ.get("OPENAI_MODEL") or config.get("OPENAI_MODEL", "gpt-5.6")


class TechnicalError(RuntimeError):
    pass


def safe_error(exc):
    # Não serializa mensagens/headers/corpos que possam conter chave ou instrumento.
    status = getattr(exc, "status_code", None)
    return type(exc).__name__ + (f" (HTTP {status})" if isinstance(status, int) else "")


def smoke_test(key, model):
    if not key:
        return {"sucesso": False, "modelo": model, "latencia_s": None, "erro_tecnico": "Sem configuração OPENAI_API_KEY; chamada não realizada."}
    start = time.monotonic()
    try:
        with OpenAI(api_key=key, timeout=30, max_retries=0) as client:
            response = client.responses.create(model=model, input="Teste técnico sintético: responde apenas OK.", max_output_tokens=32, store=False)
        success = bool(response.output_text) and response.status == "completed"
        return {"sucesso": success, "modelo": model, "latencia_s": round(time.monotonic()-start, 2), "erro_tecnico": "" if success else "Resposta incompleta ou sem texto."}
    except Exception as exc:
        return {"sucesso": False, "modelo": model, "latencia_s": round(time.monotonic()-start, 2), "erro_tecnico": safe_error(exc)}


def structured(key, model, instructions, payload, schema):
    if not key:
        raise TechnicalError("Sem OPENAI_API_KEY. Análise assistida não executada.")
    try:
        with OpenAI(api_key=key, timeout=120, max_retries=0) as client:
            response = client.responses.parse(model=model, store=False,
                input=[{"role": "developer", "content": instructions},
                       {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                text_format=schema)
        if response.output_parsed is None or response.status != "completed":
            raise TechnicalError("Resposta recusada, incompleta ou não estruturada.")
        return response.output_parsed
    except TechnicalError:
        raise
    except Exception as exc:
        raise TechnicalError(safe_error(exc)) from None


if __name__ == "__main__":
    result = smoke_test(*configuration())
    target = ROOT / "evidencias_prototipo" / "api_inicial.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
