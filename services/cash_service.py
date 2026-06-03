from __future__ import annotations
"""Camada de regras de negocio do fluxo de caixa.

Este modulo valida entradas da interface, centraliza operacoes de movimentacao,
historico e cadastros auxiliares e conversa com o repositorio SQLite.
"""

import calendar
import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime
from uuid import uuid4

from core.database import DatabaseManager
from core.models import CompanyCashAdjustment, CycleSummary, DailyFlowSummary, Movement, MovementType, PAYMENT_METHODS, RegistryItem, Technician
from services.session_service import SessionService


class CashService:
    """Servico principal usado pela interface para operar o sistema."""

    def __init__(
        self,
        repository: DatabaseManager | None = None,
        session_service: SessionService | None = None,
    ) -> None:
        self.repository = repository or DatabaseManager()
        self.session_service = session_service or SessionService()

    def initialize(self) -> None:
        """Inicializa banco e garante que exista um dia ativo em sessao."""
        self.repository.initialize()
        self.session_service.start_day(self.session_service.get_active_day())

    def get_active_day(self) -> str:
        """Retorna o dia atualmente usado como fluxo ativo."""
        return self.session_service.get_active_day()

    def start_new_day(self) -> str:
        """Inicia um novo fluxo diario usando a data atual."""
        return self.session_service.start_day(date.today().isoformat())

    def register_movement(
        self,
        *,
        tipo: str,
        valor: str | float,
        descricao: str,
        categoria: str,
        metodo: str,
        pessoa: str,
        data_movimento: str | None = None,
        anexo: str = "",
    ) -> Movement:
        """Valida e registra uma nova movimentacao."""
        movement = self._build_movement(
            tipo=tipo,
            valor=valor,
            descricao=descricao,
            categoria=categoria,
            metodo=metodo,
            pessoa=pessoa,
            data_movimento=data_movimento,
            anexo=anexo,
        )
        movement.id = self.repository.add_movement(movement)
        return movement

    def register_technical_service(
        self,
        *,
        valor_servico: str | float,
        descricao: str,
        categoria: str,
        metodo: str,
        pessoa: str,
        tecnico_ids: list[int],
        data_movimento: str | None = None,
        anexo: str = "",
    ) -> tuple[Movement, list[Movement]]:
        """Registra um serviço técnico criando uma entrada e saídas de comissão."""
        technicians = self._load_service_technicians(tecnico_ids)
        split = self.calculate_technical_service_split(valor_servico, technicians)
        service_value = split["valor_servico"]
        movement_date = self._normalize_date(data_movimento) if data_movimento else self.get_active_day()
        cleaned_description = self._require_text(descricao, "A descrição é obrigatória.")
        cleaned_category = self._require_text(categoria, "A categoria é obrigatória.")
        cleaned_person = self._require_text(pessoa, "Informe a pessoa ou empresa.")
        normalized_method = self._normalize_method(metodo)
        if normalized_method not in PAYMENT_METHODS:
            raise ValueError("Método de pagamento inválido.")

        commission_value = float(split["valor_comissao_total"])
        company_value = float(split["valor_empresa"])
        total_percent = float(split["percentual_total_comissao"])
        technician_shares = list(split["divisao_tecnicos"])
        group_id = uuid4().hex
        technicians_label = ", ".join(technician.nome for technician in technicians)
        division_payload = json.dumps(
            [
                {
                    "id": technician.id,
                    "nome": technician.nome,
                    "percentual_tecnico": technician.percentual_comissao,
                    "percentual_total": total_percent,
                    "valor_individual": share,
                }
                for technician, share in technician_shares
            ],
            ensure_ascii=False,
        )

        entry = Movement(
            tipo=MovementType.ENTRADA.value,
            valor=round(service_value, 2),
            descricao=cleaned_description,
            categoria=cleaned_category,
            metodo=normalized_method,
            pessoa=cleaned_person,
            data=movement_date,
            anexo=anexo.strip(),
            grupo_servico=group_id,
            papel_servico="entrada_servico",
            tecnico=technicians_label,
            divisao_tecnicos=division_payload,
            percentual_comissao_tecnico=total_percent,
            valor_comissao_tecnico=commission_value,
            valor_empresa=company_value,
        )
        entry.id = self.repository.add_movement(entry)

        commission_exits: list[Movement] = []
        for technician, share in technician_shares:
            commission_exit = Movement(
                tipo=MovementType.SAIDA.value,
                valor=share,
                descricao=f"Comissão técnica · {technician.nome} · {cleaned_description}",
                categoria="Comissão",
                metodo=normalized_method,
                pessoa=technician.nome,
                data=movement_date,
                anexo=anexo.strip(),
                grupo_servico=group_id,
                papel_servico="comissao_tecnica",
                tecnico=technicians_label,
                divisao_tecnicos=division_payload,
                percentual_comissao_tecnico=technician.percentual_comissao,
                valor_comissao_tecnico=share,
                valor_empresa=company_value,
            )
            commission_exit.id = self.repository.add_movement(commission_exit)
            commission_exits.append(commission_exit)
        return entry, commission_exits

    def update_movement(
        self,
        movement_id: int,
        *,
        tipo: str,
        valor: str | float,
        descricao: str,
        categoria: str,
        metodo: str,
        pessoa: str,
        data_movimento: str | None = None,
        anexo: str = "",
    ) -> Movement:
        """Valida e atualiza uma movimentacao existente."""
        existing = self.repository.get_movement(movement_id)
        effective_date = data_movimento.strip() if data_movimento and data_movimento.strip() else existing.data
        movement = self._build_movement(
            tipo=tipo,
            valor=valor,
            descricao=descricao,
            categoria=categoria,
            metodo=metodo,
            pessoa=pessoa,
            data_movimento=effective_date,
            anexo=anexo,
        )
        movement.id = movement_id
        movement.grupo_servico = existing.grupo_servico
        movement.papel_servico = existing.papel_servico
        movement.tecnico = existing.tecnico
        movement.divisao_tecnicos = existing.divisao_tecnicos
        movement.percentual_comissao_tecnico = existing.percentual_comissao_tecnico
        movement.valor_comissao_tecnico = existing.valor_comissao_tecnico
        movement.valor_empresa = existing.valor_empresa
        self.repository.update_movement(movement)
        return movement

    def delete_movement(self, movement_id: int) -> None:
        """Exclui uma movimentacao pelo identificador."""
        self.repository.delete_movement(movement_id)

    def list_movements(
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
        """Lista movimentos com filtros opcionais ja normalizados."""
        normalized_start = self._normalize_date(start_date) if start_date else None
        normalized_end = self._normalize_date(end_date) if end_date else None
        if normalized_start and normalized_end and normalized_start > normalized_end:
            raise ValueError("A data inicial deve ser menor ou igual à data final.")

        return self.repository.fetch_movements(
            search=search,
            start_date=normalized_start,
            end_date=normalized_end,
            category=category,
            movement_type=movement_type,
            person=person,
            limit=limit,
        )

    def list_active_day_movements(self, *, limit: int | None = None) -> list[Movement]:
        """Lista movimentos pertencentes apenas ao fluxo ativo do dia."""
        active_day = self.get_active_day()
        return self.repository.fetch_movements(start_date=active_day, end_date=active_day, limit=limit)

    def get_movement(self, movement_id: int) -> Movement:
        """Retorna um movimento especifico preservando compatibilidade com legado."""
        return self.repository.get_movement(movement_id)

    def get_summary(self, *, active_day_only: bool = False) -> dict[str, object]:
        """Retorna resumo financeiro geral ou apenas do dia ativo."""
        return self.repository.summary(self.get_active_day() if active_day_only else None)

    def get_cycle_history(self) -> list[CycleSummary]:
        """Mantido para compatibilidade com leituras historicas legadas."""
        return self.repository.cycle_history()

    def list_daily_flows(self) -> list[DailyFlowSummary]:
        """Lista consolidado diario para navegacao no historico."""
        return self.repository.list_daily_flows()

    def get_daily_flow_details(self, day: str) -> list[Movement]:
        """Lista movimentos detalhados de um dia especifico."""
        return self.repository.fetch_movements_by_day(day)

    def get_company_cash_overview(self) -> dict[str, object]:
        """Consolida a visão geral da empresa com base nas movimentações existentes."""
        movements = self.list_movements()
        summary = self.get_summary(active_day_only=False)
        adjustments = self.list_company_cash_adjustments()
        adjustment_additions = round(sum(item.valor for item in adjustments if item.tipo == "add_funds"), 2)
        adjustment_withdrawals = round(sum(item.valor for item in adjustments if item.tipo == "withdraw_funds"), 2)
        adjustment_balance = round(adjustment_additions - adjustment_withdrawals, 2)
        if not movements:
            return {
                "entradas": 0.0,
                "saidas": 0.0,
                "saldo_registros": 0.0,
                "ajustes_adicionados": adjustment_additions,
                "ajustes_retirados": adjustment_withdrawals,
                "ajustes_liquidos": adjustment_balance,
                "saldo_real": adjustment_balance,
                "quantidade": 0,
                "primeira_movimentacao": "",
                "ultima_movimentacao": "",
                "categoria_receita": "Sem dados",
                "categoria_despesa": "Sem dados",
                "pessoa_frequente": "Sem dados",
                "metodo_frequente": "Sem dados",
                "total_servicos": 0,
                "total_comissoes": 0.0,
                "maior_entrada": "Sem dados",
                "maior_saida": "Sem dados",
                "adjustments": adjustments,
            }

        entradas = [movement for movement in movements if movement.movement_type is MovementType.ENTRADA]
        saidas = [movement for movement in movements if movement.movement_type is MovementType.SAIDA]
        ordered = sorted(movements, key=lambda item: (item.data, item.id or 0))
        categoria_receita = self._top_group(entradas, "categoria")
        categoria_despesa = self._top_group(saidas, "categoria")
        pessoa_frequente = self._top_frequency(movements, "pessoa")
        metodo_frequente = self._top_frequency(movements, "metodo")
        total_servicos = self._count_services(entradas)
        total_comissoes = round(
            sum(
                movement.valor
                for movement in saidas
                if movement.papel_servico == "comissao_tecnica"
                or "comiss" in movement.categoria.casefold()
            ),
            2,
        )

        return {
            "entradas": float(summary["entradas"]),
            "saidas": float(summary.get("saidas", summary.get("saídas", 0.0))),
            "saldo_registros": float(summary["saldo"]),
            "ajustes_adicionados": adjustment_additions,
            "ajustes_retirados": adjustment_withdrawals,
            "ajustes_liquidos": adjustment_balance,
            "saldo_real": round(float(summary["saldo"]) + adjustment_balance, 2),
            "quantidade": int(summary["quantidade"]),
            "primeira_movimentacao": ordered[0].formatted_date,
            "ultima_movimentacao": ordered[-1].formatted_date,
            "categoria_receita": categoria_receita,
            "categoria_despesa": categoria_despesa,
            "pessoa_frequente": pessoa_frequente,
            "metodo_frequente": metodo_frequente,
            "total_servicos": total_servicos,
            "total_comissoes": total_comissoes,
            "maior_entrada": self._movement_label(max(entradas, key=lambda item: item.valor, default=None)),
            "maior_saida": self._movement_label(max(saidas, key=lambda item: item.valor, default=None)),
            "adjustments": adjustments,
        }

    def add_company_funds(
        self,
        *,
        valor: str | float,
        descricao: str,
        data_movimento: str | None = None,
    ) -> CompanyCashAdjustment:
        """Adiciona fundos manuais ao caixa da empresa sem virar movimentação comum."""
        return self._register_company_cash_adjustment(
            tipo="add_funds",
            valor=valor,
            descricao=descricao,
            data_movimento=data_movimento,
        )

    def withdraw_company_funds(
        self,
        *,
        valor: str | float,
        descricao: str,
        data_movimento: str | None = None,
    ) -> CompanyCashAdjustment:
        """Registra retirada manual do caixa da empresa sem contaminar o fluxo comum."""
        return self._register_company_cash_adjustment(
            tipo="withdraw_funds",
            valor=valor,
            descricao=descricao,
            data_movimento=data_movimento,
        )

    def list_company_cash_adjustments(self) -> list[CompanyCashAdjustment]:
        """Lista o histórico auditável de ajustes manuais do caixa da empresa."""
        return self.repository.list_company_cash_adjustments()

    def get_history_tree(self) -> dict[str, dict[str, list[str]]]:
        """Monta arvore de historico por ano, mes e dia para a UI."""
        tree: dict[str, dict[str, list[str]]] = {}
        for flow in self.list_daily_flows():
            year, month, day = flow.data.split("-")
            tree.setdefault(year, {}).setdefault(month, []).append(day)

        for months in tree.values():
            for month, days in months.items():
                months[month] = sorted(days, reverse=True)
        return dict(sorted(tree.items(), reverse=True))

    def get_history_scope_data(
        self,
        *,
        year: str | None = None,
        month: str | None = None,
        day: str | None = None,
    ) -> dict[str, object]:
        """Entrega pacote pronto para leitura historica por ano, mes ou dia."""
        scope = "year"
        if year is None:
            active_year = self.get_active_day().split("-")[0]
            year = active_year
        if month is not None:
            scope = "month"
        if day is not None:
            scope = "day"

        start_date, end_date = self._history_period_bounds(year=year, month=month, day=day)
        movements = self.list_movements(start_date=start_date, end_date=end_date)
        summary = self._summarize_movements(movements)
        timeline = self._build_history_timeline(scope=scope, movements=movements)

        return {
            "scope": scope,
            "year": year,
            "month": month,
            "day": day,
            "start_date": start_date,
            "end_date": end_date,
            "label": self._history_scope_label(scope=scope, year=year, month=month, day=day),
            "movements": movements,
            "summary": summary,
            "timeline": timeline,
        }

    def list_categories(self) -> list[RegistryItem]:
        """Lista categorias disponiveis para selecao e manutencao."""
        return self.repository.list_registry_items("categorias")

    def add_category(self, name: str) -> RegistryItem:
        """Cadastra nova categoria com validacao de unicidade."""
        try:
            return self.repository.add_registry_item("categorias", self._require_text(name, "Informe o nome da categoria."))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma categoria com esse nome.") from exc

    def update_category(self, item_id: int, new_name: str) -> None:
        """Renomeia categoria e propaga o novo nome para os movimentos."""
        try:
            self.repository.update_registry_item(
                "categorias",
                item_id,
                self._require_text(new_name, "Informe o nome da categoria."),
                "categoria",
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma categoria com esse nome.") from exc

    def delete_category(self, item_id: int) -> None:
        """Remove categoria do cadastro auxiliar."""
        self.repository.delete_registry_item("categorias", item_id)

    def list_people(self) -> list[RegistryItem]:
        """Lista pessoas e empresas cadastradas."""
        return self.repository.list_registry_items("pessoas")

    def add_person(self, name: str) -> RegistryItem:
        """Cadastra nova pessoa ou empresa com validacao de unicidade."""
        try:
            return self.repository.add_registry_item("pessoas", self._require_text(name, "Informe o nome da pessoa ou empresa."))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma pessoa ou empresa com esse nome.") from exc

    def update_person(self, item_id: int, new_name: str) -> None:
        """Renomeia pessoa ou empresa e propaga o novo nome para os movimentos."""
        try:
            self.repository.update_registry_item(
                "pessoas",
                item_id,
                self._require_text(new_name, "Informe o nome da pessoa ou empresa."),
                "pessoa",
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma pessoa ou empresa com esse nome.") from exc

    def delete_person(self, item_id: int) -> None:
        """Remove pessoa ou empresa do cadastro auxiliar."""
        self.repository.delete_registry_item("pessoas", item_id)

    def list_technicians(self, *, include_inactive: bool = True) -> list[Technician]:
        """Lista técnicos cadastrados, opcionalmente filtrando inativos."""
        technicians = self.repository.list_technicians()
        if include_inactive:
            return technicians
        return [item for item in technicians if item.status == "ativo"]

    def get_technician(self, technician_id: int) -> Technician:
        """Retorna um técnico específico pelo id."""
        for technician in self.repository.list_technicians():
            if technician.id == technician_id:
                return technician
        raise ValueError("Técnico não encontrado.")

    def calculate_technical_service_split(
        self,
        valor_servico: str | float,
        technicians: list[Technician],
    ) -> dict[str, object]:
        """Calcula comissão total, divisão por técnico e valor líquido da empresa."""
        service_value = self._normalize_amount(valor_servico)
        if not technicians:
            return {
                "valor_servico": round(service_value, 2),
                "percentual_total_comissao": 0.0,
                "percentual_empresa": 100.0,
                "valor_comissao_total": 0.0,
                "valor_empresa": round(service_value, 2),
                "divisao_tecnicos": [],
            }

        total_percent = round(sum(technician.percentual_comissao for technician in technicians), 2)
        if total_percent > 100:
            raise ValueError("A soma das comissões dos técnicos não pode ultrapassar 100%.")

        technician_shares = [
            (technician, round(service_value * technician.percentual_comissao / 100, 2))
            for technician in technicians
        ]
        commission_value = round(sum(share for _, share in technician_shares), 2)
        company_value = round(service_value - commission_value, 2)
        return {
            "valor_servico": round(service_value, 2),
            "percentual_total_comissao": total_percent,
            "percentual_empresa": round(100.0 - total_percent, 2),
            "valor_comissao_total": commission_value,
            "valor_empresa": company_value,
            "divisao_tecnicos": technician_shares,
        }

    def _load_service_technicians(self, technician_ids: list[int]) -> list[Technician]:
        """Valida e carrega os técnicos usados em um serviço técnico."""
        unique_ids: list[int] = []
        for technician_id in technician_ids:
            if technician_id not in unique_ids:
                unique_ids.append(technician_id)

        if not unique_ids:
            raise ValueError("Selecione ao menos um técnico ativo.")

        technicians = [self.get_technician(technician_id) for technician_id in unique_ids]
        if any(technician.status != "ativo" for technician in technicians):
            raise ValueError("Selecione apenas técnicos ativos.")

        total_percent = round(sum(technician.percentual_comissao for technician in technicians), 2)
        if total_percent > 100:
            raise ValueError("A soma das comissões dos técnicos não pode ultrapassar 100%.")
        return technicians

    def add_technician(self, nome: str, percentual_comissao: str | float, status: str) -> Technician:
        """Cadastra técnico com percentual de comissão validado."""
        technician = Technician(
            nome=self._require_text(nome, "Informe o nome do técnico."),
            percentual_comissao=self._normalize_percentage(percentual_comissao),
            status=self._normalize_technician_status(status),
        )
        try:
            return self.repository.add_technician(technician)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe um técnico com esse nome.") from exc

    def update_technician(self, technician_id: int, nome: str, percentual_comissao: str | float, status: str) -> None:
        """Atualiza técnico mantendo os percentuais históricos já usados."""
        technician = Technician(
            id=technician_id,
            nome=self._require_text(nome, "Informe o nome do técnico."),
            percentual_comissao=self._normalize_percentage(percentual_comissao),
            status=self._normalize_technician_status(status),
        )
        try:
            self.repository.update_technician(technician)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe um técnico com esse nome.") from exc

    def delete_technician(self, technician_id: int) -> None:
        """Exclui técnico do cadastro."""
        self.repository.delete_technician(technician_id)

    def _build_movement(
        self,
        *,
        tipo: str,
        valor: str | float,
        descricao: str,
        categoria: str,
        metodo: str,
        pessoa: str,
        data_movimento: str | None,
        anexo: str,
    ) -> Movement:
        """Converte entradas da UI em um objeto Movement consistente."""
        normalized_type = MovementType.from_db(tipo)
        amount = self._normalize_amount(valor)
        cleaned_description = self._require_text(descricao, "A descrição é obrigatória.")
        cleaned_category = self._require_text(categoria, "A categoria é obrigatória.")
        cleaned_person = self._require_text(pessoa, "Informe a pessoa ou empresa.")

        normalized_method = self._normalize_method(metodo)
        if normalized_method not in PAYMENT_METHODS:
            raise ValueError("Método de pagamento inválido.")

        movement_date = self._normalize_date(data_movimento) if data_movimento else self.get_active_day()
        return Movement(
            tipo=normalized_type.value,
            valor=round(amount, 2),
            descricao=cleaned_description,
            categoria=cleaned_category,
            metodo=normalized_method,
            pessoa=cleaned_person,
            data=movement_date,
            anexo=anexo.strip(),
        )

    def _register_company_cash_adjustment(
        self,
        *,
        tipo: str,
        valor: str | float,
        descricao: str,
        data_movimento: str | None,
    ) -> CompanyCashAdjustment:
        """Cria um ajuste manual auditável do caixa da empresa."""
        normalized_type = tipo.strip().lower()
        if normalized_type not in {"add_funds", "withdraw_funds"}:
            raise ValueError("Tipo de ajuste inválido.")
        amount = round(self._normalize_amount(valor), 2)
        description = self._require_text(descricao, "A descrição do ajuste é obrigatória.")
        movement_date = self._normalize_date(data_movimento) if data_movimento else date.today().isoformat()

        overview = self.get_company_cash_overview()
        balance_before = float(overview["saldo_real"])
        signed_amount = amount if normalized_type == "add_funds" else -amount
        balance_after = round(balance_before + signed_amount, 2)
        adjustment = CompanyCashAdjustment(
            tipo=normalized_type,
            valor=amount,
            descricao=description,
            data=movement_date,
            saldo_antes=balance_before,
            saldo_depois=balance_after,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        return self.repository.add_company_cash_adjustment(adjustment)

    def _history_period_bounds(self, *, year: str, month: str | None, day: str | None) -> tuple[str, str]:
        """Calcula intervalo ISO do recorte historico selecionado."""
        if day is not None and month is not None:
            current = date(int(year), int(month), int(day))
            iso = current.isoformat()
            return iso, iso

        if month is not None:
            last_day = calendar.monthrange(int(year), int(month))[1]
            return f"{year}-{month}-01", f"{year}-{month}-{last_day:02d}"

        return f"{year}-01-01", f"{year}-12-31"

    def _summarize_movements(self, movements: list[Movement]) -> dict[str, object]:
        """Resume movimentos em totais e agrupamentos para leitura analitica."""
        summary = {
            "entradas": 0.0,
            "saidas": 0.0,
            "saldo": 0.0,
            "quantidade": len(movements),
            "categorias": defaultdict(float),
            "metodos": defaultdict(float),
            "pessoas": defaultdict(float),
        }

        for movement in movements:
            if movement.movement_type is MovementType.ENTRADA:
                summary["entradas"] += movement.valor
            else:
                summary["saidas"] += movement.valor

            summary["saldo"] += movement.signed_value
            summary["categorias"][movement.categoria] += movement.valor
            summary["metodos"][movement.metodo] += movement.valor
            summary["pessoas"][movement.pessoa] += movement.valor

        summary["categorias"] = dict(sorted(summary["categorias"].items(), key=lambda item: item[1], reverse=True))
        summary["metodos"] = dict(sorted(summary["metodos"].items(), key=lambda item: item[1], reverse=True))
        summary["pessoas"] = dict(sorted(summary["pessoas"].items(), key=lambda item: item[1], reverse=True))
        return summary

    @staticmethod
    def _movement_label(movement: Movement | None) -> str:
        """Gera um rótulo amigável para maior entrada ou maior saída."""
        if movement is None:
            return "Sem dados"
        amount = f"R$ {movement.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{movement.categoria} · {amount}"

    @staticmethod
    def _top_group(movements: list[Movement], attribute: str) -> str:
        """Retorna o agrupador com maior volume financeiro."""
        if not movements:
            return "Sem dados"
        grouped: dict[str, float] = defaultdict(float)
        for movement in movements:
            grouped[getattr(movement, attribute)] += movement.valor
        name, value = max(grouped.items(), key=lambda item: item[1])
        amount = f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{name} · {amount}"

    @staticmethod
    def _top_frequency(movements: list[Movement], attribute: str) -> str:
        """Retorna o valor mais frequente de um campo."""
        if not movements:
            return "Sem dados"
        counts: dict[str, int] = defaultdict(int)
        for movement in movements:
            counts[getattr(movement, attribute)] += 1
        name, qty = max(counts.items(), key=lambda item: item[1])
        return f"{name} · {qty} registro(s)"

    @staticmethod
    def _count_services(entries: list[Movement]) -> int:
        """Conta serviços a partir das entradas técnicas e da categoria de serviços."""
        service_groups = {movement.grupo_servico for movement in entries if movement.grupo_servico and movement.papel_servico == "entrada_servico"}
        regular_services = [
            movement for movement in entries
            if not movement.grupo_servico and "servi" in movement.categoria.casefold()
        ]
        return len(service_groups) + len(regular_services)

    def _build_history_timeline(self, *, scope: str, movements: list[Movement]) -> list[dict[str, object]]:
        """Agrupa movimentos em linha do tempo adequada ao recorte atual."""
        grouped: dict[str, dict[str, float]] = defaultdict(lambda: {"entradas": 0.0, "saidas": 0.0, "saldo": 0.0})

        for movement in movements:
            if scope == "year":
                key = movement.data[5:7]
            elif scope == "month":
                key = movement.data[8:10]
            else:
                key = movement.data

            if movement.movement_type is MovementType.ENTRADA:
                grouped[key]["entradas"] += movement.valor
            else:
                grouped[key]["saidas"] += movement.valor
            grouped[key]["saldo"] += movement.signed_value

        ordered_keys = sorted(grouped.keys())
        timeline: list[dict[str, object]] = []
        for key in ordered_keys:
            item = grouped[key]
            label = key
            if scope == "year":
                label = f"{key}/{movements[0].data[:4]}" if movements else key
            elif scope == "month" and movements:
                label = f"{key}/{movements[0].data[5:7]}"
            elif scope == "day" and movements:
                label = movements[0].formatted_date
            timeline.append(
                {
                    "key": key,
                    "label": label,
                    "entradas": item["entradas"],
                    "saidas": item["saidas"],
                    "saldo": item["saldo"],
                }
            )
        return timeline

    @staticmethod
    def _history_scope_label(*, scope: str, year: str, month: str | None, day: str | None) -> str:
        """Gera rotulo amigavel do periodo em portugues."""
        if scope == "day" and month and day:
            return f"Histórico de {day}/{month}/{year}"
        if scope == "month" and month:
            return f"Histórico de {month}/{year}"
        return f"Histórico de {year}"

    @staticmethod
    def _normalize_amount(value: str | float) -> float:
        """Normaliza valor monetario vindo da UI para float positivo."""
        if isinstance(value, str):
            cleaned = value.strip()
            if "," in cleaned:
                cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = str(value)
        try:
            amount = float(cleaned)
        except ValueError as exc:
            raise ValueError("Informe um valor numérico válido.") from exc
        if amount <= 0:
            raise ValueError("O valor deve ser maior que zero.")
        return amount

    @staticmethod
    def _normalize_date(value: str | None) -> str:
        """Aceita data ISO ou brasileira e devolve ISO."""
        if not value:
            return date.today().isoformat()

        raw = value.strip()
        for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, pattern).date().isoformat()
            except ValueError:
                continue
        raise ValueError("Use a data no formato DD/MM/AAAA.")

    @staticmethod
    def _require_text(value: str, message: str) -> str:
        """Valida texto obrigatorio removendo espacos excedentes."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(message)
        return cleaned

    @staticmethod
    def _normalize_method(value: str) -> str:
        """Uniformiza aliases de metodo para a grafia persistida no sistema."""
        normalized = value.strip().lower()
        aliases = {
            "debito": "débito",
            "débito": "débito",
            "credito": "crédito",
            "crédito": "crédito",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _normalize_percentage(value: str | float) -> float:
        """Normaliza percentual de comissão para a faixa entre 0 e 100."""
        if isinstance(value, str):
            cleaned = value.strip().replace("%", "").replace(",", ".")
        else:
            cleaned = str(value)
        try:
            percentage = float(cleaned)
        except ValueError as exc:
            raise ValueError("Informe uma comissão numérica válida.") from exc
        if percentage < 0 or percentage > 100:
            raise ValueError("A comissão do técnico deve ficar entre 0 e 100.")
        return round(percentage, 2)

    @staticmethod
    def _normalize_technician_status(value: str) -> str:
        """Garante que o status do técnico esteja no conjunto permitido."""
        normalized = value.strip().lower()
        if normalized not in {"ativo", "inativo"}:
            raise ValueError("Status inválido.")
        return normalized
