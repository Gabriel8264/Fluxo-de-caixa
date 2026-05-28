from __future__ import annotations

from services.cash_service import CashService


_service = CashService()


def criar_tabela() -> None:
    _service.initialize()


def registrar(tipo, valor, descricao, categoria, metodo, pessoa, data_movimento=None):
    return _service.register_movement(
        tipo=tipo,
        valor=valor,
        descricao=descricao,
        categoria=categoria,
        metodo=metodo,
        pessoa=pessoa,
        data_movimento=data_movimento,
    )


def listar():
    return _service.list_movements()


def buscar(texto):
    return _service.list_movements(search=texto)


def filtro_periodo(inicio, fim):
    return _service.list_movements(start_date=inicio or None, end_date=fim or None)


def saldo_total() -> float:
    return float(_service.get_summary()["saldo"])


def carregar():
    return [
        {
            "id": movement.id,
            "tipo": movement.tipo,
            "valor": movement.valor,
            "descricao": movement.descricao,
            "categoria": movement.categoria,
            "metodo": movement.metodo,
            "pessoa": movement.pessoa,
            "data": movement.data,
        }
        for movement in _service.list_movements()
    ]
