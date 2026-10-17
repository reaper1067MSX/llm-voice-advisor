"""Benchmark comparison script for Google Gemini models in LLM Game Advisor."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load API keys
load_dotenv("keys.env")
load_dotenv(".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY no encontrada en el entorno.")
    exit(1)

from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)


def run_benchmark():
    print("================================================================================")
    print("🏁 BENCHMARK DE MODELOS GEMINI - LLM GAME ADVISOR")
    print("================================================================================")
    print(f"API Key detectada: {api_key[:8]}...{api_key[-4:]}")

    models_to_test = [
        {"id": "gemini-3.8-flash", "label": "Gemini 3.8 Flash (High Res)", "media_res": types.MediaResolution.MEDIA_RESOLUTION_HIGH},
        {"id": "gemini-3.8-flash", "label": "Gemini 3.8 Flash (Medium Res)", "media_res": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM},
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (High Res)", "media_res": types.MediaResolution.MEDIA_RESOLUTION_HIGH},
        {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (Medium Res)", "media_res": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM},
        {"id": "gemini-3.1-flash-lite-preview", "label": "Gemini 3.1 Flash Lite Preview", "media_res": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM},
    ]

    image_path = Path("captures/capture_1791949004.jpg")
    image_bytes = image_path.read_bytes() if image_path.is_file() else None
    if not image_bytes:
        print("Aviso: No se encontró imagen en captures/capture_1791949004.jpg")

    results = []

    for m in models_to_test:
        model_id = m["id"]
        label = m["label"]
        media_res = m["media_res"]
        print(f"\n--------------------------------------------------------------------------------")
        print(f"🚀 Evaluando: {label} [{model_id}]")
        print(f"--------------------------------------------------------------------------------")

        model_result = {"label": label, "model_id": model_id}

        # ----------------------------------------------------
        # TEST 1: Razonamiento Táctico Rápido (Texto puro)
        # ----------------------------------------------------
        sys_inst = "Eres un copiloto táctico. Responde en español, sin markdown, en máximo 2 oraciones."
        prompt_t1 = "Tengo un enfrentamiento a media distancia en Granja. ¿Me conviene cargar munición M80 o A1 en mi FAL? Dame tu veredicto."

        t0 = time.perf_counter()
        try:
            resp_t1 = client.models.generate_content(
                model=model_id,
                contents=prompt_t1,
                config=types.GenerateContentConfig(
                    system_instruction=sys_inst,
                    temperature=0.2,
                ),
            )
            lat_t1 = (time.perf_counter() - t0) * 1000
            usage_t1 = getattr(resp_t1, "usage_metadata", None)
            in_tok_t1 = getattr(usage_t1, "prompt_token_count", 0) or 0
            out_tok_t1 = getattr(usage_t1, "candidates_token_count", 0) or 0
            tps_t1 = (out_tok_t1 / (lat_t1 / 1000.0)) if lat_t1 > 0 else 0
            ans_t1 = resp_t1.text.strip().replace("\n", " ") if resp_t1.text else ""
            print(f"  [1. Texto Rápido] Latencia: {lat_t1:6.1f} ms | Tokens: in={in_tok_t1}, out={out_tok_t1} ({tps_t1:.1f} tok/s)")
            print(f"     Respuesta: \"{ans_t1[:110]}...\"")
            model_result["t1_lat"] = lat_t1
            model_result["t1_in"] = in_tok_t1
            model_result["t1_out"] = out_tok_t1
            model_result["t1_tps"] = tps_t1
            model_result["t1_ans"] = ans_t1
        except Exception as e:
            print(f"  [1. Texto Rápido] ❌ ERROR: {e}")
            model_result["t1_err"] = str(e)

        # ----------------------------------------------------
        # TEST 2: Visión Multimodal Táctica (Imagen + Texto)
        # ----------------------------------------------------
        if image_bytes:
            contents_t2 = [
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                "Observa mi pantalla. Identifica qué menú, interfaz o juego está activo y qué arma o equipamiento principal se ve.",
            ]
            t0 = time.perf_counter()
            try:
                resp_t2 = client.models.generate_content(
                    model=model_id,
                    contents=contents_t2,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_inst,
                        temperature=0.2,
                        media_resolution=media_res,
                    ),
                )
                lat_t2 = (time.perf_counter() - t0) * 1000
                usage_t2 = getattr(resp_t2, "usage_metadata", None)
                in_tok_t2 = getattr(usage_t2, "prompt_token_count", 0) or 0
                out_tok_t2 = getattr(usage_t2, "candidates_token_count", 0) or 0
                tps_t2 = (out_tok_t2 / (lat_t2 / 1000.0)) if lat_t2 > 0 else 0
                ans_t2 = resp_t2.text.strip().replace("\n", " ") if resp_t2.text else ""
                print(f"  [2. Visión Multimodal] Latencia: {lat_t2:6.1f} ms | Tokens: in={in_tok_t2}, out={out_tok_t2} ({tps_t2:.1f} tok/s)")
                print(f"     Respuesta: \"{ans_t2[:110]}...\"")
                model_result["t2_lat"] = lat_t2
                model_result["t2_in"] = in_tok_t2
                model_result["t2_out"] = out_tok_t2
                model_result["t2_tps"] = tps_t2
                model_result["t2_ans"] = ans_t2
            except Exception as e:
                print(f"  [2. Visión Multimodal] ❌ ERROR: {e}")
                model_result["t2_err"] = str(e)

        # ----------------------------------------------------
        # TEST 3: Tool Calling Estructurado (Reporte HTML)
        # ----------------------------------------------------
        def create_report_tool(title: str, html_body: str) -> str:
            """Genera un reporte HTML estilizado en pantalla."""
            return f"Reporte {title} creado."

        prompt_t3 = "Abre un reporte HTML comparando penetración y daño de M80 vs A1."
        t0 = time.perf_counter()
        try:
            afc = types.AutomaticFunctionCallingConfig(disable=True) if hasattr(types, "AutomaticFunctionCallingConfig") else None
            resp_t3 = client.models.generate_content(
                model=model_id,
                contents=prompt_t3,
                config=types.GenerateContentConfig(
                    system_instruction="Eres un copiloto táctico. Si te piden un reporte, invoca la herramienta create_report_tool.",
                    temperature=0.1,
                    tools=[create_report_tool],
                    automatic_function_calling=afc,
                ),
            )
            lat_t3 = (time.perf_counter() - t0) * 1000
            has_fc = bool(getattr(resp_t3, "function_calls", None))
            fc_names = [fc.name for fc in resp_t3.function_calls] if has_fc else []
            print(f"  [3. Tool Calling] Latencia: {lat_t3:6.1f} ms | Llamada a herramienta: {has_fc} ({fc_names})")
            model_result["t3_lat"] = lat_t3
            model_result["t3_tool_success"] = has_fc
            model_result["t3_tools"] = fc_names
        except Exception as e:
            print(f"  [3. Tool Calling] ❌ ERROR: {e}")
            model_result["t3_err"] = str(e)

        results.append(model_result)

    # Save benchmark JSON summary
    summary_path = Path("logs/benchmark_results.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📊 Resultados completos guardados en {summary_path}")


if __name__ == "__main__":
    run_benchmark()
