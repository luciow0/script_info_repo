import sys
import requests
import math
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

archivoRuta = "token.txt"
with open(archivoRuta, "r") as archivoAbierto: 
    token = archivoAbierto.readline().strip
GITHUB_TOKEN = token
CONSTANTE_TIEMPO = "+00:00"
CONSTANTE_NOTFOUND = "Not Found"

# ejecutar con -> python repo_health.py {nombre-usuario} {nombre-repositorio}
# prerequisitos (dependencias) -> pip install requests rich

# ejemplos de uso 

# GIGANTES

# python repo_health.py torvalds linux
# python repo_health.py rust-lang rust -> repo del compilador, librerias estandar y demas infraestructura de Rust
# python repo_health.py llvm llvm-project -> infraestructura de compilador de lenguaje C y otros 

# cuando se ejecutan estos se pierde info. ya que el buffer de scroll tiene un límite. 
# Cuando lo que se imprime excede ese límite, lo más viejo “se pierde”
# esto se puede solucionar redirigiendo la salida a un archivo 

# MEDIANOS 

# python repo_health.py psf requests
# python repo_health.py mitmproxy mitmproxy

# PEQUEÑOS

# python repo_health.py EbookFoundation free-programming-books

# MUY PEQUEÑOS 

# python repo_health.py luciow0 NewtonCompiler 

# INEXISTENTES 
# python repo_health.py usuario123 repositorioInexistente123

# METODOS AUXILIARES
def parsear_fecha(fecha_str: str):
    """
    Convierte un string ISO8601 de GitHub (ej: '2023-05-01T12:34:56Z')
    a datetime timezone-aware en UTC.
    """
    if fecha_str:
        return datetime.fromisoformat(fecha_str.replace("Z", CONSTANTE_TIEMPO))
    return None

def fetch_all(url, headers, params=None):
    results = []
    page = 1
    while True:
        p = {"per_page": 100, "page": page}
        if params:
            p.update(params)
        resp = requests.get(url, headers=headers, params=p).json()
        if not resp or "message" in resp:  # error o vacío
            break
        results.extend(resp)
        if len(resp) < 100:  # última página
            break
        page += 1
    return results

"""
Informacion basica del repositorio 
"""
def info_basica(owner: str, repo: str):
    console = Console()
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    url = f"https://api.github.com/repos/{owner}/{repo}"
    data = requests.get(url, headers=headers).json()

    if "message" in data and data["message"] == CONSTANTE_NOTFOUND:
        console.print(f"[red]Repositorio {owner}/{repo} no encontrado.[/red]")
        return

    # Extraer datos relevantes
    nombre = data.get("name", "N/A")
    descripcion = data.get("description", "N/A")
    url_html = data.get("html_url", "N/A")
    propietario = data.get("owner", {}).get("login", "N/A")
    creado = data.get("created_at", "N/A")
    actualizado = data.get("updated_at", "N/A")
    ultimo_push = data.get("pushed_at", "N/A")
    lenguaje = data.get("language", "N/A")
    size = f"{data.get('size', 0)} KB"
    visibilidad = "Privado" if data.get("private", False) else "Público"
    archivado = "Sí" if data.get("archived", False) else "No"
    plantilla = "Sí" if data.get("is_template", False) else "No"
    licencia = data.get("license", {}).get("name", "N/A")

    # Tabla
    table = Table(title=f"📊 Información básica de {owner}/{repo}")
    table.add_column("Atributo", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("📛 Nombre", nombre)
    table.add_row("📝 Descripción", descripcion if descripcion else "N/A")
    table.add_row("🔗 URL", url_html)
    table.add_row("👤 Propietario", propietario)
    table.add_row("📅 Creado", creado)
    table.add_row("⏰ Última actualización", actualizado)
    table.add_row("📤 Último push", ultimo_push)
    table.add_row("💻 Lenguaje principal", str(lenguaje))
    table.add_row("📦 Tamaño", size)
    table.add_row("🔒 Visibilidad", visibilidad)
    table.add_row("🗄️ Archivado", archivado)
    table.add_row("📐 Plantilla", plantilla)
    table.add_row("⚖️ Licencia", licencia)

    console.print(table)

"""
Muestra el recorrido completo de carpetas del repositorio
"""
def mostrar_estructura_repo(owner: str, repo: str, branch: str = "main"):
    console = Console()
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    data = requests.get(url, headers=headers).json()

    
    if "tree" not in data:
        console.print("[red]No se pudo obtener la estructura del repositorio.[/red]")
        return
    
    root = Tree(f"📂 {repo} ({branch})")
    
    print(f"📊 Estructura de {owner}/{repo}")
    nodos = {"": root}
    for item in data["tree"]:
        path = item["path"]
        partes = path.split("/")
        padre = ""
        for i, parte in enumerate(partes):
            subpath = "/".join(partes[: i + 1])
            if subpath not in nodos:
                if i == len(partes) - 1 and item["type"] == "blob":
                    nodos[subpath] = nodos[padre].add(f"📄 {parte}")
                else:
                    nodos[subpath] = nodos[padre].add(f"📂 {parte}")
            padre = subpath

    console.print(root)

"""
Muestra stars, forks, watchers en el momento, suscriptores 
Imprime una tabla de los principales contribuyentes y cuantos commits hizo cada uno 
Si el repo no tiene contribuyentes
"""
def actividad_social(owner: str, repo: str):
    console = Console()
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    base_url = f"https://api.github.com/repos/{owner}/{repo}"

    # Datos básicos del repo
    repo_data = requests.get(base_url, headers=headers).json()
    if "message" in repo_data and repo_data["message"] == CONSTANTE_NOTFOUND:
        console.print(f"[red]Repositorio {owner}/{repo} no encontrado.[/red]")
        return

    # Contribuyentes
    contrib_url = f"{base_url}/contributors"
    contrib_data = requests.get(contrib_url, headers=headers).json()
    contribuyentes = []
    if isinstance(contrib_data, list):
        for c in contrib_data[:5]:  # mostrar los primeros 5 para no explotar la terminal
            login = c.get("login", "N/A")
            commits = c.get("contributions", 0)
            contribuyentes.append(f"{login} ({commits} commits)")

    # Tabla principal
    table = Table(title=f"🤝 Actividad social de {owner}/{repo}")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("⭐ Stars", str(repo_data.get("stargazers_count", "N/A")))
    table.add_row("🍴 Forks", str(repo_data.get("forks_count", "N/A")))
    table.add_row("👀 Watchers", str(repo_data.get("subscribers_count", "N/A")))

    console.print(table)

    # Tabla aparte de contribuyentes
    if contribuyentes:
        contrib_table = Table(title="👥 Principales contribuyentes", show_lines=True)
        contrib_table.add_column("Usuario", style="cyan")
        contrib_table.add_column("Commits", style="green", justify="right")

        for c in contrib_data[:10]:  # mostrar hasta 10
            contrib_table.add_row(c.get("login", "N/A"), str(c.get("contributions", 0)))

        console.print(contrib_table)
    else:
        console.print("[yellow]No hay contribuyentes visibles o el repositorio está vacío.[/yellow]")


def issues_y_prs(owner: str, repo: str):
    console = Console()
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    base_url = f"https://api.github.com/repos/{owner}/{repo}"

    # Info básica del repo
    repo_data = requests.get(base_url, headers=headers).json()
    if "message" in repo_data and repo_data["message"] == CONSTANTE_NOTFOUND:
        console.print(f"[red]Repositorio {owner}/{repo} no encontrado.[/red]")
        return

    issues_habilitados = repo_data.get("has_issues", False)

    # === Issues ===
    #abiertos = requests.get(f"{base_url}/issues", params={"state": "open"}, headers=headers).json()
    #cerrados = requests.get(f"{base_url}/issues", params={"state": "closed"}, headers=headers).json()
    abiertos = fetch_all(f"{base_url}/issues", headers, params={"state": "open"})
    cerrados = fetch_all(f"{base_url}/issues", headers, params={"state": "closed"})

    # Filtrar solo issues (sacar PRs)
    abiertos_puros = [i for i in abiertos if "pull_request" not in i]
    cerrados_puros = [i for i in cerrados if "pull_request" not in i]

    # Calcular tiempos de resolución promedio (issues cerrados)
    tiempos_cierre = []
    for issue in cerrados_puros:
        creado = issue.get("created_at")
        cerrado = issue.get("closed_at")
        if creado and cerrado:
            t1 = parsear_fecha(issue.get("created_at"))
            t2 = parsear_fecha(issue.get("closed_at"))
            delta = (t2 - t1).days
            tiempos_cierre.append(delta)
    prom_resolucion = sum(tiempos_cierre) / len(tiempos_cierre) if tiempos_cierre else 0

    # === Pull Requests ===
    #prs_abiertos = requests.get(f"{base_url}/pulls", params={"state": "open"}, headers=headers).json()
    #prs_cerrados = requests.get(f"{base_url}/pulls", params={"state": "closed"}, headers=headers).json()
    prs_abiertos = fetch_all(f"{base_url}/pulls", headers, params={"state": "open"})
    prs_cerrados = fetch_all(f"{base_url}/pulls", headers, params={"state": "closed"})


    # Calcular tiempo promedio de merge/cierre
    tiempos_pr = []
    for pr in prs_cerrados:
        creado = pr.get("created_at")
        cerrado = pr.get("closed_at")
        if creado and cerrado:
            t1 = parsear_fecha(pr.get("created_at"))
            t2 = parsear_fecha(pr.get("closed_at"))
            delta = (t2 - t1).days
            tiempos_pr.append(delta)
    prom_resolucion_pr = sum(tiempos_pr) / len(tiempos_pr) if tiempos_pr else 0

    # === Tablas ===
    table = Table(title=f"🐛 Issues y 🔀 PRs en {owner}/{repo}")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("📌 Issues habilitados", "Sí" if issues_habilitados else "No")
    table.add_row("🐛 Issues abiertos", str(len(abiertos_puros)))
    table.add_row("✅ Issues cerrados", str(len(cerrados_puros)))
    table.add_row("⏱️ Tiempo promedio resolución Issues", f"{prom_resolucion:.1f} días")
    table.add_row("🔀 PRs abiertos", str(len(prs_abiertos)))
    table.add_row("✅ PRs cerrados", str(len(prs_cerrados)))
    table.add_row("⏱️ Tiempo promedio resolución PRs", f"{prom_resolucion_pr:.1f} días")

    console.print(table)



if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python repo_health.py <owner> <repo>")
    else:
        owner, repo = sys.argv[1], sys.argv[2]
        
        
        print("Bienvenido, elegi que queres saber acerca de", owner, repo)
        print("[0] Salir")
        print("[1] Estructura de archivos")
        print("[2] Informacion basica")
        print("[3] Actividad social")
        print("[4] Issues y pull requests")
        eleccion = input(".. ")
        while(eleccion != "0"): 
            if(eleccion) == "0": 
                break
            if(eleccion) == "1": 
                mostrar_estructura_repo(owner, repo)
            if(eleccion) == "2":
                info_basica(owner, repo)
            if(eleccion) == "3":
                actividad_social(owner, repo)
            if(eleccion) == "4": 
                issues_y_prs(owner, repo)
            
            print("[0] Salir")
            print("[1] Estructura de archivos")
            print("[2] Informacion basica")
            print("[3] Actividad social")
            print("[4] Issues y pull requests")
            eleccion = input(".. ")