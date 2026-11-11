import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src import simular_dados  # noqa: E402


@pytest.fixture(scope="session")
def df() -> pd.DataFrame:
    """Lê o CSV do projeto (gera se ainda não existir)."""
    if not simular_dados.CAMINHO_CSV.exists():
        simular_dados.salvar(simular_dados.gerar())
    return pd.read_csv(simular_dados.CAMINHO_CSV)
