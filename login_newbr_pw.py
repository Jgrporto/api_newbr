from playwright.sync_api import sync_playwright
import json
import time

BASE_URL = "https://painel.newbr.top"
USERNAME = "login_suporte"
PASSWORD = "Senha+TV26"

def login_and_get_token():
    with sync_playwright() as p:
        # headless=False se quiser ver o navegador abrindo
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="pt-BR",
        )
        
        page = context.new_page()

        # Captura o token da resposta do /api/auth/login
        token = None

        def handle_response(response):
            nonlocal token
            if "/api/auth/login" in response.url and response.status == 200:
                try:
                    data = response.json()
                    # Tenta vários formatos comuns
                    token = (
                        data.get("token")
                        or data.get("access_token")
                        or data.get("data", {}).get("token")
                        or data.get("data", {}).get("access_token")
                    )
                    if not token:
                        # Fallback: procura qualquer string no formato Sanctum (123|hash)
                        def find_token(obj):
                            if isinstance(obj, dict):
                                for v in obj.values():
                                    r = find_token(v)
                                    if r:
                                        return r
                            elif isinstance(obj, str) and "|" in obj and len(obj) > 40:
                                return obj
                            return None
                        token = find_token(data)
                    
                    if token:
                        print(f"\n[✓] Token capturado da resposta de login!")
                except Exception as e:
                    print(f"[!] Erro ao ler JSON do login: {e}")

        page.on("response", handle_response)

        print("[*] Acessando a página de login...")
        page.goto(f"{BASE_URL}/#/sign-in", wait_until="networkidle", timeout=60000)

        # Aguarda o formulário carregar
        page.wait_for_selector('input[type="text"], input[name="username"], input[placeholder*="usuário" i], input[placeholder*="login" i]', timeout=20000)

        print("[*] Preenchendo credenciais...")

        # Tenta localizar os campos de várias formas (o painel usa Vue)
        username_input = page.locator('input[type="text"]').first
        password_input = page.locator('input[type="password"]').first

        username_input.fill(USERNAME)
        password_input.fill(PASSWORD)

        # Clica no botão de login (várias possibilidades de seletor)
        login_button = page.locator('button:has-text("Entrar"), button:has-text("Login"), button[type="submit"]').first
        login_button.click()

        print("[*] Aguardando resposta do login...")
        
        # Espera um pouco + verifica se o token chegou
        for _ in range(15):
            if token:
                break
            time.sleep(1)

        # Fallback: tenta pegar do localStorage / sessionStorage
        if not token:
            print("[*] Tentando capturar token do storage...")
            storage = page.evaluate("""() => {
                const data = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    data[key] = localStorage.getItem(key);
                }
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    data[key] = sessionStorage.getItem(key);
                }
                return data;
            }""")
            
            for key, value in storage.items():
                if value and ("token" in key.lower() or "|" in str(value)):
                    if "|" in str(value) and len(str(value)) > 40:
                        token = value
                        print(f"[✓] Token encontrado no storage (chave: {key})")
                        break

        browser.close()

        if token:
            print("\n" + "="*60)
            print("TOKEN CAPTURADO COM SUCESSO:")
            print(token)
            print("="*60)
            
            # Salva em arquivo
            with open("token.txt", "w") as f:
                f.write(token)
            print("\n[*] Token salvo em token.txt")
            return token
        else:
            print("\n[!] Não foi possível capturar o token.")
            print("    Possíveis causas:")
            print("    - Credenciais incorretas")
            print("    - Captcha/2FA ativo")
            print("    - Página mudou a estrutura")
            return None


if __name__ == "__main__":
    login_and_get_token()