"""
Descarga todos los documentos del módulo Casa Market via API REST.
Usa urlFile (S3 directo) — sin scraping HTML.
"""
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

AUTH_URL      = "https://acl.casamarketapp.com/api/authenticate"
DOCUMENTS_URL = "https://n5.report.casamarketapp.com/documents"


def ensure_dir(path: str) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_token(email: str, password: str) -> str:
    resp = requests.post(
        AUTH_URL,
        json={"email": email, "password": password, "codeApp": "quipuadmin"},
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("token")
    if not token:
        raise RuntimeError("No se recibió token del servidor.")
    return token


def fetch_all_documents(token: str, days_back: int = 30) -> list[dict]:
    end_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Origin": "https://admin.casamarket.la",
    }

    all_docs: list[dict] = []
    page = 1
    last_page = 1

    while page <= last_page:
        resp = requests.get(
            DOCUMENTS_URL,
            headers=headers,
            params={"startDate": start_date, "endDate": end_date, "limit": 50, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        last_page = int(resp.headers.get("x-last-page", 1))
        all_docs.extend(resp.json())
        print(f"  Página {page}/{last_page} leída.")
        page += 1

    return all_docs


def download_file(url: str, filename: str, extension: str, output_dir: Path) -> Path:
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()

    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)
    output_path = output_dir / f"{safe_name}.{extension}"

    with output_path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return output_path


def main() -> None:
    load_dotenv()

    email     = os.getenv("gmail", "").strip()
    password  = os.getenv("password", "").strip()
    days_back = int(os.getenv("DAYS_BACK", "30"))
    output_dir = ensure_dir(os.getenv("OUTPUT_DIR", "descargas"))

    print("Autenticando...")
    token = get_token(email, password)

    print(f"Obteniendo documentos (últimos {days_back} días)...")
    docs = fetch_all_documents(token, days_back=days_back)

    # Solo descarga los finalizados (status=2)
    finalizados = [d for d in docs if d.get("status") == 2]
    print(f"\nTotal: {len(docs)} | Finalizados: {len(finalizados)}")
    print(f"Carpeta destino: {output_dir.resolve()}\n")

    errores = 0
    for i, doc in enumerate(finalizados, 1):
        url = doc.get("urlFile", "")
        if not url:
            print(f"[{i:>3}/{len(finalizados)}] SIN URL  {doc['filename'][:60]}")
            errores += 1
            continue
        try:
            saved = download_file(url, doc["filename"], doc["extension"], output_dir)
            print(f"[{i:>3}/{len(finalizados)}] OK   {saved.name}")
        except Exception as exc:
            print(f"[{i:>3}/{len(finalizados)}] ERR  {doc['filename'][:50]} -> {exc}")
            errores += 1
        time.sleep(0.3)

    print(f"\nListo. {len(finalizados) - errores}/{len(finalizados)} archivos descargados.")


if __name__ == "__main__":
    main()
