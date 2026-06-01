from __future__ import annotations
"""Painel diario do fluxo ativo.

Agrupa a leitura do dia em modulos menores para deixar o uso operacional mais
claro: resumo, movimentacoes recentes e analises.
"""

from collections import defaultdict
from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from core.models import Movement, MovementType
from services.attachments import attachment_name, open_attachment
from services.cash_service import CashService
from ui.theme import COLORS, FONTS
from ui.widgets import Card, DetailMarqueeBar, MetricBadge, SectionFrame, build_treeview_style, _bind_scrollable_mousewheel, bind_treeview_mousewheel


class DashboardView(ctk.CTkScrollableFrame):
    """View principal para acompanhamento do caixa no dia ativo."""

    recent_columns = ("data", "tipo", "pessoa", "categoria", "metodo", "valor", "anexo")

    def __init__(
        self,
        master,
        service: CashService,
        on_create: Callable[[str | None], None],
        on_start_day: Callable[[], None],
    ) -> None:
        """Inicializa o painel diario e seus callbacks externos."""
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.on_create = on_create
        self.on_start_day = on_start_day
        self._movement_map: dict[str, Movement] = {}
        self._analytics_views: dict[str, dict[str, object]] = {}
        build_treeview_style(self)

        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_tabs()
        _bind_scrollable_mousewheel(self, units_per_step=4)

    def _build_header(self) -> None:
        """Cria cabecalho com status do fluxo e acoes principais."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)

        self.active_day_label = ctk.CTkLabel(
            header,
            text="",
            font=FONTS["body_bold"],
            text_color=COLORS["primary"],
        )
        self.active_day_label.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Painel diário do caixa",
            font=FONTS["title"],
            text_color=COLORS["text"],
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        ctk.CTkLabel(
            header,
            text="Resumo, movimentações e análises do dia.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            wraplength=820,
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(6, 0))

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=3, sticky="e")
        ctk.CTkButton(
            actions,
            text="Começar o dia",
            command=self.on_start_day,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            width=150,
            height=42,
            corner_radius=14,
        ).grid(row=0, column=0, padx=(0, 12))
        ctk.CTkButton(
            actions,
            text="Nova entrada",
            command=lambda: self.on_create("entrada"),
            fg_color=COLORS["success"],
            hover_color=COLORS["success"],
            width=144,
            height=42,
            corner_radius=14,
        ).grid(row=0, column=1, padx=(0, 12))
        ctk.CTkButton(
            actions,
            text="Nova saída",
            command=lambda: self.on_create("saida"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger"],
            width=144,
            height=42,
            corner_radius=14,
        ).grid(row=0, column=2)

    def _build_tabs(self) -> None:
        """Separa a tela em abas para reduzir densidade visual."""
        self.tabs = ctk.CTkTabview(
            self,
            fg_color="transparent",
            segmented_button_fg_color=COLORS["surface_alt"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_selected_hover_color=COLORS["primary_hover"],
            segmented_button_unselected_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        )
        self.tabs.grid(row=1, column=0, sticky="nsew")
        self.tabs.add("Resumo do dia")
        self.tabs.add("Movimentações")
        self.tabs.add("Análises")

        self.summary_tab = self.tabs.tab("Resumo do dia")
        self.summary_tab.grid_columnconfigure(0, weight=1)
        self.summary_tab.grid_rowconfigure(1, weight=1)

        self.movements_tab = self.tabs.tab("Movimentações")
        self.movements_tab.grid_columnconfigure(0, weight=1)
        self.movements_tab.grid_rowconfigure(0, weight=1)

        self.analytics_tab = self.tabs.tab("Análises")
        self.analytics_tab.grid_columnconfigure(0, weight=1)
        self.analytics_tab.grid_rowconfigure(0, weight=1)

        self._build_summary_tab()
        self._build_movements_tab()
        self._build_analytics_tab()

    def _build_summary_tab(self) -> None:
        """Monta a aba de resumo executivo do dia."""
        self.cards_frame = ctk.CTkFrame(self.summary_tab, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="ew", pady=(12, 18))
        for column in range(4):
            self.cards_frame.grid_columnconfigure(column, weight=1)

        self.panorama_section = SectionFrame(
            self.summary_tab,
            title="Panorama do dia",
            subtitle="Indicadores do fluxo ativo.",
            subtitle_wraplength=760,
        )
        self.panorama_section.grid(row=1, column=0, sticky="nsew")
        self.panorama_section.grid_columnconfigure(0, weight=1)
        self.panorama_stack = ctk.CTkFrame(self.panorama_section, fg_color="transparent")
        self.panorama_stack.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.panorama_stack.grid_columnconfigure(0, weight=1)
        self.panorama_stack.grid_columnconfigure(1, weight=1)

    def _build_movements_tab(self) -> None:
        """Monta a aba de movimentacoes com tabela e detalhe textual."""
        self.recent_section = SectionFrame(
            self.movements_tab,
            title="Últimas movimentações",
            subtitle="Selecione uma linha para ver os detalhes.",
            subtitle_wraplength=760,
        )
        self.recent_section.grid(row=0, column=0, sticky="nsew", pady=(12, 0))
        self.recent_section.grid_columnconfigure(0, weight=1)
        self.recent_section.grid_rowconfigure(4, weight=1)

        self.recent_detail = DetailMarqueeBar(self.recent_section)
        self.recent_detail.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.recent_detail.set_text("Selecione uma movimentação.")

        self.recent_actions = ctk.CTkFrame(self.recent_section, fg_color="transparent")
        self.recent_actions.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.recent_actions.grid_columnconfigure(0, weight=1)
        self.recent_attachment_label = ctk.CTkLabel(
            self.recent_actions,
            text="Anexo: sem anexo",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
        )
        self.recent_attachment_label.grid(row=0, column=0, sticky="ew")
        self.open_attachment_button = ctk.CTkButton(
            self.recent_actions,
            text="Abrir anexo",
            width=132,
            height=34,
            state="disabled",
            command=self._open_selected_attachment,
        )
        self.open_attachment_button.grid(row=0, column=1, padx=(12, 0))

        table_host = ctk.CTkFrame(self.recent_section, fg_color="transparent")
        table_host.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 16))
        table_host.grid_columnconfigure(0, weight=1)
        table_host.grid_rowconfigure(0, weight=1)

        self.recent_tree = ttk.Treeview(table_host, columns=self.recent_columns, show="headings", style="Cash.Treeview")
        headings = {
            "data": "Data",
            "tipo": "Tipo",
            "pessoa": "Pessoa / empresa",
            "categoria": "Categoria",
            "metodo": "Método",
            "valor": "Valor",
            "anexo": "Anexo",
        }
        widths = {
            "data": 115,
            "tipo": 105,
            "pessoa": 320,
            "categoria": 210,
            "metodo": 150,
            "valor": 130,
            "anexo": 100,
        }
        for key in self.recent_columns:
            self.recent_tree.heading(key, text=headings[key])
            self.recent_tree.column(key, width=widths[key], anchor="w", stretch=True)
        y_scroll = ttk.Scrollbar(table_host, orient="vertical", command=self.recent_tree.yview)
        x_scroll = ttk.Scrollbar(table_host, orient="horizontal", command=self.recent_tree.xview)
        self.recent_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.recent_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        bind_treeview_mousewheel(self.recent_tree, units_per_step=3)
        self.recent_tree.bind("<<TreeviewSelect>>", self._update_selected_detail)

    def _build_analytics_tab(self) -> None:
        """Cria a estrutura base da aba de analises financeiras."""
        self.analytics_tabs = ctk.CTkTabview(
            self.analytics_tab,
            fg_color="transparent",
            segmented_button_fg_color=COLORS["surface_alt"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_selected_hover_color=COLORS["primary_hover"],
            segmented_button_unselected_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        )
        self.analytics_tabs.grid(row=0, column=0, sticky="nsew", pady=(12, 0))

        self._create_analytics_panel(
            key="overview",
            tab_title="Análise geral",
            chart_title="Distribuição financeira",
            chart_subtitle="Entradas, saídas e saldo do dia.",
            summary_title="Resumo geral",
            summary_subtitle="Leitura rápida do dia.",
        )
        self._create_analytics_panel(
            key="entries",
            tab_title="Entradas",
            chart_title="Entradas do dia",
            chart_subtitle="Entradas por categoria e método.",
            summary_title="Resumo das entradas",
            summary_subtitle="Principais entradas do período.",
        )
        self._create_analytics_panel(
            key="exits",
            tab_title="Saídas",
            chart_title="Saídas do dia",
            chart_subtitle="Saídas por categoria e método.",
            summary_title="Resumo das saídas",
            summary_subtitle="Principais saídas do período.",
        )

    def _create_analytics_panel(
        self,
        *,
        key: str,
        tab_title: str,
        chart_title: str,
        chart_subtitle: str,
        summary_title: str,
        summary_subtitle: str,
    ) -> None:
        self.analytics_tabs.add(tab_title)
        tab = self.analytics_tabs.tab(tab_title)
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        chart_section = SectionFrame(tab, title=chart_title, subtitle=chart_subtitle, subtitle_wraplength=560)
        chart_section.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        chart_section.grid_columnconfigure(0, weight=1)
        chart_section.grid_rowconfigure(3, weight=1)

        metrics_frame = ctk.CTkFrame(chart_section, fg_color="transparent")
        metrics_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        for column in range(3):
            metrics_frame.grid_columnconfigure(column, weight=1)

        chart_host = ctk.CTkFrame(chart_section, fg_color="transparent")
        chart_host.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 16))

        summary_section = SectionFrame(tab, title=summary_title, subtitle=summary_subtitle, subtitle_wraplength=340)
        summary_section.grid(row=0, column=1, sticky="nsew")
        summary_section.grid_columnconfigure(0, weight=1)

        summary_stack = ctk.CTkFrame(summary_section, fg_color="transparent")
        summary_stack.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        summary_stack.grid_columnconfigure(0, weight=1)

        self._analytics_views[key] = {
            "chart_host": chart_host,
            "metrics_frame": metrics_frame,
            "summary_stack": summary_stack,
        }

    def refresh(self) -> None:
        """Recarrega o painel inteiro com base no fluxo ativo do dia."""
        active_day = self.service.get_active_day()
        self.active_day_label.configure(text=f"Fluxo ativo: {self._display_day(active_day)}")
        summary = self.service.get_summary(active_day_only=True)
        outflows = float(summary.get("saidas", summary.get("saídas", 0.0)))
        methods_summary = summary.get("metodos", summary.get("métodos", {})) or {}
        movements = self.service.list_active_day_movements()

        self._render_cards(summary, outflows)
        self._render_panorama(summary, outflows, methods_summary)
        self._render_recent(movements[:20])
        analytics_data = self._build_analytics_data(movements, summary, methods_summary)
        self._render_analytics_panels(analytics_data)

    def _render_cards(self, summary: dict[str, object], outflows: float) -> None:
        """Atualiza os cards numericos principais do topo."""
        for child in self.cards_frame.winfo_children():
            child.destroy()
        card_data = [
            ("Saldo atual", self._currency(float(summary["saldo"])), COLORS["primary"], "Consolidação do fluxo ativo"),
            ("Entradas", self._currency(float(summary["entradas"])), COLORS["success"], "Receitas registradas hoje"),
            ("Saídas", self._currency(outflows), COLORS["danger"], "Despesas lançadas hoje"),
            ("Movimentos", str(summary["quantidade"]), COLORS["text"], "Registros do dia"),
        ]
        for column, (title, value, accent, subtitle) in enumerate(card_data):
            Card(self.cards_frame, title=title, value=value, accent=accent, subtitle=subtitle).grid(
                row=0, column=column, padx=(0, 12) if column < 3 else 0, sticky="ew"
            )

    def _render_panorama(self, summary: dict[str, object], outflows: float, methods_summary: dict[str, float]) -> None:
        """Preenche a leitura textual do panorama do dia."""
        for child in self.panorama_stack.winfo_children():
            child.destroy()

        items = [
            ("Saldo do fluxo", self._currency(float(summary["saldo"])), COLORS["primary"]),
            ("Total de saídas", self._currency(outflows), COLORS["danger"]),
            ("Métodos usados", str(len(methods_summary)), COLORS["warning"]),
            ("Registros hoje", str(summary["quantidade"]), COLORS["text"]),
        ]
        for index, (title, value, accent) in enumerate(items):
            badge = ctk.CTkFrame(self.panorama_stack, fg_color=COLORS["surface_alt"], corner_radius=16)
            badge.grid(row=index // 2, column=index % 2, sticky="ew", padx=6, pady=6)
            badge.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(badge, text=title, font=FONTS["small"], text_color=COLORS["muted"]).grid(
                row=0, column=0, sticky="w", padx=14, pady=(12, 2)
            )
            ctk.CTkLabel(badge, text=value, font=("Segoe UI Semibold", 18), text_color=accent).grid(
                row=1, column=0, sticky="w", padx=14, pady=(0, 12)
            )

    def _render_recent(self, movements: list[Movement]) -> None:
        """Atualiza a tabela de ultimas movimentacoes do dia ativo."""
        self._movement_map.clear()
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)

        if not movements:
            self.recent_detail.set_text("Nenhuma movimentação registrada no fluxo ativo.")
            self.recent_attachment_label.configure(text="Anexo: sem anexo")
            self.open_attachment_button.configure(state="disabled")
            return

        for movement in movements:
            item_id = self.recent_tree.insert(
                "",
                "end",
                values=(
                    movement.formatted_date,
                    movement.display_type.capitalize(),
                    movement.pessoa,
                    movement.categoria,
                    movement.metodo,
                    self._currency(movement.valor),
                    "Sim" if movement.anexo else "Não",
                ),
            )
            self._movement_map[item_id] = movement

        first_item = self.recent_tree.get_children()
        if first_item:
            self.recent_tree.selection_set(first_item[0])
            self._update_selected_detail()

    def _update_selected_detail(self, _event=None) -> None:
        """Sincroniza detalhe textual e anexo com a linha selecionada."""
        selected = self.recent_tree.selection()
        if not selected:
            return
        movement = self._movement_map.get(selected[0])
        if movement is None:
            return
        attachment = movement.anexo if movement.anexo else "Sem anexo"
        self.recent_detail.set_text(
            f"{movement.formatted_date} | {movement.display_type.capitalize()} | {movement.pessoa} | "
            f"{movement.categoria} | {movement.metodo} | {movement.descricao} | {attachment}"
        )
        self.recent_attachment_label.configure(text=f"Anexo: {attachment_name(movement.anexo)}")
        self.open_attachment_button.configure(state="normal" if movement.anexo else "disabled")

    def _open_selected_attachment(self) -> None:
        """Abre o anexo do registro selecionado na aba de movimentacoes."""
        selected = self.recent_tree.selection()
        if not selected:
            return
        movement = self._movement_map.get(selected[0])
        if movement is None:
            return
        try:
            open_attachment(movement.anexo)
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Anexo indisponível", str(exc))

    def _build_analytics_data(
        self,
        movements: list[Movement],
        summary: dict[str, object],
        methods_summary: dict[str, float],
    ) -> dict[str, dict[str, object]]:
        """Organiza os dados base usados pelas visoes analiticas."""
        entries = [movement for movement in movements if movement.movement_type is MovementType.ENTRADA]
        exits = [movement for movement in movements if movement.movement_type is MovementType.SAIDA]

        overview_categories = dict(summary.get("categorias") or {})
        overview_methods = dict(methods_summary)

        return {
            "overview": {
                "title": "Análise geral",
                "entry_total": float(summary["entradas"]),
                "exit_total": float(summary.get("saidas", summary.get("saídas", 0.0))),
                "balance": float(summary["saldo"]),
                "movement_count": len(movements),
                "categories": overview_categories,
                "methods": overview_methods,
                "people": self._aggregate_values(movements, "pessoa"),
            },
            "entries": self._build_direction_data("Entradas", entries, COLORS["success"]),
            "exits": self._build_direction_data("Saídas", exits, COLORS["danger"]),
        }

    def _build_direction_data(self, label: str, movements: list[Movement], accent: str) -> dict[str, object]:
        total = sum(movement.valor for movement in movements)
        return {
            "title": label,
            "accent": accent,
            "total": total,
            "movement_count": len(movements),
            "categories": self._aggregate_values(movements, "categoria"),
            "methods": self._aggregate_values(movements, "metodo"),
            "people": self._aggregate_values(movements, "pessoa"),
        }

    def _aggregate_values(self, movements: list[Movement], attribute: str) -> dict[str, float]:
        grouped: dict[str, float] = defaultdict(float)
        for movement in movements:
            grouped[getattr(movement, attribute)] += movement.valor
        return dict(sorted(grouped.items(), key=lambda item: item[1], reverse=True))

    def _render_analytics_panels(self, analytics_data: dict[str, dict[str, object]]) -> None:
        """Distribui os dados analiticos entre cards, grafico e resumo textual."""
        for key, data in analytics_data.items():
            view = self._analytics_views[key]
            self._render_analytics_metrics(key, data, view["metrics_frame"])  # type: ignore[arg-type]
            self._render_analytics_chart(key, data, view["chart_host"])  # type: ignore[arg-type]
            self._render_analytics_summary(key, data, view["summary_stack"])  # type: ignore[arg-type]

    def _render_analytics_metrics(self, key: str, data: dict[str, object], frame) -> None:
        for child in frame.winfo_children():
            child.destroy()

        if key == "overview":
            metrics = [
                ("Entradas", self._currency(float(data["entry_total"])), COLORS["success"]),
                ("Saídas", self._currency(float(data["exit_total"])), COLORS["danger"]),
                ("Saldo", self._currency(float(data["balance"])), COLORS["primary"]),
            ]
        else:
            metrics = [
                ("Total", self._currency(float(data["total"])), data["accent"]),
                ("Categorias", str(len(data["categories"])), COLORS["primary"]),
                ("Métodos", str(len(data["methods"])), COLORS["warning"]),
            ]

        for index, (title, value, accent) in enumerate(metrics):
            MetricBadge(frame, title=title, value=value, accent=accent).grid(row=0, column=index, padx=6, sticky="ew")

    def _render_analytics_chart(self, key: str, data: dict[str, object], host) -> None:
        for child in host.winfo_children():
            child.destroy()

        canvas = tk.Canvas(host, bg=COLORS["surface"], highlightthickness=0, bd=0, relief="flat")
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", lambda _event, chart_key=key, chart_data=data: self._draw_canvas_chart(canvas, chart_key, chart_data))
        self.after(20, lambda chart_key=key, chart_data=data: self._draw_canvas_chart(canvas, chart_key, chart_data))

    def _draw_canvas_chart(self, canvas: tk.Canvas, key: str, data: dict[str, object]) -> None:
        width = max(canvas.winfo_width(), 520)
        height = max(canvas.winfo_height(), 280)
        canvas.delete("all")

        if key == "overview":
            self._draw_canvas_overview(canvas, width, height, data)
            return
        self._draw_canvas_direction(canvas, width, height, data)

    def _draw_canvas_overview(self, canvas: tk.Canvas, width: int, height: int, data: dict[str, object]) -> None:
        entry_total = float(data["entry_total"])
        exit_total = float(data["exit_total"])
        values = [entry_total, exit_total]
        labels = ["Entradas", "Saídas"]
        colors = [COLORS["success"], COLORS["danger"]]

        left_x = 36
        top_y = 34
        mid_x = int(width * 0.56)
        right_x = width - 36
        bottom_y = height - 34

        canvas.create_text(left_x, 18, text="Fluxo do dia", fill=COLORS["text"], anchor="w", font=("Segoe UI Semibold", 11))
        canvas.create_text(mid_x, 18, text="Participação no volume", fill=COLORS["text"], anchor="w", font=("Segoe UI Semibold", 11))

        bar_base_y = bottom_y - 28
        bar_top_y = top_y + 24
        max_value = max(max(values), 1.0)
        for step in range(5):
            y = bar_top_y + ((bar_base_y - bar_top_y) / 4) * step
            canvas.create_line(left_x, y, mid_x - 30, y, fill="#d7e1ec", dash=(3, 5))

        bar_area_width = max((mid_x - left_x) - 44, 120)
        bar_width = min(92, bar_area_width // 3)
        bar_gap = min(54, max(24, (bar_area_width - (bar_width * 2)) // 3))
        first_x = left_x + bar_gap

        for index, (label, value, color) in enumerate(zip(labels, values, colors, strict=True)):
            x1 = first_x + index * (bar_width + bar_gap)
            x2 = x1 + bar_width
            ratio = value / max_value if max_value else 0
            y1 = bar_base_y - ((bar_base_y - bar_top_y) * ratio)
            canvas.create_rectangle(x1, y1, x2, bar_base_y, fill=color, outline="")
            canvas.create_text((x1 + x2) / 2, bar_base_y + 18, text=label, fill=COLORS["text"], font=("Segoe UI", 10))
            canvas.create_text((x1 + x2) / 2, y1 - 14, text=self._currency(value), fill=COLORS["text"], font=("Segoe UI Semibold", 9))

        donut_center_x = int(mid_x + ((right_x - mid_x) * 0.46))
        donut_center_y = int((top_y + bottom_y) / 2) - 6
        radius = min(82, max(58, int((right_x - mid_x) * 0.22)))
        total = sum(values)
        self._draw_donut(
            canvas,
            center_x=donut_center_x,
            center_y=donut_center_y,
            radius=radius,
            values=values if total > 0 else [1],
            colors=colors if total > 0 else ["#d7e1ec"],
            center_title="Fluxo",
            center_value=self._currency(total) if total > 0 else "Sem dados",
        )

        legend_y = donut_center_y + radius + 18
        for index, (label, value, color) in enumerate(zip(labels, values, colors, strict=True)):
            current_y = legend_y + (index * 24)
            canvas.create_rectangle(mid_x + 18, current_y, mid_x + 30, current_y + 12, fill=color, outline="")
            canvas.create_text(mid_x + 40, current_y + 6, text=f"{label} · {self._currency(value)}", fill=COLORS["text"], anchor="w", font=("Segoe UI", 9))

    def _draw_canvas_direction(self, canvas: tk.Canvas, width: int, height: int, data: dict[str, object]) -> None:
        categories = list(dict(data["categories"]).items())[:4]
        methods = dict(data["methods"])
        accent = str(data["accent"])

        left_x = 28
        top_y = 34
        mid_x = int(width * 0.58)
        right_x = width - 34
        bottom_y = height - 28

        canvas.create_text(left_x, 18, text="Categorias com maior volume", fill=COLORS["text"], anchor="w", font=("Segoe UI Semibold", 11))
        canvas.create_text(mid_x, 18, text="Participação por método", fill=COLORS["text"], anchor="w", font=("Segoe UI Semibold", 11))

        if not categories:
            canvas.create_text(left_x, (top_y + bottom_y) / 2, text="Sem movimentações nesta aba.", fill=COLORS["muted"], anchor="w", font=("Segoe UI", 10))
        else:
            bar_left = left_x + 104
            bar_right = mid_x - 24
            max_value = max(value for _, value in categories) or 1.0
            palette = [accent, "#3f8de0", "#70afea", "#a8cff5"]

            for index, (name, value) in enumerate(categories):
                y = top_y + 20 + (index * 48)
                canvas.create_text(left_x, y + 10, text=self._truncate(name, 16), fill=COLORS["text"], anchor="w", font=("Segoe UI", 9))
                canvas.create_rectangle(bar_left, y, bar_right, y + 20, fill="#eef3f8", outline="")
                fill_right = bar_left + ((bar_right - bar_left) * (value / max_value))
                canvas.create_rectangle(bar_left, y, fill_right, y + 20, fill=palette[index % len(palette)], outline="")
                canvas.create_text(bar_right + 6, y + 10, text=self._currency(value), fill=COLORS["muted"], anchor="w", font=("Segoe UI", 9))

        method_items = list(methods.items())
        method_values = [value for _, value in method_items] if method_items else [1]
        method_labels = [name for name, _ in method_items] if method_items else ["Sem dados"]
        method_colors = [accent, "#33A06F", "#D38D28", "#D14B67", "#7F8AA3"][: len(method_values)] if method_items else ["#d7e1ec"]

        donut_center_x = int(mid_x + ((right_x - mid_x) * 0.42))
        donut_center_y = int((top_y + bottom_y) / 2) - 8
        radius = min(80, max(56, int((right_x - mid_x) * 0.22)))
        self._draw_donut(
            canvas,
            center_x=donut_center_x,
            center_y=donut_center_y,
            radius=radius,
            values=method_values,
            colors=method_colors,
            center_title=str(data["title"]),
            center_value=self._currency(float(data["total"])) if float(data["total"]) > 0 else "Sem dados",
        )

        legend_y = donut_center_y + radius + 18
        for index, (label, value) in enumerate(zip(method_labels, method_values, strict=True)):
            current_y = legend_y + (index * 22)
            canvas.create_rectangle(mid_x + 12, current_y, mid_x + 24, current_y + 12, fill=method_colors[index], outline="")
            legend_text = label if float(data["total"]) > 0 else "Sem dados"
            suffix = self._currency(value) if float(data["total"]) > 0 else ""
            canvas.create_text(mid_x + 34, current_y + 6, text=f"{legend_text} {suffix}".strip(), fill=COLORS["text"], anchor="w", font=("Segoe UI", 9))

    def _draw_donut(
        self,
        canvas: tk.Canvas,
        *,
        center_x: int,
        center_y: int,
        radius: int,
        values: list[float],
        colors: list[str],
        center_title: str,
        center_value: str,
    ) -> None:
        total = sum(values) or 1.0
        start = 90.0
        ring_width = max(16, int(radius * 0.33))
        canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            outline="#eef3f8",
            width=ring_width,
        )
        for value, color in zip(values, colors, strict=True):
            extent = -(value / total) * 360
            canvas.create_arc(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                start=start,
                extent=extent,
                style="arc",
                outline=color,
                width=ring_width,
            )
            start += extent
        canvas.create_text(center_x, center_y - 8, text=center_title, fill=COLORS["muted"], font=("Segoe UI", 9))
        canvas.create_text(center_x, center_y + 12, text=center_value, fill=COLORS["text"], font=("Segoe UI Semibold", 10), width=radius + 30)

    def _render_analytics_summary(self, key: str, data: dict[str, object], stack) -> None:
        for child in stack.winfo_children():
            child.destroy()

        if key == "overview":
            blocks = [
                (
                    "Leitura do dia",
                    self._overview_resume(
                        entry_total=float(data["entry_total"]),
                        exit_total=float(data["exit_total"]),
                        balance=float(data["balance"]),
                        movement_count=int(data["movement_count"]),
                    ),
                ),
                ("Categorias com maior volume", self._format_rank_items(list(dict(data["categories"]).items())[:3])),
                ("Métodos mais usados", self._format_rank_items(list(dict(data["methods"]).items())[:3])),
            ]
        else:
            label = str(data["title"])
            blocks = [
                (
                    f"Resumo das {label.lower()}",
                    self._direction_resume(
                        label=label,
                        total=float(data["total"]),
                        movement_count=int(data["movement_count"]),
                        categories=len(data["categories"]),
                    ),
                ),
                ("Categorias com maior volume", self._format_rank_items(list(dict(data["categories"]).items())[:3])),
                ("Pessoas com maior volume", self._format_rank_items(list(dict(data["people"]).items())[:3])),
            ]

        for row, (title, text) in enumerate(blocks):
            card = ctk.CTkFrame(stack, fg_color=COLORS["surface_alt"], corner_radius=16)
            card.grid(row=row, column=0, sticky="ew", pady=6)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=title, font=FONTS["small"], text_color=COLORS["muted"]).grid(
                row=0, column=0, sticky="w", padx=14, pady=(12, 4)
            )
            ctk.CTkLabel(
                card,
                text=text,
                font=FONTS["body"],
                text_color=COLORS["text"],
                justify="left",
                anchor="w",
                wraplength=280,
            ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

    def _overview_resume(self, *, entry_total: float, exit_total: float, balance: float, movement_count: int) -> str:
        if movement_count == 0:
            return "Nenhuma movimentação registrada no fluxo ativo até agora."
        trend = "mais entradas do que saídas" if balance > 0 else "mais saídas do que entradas" if balance < 0 else "equilíbrio entre entradas e saídas"
        return (
            f"O dia soma {movement_count} movimentos.\n"
            f"Entradas: {self._currency(entry_total)}.\n"
            f"Saídas: {self._currency(exit_total)}.\n"
            f"Leitura rápida: {trend}."
        )

    def _direction_resume(self, *, label: str, total: float, movement_count: int, categories: int) -> str:
        if movement_count == 0:
            return f"Nenhuma movimentação de {label.lower()} registrada no fluxo ativo."
        return (
            f"{movement_count} registro(s) de {label.lower()}.\n"
            f"Volume total: {self._currency(total)}.\n"
            f"Categorias ativas na aba: {categories}."
        )

    @staticmethod
    def _format_rank_items(items: list[tuple[str, float]]) -> str:
        if not items:
            return "Sem dados no fluxo ativo."
        return "\n".join(f"{index}. {name} · {DashboardView._currency(value)}" for index, (name, value) in enumerate(items, start=1))

    @staticmethod
    def _display_day(value: str) -> str:
        year, month, day = value.split("-")
        return f"{day}/{month}/{year}"

    @staticmethod
    def _currency(value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 1)].rstrip() + "…"
