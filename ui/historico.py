from __future__ import annotations
"""Tela de historico analitico do fluxo de caixa.

O historico foi organizado em duas etapas:
1. selecao do recorte por ano, mes ou dia
2. leitura detalhada do periodo em abas de resumo, analise, grafico e registros
"""

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.models import Movement, MovementType, PAYMENT_METHODS
from services.attachments import attachment_name, open_attachment
from services.cash_service import CashService
from services.excel import exportar_excel
from services.pdf import gerar_pdf
from ui.theme import COLORS, FONTS
from ui.widgets import DateMaskEntry, DetailMarqueeBar, MarqueeLabel, MetricBadge, SectionFrame, build_treeview_style


class HistoryView(ctk.CTkScrollableFrame):
    """View dedicada ao historico por ano, mes e dia.

    Esta tela concentra navegacao temporal, leitura analitica, tabela de
    registros e acoes de edicao, exclusao, anexo e exportacao.
    """

    columns = ("data", "fluxo", "categoria", "pessoa", "valor", "impacto")

    SCOPE_LABELS = {
        "year": "Ano",
        "month": "Mês",
        "day": "Dia",
    }
    SCOPE_VALUES = {label: key for key, label in SCOPE_LABELS.items()}

    MONTH_NAMES = {
        "01": "Janeiro",
        "02": "Fevereiro",
        "03": "Março",
        "04": "Abril",
        "05": "Maio",
        "06": "Junho",
        "07": "Julho",
        "08": "Agosto",
        "09": "Setembro",
        "10": "Outubro",
        "11": "Novembro",
        "12": "Dezembro",
    }
    MONTH_SHORT = {
        "01": "Jan",
        "02": "Fev",
        "03": "Mar",
        "04": "Abr",
        "05": "Mai",
        "06": "Jun",
        "07": "Jul",
        "08": "Ago",
        "09": "Set",
        "10": "Out",
        "11": "Nov",
        "12": "Dez",
    }

    SORT_FIELDS = {
        "Data": "data",
        "Valor": "valor",
        "Fluxo": "fluxo",
        "Categoria": "categoria",
        "Pessoa / empresa": "pessoa",
        "Impacto": "impacto",
    }
    COLUMN_LABELS = {
        "data": "Data",
        "fluxo": "Fluxo",
        "categoria": "Categoria",
        "pessoa": "Pessoa / empresa",
        "valor": "Valor",
        "impacto": "Impacto",
    }

    def __init__(self, master, service: CashService, on_changed: Callable[[], None] | None = None) -> None:
        """Monta a tela completa do historico e seu estado inicial."""
        super().__init__(master, fg_color="transparent")
        self.service = service
        self._on_changed = on_changed or (lambda: None)
        self.active_scope = "month"
        self.selected_year: str | None = None
        self.selected_month: str | None = None
        self.selected_day: str | None = None
        self.current_scope_data: dict[str, object] | None = None
        self.history_tree: dict[str, dict[str, list[str]]] = {}
        self.detail_visible = False
        self.selected_movement_id: int | None = None
        self._movement_map: dict[str, Movement] = {}
        self._filtered_movements: list[Movement] = []
        self._suspend_selector_events = False
        self._year_map: dict[str, str] = {}
        self._month_map: dict[str, str] = {}
        self._day_map: dict[str, str] = {}
        self.record_sort_by = "Data"
        self.record_sort_desc = True

        build_treeview_style(self)

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Histórico analítico do caixa",
            font=FONTS["title"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(
            self,
            text="Selecione um período para abrir o histórico.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 18))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self._build_selection_screen()
        self._build_detail_screen()
        self._show_selection_screen()

    def _build_selection_screen(self) -> None:
        """Cria a primeira etapa da tela: escolha simples do periodo."""
        self.selection_screen = ctk.CTkFrame(self.body, fg_color="transparent")
        self.selection_screen.grid(row=0, column=0, sticky="nsew")
        self.selection_screen.grid_columnconfigure(0, weight=1)

        card = SectionFrame(
            self.selection_screen,
            title="Selecione o período",
            subtitle="Escolha o tipo de visão e complete os campos.",
            subtitle_wraplength=980,
        )
        card.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        for column in range(4):
            card.grid_columnconfigure(column, weight=1)

        self.scope_box = self._build_selector_box(card, row=2, column=0, title="Nível de leitura")
        self.scope_selector = ctk.CTkSegmentedButton(
            self.scope_box,
            values=list(self.SCOPE_VALUES.keys()),
            command=self._handle_scope_change,
            height=42,
            corner_radius=14,
            border_width=0,
            fg_color="#dfe7f2",
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            unselected_color="#dfe7f2",
            unselected_hover_color="#cfdbeb",
            text_color=COLORS["text"],
            text_color_disabled="#93a3b5",
            font=("Segoe UI Semibold", 12),
        )
        self.scope_selector.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))

        self.year_box, self.year_menu = self._build_period_selector(card, row=2, column=1, title="Ano")
        self.month_box, self.month_menu = self._build_period_selector(card, row=2, column=2, title="Mês")
        self.day_box, self.day_menu = self._build_period_selector(card, row=2, column=3, title="Dia")

        self.selection_preview = ctk.CTkFrame(card, fg_color=COLORS["surface_alt"], corner_radius=18)
        self.selection_preview.grid(row=3, column=0, columnspan=4, sticky="ew", padx=16, pady=(4, 14))
        self.selection_preview.grid_columnconfigure(0, weight=1)

        self.selection_preview_title = ctk.CTkLabel(
            self.selection_preview,
            text="Nenhum período pronto",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            anchor="w",
            justify="left",
        )
        self.selection_preview_title.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        self.selection_preview_text = ctk.CTkLabel(
            self.selection_preview,
            text="Selecione o período para abrir a leitura analítica.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=960,
        )
        self.selection_preview_text.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=4, column=0, columnspan=4, sticky="ew", padx=16, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        self.selection_hint = DetailMarqueeBar(footer)
        self.selection_hint.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        self.open_scope_button = ctk.CTkButton(
            footer,
            text="Abrir período",
            width=180,
            height=42,
            state="disabled",
            command=lambda: self._show_scope_details(reset_tab=True),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
        )
        self.open_scope_button.grid(row=0, column=1, sticky="e")

    def _build_selector_box(self, master, *, row: int, column: int, title: str) -> ctk.CTkFrame:
        box = ctk.CTkFrame(master, fg_color=COLORS["surface_alt"], corner_radius=18)
        if column == 0:
            outer_pad = (16, 10)
        elif column == 3:
            outer_pad = (0, 16)
        else:
            outer_pad = (0, 10)
        box.grid(row=row, column=column, sticky="nsew", padx=outer_pad, pady=(0, 14))
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            box,
            text=title,
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        return box

    def _build_period_selector(self, master, *, row: int, column: int, title: str) -> tuple[ctk.CTkFrame, ctk.CTkOptionMenu]:
        box = self._build_selector_box(master, row=row, column=column, title=title)
        menu = ctk.CTkOptionMenu(
            box,
            values=["Selecione"],
            height=42,
            fg_color=COLORS["surface"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
        )
        menu.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        return box, menu

    def _build_detail_screen(self) -> None:
        """Cria a segunda etapa: leitura do periodo selecionado."""
        self.detail_screen = ctk.CTkFrame(self.body, fg_color="transparent")
        self.detail_screen.grid(row=0, column=0, sticky="nsew")
        self.detail_screen.grid_columnconfigure(0, weight=1)
        self.detail_screen.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self.detail_screen, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(1, weight=1)

        self.back_button = ctk.CTkButton(
            header,
            text=" Voltar",
            width=118,
            height=40,
            fg_color=COLORS["surface_alt"],
            hover_color="#dfe7f3",
            text_color=COLORS["text"],
            command=self._show_selection_screen,
        )
        self.back_button.grid(row=0, column=0, sticky="w", padx=(0, 14))

        title_area = ctk.CTkFrame(header, fg_color="transparent")
        title_area.grid(row=0, column=1, sticky="ew")
        title_area.grid_columnconfigure(0, weight=1)

        self.detail_title = ctk.CTkLabel(
            title_area,
            text="Leitura do período",
            font=FONTS["title"],
            text_color=COLORS["text"],
            anchor="w",
        )
        self.detail_title.grid(row=0, column=0, sticky="w")

        self.detail_subtitle = ctk.CTkLabel(
            title_area,
            text="Abra um período no menu anterior para visualizar resumo, gráfico, análise e registros.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=980,
        )
        self.detail_subtitle.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.metrics_row = ctk.CTkFrame(self.detail_screen, fg_color="transparent")
        self.metrics_row.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for column in range(4):
            self.metrics_row.grid_columnconfigure(column, weight=1)

        self.tabs = ctk.CTkTabview(
            self.detail_screen,
            fg_color="transparent",
            segmented_button_fg_color=COLORS["surface_alt"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_selected_hover_color=COLORS["primary_hover"],
            segmented_button_unselected_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        )
        self.tabs.grid(row=2, column=0, sticky="nsew")
        self.tabs.add("Resumo")
        self.tabs.add("Análise")
        self.tabs.add("Gráfico")
        self.tabs.add("Registros")

        self._build_summary_tab()
        self._build_analysis_tab()
        self._build_chart_tab()
        self._build_records_tab()

    def _build_summary_tab(self) -> None:
        tab = self.tabs.tab("Resumo")
        tab.grid_columnconfigure(0, weight=1)
        self.summary_scroll = ctk.CTkFrame(tab, fg_color="transparent")
        self.summary_scroll.grid(row=0, column=0, sticky="ew", pady=(12, 0))
        self.summary_scroll.grid_columnconfigure(0, weight=1)
        self.summary_scroll.grid_columnconfigure(1, weight=1)

    def _build_analysis_tab(self) -> None:
        tab = self.tabs.tab("Análise")
        tab.grid_columnconfigure(0, weight=1)
        self.analysis_scroll = ctk.CTkFrame(tab, fg_color="transparent")
        self.analysis_scroll.grid(row=0, column=0, sticky="ew", pady=(12, 0))
        self.analysis_scroll.grid_columnconfigure(0, weight=1)
        self.analysis_scroll.grid_columnconfigure(1, weight=1)

    def _build_chart_tab(self) -> None:
        tab = self.tabs.tab("Gráfico")
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=0)

        self.chart_frame = ctk.CTkFrame(tab, fg_color=COLORS["surface"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        self.chart_frame.grid(row=0, column=0, sticky="nsew", pady=(12, 0), padx=(0, 12))
        self.chart_frame.grid_rowconfigure(0, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        self.chart_canvas = tk.Canvas(
            self.chart_frame,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.chart_canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chart_canvas.bind("<Configure>", lambda _event: self._render_chart())

        self.chart_sidebar = ctk.CTkFrame(tab, fg_color="transparent")
        self.chart_sidebar.grid(row=0, column=1, sticky="new", pady=(12, 0))
        self.chart_sidebar.grid_columnconfigure(0, weight=1)

    def _build_records_tab(self) -> None:
        tab = self.tabs.tab("Registros")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(4, weight=1)

        filters = ctk.CTkFrame(tab, fg_color="transparent")
        filters.grid(row=0, column=0, sticky="ew", pady=(12, 10))
        filters.grid_columnconfigure(0, weight=3)
        filters.grid_columnconfigure(1, weight=2)
        filters.grid_columnconfigure(2, weight=1)
        filters.grid_columnconfigure(3, weight=1)
        filters.grid_columnconfigure(4, weight=1)

        self.record_search_entry = ctk.CTkEntry(
            filters,
            placeholder_text="Buscar categoria, pessoa ou descrição",
            height=42,
            fg_color=COLORS["surface_alt"],
            border_width=0,
        )
        self.record_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.record_search_entry.bind("<KeyRelease>", lambda _event: self._render_records())

        self.record_type_selector = ctk.CTkSegmentedButton(
            filters,
            values=["Todos", "Entradas", "Saídas"],
            command=lambda _value: self._render_records(),
        )
        self.record_type_selector.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.record_type_selector.set("Todos")

        self.record_sort_menu = ctk.CTkOptionMenu(
            filters,
            values=list(self.SORT_FIELDS.keys()),
            height=42,
            command=self._on_record_sort_changed,
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
        )
        self.record_sort_menu.grid(row=0, column=2, sticky="ew", padx=(0, 10))
        self.record_sort_menu.set(self.record_sort_by)

        self.record_order_selector = ctk.CTkSegmentedButton(
            filters,
            values=["Decrescente", "Crescente"],
            command=self._on_record_order_changed,
        )
        self.record_order_selector.grid(row=0, column=3, sticky="ew", padx=(0, 10))
        self.record_order_selector.set("Decrescente")

        ctk.CTkButton(
            filters,
            text="Limpar",
            width=96,
            height=42,
            command=self._clear_record_controls,
            fg_color=COLORS["surface_alt"],
            hover_color="#dfe7f3",
            text_color=COLORS["text"],
        ).grid(row=0, column=4, sticky="ew")

        self.records_status = ctk.CTkLabel(
            tab,
            text="Nenhum registro.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
        )
        self.records_status.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.record_detail = DetailMarqueeBar(tab)
        self.record_detail.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.record_detail.set_text("Selecione um registro.")

        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        toolbar.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(toolbar, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        self.edit_button = ctk.CTkButton(
            left,
            text="Editar registro",
            width=146,
            height=36,
            state="disabled",
            command=self._edit_selected_movement,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        )
        self.edit_button.grid(row=0, column=0, padx=(0, 10))
        self.delete_button = ctk.CTkButton(
            left,
            text="Excluir registro",
            width=146,
            height=36,
            state="disabled",
            command=self._delete_selected_movement,
            fg_color="#fee2e2",
            text_color="#a33434",
            hover_color="#fecaca",
        )
        self.delete_button.grid(row=0, column=1)

        right = ctk.CTkFrame(toolbar, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        self.open_attachment_button = ctk.CTkButton(
            right,
            text="Abrir anexo",
            width=132,
            height=36,
            state="disabled",
            command=self._open_selected_attachment,
        )
        self.open_attachment_button.grid(row=0, column=0, padx=(0, 10))
        self.export_excel_button = ctk.CTkButton(
            right,
            text="Exportar Excel",
            width=142,
            height=36,
            state="disabled",
            command=self._export_scope_excel,
        )
        self.export_excel_button.grid(row=0, column=1, padx=(0, 10))
        self.export_pdf_button = ctk.CTkButton(
            right,
            text="Exportar PDF",
            width=142,
            height=36,
            state="disabled",
            fg_color="#1d6b4f",
            hover_color="#15523d",
            command=self._export_scope_pdf,
        )
        self.export_pdf_button.grid(row=0, column=2)

        host = ctk.CTkFrame(tab, fg_color="transparent")
        host.grid(row=4, column=0, sticky="nsew")
        host.grid_columnconfigure(0, weight=3)
        host.grid_columnconfigure(1, weight=2)
        host.grid_rowconfigure(0, weight=1)

        table_host = ctk.CTkFrame(host, fg_color="transparent")
        table_host.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        table_host.grid_columnconfigure(0, weight=1)
        table_host.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_host, columns=self.columns, show="headings", style="Cash.Treeview")
        widths = {
            "data": 110,
            "fluxo": 110,
            "categoria": 190,
            "pessoa": 220,
            "valor": 120,
            "impacto": 170,
        }
        for key in self.columns:
            self.tree.heading(key, text=self.COLUMN_LABELS[key], command=lambda current=key: self._sort_records_by_column(current))
            self.tree.column(key, width=widths[key], anchor="w", stretch=True)
        self.tree.tag_configure("entrada", foreground=COLORS["success"])
        self.tree.tag_configure("saida", foreground=COLORS["danger"])

        y_scroll = ttk.Scrollbar(table_host, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_host, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._update_selected_detail)

        self.record_side = SectionFrame(
            host,
            title="Lançamento selecionado",
            subtitle="Detalhes do registro.",
            subtitle_wraplength=340,
        )
        self.record_side.grid(row=0, column=1, sticky="nsew")
        self.record_side.grid_columnconfigure(0, weight=1)

        self.record_info_labels: dict[str, ctk.CTkLabel] = {}
        fields = [
            ("data", "Data"),
            ("tipo", "Tipo"),
            ("valor", "Valor"),
            ("categoria", "Categoria"),
            ("metodo", "Método"),
            ("pessoa", "Pessoa / empresa"),
            ("descricao", "Descrição"),
            ("anexo", "Anexo"),
        ]
        base_row = 2
        for index, (key, title) in enumerate(fields):
            label_row = base_row + index * 2
            value_row = label_row + 1
            label = ctk.CTkLabel(
                self.record_side,
                text=title,
                font=FONTS["small"],
                text_color=COLORS["muted"],
                anchor="w",
            )
            label.grid(row=label_row, column=0, sticky="w", padx=20, pady=(0, 4))
            value = ctk.CTkLabel(
                self.record_side,
                text="",
                font=FONTS["body_bold"] if key != "descricao" else FONTS["body"],
                text_color=COLORS["text"],
                anchor="w",
                justify="left",
                wraplength=320,
            )
            value.grid(row=value_row, column=0, sticky="ew", padx=20, pady=(0, 12))
            self.record_info_labels[key] = value

    def refresh(self) -> None:
        """Recarrega arvore historica e atualiza a tela conforme o estado atual."""
        self.history_tree = self.service.get_history_tree()
        self._normalize_selection()
        self._populate_selector_menus()
        self._update_selection_preview()

        if self.detail_visible and self._selection_complete():
            self._load_scope_data()
        else:
            self.current_scope_data = None
            self._reset_records_state()

    def _normalize_selection(self) -> None:
        """Mantem ano, mes e dia selecionados sempre em um estado valido."""
        if not self.history_tree:
            self.selected_year = None
            self.selected_month = None
            self.selected_day = None
            return

        if self.selected_year not in self.history_tree:
            self.selected_year = next(iter(self.history_tree))

        months = self.history_tree.get(self.selected_year or "", {})
        if months:
            if self.selected_month not in months:
                self.selected_month = next(iter(months))
            days = months.get(self.selected_month or "", [])
            if days:
                if self.selected_day not in days:
                    self.selected_day = days[0]
            else:
                self.selected_day = None
        else:
            self.selected_month = None
            self.selected_day = None

        if self.active_scope == "day" and not self.selected_day:
            self.active_scope = "month" if self.selected_month else "year"
        if self.active_scope == "month" and not self.selected_month:
            self.active_scope = "year"

    def _populate_selector_menus(self) -> None:
        """Atualiza menus de ano, mes e dia de acordo com o historico existente."""
        self._suspend_selector_events = True
        try:
            self.scope_selector.set(self.SCOPE_LABELS[self.active_scope])

            years = list(self.history_tree.keys())
            self._year_map = {year: year for year in years}
            year_values = list(self._year_map.keys()) or ["Sem dados"]
            self.year_menu.configure(values=year_values, command=self._on_year_selected, state="normal" if years else "disabled")
            self.year_menu.set(self.selected_year or year_values[0])

            months = list(self.history_tree.get(self.selected_year or "", {}).keys())
            self._month_map = {self._format_month_option(month): month for month in months}
            month_values = list(self._month_map.keys()) or ["Sem meses"]
            self.month_menu.configure(
                values=month_values,
                command=self._on_month_selected,
                state="normal" if months else "disabled",
            )
            selected_month_label = self._find_display_value(self._month_map, self.selected_month) or month_values[0]
            self.month_menu.set(selected_month_label)

            days = self.history_tree.get(self.selected_year or "", {}).get(self.selected_month or "", [])
            self._day_map = {self._format_day_option(day): day for day in days}
            day_values = list(self._day_map.keys()) or ["Sem dias"]
            self.day_menu.configure(values=day_values, command=self._on_day_selected, state="normal" if days else "disabled")
            selected_day_label = self._find_display_value(self._day_map, self.selected_day) or day_values[0]
            self.day_menu.set(selected_day_label)

            self._update_selector_visibility()
            self._update_open_button()
        finally:
            self._suspend_selector_events = False

    def _update_selector_visibility(self) -> None:
        if self.active_scope == "year":
            self.month_box.grid_remove()
            self.day_box.grid_remove()
        elif self.active_scope == "month":
            self.month_box.grid()
            self.day_box.grid_remove()
        else:
            self.month_box.grid()
            self.day_box.grid()

    def _handle_scope_change(self, value: str) -> None:
        """Troca o nivel de leitura entre ano, mes e dia."""
        normalized = value.strip().lower()
        mapping = {
            "ano": "year",
            "mes": "month",
            "mês": "month",
            "m?s": "month",
            "dia": "day",
        }
        self.active_scope = mapping.get(normalized, self.SCOPE_VALUES.get(value, self.active_scope))
        if self.active_scope == "month" and not self.selected_month:
            self.active_scope = "year"
        if self.active_scope == "day" and not self.selected_day:
            self.active_scope = "month" if self.selected_month else "year"
        self._populate_selector_menus()
        self._update_selection_preview()

    def _on_year_selected(self, value: str) -> None:
        if self._suspend_selector_events or value not in self._year_map:
            return
        self.selected_year = self._year_map[value]
        months = self.history_tree.get(self.selected_year, {})
        self.selected_month = next(iter(months), None)
        days = months.get(self.selected_month or "", [])
        self.selected_day = days[0] if days else None
        self.selected_movement_id = None
        self._populate_selector_menus()
        self._update_selection_preview()
        if self.active_scope == "year":
            self._show_scope_details(reset_tab=True)

    def _on_month_selected(self, value: str) -> None:
        if self._suspend_selector_events or value not in self._month_map:
            return
        self.selected_month = self._month_map[value]
        days = self.history_tree.get(self.selected_year or "", {}).get(self.selected_month, [])
        self.selected_day = days[0] if days else None
        self.selected_movement_id = None
        self._populate_selector_menus()
        self._update_selection_preview()
        if self.active_scope == "month":
            self._show_scope_details(reset_tab=True)

    def _on_day_selected(self, value: str) -> None:
        if self._suspend_selector_events or value not in self._day_map:
            return
        self.selected_day = self._day_map[value]
        self.selected_movement_id = None
        self._update_selection_preview()
        if self.active_scope == "day":
            self._show_scope_details(reset_tab=True)

    def _show_selection_screen(self) -> None:
        """Volta da leitura detalhada para o menu inicial do historico."""
        self.detail_visible = False
        self.detail_screen.grid_remove()
        self.selection_screen.grid()
        self._scroll_to_top()

    def _show_scope_details(self, *, reset_tab: bool = False) -> None:
        """Abre a tela de leitura assim que o recorte estiver completo."""
        if not self._selection_complete():
            return
        self.detail_visible = True
        self.selection_screen.grid_remove()
        self.detail_screen.grid()
        if reset_tab:
            self.tabs.set("Resumo")
        self._load_scope_data()
        self._scroll_to_top()

    def _scroll_to_top(self) -> None:
        """Reposiciona a rolagem principal no topo da tela."""
        parent_canvas = getattr(self, "_parent_canvas", None)
        if parent_canvas is not None:
            parent_canvas.yview_moveto(0)

    def _selection_complete(self) -> bool:
        if not self.selected_year:
            return False
        if self.active_scope == "year":
            return True
        if self.active_scope == "month":
            return self.selected_month is not None
        return self.selected_month is not None and self.selected_day is not None

    def _selected_scope_kwargs(self) -> dict[str, str | None]:
        if not self.selected_year:
            return {"year": None, "month": None, "day": None}
        if self.active_scope == "day":
            return {"year": self.selected_year, "month": self.selected_month, "day": self.selected_day}
        if self.active_scope == "month":
            return {"year": self.selected_year, "month": self.selected_month, "day": None}
        return {"year": self.selected_year, "month": None, "day": None}

    def _load_scope_data(self) -> None:
        """Busca no servico o pacote do periodo e redistribui para as abas."""
        kwargs = self._selected_scope_kwargs()
        if kwargs["year"] is None:
            self.current_scope_data = None
            self._render_empty_detail()
            return

        self.current_scope_data = self.service.get_history_scope_data(**kwargs)
        self._render_detail_header()
        self._render_metric_strip()
        self._render_summary_tab()
        self._render_analysis_tab()
        self._render_chart()
        self._render_records()

    def _render_detail_header(self) -> None:
        if not self.current_scope_data:
            self._apply_chart_layout("month")
            self.detail_title.configure(text="Leitura do período")
            self.detail_subtitle.configure(text="Abra um período para visualizar os dados.")
            return

        scope = str(self.current_scope_data["scope"])
        label = str(self.current_scope_data["label"])
        subtitles = {
            "year": "Veja entradas, saídas e saldo do ano com leitura rápida.",
            "month": "Veja quanto entrou, quanto saiu e onde o dinheiro circulou no mês.",
            "day": "Veja o que entrou, o que saiu e o impacto de cada lançamento no dia.",
        }
        self.detail_title.configure(text=label)
        self.detail_subtitle.configure(text=subtitles.get(scope, "Leitura analítica do período selecionado."))

    def _render_metric_strip(self) -> None:
        self._clear_container(self.metrics_row)
        if not self.current_scope_data:
            return

        summary = self.current_scope_data["summary"]
        cards = [
            ("Saldo líquido", self._currency(float(summary["saldo"])), COLORS["primary"]),
            ("Entradas", self._currency(float(summary["entradas"])), COLORS["success"]),
            ("Saídas", self._currency(float(summary["saidas"])), COLORS["danger"]),
            ("Movimentações", str(int(summary["quantidade"])), COLORS["text"]),
        ]
        for column, (title, value, accent) in enumerate(cards):
            badge = MetricBadge(self.metrics_row, title=title, value=value, accent=accent)
            badge.grid(row=0, column=column, sticky="ew", padx=(0, 10) if column < 3 else 0)

    def _render_summary_tab(self) -> None:
        """Renderiza a aba Resumo com leitura executiva do periodo."""
        self._clear_container(self.summary_scroll)
        if not self.current_scope_data:
            self._build_info_panel(
                self.summary_scroll,
                row=0,
                column=0,
                title="Sem dados",
                body="Selecione um período para abrir o resumo.",
                columnspan=2,
            )
            return

        summary = self.current_scope_data["summary"]
        movements = list(self.current_scope_data["movements"])
        entradas = [movement for movement in movements if movement.movement_type is MovementType.ENTRADA]
        saidas = [movement for movement in movements if movement.movement_type is MovementType.SAIDA]

        self._build_info_panel(
            self.summary_scroll,
            row=0,
            column=0,
            title="Resumo do período",
            body=self._build_overview_text(summary),
            columnspan=2,
        )
        self._build_movement_group_panel(
            self.summary_scroll,
            row=1,
            column=0,
            title="Entradas",
            movements=entradas,
            accent=COLORS["success"],
            empty_text="Sem entradas neste período.",
        )
        self._build_movement_group_panel(
            self.summary_scroll,
            row=1,
            column=1,
            title="Saídas",
            movements=saidas,
            accent=COLORS["danger"],
            empty_text="Sem saídas neste período.",
        )
        self._build_info_panel(
            self.summary_scroll,
            row=2,
            column=0,
            title="Origem do dinheiro",
            body=self._build_flow_origin_text(entradas, "entrada"),
        )
        self._build_info_panel(
            self.summary_scroll,
            row=2,
            column=1,
            title="Destino do dinheiro",
            body=self._build_flow_origin_text(saidas, "saída"),
        )
        self._build_info_panel(
            self.summary_scroll,
            row=3,
            column=0,
            title="Impacto no saldo",
            body=self._build_impact_text(summary, entradas, saidas),
            columnspan=2,
        )

    def _render_analysis_tab(self) -> None:
        """Renderiza a aba Analise com diagnosticos e agrupamentos relevantes."""
        self._clear_container(self.analysis_scroll)
        if not self.current_scope_data:
            self._build_info_panel(
                self.analysis_scroll,
                row=0,
                column=0,
                title="Sem dados",
                body="Selecione um período para abrir a análise.",
                columnspan=2,
            )
            return

        movements = list(self.current_scope_data["movements"])
        timeline = list(self.current_scope_data["timeline"])
        entradas = [movement for movement in movements if movement.movement_type is MovementType.ENTRADA]
        saidas = [movement for movement in movements if movement.movement_type is MovementType.SAIDA]

        self._build_info_panel(
            self.analysis_scroll,
            row=0,
            column=0,
            title="Leitura financeira",
            body=self._build_financial_diagnostic(movements, timeline),
        )
        self._build_info_panel(
            self.analysis_scroll,
            row=0,
            column=1,
            title="Saldo do período",
            body=self._build_distribution_text(self.current_scope_data["summary"]),
        )
        self._build_info_panel(
            self.analysis_scroll,
            row=1,
            column=0,
            title="Entradas",
            body=self._build_type_analysis(entradas, "entrada"),
        )
        self._build_info_panel(
            self.analysis_scroll,
            row=1,
            column=1,
            title="Saídas",
            body=self._build_type_analysis(saidas, "saída"),
        )
        self._build_info_panel(
            self.analysis_scroll,
            row=2,
            column=0,
            title="Principais origens",
            body=self._format_rank_items(self._group_values(entradas, "categoria"), with_share=True, limit=5),
        )
        self._build_info_panel(
            self.analysis_scroll,
            row=2,
            column=1,
            title="Principais destinos",
            body=self._format_rank_items(self._group_values(saidas, "categoria"), with_share=True, limit=5),
        )

    def _render_chart(self) -> None:
        """Redesenha o gráfico conforme o recorte atual e o tamanho do canvas."""
        self.chart_canvas.delete("all")
        self._clear_container(self.chart_sidebar)
        width = max(self.chart_canvas.winfo_width(), 300)
        height = max(self.chart_canvas.winfo_height(), 240)
        if not self.current_scope_data:
            self._apply_chart_layout("month")
            self._draw_empty_canvas(width, height, "Selecione um período para montar o gráfico analítico.")
            self._build_info_panel(
                self.chart_sidebar,
                row=0,
                column=0,
                title="Leitura gráfica",
                body="Abra um período para visualizar a evolução financeira e os principais destaques visuais.",
            )
            return
        scope = str(self.current_scope_data["scope"])
        movements = list(self.current_scope_data["movements"])
        timeline = list(self.current_scope_data["timeline"])
        self._apply_chart_layout(scope)
        if scope in {"year", "month"} and timeline:
            self._draw_timeline_chart(width, height, scope, timeline)
            self._render_chart_sidebar_for_timeline(movements, timeline)
            return
        self._draw_composition_chart(width, height, movements)
        self._render_chart_sidebar_for_day(movements)
    def _apply_chart_layout(self, scope: str) -> None:
        """Ajusta a aba gráfica para aproveitar melhor a largura disponível."""
        if scope == "day":
            self.chart_frame.grid_configure(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(12, 12))
            self.chart_sidebar.grid_configure(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 0))
            self.chart_sidebar.grid_columnconfigure(0, weight=1)
            self.chart_sidebar.grid_columnconfigure(1, weight=1)
        else:
            self.chart_frame.grid_configure(row=0, column=0, columnspan=1, sticky="nsew", padx=(0, 12), pady=(12, 0))
            self.chart_sidebar.grid_configure(row=0, column=1, columnspan=1, sticky="new", pady=(12, 0))
            self.chart_sidebar.grid_columnconfigure(0, weight=1)
            self.chart_sidebar.grid_columnconfigure(1, weight=0)

    def _draw_timeline_chart(self, width: int, height: int, scope: str, timeline: list[dict[str, object]]) -> None:
        """Desenha grafico temporal para visoes anual e mensal."""
        margin_left = 74
        margin_right = 40
        margin_top = 52
        margin_bottom = 84
        baseline = height - margin_bottom
        plot_height = max(120, height - margin_top - margin_bottom)
        plot_width = max(240, width - margin_left - margin_right)
        upper_bound = max(
            max(float(item["entradas"]) for item in timeline),
            max(float(item["saidas"]) for item in timeline),
            max(abs(float(item["saldo"])) for item in timeline),
            1.0,
        )

        self.chart_canvas.create_text(
            margin_left,
            26,
            text="Fluxo do período",
            anchor="w",
            fill=COLORS["text"],
            font=("Segoe UI Semibold", 16),
        )
        subtitle = "Entradas e saídas por intervalo, com saldo líquido destacado pela linha azul."
        self.chart_canvas.create_text(
            margin_left,
            46,
            text=subtitle,
            anchor="w",
            fill=COLORS["muted"],
            font=FONTS["small"],
        )

        for step in range(5):
            y = baseline - (plot_height * step / 4)
            value = upper_bound * step / 4
            self.chart_canvas.create_line(margin_left, y, width - margin_right, y, fill="#e6edf5")
            self.chart_canvas.create_text(
                margin_left - 12,
                y,
                text=self._currency(value),
                anchor="e",
                fill=COLORS["muted"],
                font=FONTS["small"],
            )

        self.chart_canvas.create_line(margin_left, baseline, width - margin_right, baseline, fill="#9fb2c8", width=2)

        slot_width = plot_width / max(len(timeline), 1)
        bar_width = max(14, min(28, slot_width * 0.28))
        points: list[tuple[float, float]] = []

        for index, item in enumerate(timeline):
            center_x = margin_left + slot_width * index + slot_width / 2
            entradas = float(item["entradas"])
            saidas = float(item["saidas"])
            saldo = float(item["saldo"])

            entry_height = (entradas / upper_bound) * plot_height
            exit_height = (saidas / upper_bound) * plot_height

            self.chart_canvas.create_rectangle(
                center_x - bar_width - 3,
                baseline - entry_height,
                center_x - 3,
                baseline,
                fill="#29a36a",
                width=0,
            )
            self.chart_canvas.create_rectangle(
                center_x + 3,
                baseline - exit_height,
                center_x + bar_width + 3,
                baseline,
                fill="#d14b67",
                width=0,
            )

            balance_y = baseline - ((saldo + upper_bound) / (2 * upper_bound)) * plot_height
            points.append((center_x, balance_y))

            label = self._timeline_label(scope, str(item["key"]))
            self.chart_canvas.create_text(center_x, baseline + 20, text=label, fill=COLORS["muted"], font=FONTS["small"])

        for index in range(len(points) - 1):
            self.chart_canvas.create_line(
                points[index][0],
                points[index][1],
                points[index + 1][0],
                points[index + 1][1],
                fill=COLORS["primary"],
                width=3,
                smooth=True,
            )
        for x, y in points:
            self.chart_canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=COLORS["primary"], outline="")

        legend_y = height - 34
        self._draw_legend_item(legend_y, margin_left, "#29a36a", "Entradas")
        self._draw_legend_item(legend_y, margin_left + 140, "#d14b67", "Saídas")
        self._draw_legend_item(legend_y, margin_left + 268, COLORS["primary"], "Saldo")

    def _draw_composition_chart(self, width: int, height: int, movements: list[Movement]) -> None:
        """Desenha a visão diária separando entradas e saídas em blocos independentes."""
        entrada_categorias = list(self._group_values(movements, "categoria", movement_type=MovementType.ENTRADA).items())[:4]
        saida_categorias = list(self._group_values(movements, "categoria", movement_type=MovementType.SAIDA).items())[:4]
        entrada_metodos = list(self._group_values(movements, "metodo", movement_type=MovementType.ENTRADA).items())[:3]
        saida_metodos = list(self._group_values(movements, "metodo", movement_type=MovementType.SAIDA).items())[:3]
        entradas = sum(item.valor for item in movements if item.movement_type is MovementType.ENTRADA)
        saidas = sum(item.valor for item in movements if item.movement_type is MovementType.SAIDA)
        saldo = entradas - saidas
        self.chart_canvas.create_rectangle(20, 20, width - 20, height - 20, outline="#e1e9f2", width=1)
        self.chart_canvas.create_text(
            42,
            34,
            text="Fluxo do dia",
            anchor="w",
            fill=COLORS["text"],
            font=("Segoe UI Semibold", 18),
        )
        self.chart_canvas.create_text(
            42,
            58,
            text="Entradas e saídas separadas para leitura imediata.",
            anchor="w",
            fill=COLORS["muted"],
            font=FONTS["small"],
        )
        card_top = 96
        card_height = 74
        card_gap = 14
        card_width = (width - 84 - card_gap * 2) / 3
        cards = [
            ("Entradas", self._currency(entradas), COLORS["success"]),
            ("Saídas", self._currency(saidas), COLORS["danger"]),
            ("Saldo", self._currency(saldo), COLORS["primary"]),
        ]
        for index, (title, value, accent) in enumerate(cards):
            x1 = 42 + index * (card_width + card_gap)
            x2 = x1 + card_width
            self.chart_canvas.create_rectangle(x1, card_top, x2, card_top + card_height, fill="#f6f9fd", outline="#d8e2ef", width=1)
            self.chart_canvas.create_text(x1 + 16, card_top + 20, text=title, anchor="w", fill=COLORS["muted"], font=FONTS["small"])
            self.chart_canvas.create_text(x1 + 16, card_top + 50, text=value, anchor="w", fill=accent, font=("Segoe UI Semibold", 19))
        groups_top = 198
        groups_gap = 28
        column_gap = 28
        inner_width = width - 84
        left_width = max(220, (inner_width - column_gap) / 2)
        right_left = 42 + left_width + column_gap
        box_height = 170
        self._draw_rank_group(42, groups_top, 42 + left_width, groups_top + box_height, "Entradas por categoria", entrada_categorias, COLORS["success"])
        self._draw_rank_group(right_left, groups_top, width - 42, groups_top + box_height, "Saídas por categoria", saida_categorias, COLORS["danger"])
        second_top = groups_top + box_height + groups_gap
        self._draw_rank_group(42, second_top, 42 + left_width, second_top + 132, "Métodos de entrada", entrada_metodos, COLORS["success"])
        self._draw_rank_group(right_left, second_top, width - 42, second_top + 132, "Métodos de saída", saida_metodos, COLORS["danger"])

    def _draw_rank_group(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        title: str,
        items: list[tuple[str, float]],
        accent: str,
    ) -> None:
        """Desenha barras com folga vertical para leitura clara."""
        self.chart_canvas.create_text(left, top, text=title, anchor="w", fill=COLORS["text"], font=("Segoe UI Semibold", 15))
        if not items:
            self.chart_canvas.create_text(left, top + 30, text="Sem dados suficientes neste recorte.", anchor="w", fill=COLORS["muted"], font=FONTS["small"])
            return
        max_value = max(value for _, value in items) or 1.0
        row_gap = 38
        start_y = top + 34
        track_height = 14
        track_right = right - 6
        for index, (label, value) in enumerate(items):
            row_y = start_y + index * row_gap
            self.chart_canvas.create_text(left, row_y, text=self._truncate(label, 38), anchor="w", fill=COLORS["text"], font=FONTS["small"])
            self.chart_canvas.create_text(track_right, row_y, text=self._currency(value), anchor="e", fill=COLORS["muted"], font=FONTS["small"])
            track_top = row_y + 12
            self.chart_canvas.create_rectangle(left, track_top, track_right, track_top + track_height, fill="#edf2f8", width=0)
            bar_width = (track_right - left) * (value / max_value)
            self.chart_canvas.create_rectangle(left, track_top, left + bar_width, track_top + track_height, fill=accent, width=0)

    def _render_chart_sidebar_for_timeline(self, movements: list[Movement], timeline: list[dict[str, object]]) -> None:
        best = max(timeline, key=lambda item: float(item["saldo"]))
        worst = min(timeline, key=lambda item: float(item["saldo"]))

        self._build_info_panel(
            self.chart_sidebar,
            row=0,
            column=0,
            title="Como ler este gráfico",
            body=(
                "As barras verdes mostram entradas, as barras vermelhas mostram saídas "
                "e a linha azul acompanha o saldo líquido de cada intervalo."
            ),
        )
        self._build_info_panel(
            self.chart_sidebar,
            row=1,
            column=0,
            title="Melhor momento",
            body=f"{best['label']} registrou saldo de {self._currency(float(best['saldo']))}.",
        )
        self._build_info_panel(
            self.chart_sidebar,
            row=2,
            column=0,
            title="Ponto de atenção",
            body=f"{worst['label']} foi o intervalo mais pressionado, com saldo de {self._currency(float(worst['saldo']))}.",
        )
        self._build_info_panel(
            self.chart_sidebar,
            row=3,
            column=0,
            title="Categorias mais relevantes",
            body=self._format_rank_items(self._group_values(movements, "categoria"), with_share=True),
        )

    def _render_chart_sidebar_for_day(self, movements: list[Movement]) -> None:
        entradas = [movement for movement in movements if movement.movement_type is MovementType.ENTRADA]
        saidas = [movement for movement in movements if movement.movement_type is MovementType.SAIDA]
        categorias_entrada = self._group_values(entradas, "categoria")
        categorias_saida = self._group_values(saidas, "categoria")
        self._build_info_panel(
            self.chart_sidebar,
            row=0,
            column=0,
            title="Entradas",
            body=self._format_rank_items(categorias_entrada, with_share=True, limit=4),
        )
        self._build_info_panel(
            self.chart_sidebar,
            row=0,
            column=1,
            title="Saídas",
            body=self._format_rank_items(categorias_saida, with_share=True, limit=4),
        )
        self._build_info_panel(
            self.chart_sidebar,
            row=1,
            column=0,
            title="Maior entrada",
            body=self._largest_movement_text(entradas),
        )
        self._build_info_panel(
            self.chart_sidebar,
            row=1,
            column=1,
            title="Maior saída",
            body=self._largest_movement_text(saidas),
        )
        self._build_info_panel(
            self.chart_sidebar,
            row=2,
            column=0,
            title="Leitura do saldo",
            body=self._build_impact_text(self.current_scope_data["summary"], entradas, saidas),
            columnspan=2,
        )

    def _render_records(self) -> None:
        """Atualiza tabela e painel lateral de detalhes dos registros."""
        self._movement_map.clear()
        self.tree.delete(*self.tree.get_children())

        if not self.current_scope_data:
            self.records_status.configure(text="Nenhum registro carregado.")
            self.export_excel_button.configure(state="disabled")
            self.export_pdf_button.configure(state="disabled")
            self._reset_records_state()
            self._refresh_tree_headings()
            return

        movements = self._filtered_scope_movements()
        self._filtered_movements = movements
        total = len(list(self.current_scope_data["movements"]))
        self.records_status.configure(
            text=(
                f"{len(movements)} de {total} registros"
                f" · {self.record_sort_by.lower()}"
                f" ({'decrescente' if self.record_sort_desc else 'crescente'})"
            )
        )
        self.export_excel_button.configure(state="normal" if total else "disabled")
        self.export_pdf_button.configure(state="normal" if total else "disabled")
        self._refresh_tree_headings()

        for index, movement in enumerate(movements):
            item_id = str(movement.id or f"temp-{index}")
            self._movement_map[item_id] = movement
            self.tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    movement.formatted_date,
                    "+ Entrada" if movement.movement_type is MovementType.ENTRADA else "- Saída",
                    movement.categoria,
                    movement.pessoa,
                    self._currency(movement.valor),
                    self._impact_text(movement),
                ),
                tags=("entrada" if movement.movement_type is MovementType.ENTRADA else "saida",),
            )

        if movements and self.selected_movement_id is not None:
            selected_item = str(self.selected_movement_id)
            if selected_item in self._movement_map:
                self.tree.selection_set(selected_item)
                self.tree.focus(selected_item)
                self.tree.see(selected_item)
                self._update_selected_detail()
                return

        self.selected_movement_id = None
        self._reset_records_state()

    def _filtered_scope_movements(self) -> list[Movement]:
        """Aplica busca, filtro por tipo e ordenacao sobre os registros do recorte."""
        if not self.current_scope_data:
            return []

        movements = list(self.current_scope_data["movements"])
        search = self.record_search_entry.get().strip().lower()
        type_filter = self.record_type_selector.get()
        sort_field = self.SORT_FIELDS[self.record_sort_by]

        if type_filter == "Entradas":
            movements = [movement for movement in movements if movement.movement_type is MovementType.ENTRADA]
        elif type_filter == "Saídas":
            movements = [movement for movement in movements if movement.movement_type is MovementType.SAIDA]

        if search:
            movements = [
                movement
                for movement in movements
                if search in movement.descricao.lower()
                or search in movement.categoria.lower()
                or search in movement.pessoa.lower()
                or search in movement.metodo.lower()
            ]

        return sorted(movements, key=lambda movement: self._record_sort_value(movement, sort_field), reverse=self.record_sort_desc)

    def _record_sort_value(self, movement: Movement, field: str):
        if field == "data":
            return movement.data
        if field == "valor":
            return movement.valor
        if field == "fluxo":
            return movement.display_type
        if field == "categoria":
            return movement.categoria.lower()
        if field == "pessoa":
            return movement.pessoa.lower()
        if field == "impacto":
            return movement.signed_value
        return movement.data

    def _sort_records_by_column(self, column: str) -> None:
        label = self.COLUMN_LABELS[column]
        if self.record_sort_by == label:
            self.record_sort_desc = not self.record_sort_desc
        else:
            self.record_sort_by = label
            self.record_sort_desc = column in {"data", "valor"}
            self.record_sort_menu.set(label)
        self.record_order_selector.set("Decrescente" if self.record_sort_desc else "Crescente")
        self._render_records()

    def _refresh_tree_headings(self) -> None:
        for column in self.columns:
            text = self.COLUMN_LABELS[column]
            if self.SORT_FIELDS[self.record_sort_by] == column:
                text = f"{text} {'' if self.record_sort_desc else ''}"
            self.tree.heading(column, text=text, command=lambda current=column: self._sort_records_by_column(current))

    def _on_record_sort_changed(self, value: str) -> None:
        self.record_sort_by = value
        self._render_records()

    def _on_record_order_changed(self, value: str) -> None:
        self.record_sort_desc = value == "Decrescente"
        self._render_records()

    def _clear_record_controls(self) -> None:
        self.record_search_entry.delete(0, "end")
        self.record_type_selector.set("Todos")
        self.record_sort_by = "Data"
        self.record_sort_desc = True
        self.record_sort_menu.set("Data")
        self.record_order_selector.set("Decrescente")
        self._render_records()

    def _update_selected_detail(self, _event=None) -> None:
        """Sincroniza o painel lateral com a linha selecionada da tabela."""
        selection = self.tree.selection()
        if not selection:
            self.selected_movement_id = None
            self._reset_records_state()
            return

        item_id = selection[0]
        movement = self._movement_map.get(item_id)
        if movement is None:
            self.selected_movement_id = None
            self._reset_records_state()
            return

        self.selected_movement_id = movement.id
        description = (
            f"{movement.formatted_date} · {movement.display_type.capitalize()} · "
            f"{movement.pessoa} · {movement.categoria} · {self._currency(movement.valor)} · {movement.descricao}"
        )
        self.record_detail.set_text(description)
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        self.open_attachment_button.configure(state="normal" if movement.anexo else "disabled")
        self.record_info_labels["data"].configure(text=movement.formatted_date)
        self.record_info_labels["tipo"].configure(text=movement.display_type.capitalize())
        self.record_info_labels["valor"].configure(text=self._currency(movement.valor))
        self.record_info_labels["categoria"].configure(text=movement.categoria)
        self.record_info_labels["metodo"].configure(text=movement.metodo)
        self.record_info_labels["pessoa"].configure(text=movement.pessoa)
        self.record_info_labels["descricao"].configure(text=movement.descricao or "Sem descrição")
        self.record_info_labels["anexo"].configure(text=attachment_name(movement.anexo))

    def _reset_records_state(self) -> None:
        self.record_detail.set_text("Selecione um registro.")
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.open_attachment_button.configure(state="disabled")
        for key, value in self.record_info_labels.items():
            if key == "descricao":
                value.configure(text="Selecione um registro para ler a descrição completa.")
            elif key == "anexo":
                value.configure(text="Sem anexo")
            else:
                value.configure(text="")

    def _selected_movement(self) -> Movement | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._movement_map.get(selection[0])

    def _open_selected_attachment(self) -> None:
        movement = self._selected_movement()
        if movement is None:
            messagebox.showwarning("Seleção necessária", "Selecione um registro com anexo.")
            return
        try:
            open_attachment(movement.anexo)
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Anexo indisponível", str(exc))

    def _edit_selected_movement(self) -> None:
        """Abre modal de edicao para o registro atualmente selecionado."""
        movement = self._selected_movement()
        if movement is None:
            messagebox.showwarning("Seleção necessária", "Selecione um registro antes de editar.")
            return
        MovementEditorDialog(
            self.winfo_toplevel(),
            self.service,
            movement,
            on_saved=self._handle_movement_updated,
        )

    def _handle_movement_updated(self, movement: Movement) -> None:
        self.selected_movement_id = movement.id
        self._on_changed()

    def _delete_selected_movement(self) -> None:
        """Solicita confirmacao e exclui o registro selecionado."""
        movement = self._selected_movement()
        if movement is None or movement.id is None:
            messagebox.showwarning("Seleção necessária", "Selecione um registro antes de excluir.")
            return

        confirmed = messagebox.askyesno(
            "Excluir registro",
            (
                f"Deseja excluir o lançamento de {movement.formatted_date} "
                f"no valor de {self._currency(movement.valor)}?\n\n"
                "Essa ação não pode ser desfeita."
            ),
        )
        if not confirmed:
            return

        try:
            self.service.delete_movement(movement.id)
        except ValueError as exc:
            messagebox.showerror("Exclusão indisponível", str(exc))
            return

        self.selected_movement_id = None
        self._on_changed()
        messagebox.showinfo("Registro excluído", "O lançamento selecionado foi removido do histórico.")

    def _export_scope_excel(self) -> None:
        """Exporta o periodo atual para Excel no caminho escolhido pelo usuario."""
        if not self.current_scope_data:
            messagebox.showwarning("Seleção necessária", "Selecione um período antes de exportar.")
            return
        output_path = filedialog.asksaveasfilename(
            title="Salvar período em Excel",
            defaultextension=".xlsx",
            filetypes=[("Planilhas Excel", "*.xlsx")],
            initialfile=f"{self._scope_filename()}.xlsx",
        )
        if not output_path:
            return
        try:
            path = exportar_excel(
                output_path=output_path,
                movements=list(self.current_scope_data["movements"]),
                title=str(self.current_scope_data["label"]),
            )
        except OSError as exc:
            messagebox.showerror("Falha ao salvar", str(exc))
            return
        messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{path.resolve()}")

    def _export_scope_pdf(self) -> None:
        """Exporta o periodo atual para PDF no caminho escolhido pelo usuario."""
        if not self.current_scope_data:
            messagebox.showwarning("Seleção necessária", "Selecione um período antes de exportar.")
            return
        output_path = filedialog.asksaveasfilename(
            title="Salvar período em PDF",
            defaultextension=".pdf",
            filetypes=[("Arquivos PDF", "*.pdf")],
            initialfile=f"{self._scope_filename()}.pdf",
        )
        if not output_path:
            return
        try:
            path = gerar_pdf(
                output_path=output_path,
                movements=list(self.current_scope_data["movements"]),
                title=str(self.current_scope_data["label"]),
            )
        except OSError as exc:
            messagebox.showerror("Falha ao salvar", str(exc))
            return
        messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{path.resolve()}")

    def _scope_filename(self) -> str:
        if not self.current_scope_data:
            return "historico"
        scope = str(self.current_scope_data["scope"])
        year = str(self.current_scope_data["year"])
        month = str(self.current_scope_data["month"] or "")
        day = str(self.current_scope_data["day"] or "")
        if scope == "day":
            return f"historico_{day}-{month}-{year}"
        if scope == "month":
            return f"historico_{month}-{year}"
        return f"historico_{year}"

    def _render_empty_detail(self) -> None:
        self.detail_title.configure(text="Leitura do período")
        self.detail_subtitle.configure(text="Selecione um período válido para abrir o histórico.")
        self._clear_container(self.metrics_row)
        self._clear_container(self.summary_scroll)
        self._clear_container(self.analysis_scroll)
        self._clear_container(self.chart_sidebar)
        self.chart_canvas.delete("all")
        self._draw_empty_canvas(max(self.chart_canvas.winfo_width(), 300), max(self.chart_canvas.winfo_height(), 240), "Nenhum período disponível.")
        self.tree.delete(*self.tree.get_children())
        self._reset_records_state()
        self.records_status.configure(text="Nenhum registro carregado.")

    def _update_selection_preview(self) -> None:
        if not self.history_tree:
            self.selection_preview_title.configure(text="Sem histórico")
            self.selection_preview_text.configure(text="Cadastre movimentações para começar.")
            self.selection_hint.set_text("Sem dados no momento.")
            self.open_scope_button.configure(state="disabled")
            return

        label = self._pending_scope_label()
        self.selection_preview_title.configure(text=f"Pronto: {label}" if self._selection_complete() else "Escolha o período")
        self.selection_preview_text.configure(text=self._selection_description())
        self.selection_hint.set_text(self._selection_hint_text())
        self._update_open_button()

    def _update_open_button(self) -> None:
        self.open_scope_button.configure(
            state="normal" if self._selection_complete() else "disabled",
            text=f"Abrir visão {self.SCOPE_LABELS[self.active_scope].lower()}",
        )

    def _selection_description(self) -> str:
        if not self._selection_complete():
            if self.active_scope == "year":
                return "Selecione o ano."
            if self.active_scope == "month":
                return "Selecione ano e mês."
            return "Selecione ano, mês e dia."

        scope = self.active_scope
        if scope == "year":
            return "Abrirá a visão anual."
        if scope == "month":
            return "Abrirá a visão mensal."
        return "Abrirá a visão diária."

    def _selection_hint_text(self) -> str:
        if not self._selection_complete():
            return "A leitura abre ao completar a seleção."
        return f"Período preparado: {self._pending_scope_label()}."

    def _pending_scope_label(self) -> str:
        if not self.selected_year:
            return "nenhum período"
        if self.active_scope == "year":
            return self.selected_year
        if self.active_scope == "month" and self.selected_month:
            return f"{self.MONTH_NAMES.get(self.selected_month, self.selected_month)} de {self.selected_year}"
        if self.active_scope == "day" and self.selected_month and self.selected_day:
            return f"{self.selected_day}/{self.selected_month}/{self.selected_year}"
        return self.selected_year

    def _build_overview_text(self, summary: dict[str, object]) -> str:
        scope_prefix = {
            "year": "No ano selecionado",
            "month": "No mês selecionado",
            "day": "No dia selecionado",
        }[str(self.current_scope_data["scope"])]
        saldo = float(summary["saldo"])
        trend = "predomínio de entradas" if saldo > 0 else "predomínio de saídas" if saldo < 0 else "equilíbrio entre entradas e saídas"
        return (
            f"{scope_prefix}, o caixa fechou com saldo líquido de {self._currency(saldo)}.\n"
            f"Foram {int(summary['quantidade'])} movimentações, somando {self._currency(float(summary['entradas']))} em entradas "
            f"e {self._currency(float(summary['saidas']))} em saídas.\n"
            f"Leitura geral: {trend}."
        )

    def _build_distribution_text(self, summary: dict[str, object]) -> str:
        entradas = float(summary["entradas"])
        saidas = float(summary["saidas"])
        total = entradas + saidas
        if total <= 0:
            return "Sem volume financeiro suficiente para medir a distribuição do período."

        share_entradas = (entradas / total) * 100
        share_saidas = (saidas / total) * 100
        return (
            f"Entradas representam {share_entradas:.1f}% do volume financeiro do período.\n"
            f"Saídas representam {share_saidas:.1f}%.\n"
            f"O saldo líquido corresponde a {self._currency(float(summary['saldo']))}."
        )

    def _build_highlights_text(self, movements: list[Movement]) -> str:
        largest = self._largest_movement(movements)
        categories = self._group_values(movements, "categoria")
        methods = self._group_values(movements, "metodo")
        people = self._group_values(movements, "pessoa")

        parts = []
        top_category = next(iter(categories.items()), None)
        top_method = next(iter(methods.items()), None)
        top_person = next(iter(people.items()), None)
        if top_category:
            parts.append(f"Categoria dominante: {top_category[0]} ({self._currency(top_category[1])}).")
        if top_method:
            parts.append(f"Método mais usado: {top_method[0]} ({self._currency(top_method[1])}).")
        if top_person:
            parts.append(f"Maior recorrência: {top_person[0]} ({self._currency(top_person[1])}).")
        if largest:
            parts.append(
                f"Maior lançamento: {largest.display_type.capitalize()} de {self._currency(largest.valor)} "
                f"em {largest.formatted_date}."
            )
        return "\n".join(parts) if parts else "Sem destaques suficientes neste período."

    def _build_rhythm_text(self, movements: list[Movement]) -> str:
        if not movements:
            return "Sem movimentações para avaliar o ritmo do período."

        timeline = list(self.current_scope_data["timeline"])
        if timeline:
            best = max(timeline, key=lambda item: float(item["saldo"]))
            worst = min(timeline, key=lambda item: float(item["saldo"]))
            interval_text = (
                f"Melhor intervalo: {best['label']} com saldo de {self._currency(float(best['saldo']))}.\n"
                f"Ponto de atenção: {worst['label']} com saldo de {self._currency(float(worst['saldo']))}.\n"
            )
        else:
            interval_text = ""

        average_ticket = sum(movement.valor for movement in movements) / len(movements)
        return (
            f"{interval_text}"
            f"Ticket médio do período: {self._currency(average_ticket)}.\n"
            f"Primeiro lançamento: {movements[0].formatted_date}. "
            f"Último lançamento: {movements[-1].formatted_date}."
        )

    def _build_financial_diagnostic(self, movements: list[Movement], timeline: list[dict[str, object]]) -> str:
        if not movements:
            return "Sem dados para produzir o diagnóstico financeiro."

        summary = self.current_scope_data["summary"]
        saldo = float(summary["saldo"])
        average_ticket = sum(item.valor for item in movements) / len(movements)
        best_line = ""
        if timeline:
            best = max(timeline, key=lambda item: float(item["saldo"]))
            worst = min(timeline, key=lambda item: float(item["saldo"]))
            best_line = (
                f"O melhor intervalo foi {best['label']} ({self._currency(float(best['saldo']))}) "
                f"e o mais pressionado foi {worst['label']} ({self._currency(float(worst['saldo']))}).\n"
            )

        return (
            f"O período fechou em {self._currency(saldo)} de saldo líquido.\n"
            f"{best_line}"
            f"O ticket médio foi de {self._currency(average_ticket)}, o que ajuda a entender o porte dos lançamentos."
        )

    def _build_type_analysis(self, movements: list[Movement], label: str) -> str:
        if not movements:
            return f"Não houve registros de {label} neste período."

        total = sum(item.valor for item in movements)
        average = total / len(movements)
        top_category = next(iter(self._group_values(movements, "categoria").items()), None)
        top_person = next(iter(self._group_values(movements, "pessoa").items()), None)
        largest = max(movements, key=lambda item: item.valor)

        parts = [
            f"Total de {label}s: {self._currency(total)} em {len(movements)} registros.",
            f"Ticket médio: {self._currency(average)}.",
            (
                f"Categoria mais relevante: {top_category[0]} ({self._currency(top_category[1])})."
                if top_category
                else "Sem categoria dominante."
            ),
            (
                f"Maior impacto em {top_person[0]} ({self._currency(top_person[1])})."
                if top_person
                else "Sem pessoa / empresa dominante."
            ),
            f"Maior lançamento individual: {self._currency(largest.valor)} em {largest.formatted_date}.",
        ]
        return "\n".join(parts)

    def _group_values(
        self,
        movements: list[Movement],
        attribute: str,
        *,
        movement_type: MovementType | None = None,
    ) -> dict[str, float]:
        grouped: dict[str, float] = defaultdict(float)
        for movement in movements:
            if movement_type is not None and movement.movement_type is not movement_type:
                continue
            grouped[str(getattr(movement, attribute))] += movement.valor
        return dict(sorted(grouped.items(), key=lambda item: item[1], reverse=True))

    def _format_rank_items(self, items: dict[str, float], *, limit: int = 4, with_share: bool = False) -> str:
        if not items:
            return "Sem dados no período."
        total = sum(items.values()) or 1.0
        lines = []
        for index, (name, value) in enumerate(list(items.items())[:limit], start=1):
            if with_share:
                share = (value / total) * 100
                lines.append(f"{index}. {name} · {self._currency(value)} · {share:.1f}%")
            else:
                lines.append(f"{index}. {name} · {self._currency(value)}")
        return "\n".join(lines)

    def _largest_movement(self, movements: list[Movement]) -> Movement | None:
        if not movements:
            return None
        return max(movements, key=lambda movement: movement.valor)

    def _largest_movement_text(self, movements: list[Movement]) -> str:
        largest = self._largest_movement(movements)
        if largest is None:
            return "Sem dados suficientes neste período."
        return (
            f"{largest.display_type.capitalize()} de {self._currency(largest.valor)} "
            f"em {largest.formatted_date}, vinculada a {largest.pessoa}."
        )

    def _build_movement_group_panel(
        self,
        master,
        *,
        row: int,
        column: int,
        title: str,
        movements: list[Movement],
        accent: str,
        empty_text: str,
    ) -> None:
        """Cria um bloco visual com movimentações de um único tipo."""
        panel = SectionFrame(master, title=title)
        panel.grid(row=row, column=column, sticky="nsew", padx=(0, 12) if column == 0 else 0, pady=(0, 12))
        panel.grid_columnconfigure(0, weight=1)

        if not movements:
            ctk.CTkLabel(
                panel,
                text=empty_text,
                font=FONTS["body"],
                text_color=COLORS["muted"],
                anchor="w",
                justify="left",
            ).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 18))
            return

        for index, movement in enumerate(sorted(movements, key=lambda item: item.data, reverse=True)[:5], start=2):
            self._build_movement_item(panel, row=index, movement=movement, accent=accent)

    def _build_movement_item(self, master, *, row: int, movement: Movement, accent: str) -> None:
        """Desenha um cartão compacto de lançamento para leitura rápida."""
        card = ctk.CTkFrame(master, fg_color=COLORS["surface_alt"], corner_radius=16)
        card.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)

        sign = "+" if movement.movement_type is MovementType.ENTRADA else "−"
        person = movement.pessoa.strip() or "Sem pessoa"
        title = movement.categoria.strip() or movement.descricao.strip() or "Sem categoria"
        subtitle = movement.descricao.strip() if movement.descricao.strip() and movement.descricao.strip() != title else person

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 4))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text=sign,
            font=("Segoe UI Semibold", 20),
            text_color=accent,
            width=20,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text=title,
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkLabel(
            header,
            text=self._currency(movement.valor),
            font=FONTS["body_bold"],
            text_color=accent,
            anchor="e",
        ).grid(row=0, column=2, sticky="e")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            text=subtitle,
            font=FONTS["body"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            footer,
            text=movement.formatted_date,
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

    def _build_flow_origin_text(self, movements: list[Movement], label: str) -> str:
        """Resume de onde o dinheiro veio ou para onde foi."""
        if not movements:
            return f"Sem registros de {label}."

        categories = self._group_values(movements, "categoria")
        people = self._group_values(movements, "pessoa")
        methods = self._group_values(movements, "metodo")

        lines = []
        top_category = next(iter(categories.items()), None)
        top_person = next(iter(people.items()), None)
        top_method = next(iter(methods.items()), None)
        if top_category:
            lines.append(f"Categoria principal: {top_category[0]} · {self._currency(top_category[1])}")
        if top_person:
            lines.append(f"Pessoa / empresa: {top_person[0]} · {self._currency(top_person[1])}")
        if top_method:
            lines.append(f"Método: {top_method[0]} · {self._currency(top_method[1])}")
        return "\n".join(lines)

    def _build_impact_text(
        self,
        summary: dict[str, object],
        entradas: list[Movement],
        saidas: list[Movement],
    ) -> str:
        """Monta a leitura do impacto geral do período no saldo."""
        saldo = float(summary["saldo"])
        entrada_total = float(summary["entradas"])
        saida_total = float(summary["saidas"])
        largest_entry = self._largest_movement(entradas)
        largest_exit = self._largest_movement(saidas)
        lines = [
            f"Entrou {self._currency(entrada_total)} e saiu {self._currency(saida_total)}.",
            f"Saldo resultante: {self._currency(saldo)}.",
        ]
        if largest_entry:
            lines.append(f"Maior entrada: {largest_entry.categoria} · {self._currency(largest_entry.valor)}.")
        if largest_exit:
            lines.append(f"Maior saída: {largest_exit.categoria} · {self._currency(largest_exit.valor)}.")
        return "\n".join(lines)

    def _impact_text(self, movement: Movement) -> str:
        """Texto curto de impacto individual do lançamento no saldo."""
        sign = "+" if movement.movement_type is MovementType.ENTRADA else "-"
        return f"{sign} {self._currency(movement.valor)}"

    def _build_info_panel(
        self,
        master,
        *,
        row: int,
        column: int,
        title: str,
        body: str,
        columnspan: int = 1,
    ) -> None:
        panel = SectionFrame(master, title=title)
        panel.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=(0, 12) if columnspan == 1 and column == 0 else 0, pady=(0, 12))
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            panel,
            text=body,
            font=FONTS["body"],
            text_color=COLORS["text"],
            anchor="w",
            justify="left",
            wraplength=460 if columnspan == 1 else 930,
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 18))

    def _draw_empty_canvas(self, width: int, height: int, text: str) -> None:
        self.chart_canvas.create_rectangle(0, 0, width, height, fill=COLORS["surface"], width=0)
        self.chart_canvas.create_text(
            width / 2,
            height / 2,
            text=text,
            fill=COLORS["muted"],
            font=FONTS["body"],
            width=width - 80,
            justify="center",
        )

    def _draw_legend_item(self, y: float, x: float, color: str, label: str) -> None:
        self.chart_canvas.create_rectangle(x, y - 8, x + 16, y + 8, fill=color, width=0)
        self.chart_canvas.create_text(x + 24, y, text=label, anchor="w", fill=COLORS["muted"], font=FONTS["small"])

    def _timeline_label(self, scope: str, key: str) -> str:
        if scope == "year":
            return self.MONTH_SHORT.get(key, key)
        return key

    def _format_month_option(self, month: str) -> str:
        return f"{month} · {self.MONTH_NAMES.get(month, month)}"

    def _format_day_option(self, day: str) -> str:
        if not self.selected_year or not self.selected_month:
            return day
        return f"{day}/{self.selected_month}/{self.selected_year}"

    @staticmethod
    def _find_display_value(mapping: dict[str, str], selected: str | None) -> str | None:
        for display, value in mapping.items():
            if value == selected:
                return display
        return None

    @staticmethod
    def _clear_container(container) -> None:
        for child in container.winfo_children():
            child.destroy()

    @staticmethod
    def _currency(value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 1)].rstrip() + ""


class MovementEditorDialog(ctk.CTkToplevel):
    """Modal maximizado para editar um registro vindo do historico."""

    def __init__(
        self,
        master,
        service: CashService,
        movement: Movement,
        *,
        on_saved: Callable[[Movement], None],
    ) -> None:
        """Prepara formulario de edicao com os dados atuais do movimento."""
        super().__init__(master)
        self.service = service
        self.movement = movement
        self.on_saved = on_saved
        self.attachment_path = movement.anexo or ""

        self.title("Editar registro")
        self.minsize(700, 620)
        self.configure(fg_color=COLORS["bg"])
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self.after(0, self._maximize_window)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.scroll, text="Editar lançamento", font=FONTS["title"], text_color=COLORS["text"]).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        ctk.CTkLabel(
            self.scroll,
            text="Ajuste os dados do registro selecionado e salve as alterações no histórico.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            wraplength=700,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 18))

        self._build_form()
        self._populate()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_form(self) -> None:
        """Monta o formulario rolavel de edicao do registro."""
        section = SectionFrame(
            self.scroll,
            title="Dados do registro",
            subtitle="Revise tipo, valor, descrição, categoria, pessoa, data, método e anexo antes de salvar.",
            subtitle_wraplength=680,
        )
        section.grid(row=2, column=0, sticky="nsew")
        section.grid_columnconfigure(0, weight=1)
        section.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(section, text="Tipo", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=2, column=0, padx=20, sticky="w"
        )
        self.type_selector = ctk.CTkSegmentedButton(section, values=[movement.value for movement in MovementType])
        self.type_selector.grid(row=3, column=0, columnspan=2, padx=20, pady=(8, 18), sticky="ew")

        self.value_entry = self._build_entry(section, row=4, column=0, label="Valor", placeholder="0,00")
        self.description_entry = self._build_entry(section, row=4, column=1, label="Descrição", placeholder="Ex.: ajuste do lançamento")

        ctk.CTkLabel(section, text="Categoria", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=6, column=0, padx=20, sticky="w"
        )
        self.category_selector = ctk.CTkComboBox(section, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.category_selector.grid(row=7, column=0, padx=20, pady=(8, 18), sticky="ew")

        ctk.CTkLabel(section, text="Pessoa / empresa", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=6, column=1, padx=20, sticky="w"
        )
        self.person_selector = ctk.CTkComboBox(section, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.person_selector.grid(row=7, column=1, padx=20, pady=(8, 18), sticky="ew")

        ctk.CTkLabel(section, text="Data", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=8, column=0, padx=20, sticky="w"
        )
        date_row = ctk.CTkFrame(section, fg_color="transparent")
        date_row.grid(row=9, column=0, padx=20, pady=(8, 18), sticky="ew")
        date_row.grid_columnconfigure(0, weight=1)

        self.date_entry = DateMaskEntry(
            date_row,
            placeholder_text="dd/mm/aaaa",
            height=42,
            fg_color=COLORS["surface_alt"],
            border_width=0,
        )
        self.date_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            date_row,
            text="Hoje",
            width=88,
            height=38,
            command=self.date_entry.set_today,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        ).grid(row=0, column=1, padx=(10, 0))

        ctk.CTkLabel(section, text="Método", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=8, column=1, padx=20, sticky="w"
        )
        self.method_selector = ctk.CTkOptionMenu(
            section,
            values=list(PAYMENT_METHODS),
            height=42,
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
        )
        self.method_selector.grid(row=9, column=1, padx=20, pady=(8, 18), sticky="ew")

        ctk.CTkLabel(section, text="Anexo", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=10, column=0, padx=20, sticky="w"
        )
        attachment_row = ctk.CTkFrame(section, fg_color="transparent")
        attachment_row.grid(row=11, column=0, columnspan=2, padx=20, pady=(8, 18), sticky="ew")
        attachment_row.grid_columnconfigure(0, weight=1)

        self.attachment_label = MarqueeLabel(
            attachment_row,
            text="Nenhum arquivo anexado",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            height=40,
            fg_color=COLORS["surface_alt"],
            corner_radius=12,
        )
        self.attachment_label.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            attachment_row,
            text="Selecionar arquivo",
            width=160,
            height=38,
            command=self._select_attachment,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        ).grid(row=0, column=1, padx=(10, 0))

        ctk.CTkButton(
            attachment_row,
            text="Limpar",
            width=96,
            height=38,
            command=self._clear_attachment,
            fg_color="#eef3f9",
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        ).grid(row=0, column=2, padx=(10, 0))

        self.open_attachment_button = ctk.CTkButton(
            attachment_row,
            text="Abrir",
            width=88,
            height=38,
            state="disabled",
            command=self._open_current_attachment,
        )
        self.open_attachment_button.grid(row=0, column=3, padx=(10, 0))

        footer = ctk.CTkFrame(section, fg_color="transparent")
        footer.grid(row=12, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 20))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer,
            text="Cancelar",
            width=120,
            height=44,
            command=self._close,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        ).grid(row=0, column=1, padx=(0, 10))

        ctk.CTkButton(
            footer,
            text="Salvar alterações",
            width=170,
            height=44,
            command=self._save,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
        ).grid(row=0, column=2)

    def _build_entry(self, master, *, row: int, column: int, label: str, placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(master, text=label, font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=row, column=column, padx=20, sticky="w"
        )
        entry = ctk.CTkEntry(master, placeholder_text=placeholder, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        entry.grid(row=row + 1, column=column, padx=20, pady=(8, 18), sticky="ew")
        return entry

    def _populate(self) -> None:
        """Carrega no formulario os dados atuais do movimento selecionado."""
        categories = [item.nome for item in self.service.list_categories()]
        if self.movement.categoria and self.movement.categoria not in categories:
            categories.insert(0, self.movement.categoria)
        self.category_selector.configure(values=categories or [self.movement.categoria or ""])
        self.category_selector.set(self.movement.categoria)

        people = [item.nome for item in self.service.list_people()]
        if self.movement.pessoa and self.movement.pessoa not in people:
            people.insert(0, self.movement.pessoa)
        self.person_selector.configure(values=people or [self.movement.pessoa or ""])
        self.person_selector.set(self.movement.pessoa)

        methods = list(PAYMENT_METHODS)
        if self.movement.metodo and self.movement.metodo not in methods:
            methods.append(self.movement.metodo)
            self.method_selector.configure(values=methods)

        self.type_selector.set(MovementType.from_db(self.movement.tipo).value)
        self.value_entry.insert(0, self._format_amount(self.movement.valor))
        self.description_entry.insert(0, self.movement.descricao)
        self.date_entry.insert(0, self.movement.formatted_date)
        self.method_selector.set(self.movement.metodo)
        self._refresh_attachment_ui()

    def _select_attachment(self) -> None:
        selected = filedialog.askopenfilename(title="Selecionar arquivo para o registro")
        if not selected:
            return
        self.attachment_path = selected
        self._refresh_attachment_ui()

    def _clear_attachment(self) -> None:
        self.attachment_path = ""
        self._refresh_attachment_ui()

    def _open_current_attachment(self) -> None:
        try:
            open_attachment(self.attachment_path)
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Anexo indisponível", str(exc), parent=self)

    def _refresh_attachment_ui(self) -> None:
        label = Path(self.attachment_path).name if self.attachment_path else "Nenhum arquivo anexado"
        self.attachment_label.configure_text(label)
        self.open_attachment_button.configure(state="normal" if self.attachment_path else "disabled")

    def _save(self) -> None:
        """Valida e salva as alteracoes, devolvendo o movimento atualizado."""
        if self.movement.id is None:
            messagebox.showerror("Registro inválido", "Não foi possível identificar o lançamento selecionado.", parent=self)
            return

        try:
            updated = self.service.update_movement(
                self.movement.id,
                tipo=self.type_selector.get(),
                valor=self.value_entry.get(),
                descricao=self.description_entry.get(),
                categoria=self.category_selector.get(),
                metodo=self.method_selector.get(),
                pessoa=self.person_selector.get(),
                data_movimento=self.date_entry.get().strip() or None,
                anexo=self.attachment_path,
            )
        except ValueError as exc:
            messagebox.showerror("Edição inválida", str(exc), parent=self)
            return

        self.grab_release()
        self.destroy()
        self.on_saved(updated)
        messagebox.showinfo("Registro atualizado", "As alterações foram salvas com sucesso.")

    def _close(self) -> None:
        self.grab_release()
        self.destroy()

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except Exception:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            self.geometry(f"{screen_width}x{screen_height}+0+0")

    @staticmethod
    def _format_amount(value: float) -> str:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")





