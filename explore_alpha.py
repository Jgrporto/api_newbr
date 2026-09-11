#!/usr/bin/env python3
"""Loga no alpha-server-oficial.sigma.st e consulta todos os endpoints
de leitura (GET) disponíveis após o login, salvando cada resposta em JSON
e imprimindo tudo no terminal.

Uso:
    python explore_alpha.py

Credenciais via .env (ALPHA_USERNAME / ALPHA_PASSWORD) ou usa o fallback
abaixo. Proxy opcional via .env (PROXY_URL), mesmo padrão do login_newbr.py.
Saída fica em output/alpha/<endpoint>.json
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

BASE_URL = "https://alpha-server-oficial.sigma.st"
LOGIN_URL = f"{BASE_URL}/api/auth/login"

USERNAME = os.getenv("ALPHA_USERNAME", "Danilo123")
PASSWORD = os.getenv("ALPHA_PASSWORD", "URxdZlwjAQ3572!")

# Proxy opcional (mesmo formato usado em login_newbr.py). Deixe vazio no
# .env para nao usar.
PROXY_URL = os.getenv("PROXY_URL")
PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

OUTPUT_DIR = Path(__file__).parent / "output" / "alpha"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 OPR/135.0.0.0",
    "x-app-version": "3.91",
    "locale": "pt",
}

LOGIN_PAYLOAD = {
    "captcha": "not-a-robot",
    "captchaChecked": True,
    "username": USERNAME,
    "password": PASSWORD,
    "twofactor_code": "",
    "twofactor_recovery_code": "",
    "twofactor_trusted_device_id": "",
}

# Endpoints GET observados navegando pelo painel (dashboard, clientes,
# revendas, financeiro, integrações, sessões, auditoria).
ENDPOINTS = {
    "auth_me": "/api/auth/me",
    "settings_public": "/api/settings/public",
    "servers": "/api/servers",
    "dashboard_preferences": "/api/dashboard/preferences",
    "notices_list": "/api/notices/list",
    "resellers_customers_count": "/api/resellers/customers-count",
    "resellers_list": "/api/resellers/list",
    "customers_expiring": "/api/customers/expiring",
    "customers_list": "/api/customers?page=1&perPage=20",
    "customers_statistics": "/api/customers/statistics",
    "customers_statistics_top10": "/api/customers/statistics/top10",
    "customers_recovery_lapsed": "/api/customers/recovery/lapsed?cohort=3",
    "customers_recovery_dispatch_history": "/api/customers/recovery/dispatch-history",
    "dashboard_chart_new_customers": "/api/dashboard/charts/new-customers?period=last-30-days",
    "dashboard_chart_revenue_forecast": "/api/dashboard/charts/revenue-forecast",
    "dashboard_chart_lost_revenue": "/api/dashboard/charts/lost-revenue",
    "dashboard_chart_customer_retention": "/api/dashboard/charts/customer-retention",
    "dashboard_metrics_recovery": "/api/dashboard/metrics/recovery",
    "dashboard_ai_analysis": "/api/dashboard/ai-analysis",
    "integrations": "/api/integrations",
    "auth_active_sessions": "/api/auth/active-sessions",
    "audit_my_sign_in_logs": "/api/audit/my-sign-in-logs",
    "credit_packages": "/api/creditpackages/list",
    "credit_bonus_campaigns": "/api/creditbonuscampaigns/list",
}


def login() -> str:
    session = requests.Session()
    session.headers.update(HEADERS)
    print("[*] Fazendo login...")
    if PROXIES:
        print(f"[*] Usando proxy: {PROXY_URL}")
    resp = session.post(LOGIN_URL, json=LOGIN_PAYLOAD, timeout=30, proxies=PROXIES)
    resp.raise_for_status()
    data = resp.json()

    token = None
    for key in ("token", "access_token", "bearer_token", "auth_token"):
        if key in data:
            token = data[key]
            break
    if not token:
        def find_token(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    r = find_token(v)
                    if r:
                        return r
            elif isinstance(obj, str) and "|" in obj and len(obj) > 30:
                return obj
            return None
        token = find_token(data)

    if not token:
        raise RuntimeError(f"Não consegui extrair o token da resposta de login: {data}")

    print(f"[OK] Login feito, token: {token[:20]}...")
    return token


def explore(token: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {token}"

    summary = []
    for name, path in ENDPOINTS.items():
        url = f"{BASE_URL}{path}"
        try:
            resp = requests.get(url, headers=headers, timeout=30, proxies=PROXIES)
        except requests.RequestException as e:
            print(f"[!] {name}: erro de conexão ({e})")
            summary.append({"endpoint": name, "path": path, "status": "conn_error"})
            continue

        status = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = resp.text

        out_file = OUTPUT_DIR / f"{name}.json"
        out_file.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")

        ok = "OK" if status == 200 else "FALHOU"
        print(f"\n{'=' * 90}")
        print(f"[{ok}] {name}  ({path})  -> {status}")
        print("=" * 90)
        print(json.dumps(body, indent=2, ensure_ascii=False))

        summary.append({"endpoint": name, "path": path, "status": status})

    summary_file = OUTPUT_DIR / "_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[*] {len(ENDPOINTS)} endpoints consultados.")
    print(f"[*] Resultados salvos em: {OUTPUT_DIR}")


if __name__ == "__main__":
    tok = login()
    explore(tok)
