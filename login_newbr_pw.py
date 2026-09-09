from playwright.sync_api import sync_playwright
import json
import time

BASE_URL = "https://painel.newbr.top"
USERNAME = "login_suporte"
PASSWORD = "Senha+TV26"

def login_and_get_token():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        
        # Remove sinais de automação
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = context.new_page()

        token = None

        def handle_response(response):
            nonlocal token
            if "/api/auth/login" in response.url and response.status == 200:
                try:
                    data = response.json()
                    print(f"\n[DEBUG] Resposta do login recebida:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
                    
                    # Tenta vários caminhos possíveis
                    token = (
                        data.get("token")
                        or data.get("access_token")
                        or data.get("bearer_token")
                        or data.get("data", {}).get("token")
                        or data.get("data", {}).get("access_token")
                        or data.get("user", {}).get("token")
                    )
                    
                    if not token:
                        # Procura qualquer string no formato Sanctum (id|hash)
                        def find_token(obj):
                            if isinstance(obj, dict):
                                for v in obj.values():
                                    r = find_token(v)
                                    if r: return r
                            elif isinstance(obj, str) and "|" in obj and len(obj) > 40:
                                return obj
                            return None
                        token = find_token(data)
                        
                except Exception as e:
                    print(f"[!] Erro ao processar resposta: {e}")

        page.on("response", handle_response)

        print("[*] Acessando a página de login...")
        try:
            page.goto(f"{BASE_URL}/#/sign-in", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[!] Erro ao carregar página: {e}")

        # Aguarda um pouco para o Vue renderizar + Cloudflare
        print("[*] Aguardando renderização da página...")
        time.sleep(5)

        # Salva screenshot e HTML para debug
        page.screenshot(path="debug_login.png", full_page=True)
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("[*] Screenshot salvo em debug_login.png")
        print("[*] HTML salvo em debug_page.html")

        # Tenta vários seletores possíveis
        selectors_username = [
            'input[type="text"]',
            'input[name="username"]',
            'input[placeholder*="usuário" i]',
            'input[placeholder*="Usuário" i]',
            'input[placeholder*="login" i]',
            'input[placeholder*="Login" i]',
            'input[placeholder*="email" i]',
            'input.v-field__input',
            '.v-text-field input',
            'input[autocomplete="username"]',
        ]

        selectors_password = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="senha" i]',
            'input[placeholder*="Senha" i]',
            'input[autocomplete="current-password"]',
        ]

        username_input = None
        password_input = None

        print("[*] Procurando campos do formulário...")
        for sel in selectors_username:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    username_input = el
                    print(f"[✓] Campo usuário encontrado com: {sel}")
                    break
            except:
                continue

        for sel in selectors_password:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    password_input = el
                    print(f"[✓] Campo senha encontrado com: {sel}")
                    break
            except:
                continue

        if not username_input or not password_input:
            print("\n[!] Não encontrou os campos de login.")
            print("    Verifique o arquivo debug_login.png e debug_page.html")
            print("    Possivelmente o Cloudflare está bloqueando ou a página mudou.")
            browser.close()
            return None

        print("[*] Preenchendo credenciais...")
        username_input.fill(USERNAME)
        time.sleep(0.5)
        password_input.fill(PASSWORD)
        time.sleep(0.5)

        # Clica no botão
        button_selectors = [
            'button:has-text("Entrar")',
            'button:has-text("Login")',
            'button:has-text("Acessar")',
            'button[type="submit"]',
            '.v-btn:has-text("Entrar")',
            'button.v-btn',
        ]

        clicked = False
        for sel in button_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    print(f"[✓] Botão clicado com: {sel}")
                    clicked = True
                    break
            except:
                continue

        if not clicked:
            print("[!] Não encontrou botão de login. Tentando pressionar Enter...")
            password_input.press("Enter")

        print("[*] Aguardando resposta do login (até 20s)...")
        for i in range(20):
            if token:
                break
            time.sleep(1)
            if i % 5 == 0:
                print(f"    ... ainda aguardando ({i}s)")

        # Fallback: tenta pegar do localStorage
        if not token:
            print("[*] Tentando capturar do localStorage/sessionStorage...")
            try:
                storage = page.evaluate("""() => {
                    const data = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        data['local_' + key] = localStorage.getItem(key);
                    }
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        data['session_' + key] = sessionStorage.getItem(key);
                    }
                    return data;
                }""")
                
                print("[DEBUG] Storage encontrado:")
                for k, v in storage.items():
                    print(f"  {k}: {str(v)[:80]}...")
                
                for key, value in storage.items():
                    if value and isinstance(value, str) and "|" in value and len(value) > 40:
                        token = value
                        print(f"[✓] Token encontrado no storage ({key})")
                        break
            except Exception as e:
                print(f"[!] Erro ao ler storage: {e}")

        browser.close()

        if token:
            print("\n" + "="*60)
            print("✅ TOKEN CAPTURADO COM SUCESSO:")
            print(token)
            print("="*60)
            
            with open("token.txt", "w") as f:
                f.write(token)
            print("\n[*] Token salvo em token.txt")
            return token
        else:
            print("\n[!] Não foi possível capturar o token.")
            print("    Veja os arquivos de debug gerados.")
            return None


if __name__ == "__main__":
    login_and_get_token()