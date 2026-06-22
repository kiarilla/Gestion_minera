"""
model_store.py -- Persistencia de resultados de forecast en disco.

Guarda y carga resultados de backtesting, forecast completo y metadatos
en formato Parquet dentro de data/cache/. Esto permite que la app
Streamlit arranque rapido si ya se ejecutaron los modelos previamente,
y da la opcion de re-ejecutar manualmente.
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
BACKTESTING_FILE = "backtesting_results.parquet"
FORECAST_FILE = "forecast_5plus7.parquet"
METADATA_FILE = "metadata.json"


def _ensure_cache_dir() -> Path:
    """Crea el directorio de cache si no existe."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


# ---------------------------------------------------------------------------
# Guardado
# ---------------------------------------------------------------------------

def save_backtesting_results(results_df: pd.DataFrame) -> Path:
    """
    Guarda los resultados del backtesting en disco.

    Parameters
    ----------
    results_df : pd.DataFrame
        Resultado de run_backtesting().

    Returns
    -------
    Path
        Ruta del archivo guardado.
    """
    cache = _ensure_cache_dir()
    file_path = cache / BACKTESTING_FILE
    results_df.to_parquet(file_path, index=False)
    return file_path


def save_forecast(forecast_lines: pd.DataFrame) -> Path:
    """
    Guarda el forecast 5+7 completo en disco.

    Parameters
    ----------
    forecast_lines : pd.DataFrame
        Resultado de project_full_forecast().

    Returns
    -------
    Path
        Ruta del archivo guardado.
    """
    cache = _ensure_cache_dir()
    file_path = cache / FORECAST_FILE
    forecast_lines.to_parquet(file_path, index=False)
    return file_path


def save_metadata(
    best_method: str,
    kpis: dict,
    executed_at: Optional[str] = None,
) -> Path:
    """
    Guarda metadatos de la ejecucion (metodo ganador, KPIs, timestamp).

    Parameters
    ----------
    best_method : str
        Nombre del metodo seleccionado.
    kpis : dict
        Diccionario de KPIs.
    executed_at : str, optional
        Timestamp ISO. Si es None, usa el momento actual.

    Returns
    -------
    Path
        Ruta del archivo guardado.
    """
    from datetime import datetime

    cache = _ensure_cache_dir()
    file_path = cache / METADATA_FILE

    payload = {
        "best_method": best_method,
        "kpis": {k: float(v) if isinstance(v, (int, float)) else str(v)
                 for k, v in kpis.items()},
        "executed_at": executed_at or datetime.now().isoformat(),
    }
    file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

def load_backtesting_results() -> Optional[pd.DataFrame]:
    """
    Carga resultados de backtesting desde disco.

    Returns
    -------
    pd.DataFrame or None
        None si el archivo no existe o esta corrupto.
    """
    file_path = CACHE_DIR / BACKTESTING_FILE
    if not file_path.exists():
        return None
    try:
        return pd.read_parquet(file_path)
    except Exception:
        return None


def load_forecast() -> Optional[pd.DataFrame]:
    """
    Carga forecast 5+7 desde disco.

    Returns
    -------
    pd.DataFrame or None
        None si el archivo no existe o esta corrupto.
    """
    file_path = CACHE_DIR / FORECAST_FILE
    if not file_path.exists():
        return None
    try:
        return pd.read_parquet(file_path)
    except Exception:
        return None


def load_metadata() -> Optional[dict]:
    """
    Carga metadatos desde disco.

    Returns
    -------
    dict or None
        None si el archivo no existe o esta corrupto.
    """
    file_path = CACHE_DIR / METADATA_FILE
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def cache_exists() -> bool:
    """
    Verfica que todos los archivos de cache existan.

    Returns
    -------
    bool
        True si backtesting, forecast y metadata estan en disco.
    """
    return (
        (CACHE_DIR / BACKTESTING_FILE).exists()
        and (CACHE_DIR / FORECAST_FILE).exists()
        and (CACHE_DIR / METADATA_FILE).exists()
    )


def clear_cache() -> None:
    """Elimina todos los archivos de cache."""
    for f in [BACKTESTING_FILE, FORECAST_FILE, METADATA_FILE]:
        p = CACHE_DIR / f
        if p.exists():
            p.unlink()


def invalidate_cache() -> None:
    """Alias de clear_cache para semantica mas clara."""
    clear_cache()
