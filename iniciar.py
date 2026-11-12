"""Inicio con un clic del Sistema de Control Presupuestario.

Hace todo lo necesario y deja la página funcionando en UN solo puerto (página + API juntas):
  1. Comprueba Python (3.11+) y crea el entorno virtual backend/.venv con sus dependencias (solo la primera vez).
  2. Compila la interfaz (frontend/dist) si falta o si cambió el código (necesita Node.js solo para eso).
  3. Arranca el servidor en 0.0.0.0 para que lo abran otros dispositivos de la misma red.
  4. Con --internet crea además un enlace público https://….trycloudflare.com (Cloudflare Tunnel, gratuito).
  5. Muestra los enlaces, los guarda en ENLACES.txt y abre el navegador.

Uso:  python iniciar.py            (esta computadora + red local)
      python iniciar.py --internet (además, enlace para cualquier lugar)
Variables opcionales: PUERTO (por defecto 8000).
"""
from __future__ import annotations

import base64
import hashlib
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ / "backend"
FRONTEND = RAIZ / "frontend"
DIST = FRONTEND / "dist"
VENV = BACKEND / ".venv"
HERRAMIENTAS = RAIZ / "tools"
ES_WINDOWS = os.name == "nt"
INTERNET = "--internet" in sys.argv

try:  # acentos correctos en la consola de Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


def titulo(t: str) -> None:
    print(f"\n=== {t} ===", flush=True)


def fallar(msg: str, ayuda: str = "") -> None:
    print(f"\n[ERROR] {msg}")
    if ayuda:
        print(f"        {ayuda}")
    sys.exit(1)


def ejecutar(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, env=env)
    if r.returncode != 0:
        fallar(f"Falló el comando: {' '.join(cmd)}", "Revise los mensajes de arriba (¿hay conexión a internet para descargar paquetes?).")


def huella(*archivos: Path) -> str:
    h = hashlib.sha256()
    for a in archivos:
        if a.exists():
            h.update(a.read_bytes())
    return h.hexdigest()


# ------------------------------------------------------------------ 1. Python y dependencias
def preparar_python() -> Path:
    titulo("1/4 Preparando el servidor (Python)")
    if sys.version_info < (3, 11):
        fallar(f"Se necesita Python 3.11 o superior (tiene {platform.python_version()}).", "Descárguelo en https://www.python.org/downloads/")
    py = VENV / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")
    if not py.exists():
        print("Creando entorno virtual (solo la primera vez)…")
        r = subprocess.run([sys.executable, "-m", "venv", str(VENV)])
        if r.returncode != 0 or not py.exists():
            fallar("No se pudo crear el entorno virtual.", "En Linux instale el paquete python3-venv (sudo apt install python3-venv).")
    req = BACKEND / "requirements.txt"
    marca = VENV / ".requisitos_instalados"
    if not marca.exists() or marca.read_text() != huella(req):
        print("Instalando dependencias del servidor (puede tardar unos minutos la primera vez)…")
        ejecutar([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", str(req)], BACKEND)
        marca.write_text(huella(req))
    print("Servidor listo.")
    return py


# ------------------------------------------------------------------ 2. Interfaz (frontend)
def _mas_reciente(carpeta: Path) -> float:
    return max((p.stat().st_mtime for p in carpeta.rglob("*") if p.is_file()), default=0)


def preparar_frontend() -> None:
    titulo("2/4 Preparando la página (interfaz)")
    indice = DIST / "index.html"
    fuentes = [FRONTEND / "src", FRONTEND / "public"]
    archivos = [FRONTEND / f for f in ("index.html", "package.json", "vite.config.ts", "tailwind.config.js")]
    cambio = max([_mas_reciente(c) for c in fuentes] + [a.stat().st_mtime for a in archivos if a.exists()])
    if indice.exists() and indice.stat().st_mtime >= cambio:
        print("La página ya está compilada y al día.")
        return
    npm = shutil.which("npm")
    if not npm:
        if indice.exists():
            print("[AVISO] Hay cambios sin compilar, pero Node.js no está instalado: se usará la versión compilada existente.")
            return
        fallar("Falta compilar la página y Node.js no está instalado.",
               "Instale Node.js LTS desde https://nodejs.org (solo se necesita una vez) o copie la carpeta frontend/dist desde otra computadora.")
    env = {k: v for k, v in os.environ.items() if k != "VITE_API_URL"}  # la API va en el mismo servidor
    marca = FRONTEND / "node_modules" / ".instalado"
    if not marca.exists() or marca.read_text() != huella(FRONTEND / "package-lock.json", FRONTEND / "package.json"):
        print("Instalando componentes de la interfaz (solo la primera vez)…")
        lock = (FRONTEND / "package-lock.json").exists()
        ejecutar([npm, "ci" if lock else "install", "--no-audit", "--no-fund"], FRONTEND, env)
        marca.write_text(huella(FRONTEND / "package-lock.json", FRONTEND / "package.json"))
    print("Compilando la página…")
    ejecutar([npm, "run", "build"], FRONTEND, env)
    print("Página compilada.")


# ------------------------------------------------------------------ 3. Servidor
def ip_local() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no envía datos: solo elige la interfaz de red
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return None
    finally:
        s.close()


VIRTUALES = re.compile(r"vethernet|virtualbox|vmware|vmnet|hyper-v|wsl|docker|vbox|loopback|bluetooth|tailscale|zerotier|hamachi|vpn|tap-|tun|utun|bridge|br-|virbr", re.I)
INALAMBRICO = re.compile(r"wi-?fi|inal[aá]mbric|wireless|wlan|wlp|^en0$|airport", re.I)


def _privada(ip: str) -> bool:
    a = [int(x) for x in ip.split(".")]
    return a[0] == 10 or (a[0] == 172 and 16 <= a[1] <= 31) or (a[0] == 192 and a[1] == 168)


def direcciones() -> list[tuple[str, str]]:
    """[(adaptador, ip)] de las redes locales reales, primero el Wi-Fi. Excluye adaptadores virtuales y VPN."""
    pares: list[tuple[str, str]] = []
    try:
        if ES_WINDOWS:
            salida = subprocess.run(["ipconfig"], capture_output=True, text=True, errors="replace", timeout=10).stdout
            adaptador = ""
            for linea in salida.splitlines():
                if linea and not linea[0].isspace() and linea.rstrip().endswith(":"):
                    adaptador = linea.strip().rstrip(":")
                elif "IPv4" in linea:
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", linea)
                    if m:
                        pares.append((adaptador, m.group(1)))
        elif platform.system() == "Darwin":
            salida = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=10).stdout
            adaptador = ""
            for linea in salida.splitlines():
                if linea and not linea[0].isspace():
                    adaptador = linea.split(":")[0]
                m = re.search(r"\binet (\d+\.\d+\.\d+\.\d+)", linea)
                if m:
                    pares.append((adaptador, m.group(1)))
        else:
            salida = subprocess.run(["ip", "-4", "-o", "addr"], capture_output=True, text=True, timeout=10).stdout
            for linea in salida.splitlines():
                m = re.search(r"^\d+:\s+(\S+)\s+inet (\d+\.\d+\.\d+\.\d+)", linea)
                if m:
                    pares.append((m.group(1), m.group(2)))
    except Exception:
        pass
    principal = ip_local()
    if principal and not any(ip == principal for _, ip in pares):
        pares.append(("red principal", principal))
    vistos, buenas = set(), []
    for ad, ip in pares:
        if ip in vistos or ip.startswith(("127.", "169.254.")) or not _privada(ip) or VIRTUALES.search(ad):
            continue
        vistos.add(ip)
        buenas.append((ad, ip))
    buenas.sort(key=lambda x: (not INALAMBRICO.search(x[0]), x[1] != principal))
    return buenas


# ------------------------------------------------------------------ cortafuegos (firewall)
REGLA = "Control Presupuestario EXB (TCP 8000-8019)"  # también abre 5173/4173 (modo desarrollo)


def _ejecutables_python(py: Path) -> list[str]:
    rutas = {str(Path(sys.executable).resolve()), str(py)}
    try:  # en Windows el python del entorno virtual lanza el python base, que es el que recibe las conexiones
        base = subprocess.run([str(py), "-c", "import sys;print(getattr(sys,'_base_executable',sys.executable))"],
                              capture_output=True, text=True, timeout=20).stdout.strip()
        if base:
            rutas.add(str(Path(base).resolve()))
    except Exception:
        pass
    return sorted(rutas)


def _bloqueos_windows(programas: list[str]) -> bool:
    """True si hay reglas de ENTRADA que BLOQUEAN a Python (se crean al cancelar el aviso de Windows)."""
    try:
        salida = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", "name=all", "dir=in", "verbose"],
                                capture_output=True, text=True, errors="replace", timeout=60).stdout.lower()
    except Exception:
        return False
    objetivos = {p.lower() for p in programas}
    for bloque in re.split(r"\n\s*\n", salida):
        if not re.search(r"(acci[oó]n|action)\s*:\s*(bloquear|block)", bloque):
            continue
        m = re.search(r"(programa|program)\s*:\s*(.+)", bloque)
        if m and os.path.expandvars(m.group(2).strip()).lower() in objetivos:
            return True
    return False


def _regla_existe() -> bool:
    r = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", f"name={REGLA}"], capture_output=True, text=True, errors="replace")
    return r.returncode == 0 and "8000-8019" in r.stdout


def preparar_firewall_windows(py: Path) -> None:
    """Abre los puertos 8000-8019 en el firewall de Windows (todas las redes) y quita bloqueos previos a Python.
    Solo pide permiso de administrador si hace falta (una vez)."""
    programas = _ejecutables_python(py)
    falta_regla, hay_bloqueo = not _regla_existe(), _bloqueos_windows(programas)
    if not falta_regla and not hay_bloqueo:
        print("Firewall de Windows: acceso desde la red permitido.")
        return
    motivo = "hay una regla que BLOQUEA a Python" if hay_bloqueo else "falta permitir el acceso desde la red"
    print(f"Firewall de Windows: {motivo}.")
    print("Windows pedirá permiso de administrador UNA sola vez para corregirlo. Pulse «Sí».")
    HERRAMIENTAS.mkdir(exist_ok=True)
    ps1 = HERRAMIENTAS / "configurar-firewall.ps1"
    lista = ", ".join("'" + p.replace("'", "''") + "'" for p in programas)
    ps1.write_text(f"""$ErrorActionPreference = 'SilentlyContinue'
$nombre = '{REGLA}'
$objetivos = @({lista}) | ForEach-Object {{ $_.ToLower() }}
# 1) Quitar reglas de entrada que bloquean a Python (aparecen si se canceló el aviso de Windows)
Get-NetFirewallRule -Direction Inbound -Action Block | ForEach-Object {{
  $prog = ($_ | Get-NetFirewallApplicationFilter).Program
  if ($prog -and ($objetivos -contains [Environment]::ExpandEnvironmentVariables($prog).ToLower())) {{ Remove-NetFirewallRule -Name $_.Name }}
}}
# 2) Permitir los puertos del sistema en redes privadas, públicas y de dominio
Get-NetFirewallRule -DisplayName "$nombre*" | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $nombre -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5173,4173,8000-8019 -Profile Any | Out-Null
# 3) Permitir también a los ejecutables de Python (así Windows no vuelve a mostrar el aviso ni crea bloqueos)
@({lista}) | ForEach-Object {{ New-NetFirewallRule -DisplayName "$nombre - $(Split-Path $_ -Leaf) - $($_.GetHashCode())" -Direction Inbound -Action Allow -Program $_ -Profile Any | Out-Null }}
""", encoding="utf-8-sig")
    ruta = str(ps1).replace("'", "''")
    orden = (f"try {{ Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList "
             f"@('-NoProfile','-ExecutionPolicy','Bypass','-File',('\"' + '{ruta}' + '\"')) }} catch {{ }}")
    codificado = base64.b64encode(orden.encode("utf-16-le")).decode()  # evita problemas de comillas y espacios
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", codificado])
    if _regla_existe() and not _bloqueos_windows(programas):
        print("Firewall configurado correctamente.")
    else:
        print("[AVISO] No se pudo configurar el firewall (¿se pulsó «No»?). Otros dispositivos no podrán entrar.")
        print("        Vuelva a iniciar y acepte, o ejecute como administrador en PowerShell:")
        print(f"        New-NetFirewallRule -DisplayName '{REGLA}' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5173,4173,8000-8019 -Profile Any")


def avisos_firewall_otros() -> None:
    if platform.system() == "Darwin":
        fw = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        try:
            estado = subprocess.run([fw, "--getglobalstate"], capture_output=True, text=True, timeout=10).stdout
            bloqueo = subprocess.run([fw, "--getblockall"], capture_output=True, text=True, timeout=10).stdout
            if "enabled" in estado.lower() or "activ" in estado.lower():
                print("Firewall de macOS activo: si aparece «¿Permitir conexiones entrantes a Python?», pulse «Permitir».")
            if "enabled" in bloqueo.lower() or "block all" in bloqueo.lower():
                print("[AVISO] macOS está bloqueando TODAS las conexiones entrantes. Desactívelo en Ajustes › Red › Firewall › Opciones.")
        except Exception:
            pass
    else:
        try:
            if subprocess.run(["systemctl", "is-active", "--quiet", "ufw"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                print("Firewall ufw activo: si otros dispositivos no entran, ejecute  sudo ufw allow 8000:8019/tcp")
        except Exception:
            pass


def prueba_local(ip: str, puerto: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{ip}:{puerto}/api/salud", timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def puerto_libre(inicial: int) -> int:
    for p in range(inicial, inicial + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    fallar("No se encontró un puerto libre.")
    return inicial


def esperar_servidor(proc: subprocess.Popen, puerto: int, limite: int = 90) -> None:
    url = f"http://127.0.0.1:{puerto}/api/salud"
    fin = time.time() + limite
    while time.time() < fin:
        if proc.poll() is not None:
            fallar("El servidor se detuvo al arrancar.", "Revise los mensajes de arriba.")
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(1)
    fallar("El servidor no respondió a tiempo.")


# ------------------------------------------------------------------ 4. Enlace de internet (Cloudflare Tunnel)
def cloudflared() -> Path | None:
    encontrado = shutil.which("cloudflared")
    if encontrado:
        return Path(encontrado)
    HERRAMIENTAS.mkdir(exist_ok=True)
    destino = HERRAMIENTAS / ("cloudflared.exe" if ES_WINDOWS else "cloudflared")
    if destino.exists():
        return destino
    maq = platform.machine().lower()
    arq = "arm64" if maq in ("arm64", "aarch64") else "amd64"
    sistema = {"Windows": "windows", "Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    if not sistema:
        return None
    nombre = f"cloudflared-{sistema}-{arq}" + (".exe" if sistema == "windows" else ".tgz" if sistema == "darwin" else "")
    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{nombre}"
    print(f"Descargando Cloudflare Tunnel (solo la primera vez, ~30 MB)…\n  {url}")
    try:
        tmp = HERRAMIENTAS / (nombre + ".descarga")
        urllib.request.urlretrieve(url, tmp)
        if nombre.endswith(".tgz"):
            with tarfile.open(tmp) as t:
                miembro = next(m for m in t.getmembers() if m.name.endswith("cloudflared"))
                with t.extractfile(miembro) as origen, open(destino, "wb") as dst:  # type: ignore[union-attr]
                    shutil.copyfileobj(origen, dst)
            tmp.unlink()
        else:
            tmp.replace(destino)
        destino.chmod(0o755)
        return destino
    except Exception as exc:
        print(f"[AVISO] No se pudo descargar: {exc}")
        print(f"        Descárguelo a mano desde {url} y guárdelo como {destino}")
        return None


def abrir_tunel(puerto: int) -> tuple[subprocess.Popen | None, str | None]:
    exe = cloudflared()
    if not exe:
        return None, None
    proc = subprocess.Popen([str(exe), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{puerto}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    hallado: list[str] = []

    def leer():
        for linea in proc.stdout:  # type: ignore[union-attr]
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linea)
            if m and not hallado:
                hallado.append(m.group(0))
    threading.Thread(target=leer, daemon=True).start()
    fin = time.time() + 60
    while time.time() < fin and not hallado and proc.poll() is None:
        time.sleep(0.5)
    if hallado:  # se espera a que el nombre público quede activo
        for _ in range(20):
            try:
                with urllib.request.urlopen(hallado[0] + "/api/salud", timeout=4):
                    break
            except Exception:
                time.sleep(1.5)
    return proc, (hallado[0] if hallado else None)


# ------------------------------------------------------------------ principal
def main() -> None:
    print("Sistema de Control Presupuestario · Enseña por Bolivia")
    py = preparar_python()
    preparar_frontend()

    titulo("3/4 Iniciando el servidor")
    if ES_WINDOWS:
        preparar_firewall_windows(py)
    else:
        avisos_firewall_otros()
    puerto = puerto_libre(int(os.environ.get("PUERTO", "8000")))
    if not 8000 <= puerto <= 8019:
        print(f"[AVISO] Se usa el puerto {puerto}, fuera del rango 8000-8019 abierto en el firewall.")
    servidor = subprocess.Popen([str(py), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(puerto)], cwd=BACKEND)
    procesos = [servidor]
    try:
        esperar_servidor(servidor, puerto)
        redes = direcciones()
        enlaces = [("En esta computadora", f"http://localhost:{puerto}")]
        for i, (adaptador, ip) in enumerate(redes):
            nombre = "Otros dispositivos de la MISMA red" if i == 0 else "Alternativa (si la anterior no abre)"
            enlaces.append((f"{nombre} · {adaptador}", f"http://{ip}:{puerto}"))
            if i == 0 and not prueba_local(ip, puerto):
                print(f"[AVISO] El servidor no responde en {ip}. Revise que la red esté conectada.")
        if not redes:
            print("[AVISO] No se detectó ninguna red local (Wi-Fi o cable). Solo funcionará en esta computadora.")

        titulo("4/4 Enlace de internet")
        if INTERNET:
            tunel, publico = abrir_tunel(puerto)
            if tunel:
                procesos.append(tunel)
            if publico:
                enlaces.append(("Desde CUALQUIER lugar (internet)", publico))
            else:
                print("[AVISO] No se pudo crear el enlace de internet. La red local sigue funcionando.")
        else:
            print("Desactivado. Para compartir por internet use INICIAR-CON-INTERNET.")

        texto = "\n".join(f"  {n}:\n    {u}" for n, u in enlaces)
        print("\n" + "=" * 62 + "\n  LA PÁGINA ESTÁ FUNCIONANDO\n\n" + texto + "\n")
        if redes:
            print("  En el otro dispositivo escriba la dirección EXACTA, empezando por http://")
            print(f"  (no https). Prueba rápida: http://{redes[0][1]}:{puerto}/api/salud debe mostrar «ok».")
            print("  Si no abre: ambos equipos deben estar en la misma red Wi-Fi, sin VPN ni datos móviles.")
            print("  Algunas redes (invitados, hoteles, universidades, eventos) aíslan a los dispositivos:")
            print("  en ese caso use INICIAR-CON-INTERNET o comparta datos desde un celular (hotspot).")
        print()
        print("  Mantenga esta ventana abierta. Para apagar: ciérrela o pulse Ctrl+C.")
        if INTERNET:
            print("  El enlace de internet cambia cada vez que se inicia y solo funciona")
            print("  mientras esta computadora esté encendida con esta ventana abierta.")
        print("=" * 62, flush=True)
        (RAIZ / "ENLACES.txt").write_text("Enlaces de la última ejecución\n\n" + texto + "\n", encoding="utf-8")
        # se abre la dirección compartible (no «localhost») para poder copiarla de la barra del navegador
        webbrowser.open(enlaces[-1][1] if INTERNET and len(enlaces) > 1 and "trycloudflare" in enlaces[-1][1] else enlaces[min(1, len(enlaces) - 1)][1])
        while servidor.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nApagando…")
    finally:
        for p in procesos:
            if p.poll() is None:
                p.terminate()
        for p in procesos:
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
