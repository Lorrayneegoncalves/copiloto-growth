"""Limite diário de uso do LLM, somando TODOS os visitantes do app.

No Streamlit, uma única instância deste contador é compartilhada entre as sessões
(st.cache_resource). Recarregar a página não zera o contador; ele zera na virada do
dia ou quando o app reinicia.
"""

from __future__ import annotations

import threading
from datetime import date
from typing import Callable


class ContadorDiario:
    def __init__(self, limite: int, hoje: Callable[[], date] = date.today):
        self.limite = limite
        self._hoje = hoje
        self._dia = hoje()
        self._usos = 0
        self._trava = threading.Lock()  # vários visitantes ao mesmo tempo

    def _virar_dia(self) -> None:
        if self._hoje() != self._dia:
            self._dia = self._hoje()
            self._usos = 0

    def consumir(self) -> bool:
        """Registra um uso. Devolve False (sem registrar) se o limite do dia já foi atingido."""
        with self._trava:
            self._virar_dia()
            if self._usos >= self.limite:
                return False
            self._usos += 1
            return True

    def restantes(self) -> int:
        with self._trava:
            self._virar_dia()
            return max(self.limite - self._usos, 0)
