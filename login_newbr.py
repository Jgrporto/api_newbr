import os
import requests
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÕES
# ============================================================
BASE_URL = "https://painel.newbr.top"
LOGIN_URL = f"{BASE_URL}/api/auth/login"

USERNAME = "login_suporte"
PASSWORD = "Senha+TV26"

# Proxy opcional. Preencha PROXY_URL no .env, no formato:
#   http://usuario:senha@host:porta
# (para HTTPS via proxy HTTP, mantenha o esquema "http://" na URL mesmo
# fazendo requisicoes para um site HTTPS - o requests cuida do CONNECT).
PROXY_URL = os.getenv("PROXY_URL")
PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

# Headers baseados no que você capturou
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://painel.newbr.top",
    "Referer": "https://painel.newbr.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 OPR/135.0.0.0",
    "x-app-version": "3.91",
    "locale": "pt",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Opera GX";v="135", "Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

# Payload exatamente como no DevTools
PAYLOAD = {
    "captcha": "not-a-robot",
    "captchaChecked": True,
    "username": USERNAME,
    "password": PASSWORD,
    "twofactor_code": "",
    "twofactor_recovery_code": "",
    "twofactor_trusted_device_id": ""
}


def login() -> Optional[str]:
    session = requests.Session()
    session.headers.update(HEADERS)

    # Se você tiver o cookie cf_clearance válido, descomente e cole:
    # session.cookies.set("cf_clearance", "SEU_CF_CLEARANCE_AQUI", domain="painel.newbr.top")

    print("[*] Fazendo login...")
    if PROXIES:
        print(f"[*] Usando proxy: {PROXY_URL}")
    try:
        response = session.post(
            LOGIN_URL,
            json=PAYLOAD,
            timeout=30,
            proxies=PROXIES,
        )
    except requests.exceptions.RequestException as e:
        print(f"[!] Erro de conexão: {e}")
        return None

    print(f"[*] Status Code: {response.status_code}")

    if response.status_code == 403:
        print("[!] Bloqueado pelo Cloudflare (403).")
        print("    → Solução: use o cookie cf_clearance atualizado ou use Playwright/Selenium.")
        return None

    if response.status_code != 200:
        print(f"[!] Erro no login: {response.status_code}")
        print(response.text[:500])
        return None

    try:
        data = response.json()
    except json.JSONDecodeError:
        print("[!] Resposta não é JSON válido:")
        print(response.text[:500])
        return None

    # Tenta encontrar o token em vários formatos comuns
    token = None
    possible_keys = [
        "token",
        "access_token",
        "bearer_token",
        "auth_token",
        "data.token",
        "data.access_token",
        "user.token",
    ]

    # Busca direta
    for key in possible_keys:
        if "." in key:
            parts = key.split(".")
            temp = data
            try:
                for part in parts:
                    temp = temp[part]
                token = temp
                break
            except (KeyError, TypeError):
                continue
        else:
            if key in data:
                token = data[key]
                break

    # Fallback: procura qualquer string que pareça token Sanctum (número|hash)
    if not token:
        def find_token(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    result = find_token(v)
                    if result:
                        return result
            elif isinstance(obj, str) and "|" in obj and len(obj) > 30:
                return obj
            return None
        token = find_token(data)

    if token:
        print("\n[✓] Login realizado com sucesso!")
        print(f"[✓] Token capturado:\n{token}\n")
        return token
    else:
        print("[!] Token não encontrado na resposta. Resposta completa:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return None


def test_token(token: str):
    """Testa se o token funciona chamando /api/auth/me"""
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"

    print("[*] Testando token em /api/auth/me ...")
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=20, proxies=PROXIES)

    if r.status_code == 200:
        print("[✓] Token válido!")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:800])
    else:
        print(f"[!] Token inválido ou expirado (status {r.status_code})")
        print(r.text[:300])


if __name__ == "__main__":
    token = login()

    if token:
        # Salva o token em arquivo
        with open("token.txt", "w") as f:
            f.write(token)
        print("[*] Token salvo em token.txt")

        # Testa o token
        test_token(token)