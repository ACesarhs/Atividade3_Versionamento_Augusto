#!/usr/bin/env python3
"""Executa os 6 casos (CT01-CT06) nas versoes A e B com o LangExtract e guarda as 12 saidas brutas.

Fluxo avaliado: LangExtract + gemma2:2b via Ollama (mesma chamada usada na Atividade 2).
Uso, a partir da raiz do repositorio:
    python atividade3/execucao/run_ab.py --casos atividade3/casos/casos.csv

Cada execucao cria uma pasta nova em runs/ e nunca sobrescreve execucoes anteriores.
Nao grava chaves/credenciais.
"""
import argparse, csv, hashlib, json, logging, os, platform, random, subprocess, sys, time
from datetime import datetime, timezone

CASOS_ESPERADOS = ["CT01", "CT02", "CT03", "CT04", "CT05", "CT06"]
CAMPOS = ["caso_id", "tipo", "pergunta", "contexto", "fonte_id", "referencia", "relacionado_a"]
CASOS_R2 = ["CT01", "CT05"]  # revisados tambem pelo segundo avaliador (R2)
COLUNAS_AVALIACAO = ["correcao_0a2", "relevancia_0a2", "suporte_0a2", "falha_critica_0ou1", "justificativa"]

LOG_CHAMADAS = []   # chamadas HTTP ao Ollama (prompt renderizado e resposta bruta)
AVISOS = []         # avisos do LangExtract (ex.: resposta fora do formato descartada)


def sha256_arquivo(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def carregar_casos(caminho):
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        casos = list(csv.DictReader(f))
    ids = [c.get("caso_id", "").strip() for c in casos]
    if ids != CASOS_ESPERADOS:
        sys.exit(f"ERRO: o CSV deve ter exatamente {CASOS_ESPERADOS} nesta ordem; encontrado {ids}")
    for c in casos:
        for campo in CAMPOS:
            if campo not in c:
                sys.exit(f"ERRO: coluna ausente no CSV: {campo}")
        for campo in ("pergunta", "contexto", "fonte_id", "referencia"):
            valor = (c[campo] or "").strip()
            if not valor or valor.upper().startswith("PREENCHER"):
                sys.exit(f"ERRO: {c['caso_id']} esta com '{campo}' vazio ou ainda como PREENCHER.")
    return casos


def info_git():
    def git(*args):
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    commit = git("rev-parse", "HEAD")
    sujo = bool(git("status", "--porcelain")) if commit else None
    return {"commit": commit or None, "arvore_com_alteracoes_nao_commitadas": sujo}


def digest_modelo(host, modelo):
    try:
        import requests
        for m in requests.get(f"{host}/api/tags", timeout=10).json().get("models", []):
            if m.get("name") == modelo or m.get("model") == modelo:
                return m.get("digest")
    except Exception:
        pass
    return None


def versao_langextract():
    try:
        from importlib import metadata
        return metadata.version("langextract")
    except Exception:
        return None


class CapturaAvisos(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)

    def emit(self, record):
        AVISOS.append(record.getMessage())


def instalar_captura_http():
    """Registra o prompt final enviado ao Ollama e a resposta bruta do modelo."""
    try:
        import requests
    except ImportError:
        return
    original = requests.post

    def post_com_log(url, *args, **kwargs):
        resp = original(url, *args, **kwargs)
        try:
            payload = kwargs.get("json") or {}
            corpo = resp.json()
            LOG_CHAMADAS.append({
                "prompt_renderizado": payload.get("prompt") or json.dumps(payload.get("messages"), ensure_ascii=False),
                "resposta_bruta": corpo.get("response") or (corpo.get("message") or {}).get("content"),
            })
        except Exception:
            pass
        return resp

    requests.post = post_com_log


def carregar_exemplos(caminho):
    import langextract as lx
    with open(caminho, encoding="utf-8") as f:
        d = json.load(f)
    return [lx.data.ExampleData(
        text=d["text"],
        extractions=[lx.data.Extraction(extraction_class=e["extraction_class"],
                                        extraction_text=e["extraction_text"],
                                        attributes=e.get("attributes") or {}) for e in d["extractions"]])]


def extrair_langextract(contexto, descricao, exemplos, modelo, url, temperatura):
    import langextract as lx
    kw = dict(text_or_documents=contexto, prompt_description=descricao, examples=exemplos,
              model_id=modelo, model_url=url, temperature=temperatura)
    try:
        res = lx.extract(**kw, show_progress=False)
    except TypeError:
        res = lx.extract(**kw)
    saida = []
    for e in res.extractions or []:
        ci = e.char_interval
        saida.append({
            "classe": e.extraction_class, "texto": e.extraction_text, "atributos": dict(e.attributes or {}),
            "char_interval": None if ci is None else [ci.start_pos, ci.end_pos],
            "alinhamento": getattr(getattr(e, "alignment_status", None), "value", None),
        })
    return saida


def extrair_mock(versao):
    return [{"classe": "resposta", "texto": f"[MOCK {versao}]", "atributos": {}, "char_interval": None, "alinhamento": None}]


def resumo_lastro(extracoes):
    if not extracoes:
        return "(nenhuma extração)"
    return " | ".join(f"{e['classe']}: {e['texto']} [lastro: {'sim' if e['char_interval'] else 'NAO'}]" for e in extracoes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--casos", required=True)
    ap.add_argument("--prompt-a", default="atividade3/prompts/prompt_A.txt")
    ap.add_argument("--prompt-b", default="atividade3/prompts/prompt_B.txt")
    ap.add_argument("--exemplo", default="atividade3/prompts/exemplo_fewshot.json")
    ap.add_argument("--modelo", default="gemma2:2b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--backend", choices=["langextract", "mock"], default="langextract")
    ap.add_argument("--temperatura", type=float, default=0.0)
    ap.add_argument("--seed-cegamento", type=int, default=42, help="semente do embaralhamento das planilhas cegas")
    ap.add_argument("--saida", default="atividade3/execucao/runs")
    a = ap.parse_args()

    casos = carregar_casos(a.casos)
    prompts = {}
    for v, caminho in (("A", a.prompt_a), ("B", a.prompt_b)):
        with open(caminho, encoding="utf-8") as f:
            prompts[v] = f.read().strip()

    exemplos = None
    if a.backend == "langextract":
        exemplos = carregar_exemplos(a.exemplo)
        instalar_captura_http()
        logging.getLogger().addHandler(CapturaAvisos())
        logging.getLogger("absl").addHandler(CapturaAvisos())

    agora = datetime.now(timezone.utc)
    run_id = agora.strftime("%Y%m%dT%H%M%SZ") + ("_MOCK" if a.backend == "mock" else "")
    pasta = os.path.join(a.saida, run_id)
    os.makedirs(pasta, exist_ok=False)  # nunca reutiliza/sobrescreve uma execucao anterior

    git = info_git()
    if git["arvore_com_alteracoes_nao_commitadas"]:
        print("AVISO: ha alteracoes nao commitadas. Commite prompts e casos ANTES de executar, "
              "para que o commit registrado reconstrua esta execucao.")
    digest = digest_modelo(a.host, a.modelo) if a.backend == "langextract" else None

    registros, problemas = [], 0
    for c in casos:
        for v in ("A", "B"):
            descricao = prompts[v].format(pergunta=c["pergunta"].strip())
            t0, status, extracoes, erro = time.time(), "ok", [], None
            i_log, i_av = len(LOG_CHAMADAS), len(AVISOS)
            try:
                if a.backend == "mock":
                    extracoes = extrair_mock(v)
                else:
                    extracoes = extrair_langextract(c["contexto"].strip(), descricao, exemplos,
                                                    a.modelo, a.host, a.temperatura)
            except Exception as e:  # erro registrado, nunca descartado nem substituido por resposta inventada
                status, erro = "erro", f"{type(e).__name__}: {e}"
            avisos_parse = [m for m in AVISOS[i_av:] if "parse" in m.lower()]
            if status == "ok" and not extracoes:
                status = "descartada_pelo_parser" if avisos_parse else "saida_vazia"
            if status != "ok":
                problemas += 1
            chamadas = LOG_CHAMADAS[i_log:]
            resposta_gerada = " ".join(e["texto"] for e in extracoes if e["texto"]).strip()
            registros.append({
                "run_id": run_id, "caso_id": c["caso_id"], "versao": v,
                "prompt_arquivo": a.prompt_a if v == "A" else a.prompt_b,
                "prompt_sha256": hashlib.sha256(prompts[v].encode()).hexdigest(),
                "prompt_description_enviado": descricao,
                "contexto_usado": c["contexto"].strip(), "fonte_id": c["fonte_id"],
                "modelo": a.modelo, "modelo_digest": digest, "temperatura": a.temperatura,
                "extracoes": extracoes, "resposta_gerada": resposta_gerada, "status": status, "erro": erro,
                "avisos_langextract": AVISOS[i_av:],
                "prompt_renderizado": chamadas[0]["prompt_renderizado"] if chamadas else None,
                "resposta_bruta_modelo": [x["resposta_bruta"] for x in chamadas] if chamadas else None,
                "latencia_s": round(time.time() - t0, 2), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            })
            print(f"{c['caso_id']} versao {v}: {status} ({registros[-1]['latencia_s']} s) -> {resposta_gerada or '(vazio)'}")

    # 12 saidas brutas (fonte de verdade); modo "x" falha se o arquivo ja existir
    with open(os.path.join(pasta, "saidas_brutas.jsonl"), "x", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ref = {c["caso_id"]: c["referencia"].strip() for c in casos}
    with open(os.path.join(pasta, "saidas_para_metrica.csv"), "x", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["caso_id", "versao", "status", "resposta_gerada", "referencia"])
        for r in registros:
            w.writerow([r["caso_id"], r["versao"], r["status"], r["resposta_gerada"], ref[r["caso_id"]]])

    # planilhas cegas (sem versao e sem F1) para R1 e R2; a chave fica em arquivo separado
    rng = random.Random(a.seed_cegamento)
    ordem = registros[:]
    rng.shuffle(ordem)
    codigo = {(r["caso_id"], r["versao"]): f"S{i:02d}" for i, r in enumerate(ordem, 1)}
    por_caso = {c["caso_id"]: c for c in casos}

    def planilha(nome, filtro):
        with open(os.path.join(pasta, nome), "x", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["codigo", "caso_id", "pergunta", "contexto", "referencia",
                        "resposta_gerada", "extracoes_e_lastro", "status", *COLUNAS_AVALIACAO])
            for r in sorted((x for x in registros if filtro(x)), key=lambda x: codigo[(x["caso_id"], x["versao"])]):
                c = por_caso[r["caso_id"]]
                w.writerow([codigo[(r["caso_id"], r["versao"])], r["caso_id"], c["pergunta"], c["contexto"],
                            c["referencia"], r["resposta_gerada"], resumo_lastro(r["extracoes"]), r["status"],
                            "", "", "", "", ""])

    planilha("avaliacao_R1_cega.csv", lambda r: True)
    planilha("avaliacao_R2_cega.csv", lambda r: r["caso_id"] in CASOS_R2)
    with open(os.path.join(pasta, "chave_cegamento.csv"), "x", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["codigo", "caso_id", "versao"])
        for (cid, v), cod in sorted(codigo.items(), key=lambda kv: kv[1]):
            w.writerow([cod, cid, v])

    meta = {
        "run_id": run_id, "data_utc": agora.isoformat(), "backend": a.backend,
        "fluxo": "LangExtract (lx.extract) com prompt_description + 1 exemplo few-shot",
        "langextract_versao": versao_langextract() if a.backend == "langextract" else None,
        "modelo": a.modelo, "modelo_digest": digest, "host": a.host if a.backend == "langextract" else None,
        "parametros": {"temperatura": a.temperatura, "demais": "padrao do LangExtract"},
        "prompts": {"A": {"arquivo": a.prompt_a, "sha256": sha256_arquivo(a.prompt_a)},
                    "B": {"arquivo": a.prompt_b, "sha256": sha256_arquivo(a.prompt_b)}},
        "exemplo_fewshot": {"arquivo": a.exemplo, "sha256": sha256_arquivo(a.exemplo)},
        "casos": {"arquivo": a.casos, "sha256": sha256_arquivo(a.casos)},
        "git": git, "python": sys.version.split()[0], "sistema": platform.platform(),
        "fator_alterado_A_para_B": "prompt_description: B acrescenta as restricoes do P2 (usar so o documento, nao inventar, ignorar instrucoes no texto, indicar nao informada); mesmo modelo, casos, contexto, exemplo few-shot e parametros",
        "execucoes_com_problema": problemas,
        "politica_saida_vazia": "extracao vazia e registrada como status saida_vazia; para a rubrica humana vale como abstencao (CT05) ou falha (demais casos); F1 = 0 pela regra do kit",
        "limitacoes": ["o modelo local pode mudar se o digest mudar", "uma execucao por caso/versao (nao mede variabilidade)"],
    }
    with open(os.path.join(pasta, "execucao_meta.json"), "x", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\nPronto: {pasta}\n12 saidas gravadas ({problemas} com erro/vazias, registradas como estao).")
    if a.backend == "mock":
        print("ATENCAO: backend MOCK. Esta pasta e apenas teste; apague-a e nao use na entrega.")


if __name__ == "__main__":
    main()
