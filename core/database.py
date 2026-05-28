from __future__ import annotations
"""Camada de persistencia SQLite do fluxo de caixa.

Este modulo concentra a criacao das tabelas, migracoes leves de legado e
operacoes CRUD usadas pelos servicos da aplicacao.
"""

import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from core.app_paths import data_file
from core.models import CycleSummary, DailyFlowSummary, Movement, MovementType, RegistryItem, Technician


DEFAULT_DB_PATH = data_file("caixa.db")
DEFAULT_CATEGORIES = ["Vendas", "Serviços", "Fornecedores", "Operacional", "Transporte", "Impostos", "Comissão"]


class DatabaseManager:
    """Encapsula o acesso ao banco SQLite da aplicacao."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        """Abre conexao configurada com row factory por nome de coluna."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        """Prepara o banco com tabelas, indices, migracoes e dados padrao."""
        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS movimentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL,
                    valor REAL NOT NULL CHECK(valor >= 0),
                    descricao TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    metodo TEXT NOT NULL,
                    pessoa TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )
            self._ensure_attachment_column(cur)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE COLLATE NOCASE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pessoas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE COLLATE NOCASE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tecnicos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    percentual_comissao REAL NOT NULL CHECK(percentual_comissao >= 0 AND percentual_comissao <= 100),
                    status TEXT NOT NULL CHECK(status IN ('ativo', 'inativo'))
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimentos_data ON movimentos (data DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimentos_busca ON movimentos (pessoa, descricao, categoria)")
            self._migrate_legacy_types(cur)
            self._ensure_service_columns(cur)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_movimentos_servico ON movimentos (grupo_servico)")
            self._seed_categories(cur)
            self._sync_registry_from_movements(cur, "categorias", "categoria")
            self._sync_registry_from_movements(cur, "pessoas", "pessoa")
            con.commit()

    def _ensure_attachment_column(self, cur: sqlite3.Cursor) -> None:
        """Garante compatibilidade com bases antigas sem coluna de anexo."""
        columns = {row["name"] for row in cur.execute("PRAGMA table_info(movimentos)").fetchall()}
        if "anexo" not in columns:
            cur.execute("ALTER TABLE movimentos ADD COLUMN anexo TEXT NOT NULL DEFAULT ''")

    def _migrate_legacy_types(self, cur: sqlite3.Cursor) -> None:
        """Normaliza tipos e metodos legados para o padrao atual."""
        cur.execute("UPDATE movimentos SET tipo = 'entrada' WHERE LOWER(tipo) IN ('receber')")
        cur.execute("UPDATE movimentos SET tipo = 'saida' WHERE LOWER(tipo) IN ('pagar', 'saída')")
        cur.execute("UPDATE movimentos SET metodo = 'débito' WHERE LOWER(metodo) = 'debito'")
        cur.execute("UPDATE movimentos SET metodo = 'crédito' WHERE LOWER(metodo) = 'credito'")

    def _ensure_service_columns(self, cur: sqlite3.Cursor) -> None:
        """Garante campos extras necessários ao fluxo de serviço técnico."""
        columns = {row["name"] for row in cur.execute("PRAGMA table_info(movimentos)").fetchall()}
        additions = {
            "grupo_servico": "TEXT NOT NULL DEFAULT ''",
            "papel_servico": "TEXT NOT NULL DEFAULT ''",
            "tecnico": "TEXT NOT NULL DEFAULT ''",
            "percentual_comissao_tecnico": "REAL NOT NULL DEFAULT 0",
            "valor_comissao_tecnico": "REAL NOT NULL DEFAULT 0",
            "valor_empresa": "REAL NOT NULL DEFAULT 0",
        }
        for column_name, definition in additions.items():
            if column_name not in columns:
                cur.execute(f"ALTER TABLE movimentos ADD COLUMN {column_name} {definition}")

    def _seed_categories(self, cur: sqlite3.Cursor) -> None:
        """Insere categorias padrao caso ainda nao existam."""
        for name in DEFAULT_CATEGORIES:
            cur.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (?)", (name,))

    def _sync_registry_from_movements(self, cur: sqlite3.Cursor, table_name: str, column_name: str) -> None:
        """Sincroniza cadastros auxiliares com valores ja usados em movimentos."""
        rows = cur.execute(
            f"SELECT DISTINCT TRIM({column_name}) AS nome FROM movimentos WHERE TRIM({column_name}) <> ''"
        ).fetchall()
        for row in rows:
            cur.execute(f"INSERT OR IGNORE INTO {table_name} (nome) VALUES (?)", (row["nome"],))

    def add_movement(self, movement: Movement) -> int:
        """Persiste um novo movimento e devolve o identificador gerado."""
        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO movimentos (
                    tipo, valor, descricao, categoria, metodo, pessoa, data, anexo,
                    grupo_servico, papel_servico, tecnico, percentual_comissao_tecnico,
                    valor_comissao_tecnico, valor_empresa
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    movement.movement_type.storage_value,
                    movement.valor,
                    movement.descricao,
                    movement.categoria,
                    movement.metodo,
                    movement.pessoa,
                    movement.data,
                    movement.anexo,
                    movement.grupo_servico,
                    movement.papel_servico,
                    movement.tecnico,
                    movement.percentual_comissao_tecnico,
                    movement.valor_comissao_tecnico,
                    movement.valor_empresa,
                ),
            )
            cur.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (?)", (movement.categoria,))
            cur.execute("INSERT OR IGNORE INTO pessoas (nome) VALUES (?)", (movement.pessoa,))
            con.commit()
            return int(cur.lastrowid)

    def update_movement(self, movement: Movement) -> None:
        """Atualiza um movimento existente e mantem cadastros auxiliares coerentes."""
        if movement.id is None:
            raise ValueError("Registro não encontrado.")

        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE movimentos
                SET tipo = ?, valor = ?, descricao = ?, categoria = ?, metodo = ?, pessoa = ?, data = ?, anexo = ?,
                    grupo_servico = ?, papel_servico = ?, tecnico = ?, percentual_comissao_tecnico = ?,
                    valor_comissao_tecnico = ?, valor_empresa = ?
                WHERE id = ?
                """,
                (
                    movement.movement_type.storage_value,
                    movement.valor,
                    movement.descricao,
                    movement.categoria,
                    movement.metodo,
                    movement.pessoa,
                    movement.data,
                    movement.anexo,
                    movement.grupo_servico,
                    movement.papel_servico,
                    movement.tecnico,
                    movement.percentual_comissao_tecnico,
                    movement.valor_comissao_tecnico,
                    movement.valor_empresa,
                    movement.id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("Registro não encontrado.")
            cur.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (?)", (movement.categoria,))
            cur.execute("INSERT OR IGNORE INTO pessoas (nome) VALUES (?)", (movement.pessoa,))
            con.commit()

    def delete_movement(self, movement_id: int) -> None:
        """Remove um movimento pelo id."""
        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM movimentos WHERE id = ?", (movement_id,))
            if cur.rowcount == 0:
                raise ValueError("Registro não encontrado.")
            con.commit()

    def fetch_movements(
        self,
        *,
        search: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
        category: str | None = None,
        movement_type: str | None = None,
        person: str | None = None,
        limit: int | None = None,
    ) -> list[Movement]:
        """Lista movimentos aplicando filtros opcionais e ordenacao mais recente primeiro."""
        clauses: list[str] = []
        params: list[object] = []

        if search.strip():
            term = f"%{search.strip()}%"
            clauses.append(
                "(LOWER(pessoa) LIKE LOWER(?) OR LOWER(descricao) LIKE LOWER(?) OR LOWER(categoria) LIKE LOWER(?) OR LOWER(anexo) LIKE LOWER(?) OR LOWER(tecnico) LIKE LOWER(?))"
            )
            params.extend([term, term, term, term, term])

        if start_date:
            clauses.append("data >= ?")
            params.append(start_date)

        if end_date:
            clauses.append("data <= ?")
            params.append(end_date)

        if category:
            clauses.append("categoria = ?")
            params.append(category)

        if person:
            clauses.append("pessoa = ?")
            params.append(person)

        if movement_type:
            clauses.append("tipo = ?")
            params.append(MovementType.from_db(movement_type).storage_value)

        query = """
            SELECT
                id, tipo, valor, descricao, categoria, metodo, pessoa, data, anexo,
                grupo_servico, papel_servico, tecnico, percentual_comissao_tecnico,
                valor_comissao_tecnico, valor_empresa
            FROM movimentos
        """
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY data DESC, id DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with closing(self.connect()) as con:
            rows = con.execute(query, params).fetchall()
        return [Movement(**dict(row)) for row in rows]

    def fetch_movements_by_day(self, day: str) -> list[Movement]:
        """Retorna todos os movimentos de um dia especifico."""
        return self.fetch_movements(start_date=day, end_date=day)

    def list_daily_flows(self) -> list[DailyFlowSummary]:
        """Agrupa os movimentos por dia para uso em historico e navegacao temporal."""
        with closing(self.connect()) as con:
            rows = con.execute(
                """
                SELECT
                    data AS data,
                    SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE 0 END) AS entradas,
                    SUM(CASE WHEN tipo = 'saida' THEN valor ELSE 0 END) AS saidas,
                    SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE -valor END) AS saldo,
                    COUNT(*) AS quantidade
                FROM movimentos
                GROUP BY data
                ORDER BY data DESC
                """
            ).fetchall()
        return [DailyFlowSummary(**dict(row)) for row in rows]

    def list_registry_items(self, table_name: str) -> list[RegistryItem]:
        """Lista itens de cadastro auxiliar ordenados alfabeticamente."""
        with closing(self.connect()) as con:
            rows = con.execute(f"SELECT id, nome FROM {table_name} ORDER BY LOWER(nome)").fetchall()
        return [RegistryItem(id=row["id"], nome=row["nome"]) for row in rows]

    def list_technicians(self) -> list[Technician]:
        """Lista técnicos com comissão e status."""
        with closing(self.connect()) as con:
            rows = con.execute(
                """
                SELECT id, nome, percentual_comissao, status
                FROM tecnicos
                ORDER BY LOWER(nome)
                """
            ).fetchall()
        return [
            Technician(
                id=row["id"],
                nome=row["nome"],
                percentual_comissao=float(row["percentual_comissao"]),
                status=row["status"],
            )
            for row in rows
        ]

    def add_technician(self, technician: Technician) -> Technician:
        """Adiciona técnico ao cadastro."""
        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO tecnicos (nome, percentual_comissao, status)
                VALUES (?, ?, ?)
                """,
                (technician.nome, technician.percentual_comissao, technician.status),
            )
            con.commit()
            technician.id = int(cur.lastrowid)
            return technician

    def update_technician(self, technician: Technician) -> None:
        """Atualiza técnico sem alterar serviços já lançados."""
        if technician.id is None:
            raise ValueError("Técnico não encontrado.")
        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE tecnicos
                SET nome = ?, percentual_comissao = ?, status = ?
                WHERE id = ?
                """,
                (technician.nome, technician.percentual_comissao, technician.status, technician.id),
            )
            if cur.rowcount == 0:
                raise ValueError("Técnico não encontrado.")
            con.commit()

    def delete_technician(self, technician_id: int) -> None:
        """Exclui técnico do cadastro."""
        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM tecnicos WHERE id = ?", (technician_id,))
            if cur.rowcount == 0:
                raise ValueError("Técnico não encontrado.")
            con.commit()

    def add_registry_item(self, table_name: str, name: str) -> RegistryItem:
        """Adiciona item em tabela auxiliar de cadastro."""
        with closing(self.connect()) as con:
            cur = con.cursor()
            cur.execute(f"INSERT INTO {table_name} (nome) VALUES (?)", (name,))
            con.commit()
            return RegistryItem(id=int(cur.lastrowid), nome=name)

    def update_registry_item(self, table_name: str, item_id: int, new_name: str, linked_column: str) -> None:
        """Renomeia item auxiliar e propaga o novo nome para os movimentos vinculados."""
        with closing(self.connect()) as con:
            cur = con.cursor()
            current = cur.execute(f"SELECT nome FROM {table_name} WHERE id = ?", (item_id,)).fetchone()
            if current is None:
                raise ValueError("Registro não encontrado.")
            old_name = current["nome"]
            cur.execute(f"UPDATE {table_name} SET nome = ? WHERE id = ?", (new_name, item_id))
            cur.execute(f"UPDATE movimentos SET {linked_column} = ? WHERE {linked_column} = ?", (new_name, old_name))
            con.commit()

    def delete_registry_item(self, table_name: str, item_id: int) -> None:
        """Exclui item de cadastro auxiliar pelo identificador."""
        with closing(self.connect()) as con:
            con.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
            con.commit()

    def summary(self, day: str | None = None) -> dict[str, object]:
        """Calcula resumo geral ou de um dia especifico para paines de leitura."""
        movements = self.fetch_movements_by_day(day) if day else self.fetch_movements()
        totals = {"saldo": 0.0, "entradas": 0.0, "saídas": 0.0, "quantidade": len(movements)}
        categories = defaultdict(float)
        methods = defaultdict(float)
        daily = defaultdict(lambda: {"saldo": 0.0, "quantidade": 0})

        for movement in movements:
            if movement.movement_type is MovementType.ENTRADA:
                totals["entradas"] += movement.valor
            else:
                totals["saídas"] += movement.valor

            totals["saldo"] += movement.signed_value
            categories[movement.categoria] += movement.valor
            methods[movement.metodo] += movement.valor
            daily[movement.data]["saldo"] += movement.signed_value
            daily[movement.data]["quantidade"] += 1

        recent_days = [
            {"data": current_day, "saldo": values["saldo"], "quantidade": values["quantidade"]}
            for current_day, values in sorted(daily.items(), reverse=True)[:7]
        ]
        return {
            **totals,
            "categorias": dict(sorted(categories.items(), key=lambda item: item[1], reverse=True)),
            "métodos": dict(sorted(methods.items(), key=lambda item: item[1], reverse=True)),
            "dias_recentes": recent_days,
        }

    def cycle_history(self) -> list[CycleSummary]:
        with closing(self.connect()) as con:
            rows = con.execute(
                """
                SELECT
                    substr(data, 1, 7) AS ciclo,
                    MIN(data) AS inicio,
                    MAX(data) AS fim,
                    SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE 0 END) AS entradas,
                    SUM(CASE WHEN tipo = 'saida' THEN valor ELSE 0 END) AS saidas,
                    SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE -valor END) AS saldo,
                    COUNT(*) AS quantidade
                FROM movimentos
                GROUP BY substr(data, 1, 7)
                ORDER BY ciclo DESC
                """
            ).fetchall()
        return [CycleSummary(**dict(row)) for row in rows]
