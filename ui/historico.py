from __future__ import annotations

"""Tela de histórico com leitura financeira por período."""

from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
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
from ui.widgets import DateMaskEntry, SectionFrame, build_treeview_style, _bind_scrollable_mousewheel, _mousewheel_steps, bind_treeview_mousewheel


class ToggleDropdown(ctk.CTkFrame):
    """Dropdown simples com alternancia explicita de abrir/fechar."""

    NORMAL_BORDER = COLORS["border"]
    HOVER_BORDER = "#b8cae0"
    OPEN_BORDER = COLORS["primary"]
    FIELD_BG = COLORS["surface"]
    FIELD_HOVER = "#f6f9fd"

    def __init__(
        self,
        master,
        *,
        values: list[str],
        command: Callable[[str], None],
        on_toggle: Callable[["ToggleDropdown"], None],
        on_close: Callable[["ToggleDropdown"], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=self.FIELD_BG,
            corner_radius=12,
            border_width=1,
            border_color=self.NORMAL_BORDER,
        )
        self.grid_columnconfigure(0, weight=1)

        self._values = list(values)
        self._command = command
        self._on_toggle = on_toggle
        self._on_close = on_close
        self._value = self._values[0] if self._values else ""
        self._popup: ctk.CTkToplevel | None = None
        self._hovered = False

        self.content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=12)
        self.content.grid(row=0, column=0, sticky="ew")
        self.content.grid_columnconfigure(0, weight=1)

        self.value_label = ctk.CTkLabel(
            self.content,
            text=self._value,
            font=FONTS["body"],
            text_color=COLORS["text"],
            anchor="w",
            justify="left",
        )
        self.value_label.grid(row=0, column=0, sticky="ew", padx=(14, 10), pady=9)

        self.arrow_label = ctk.CTkLabel(
            self.content,
            text="▼",
            font=FONTS["body_bold"],
            text_color=COLORS["muted"],
            width=22,
            anchor="e",
            justify="right",
        )
        self.arrow_label.grid(row=0, column=1, sticky="e", padx=(0, 14), pady=9)

        for widget in (self, self.content, self.value_label, self.arrow_label):
            widget.bind("<Button-1>", self._handle_click, add="+")
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")

        self._refresh_visual_state()

    def configure(self, require_redraw: bool = False, **kwargs):  # type: ignore[override]
        values = kwargs.pop("values", None)
        command = kwargs.pop("command", None)
        if values is not None:
            self._values = list(values)
            if self._value not in self._values:
                self._value = self._values[0] if self._values else ""
            if self.is_open:
                self.close()
        if command is not None:
            self._command = command
        super().configure(require_redraw=require_redraw, **kwargs)
        self._refresh_visual_state()

    def set(self, value: str) -> None:
        self._value = value
        self._refresh_visual_state()

    def get(self) -> str:
        return self._value

    @property
    def is_open(self) -> bool:
        return self._popup is not None and self._popup.winfo_exists()

    def toggle(self) -> None:
        self._on_toggle(self)

    def _handle_click(self, _event=None) -> str:
        self.toggle()
        return "break"

    def open(self) -> None:
        if not self._values:
            return
        if self.is_open:
            return

        popup = ctk.CTkToplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(fg_color=COLORS["surface"])
        popup.bind("<Escape>", lambda _event: self.close())

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        width = max(self.winfo_width(), 220)
        popup.geometry(f"{width}x1+{x}+{y}")

        container = ctk.CTkFrame(popup, fg_color=COLORS["surface"], corner_radius=12, border_width=1, border_color="#d8e2ef")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)

        for index, value in enumerate(self._values):
            button = ctk.CTkButton(
                container,
                text=value,
                command=lambda selected=value: self._select_value(selected),
                height=38,
                corner_radius=0 if 0 < index < len(self._values) - 1 else 10,
                fg_color=COLORS["surface"],
                hover_color=COLORS["surface_alt"],
                text_color=COLORS["text"],
                font=FONTS["body"],
                anchor="w",
            )
            button.grid(row=index, column=0, sticky="ew", padx=4, pady=(4 if index == 0 else 0, 4 if index == len(self._values) - 1 else 0))

        popup.update_idletasks()
        popup.geometry(f"{width}x{container.winfo_reqheight()}+{x}+{y}")
        self._popup = popup
        self._refresh_visual_state()

    def close(self) -> None:
        popup = self._popup
        self._popup = None
        if popup is not None and popup.winfo_exists():
            popup.destroy()
        self._refresh_visual_state()
        if self._on_close is not None:
            self._on_close(self)

    def _select_value(self, value: str) -> None:
        self._value = value
        self.close()
        self._command(value)

    def _button_text(self) -> str:
        arrow = "▲" if self.is_open else "▼"
        return f"{self._value}  {arrow}".strip()

    def _refresh_button(self) -> None:
        self._refresh_visual_state()

    def _on_enter(self, _event=None) -> None:
        self._hovered = True
        self._refresh_visual_state()

    def _on_leave(self, _event=None) -> None:
        pointer_widget = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        if self._widget_in_subtree(pointer_widget):
            return
        self._hovered = False
        self._refresh_visual_state()

    def _widget_in_subtree(self, widget) -> bool:
        current = widget
        while current is not None:
            if current is self:
                return True
            current = getattr(current, "master", None)
        return False

    def _refresh_visual_state(self) -> None:
        if self.is_open:
            border_color = self.OPEN_BORDER
            field_color = self.FIELD_BG
            arrow_color = self.OPEN_BORDER
            arrow = "▲"
        elif self._hovered:
            border_color = self.HOVER_BORDER
            field_color = self.FIELD_HOVER
            arrow_color = COLORS["text"]
            arrow = "▼"
        else:
            border_color = self.NORMAL_BORDER
            field_color = self.FIELD_BG
            arrow_color = COLORS["muted"]
            arrow = "▼"

        super().configure(border_color=border_color, fg_color=field_color)
        self.value_label.configure(text=self._value, text_color=COLORS["text"])
        self.arrow_label.configure(text=arrow, text_color=arrow_color)


class HistoryView(ctk.CTkFrame):
    """Histórico financeiro por ano, mês e dia."""

    columns = ("data", "tipo", "valor", "categoria", "descricao", "pessoa", "metodo", "anexo")
    COLUMN_LABELS = {
        "data": "Data",
        "tipo": "Tipo",
        "valor": "Valor",
        "categoria": "Categoria",
        "descricao": "DescriÃ§Ã£o",
        "pessoa": "Pessoa / empresa",
        "metodo": "MÃ©todo",
        "anexo": "Anexo",
    }

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
        "Tipo": "tipo",
        "Categoria": "categoria",
        "Descrição": "descricao",
        "Pessoa / empresa": "pessoa",
        "Método": "metodo",
        "Anexo": "anexo",
    }

    def __init__(self, master, service: CashService, on_changed: Callable[[], None] | None = None) -> None:
        super().__init__(master, fg_color=COLORS["bg"])
        self.service = service
        self._on_changed = on_changed or (lambda: None)

        self.active_scope = "month"
        self.selected_year: str | None = None
        self.selected_month: str | None = None
        self.selected_day: str | None = None
        self.detail_visible = False
        self.current_scope_data: dict[str, object] | None = None
        self.history_tree: dict[str, dict[str, list[str]]] = {}
        self._filtered_movements: list[Movement] = []
        self._movement_map: dict[str, Movement] = {}
        self.selected_movement_id: int | None = None
        self._suspend_events = False
        self._active_period_dropdown: ToggleDropdown | None = None
        self.active_tab_name = "Resumo"
        self._tab_dirty: dict[str, bool] = {
            "Resumo": True,
            "Análise": True,
            "Gráfico": True,
            "Registros": True,
        }

        self.record_type_filter = "Todos"
        self.record_category_filter = "Todas as categorias"
        self.record_person_filter = "Todas as pessoas"
        self.record_method_filter = "Todos os métodos"
        self.record_sort_by: str | None = None
        self.record_sort_desc = False

        build_treeview_style(self)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            bg=COLORS["bg"],
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.viewport = ctk.CTkFrame(self.canvas, fg_color=COLORS["bg"])
        self.viewport.grid_columnconfigure(0, weight=1)
        self.viewport_window = self.canvas.create_window((0, 0), window=self.viewport, anchor="nw")

        self.viewport.bind("<Configure>", self._sync_scroll_region)
        self.canvas.bind("<Configure>", self._sync_viewport_width)
        self.body = ctk.CTkFrame(self.viewport, fg_color=COLORS["bg"])
        self.body.grid(row=0, column=0, sticky="ew")
        self.body.grid_columnconfigure(0, weight=1)

        self._build_selection_screen()
        self._build_detail_screen()
        self._show_selection_screen()

        self.refresh()
        self._bind_history_mousewheel(self)
        self._bind_history_mousewheel(self.canvas)
        self._bind_history_mousewheel(self.viewport)
        self._bind_history_mousewheel(self.body)
        self.after(0, self._bind_period_dropdown_events)

    def _sync_scroll_region(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_viewport_width(self, event) -> None:
        self.canvas.itemconfigure(self.viewport_window, width=event.width)

    def _on_mousewheel(self, event) -> str | None:
        if not self.winfo_exists():
            return None
        try:
            steps = _mousewheel_steps(event)
            if steps == 0:
                return None
            self.canvas.yview_scroll(steps * 4, "units")
            return "break"
        except tk.TclError:
            return None

    def _bind_history_mousewheel(self, widget) -> None:
        if hasattr(self, "records_tree") and (widget is self.records_tree or self._is_widget_in_subtree(widget, self.records_tree)):
            return
        try:
            if not getattr(widget, "_history_mousewheel_bound", False):
                widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
                widget.bind("<Button-4>", self._on_mousewheel, add="+")
                widget.bind("<Button-5>", self._on_mousewheel, add="+")
                widget._history_mousewheel_bound = True
        except Exception:
            return
        for child in widget.winfo_children():
            self._bind_history_mousewheel(child)

    @staticmethod
    def _is_widget_in_subtree(widget, ancestor) -> bool:
        current = widget
        while current is not None:
            if current is ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    def refresh(self) -> None:
        """Recarrega árvore de datas e visão atual."""
        self.history_tree = self.service.get_history_tree()
        self._ensure_valid_selection()
        self._refresh_selectors()

        if self.detail_visible and self.current_scope_data:
            scope = str(self.current_scope_data.get("scope", "month"))
            self.active_scope = scope
            self._open_scope(reset_tab=False)
        else:
            self._render_selection_preview()

    def _build_selection_screen(self) -> None:
        self.selection_screen = ctk.CTkFrame(self.body, fg_color=COLORS["bg"])
        self.selection_screen.grid(row=0, column=0, sticky="ew")
        self.selection_screen.grid_columnconfigure(0, weight=1)

        card = SectionFrame(self.selection_screen, title="Selecione o período")
        card.grid(row=0, column=0, sticky="ew")
        for column in range(4):
            card.grid_columnconfigure(column, weight=1)

        self.scope_box = self._selector_box(card, 2, 0, "Nível de leitura", padx=(18, 10))
        self.scope_selector = ctk.CTkSegmentedButton(
            self.scope_box,
            values=["Ano", "Mês", "Dia"],
            command=self._on_scope_change,
            height=42,
            fg_color="#dfe7f2",
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            unselected_color="#dfe7f2",
            unselected_hover_color="#cfdbeb",
            text_color=COLORS["text"],
            font=FONTS["body_bold"],
        )
        self.scope_selector.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))

        self.year_box, self.year_menu = self._period_menu(card, 2, 1, "Ano")
        self.month_box, self.month_menu = self._period_menu(card, 2, 2, "Mês")
        self.day_box, self.day_menu = self._period_menu(card, 2, 3, "Dia", padx=(0, 18))

        self.preview_box = ctk.CTkFrame(card, fg_color=COLORS["surface_alt"], corner_radius=18)
        self.preview_box.grid(row=3, column=0, columnspan=4, sticky="ew", padx=18, pady=(0, 14))
        self.preview_box.grid_columnconfigure(0, weight=1)
        self.preview_title = ctk.CTkLabel(
            self.preview_box,
            text="Selecione o período",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            anchor="w",
        )
        self.preview_title.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))
        self.preview_text = ctk.CTkLabel(
            self.preview_box,
            text="",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=980,
        )
        self.preview_text.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=4, column=0, columnspan=4, sticky="ew", padx=18, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        self.selection_hint = ctk.CTkLabel(
            footer,
            text="",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
        )
        self.selection_hint.grid(row=0, column=0, sticky="w")

        self.open_scope_button = ctk.CTkButton(
            footer,
            text="Abrir período",
            command=lambda: self._open_scope(reset_tab=True),
            width=190,
            height=42,
            state="disabled",
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
        )
        self.open_scope_button.grid(row=0, column=1, sticky="e")

    def _build_detail_screen(self) -> None:
        self.detail_screen = ctk.CTkFrame(self.body, fg_color=COLORS["bg"])
        self.detail_screen.grid(row=0, column=0, sticky="ew")
        self.detail_screen.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.detail_screen, fg_color=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.grid_columnconfigure(1, weight=1)

        self.back_button = ctk.CTkButton(
            header,
            text="← Voltar",
            width=120,
            height=40,
            fg_color=COLORS["surface_alt"],
            hover_color="#dfe7f3",
            text_color=COLORS["text"],
            command=self._show_selection_screen,
        )
        self.back_button.grid(row=0, column=0, sticky="w", padx=(0, 14))

        title_box = ctk.CTkFrame(header, fg_color=COLORS["bg"])
        title_box.grid(row=0, column=1, sticky="ew")
        title_box.grid_columnconfigure(0, weight=1)

        self.detail_title = ctk.CTkLabel(title_box, text="Leitura do período", font=FONTS["title"], text_color=COLORS["text"], anchor="w")
        self.detail_title.grid(row=0, column=0, sticky="w")
        self.detail_subtitle = ctk.CTkLabel(title_box, text="", font=FONTS["body"], text_color=COLORS["muted"], anchor="w")
        self.detail_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.tab_selector = ctk.CTkSegmentedButton(
            self.detail_screen,
            values=["Resumo", "Análise", "Gráfico", "Registros"],
            command=self._show_tab,
            height=38,
            fg_color=COLORS["surface_alt"],
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["surface_alt"],
            unselected_hover_color="#dfe7f3",
            text_color=COLORS["text"],
            font=FONTS["body_bold"],
        )
        self.tab_selector.grid(row=1, column=0, sticky="w")

        self.tab_container = ctk.CTkFrame(self.detail_screen, fg_color=COLORS["bg"])
        self.tab_container.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.tab_container.grid_columnconfigure(0, weight=1)

        self.summary_tab = ctk.CTkFrame(self.tab_container, fg_color=COLORS["bg"])
        self.summary_tab.grid(row=0, column=0, sticky="ew")
        self.summary_tab.grid_columnconfigure(0, weight=1)
        self.summary_tab.grid_columnconfigure(1, weight=1)

        self.analysis_tab = ctk.CTkFrame(self.tab_container, fg_color=COLORS["bg"])
        self.analysis_tab.grid(row=0, column=0, sticky="ew")
        self.analysis_tab.grid_columnconfigure(0, weight=1)
        self.analysis_tab.grid_columnconfigure(1, weight=1)

        self.chart_tab = ctk.CTkFrame(self.tab_container, fg_color=COLORS["bg"])
        self.chart_tab.grid(row=0, column=0, sticky="ew")
        self.chart_tab.grid_columnconfigure(0, weight=1)
        self.chart_tab.grid_columnconfigure(1, weight=1)

        self.records_tab = ctk.CTkFrame(self.tab_container, fg_color=COLORS["bg"])
        self.records_tab.grid(row=0, column=0, sticky="ew")
        self._build_records_tab()
        self.tab_frames = {
            "Resumo": self.summary_tab,
            "Análise": self.analysis_tab,
            "Gráfico": self.chart_tab,
            "Registros": self.records_tab,
        }
        self._show_tab("Resumo")

    def _build_records_tab(self) -> None:
        self.records_tab.grid_columnconfigure(0, weight=1)

        filters = SectionFrame(self.records_tab, title="Filtros")
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        for column in range(6):
            filters.grid_columnconfigure(column, weight=1)

        self.search_entry = ctk.CTkEntry(filters, height=40, placeholder_text="Descrição")
        self.search_entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(18, 10), pady=(0, 14))

        self.type_menu = self._simple_option_menu(filters, ["Todos", "Entrada", "Saída"], lambda value: setattr(self, "record_type_filter", value))
        self.type_menu.grid(row=2, column=2, sticky="ew", padx=(0, 10), pady=(0, 14))

        self.category_menu = self._simple_option_menu(filters, ["Todas as categorias"], lambda value: setattr(self, "record_category_filter", value))
        self.category_menu.grid(row=2, column=3, sticky="ew", padx=(0, 10), pady=(0, 14))

        self.person_menu = self._simple_option_menu(filters, ["Todas as pessoas"], lambda value: setattr(self, "record_person_filter", value))
        self.person_menu.grid(row=2, column=4, sticky="ew", padx=(0, 10), pady=(0, 14))

        self.method_menu = self._simple_option_menu(filters, ["Todos os métodos"], lambda value: setattr(self, "record_method_filter", value))
        self.method_menu.grid(row=2, column=5, sticky="ew", padx=(0, 18), pady=(0, 14))

        filter_actions = ctk.CTkFrame(filters, fg_color="transparent")
        filter_actions.grid(row=3, column=0, columnspan=6, sticky="ew", padx=18, pady=(0, 14))
        filter_actions.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            filter_actions,
            text="Aplicar",
            command=self._apply_record_filters,
            height=40,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            width=180,
        ).grid(row=0, column=1, sticky="e", padx=(0, 10))
        ctk.CTkButton(
            filter_actions,
            text="Limpar",
            command=self._reset_record_filters,
            height=40,
            fg_color=COLORS["surface_alt"],
            hover_color="#dfe7f3",
            text_color=COLORS["text"],
            width=180,
        ).grid(row=0, column=2, sticky="e")

        table_card = SectionFrame(self.records_tab, title="Movimentações")
        table_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(2, weight=1)

        self.records_status = ctk.CTkLabel(table_card, text="", font=FONTS["small"], text_color=COLORS["muted"], anchor="w")
        self.records_status.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 8))

        table_wrap = ctk.CTkFrame(table_card, fg_color=COLORS["surface"])
        table_wrap.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        self.records_tree = ttk.Treeview(
            table_wrap,
            columns=self.columns,
            show="headings",
            height=14,
        )
        for key, label, width in (
            ("data", "Data", 90),
            ("tipo", "Tipo", 90),
            ("valor", "Valor", 110),
            ("categoria", "Categoria", 130),
            ("descricao", "Descrição", 260),
            ("pessoa", "Pessoa / empresa", 180),
            ("metodo", "Método", 110),
            ("anexo", "Anexo", 120),
        ):
            self.records_tree.heading(key, text=label, command=lambda column=key: self._sort_records_by_column(column))
            self.records_tree.column(key, width=width, anchor="w")

        tree_y = ttk.Scrollbar(table_wrap, orient="vertical", command=self.records_tree.yview)
        tree_x = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.records_tree.xview)
        self.records_tree.configure(yscrollcommand=tree_y.set, xscrollcommand=tree_x.set)
        self.records_tree.grid(row=0, column=0, sticky="nsew")
        tree_y.grid(row=0, column=1, sticky="ns")
        tree_x.grid(row=1, column=0, sticky="ew")
        bind_treeview_mousewheel(self.records_tree, units_per_step=3)
        self.records_tree.bind("<<TreeviewSelect>>", self._handle_record_selection)
        self.records_tree.bind("<Double-1>", lambda _event: self._edit_selected_movement())

        actions = ctk.CTkFrame(self.records_tab, fg_color=COLORS["bg"])
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        for column in range(5):
            actions.grid_columnconfigure(column, weight=1)

        self.edit_button = ctk.CTkButton(actions, text="Editar registro", height=40, state="disabled", command=self._edit_selected_movement, fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.edit_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.delete_button = ctk.CTkButton(actions, text="Excluir registro", height=40, state="disabled", command=self._delete_selected_movement, fg_color=COLORS["danger"], hover_color="#a7394f")
        self.delete_button.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.open_attachment_button = ctk.CTkButton(actions, text="Abrir anexo", height=40, state="disabled", command=self._open_selected_attachment, fg_color=COLORS["surface_alt"], hover_color="#dfe7f3", text_color=COLORS["text"])
        self.open_attachment_button.grid(row=0, column=2, sticky="ew", padx=(0, 10))
        self.export_excel_button = ctk.CTkButton(actions, text="Exportar Excel", height=40, command=self._export_excel_scope, fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"])
        self.export_excel_button.grid(row=0, column=3, sticky="ew", padx=(0, 10))
        self.export_pdf_button = ctk.CTkButton(actions, text="Exportar PDF", height=40, command=self._export_pdf_scope, fg_color=COLORS["success"], hover_color="#167b4f")
        self.export_pdf_button.grid(row=0, column=4, sticky="ew")

        self.record_detail = SectionFrame(self.records_tab, title="Lançamento selecionado")
        self.record_detail.grid(row=3, column=0, sticky="ew")
        self.record_detail.grid_columnconfigure(0, weight=1)
        self.detail_fields: dict[str, ctk.CTkLabel] = {}

    def _selector_box(self, master, row: int, column: int, title: str, *, padx: tuple[int, int]) -> ctk.CTkFrame:
        box = ctk.CTkFrame(master, fg_color=COLORS["surface_alt"], corner_radius=18)
        box.grid(row=row, column=column, sticky="nsew", padx=padx, pady=(0, 14))
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text=title, font=FONTS["small"], text_color=COLORS["muted"], anchor="w").grid(row=0, column=0, sticky="w", padx=18, pady=(14, 8))
        return box

    def _period_menu(self, master, row: int, column: int, title: str, *, padx: tuple[int, int] = (0, 10)) -> tuple[ctk.CTkFrame, ToggleDropdown]:
        box = self._selector_box(master, row, column, title, padx=padx)
        menu = ToggleDropdown(
            box,
            values=["Selecione"],
            command=lambda _value: None,
            on_toggle=self._toggle_period_dropdown,
            on_close=self._on_period_dropdown_closed,
        )
        menu.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))
        return box, menu

    def _simple_option_menu(self, master, values: list[str], command: Callable[[str], None]) -> ctk.CTkOptionMenu:
        return ctk.CTkOptionMenu(
            master,
            values=values,
            command=command,
            height=40,
            corner_radius=12,
            fg_color=COLORS["surface_alt"],
            button_color="#dde7f3",
            button_hover_color="#cedbec",
            text_color=COLORS["text"],
            font=FONTS["body"],
            dropdown_fg_color=COLORS["surface"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["surface_alt"],
            anchor="w",
            dynamic_resizing=False,
        )

    def _bind_period_dropdown_events(self) -> None:
        try:
            self.winfo_toplevel().bind("<Button-1>", self._handle_period_dropdown_click, add="+")
        except tk.TclError:
            return

    def _toggle_period_dropdown(self, dropdown: ToggleDropdown) -> None:
        if self._active_period_dropdown is dropdown and dropdown.is_open:
            dropdown.close()
            self._active_period_dropdown = None
            return

        if self._active_period_dropdown is not None and self._active_period_dropdown is not dropdown:
            self._active_period_dropdown.close()

        dropdown.open()
        self._active_period_dropdown = dropdown if dropdown.is_open else None

    def _on_period_dropdown_closed(self, dropdown: ToggleDropdown) -> None:
        if self._active_period_dropdown is dropdown:
            self._active_period_dropdown = None

    def _handle_period_dropdown_click(self, event) -> None:
        dropdown = self._active_period_dropdown
        if dropdown is None or not dropdown.is_open:
            return

        x_root = getattr(event, "x_root", None)
        y_root = getattr(event, "y_root", None)
        if x_root is None or y_root is None:
            return

        if self._point_inside_widget(dropdown, x_root, y_root) or self._point_inside_widget(dropdown._popup, x_root, y_root):
            return

        dropdown.close()
        self._active_period_dropdown = None

    @staticmethod
    def _widget_in_subtree(widget, ancestor) -> bool:
        current = widget
        while current is not None:
            if current is ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    @staticmethod
    def _point_inside_widget(widget, x_root: int, y_root: int) -> bool:
        if widget is None:
            return False
        try:
            if not widget.winfo_exists():
                return False
            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            right = left + widget.winfo_width()
            bottom = top + widget.winfo_height()
        except tk.TclError:
            return False
        return left <= x_root <= right and top <= y_root <= bottom

    def _ensure_valid_selection(self) -> None:
        years = list(self.history_tree.keys())
        if not years:
            self.selected_year = None
            self.selected_month = None
            self.selected_day = None
            self._bind_history_mousewheel(self.analysis_tab)
            return

        if self.selected_year not in years:
            self.selected_year = years[0]

        months = list(self.history_tree.get(self.selected_year, {}).keys())
        if self.active_scope in {"month", "day"}:
            if months:
                if self.selected_month not in months:
                    self.selected_month = months[0]
            else:
                self.selected_month = None
        else:
            self.selected_month = None

        days = list(self.history_tree.get(self.selected_year, {}).get(self.selected_month or "", []))
        if self.active_scope == "day":
            if days:
                if self.selected_day not in days:
                    self.selected_day = days[0]
            else:
                self.selected_day = None
        else:
            self.selected_day = None

    def _refresh_selectors(self) -> None:
        if self._active_period_dropdown is not None:
            self._active_period_dropdown.close()
            self._active_period_dropdown = None
        self._suspend_events = True
        self.scope_selector.set({"year": "Ano", "month": "Mês", "day": "Dia"}[self.active_scope])

        years = list(self.history_tree.keys()) or ["Sem dados"]
        self.year_menu.configure(values=years, command=self._on_year_selected)
        self.year_menu.set(self.selected_year or years[0])

        months_raw = list(self.history_tree.get(self.selected_year or "", {}).keys())
        month_values = [self._month_display(month) for month in months_raw] or ["Selecione"]
        self.month_menu.configure(values=month_values, command=self._on_month_selected)
        self.month_menu.set(self._month_display(self.selected_month) if self.selected_month else month_values[0])

        days_raw = list(self.history_tree.get(self.selected_year or "", {}).get(self.selected_month or "", []))
        day_values = [self._day_display(day) for day in days_raw] or ["Selecione"]
        self.day_menu.configure(values=day_values, command=self._on_day_selected)
        self.day_menu.set(self._day_display(self.selected_day) if self.selected_day else day_values[0])

        if self.active_scope == "year":
            self.month_box.grid_remove()
            self.day_box.grid_remove()
        elif self.active_scope == "month":
            self.month_box.grid()
            self.day_box.grid_remove()
        else:
            self.month_box.grid()
            self.day_box.grid()

        self._suspend_events = False
        self._render_selection_preview()

    def _on_scope_change(self, value: str) -> None:
        if self._suspend_events:
            self._bind_history_mousewheel(self.chart_tab)
            return
        self.active_scope = {"Ano": "year", "Mês": "month", "Dia": "day"}[value]
        self._ensure_valid_selection()
        self._refresh_selectors()

    def _on_year_selected(self, value: str) -> None:
        if self._suspend_events or value == "Sem dados":
            self._bind_history_mousewheel(self.records_tab)
            return
        self.selected_year = value
        self._ensure_valid_selection()
        self._refresh_selectors()

    def _on_month_selected(self, value: str) -> None:
        if self._suspend_events or value == "Selecione":
            return
        self.selected_month = value.split(" · ", 1)[0]
        self._ensure_valid_selection()
        self._refresh_selectors()

    def _on_day_selected(self, value: str) -> None:
        if self._suspend_events or value == "Selecione":
            return
        self.selected_day = value.split("/", 1)[0]
        self._render_selection_preview()

    def _render_selection_preview(self) -> None:
        if not self.history_tree:
            self.preview_title.configure(text="Sem histórico")
            self.preview_text.configure(text="Ainda não há períodos salvos para leitura.")
            self.selection_hint.configure(text="Cadastre movimentações para começar.")
            self.open_scope_button.configure(state="disabled", text="Abrir período")
            return

        scope_ready = self._scope_ready()
        if not scope_ready:
            self.preview_title.configure(text="Seleção incompleta")
            self.preview_text.configure(text="Escolha o período completo para abrir a leitura financeira.")
            self.selection_hint.configure(text="Ano, mês e dia aparecem conforme o nível escolhido.")
            self.open_scope_button.configure(state="disabled", text="Abrir período")
            return

        label = self._selection_label()
        self.preview_title.configure(text=f"Pronto para abrir: {label}")
        self.preview_text.configure(text=self._selection_description())
        self.selection_hint.configure(text=f"Período preparado: {label}")
        self.open_scope_button.configure(
            state="normal",
            text=f"Abrir visão {self._scope_label_word()}",
        )

    def _scope_ready(self) -> bool:
        if not self.selected_year:
            return False
        if self.active_scope == "year":
            return True
        if self.active_scope == "month":
            return bool(self.selected_month)
        return bool(self.selected_month and self.selected_day)

    def _selection_label(self) -> str:
        if self.active_scope == "day" and self.selected_year and self.selected_month and self.selected_day:
            return f"{self.selected_day}/{self.selected_month}/{self.selected_year}"
        if self.active_scope == "month" and self.selected_year and self.selected_month:
            return f"{self.MONTH_NAMES.get(self.selected_month, self.selected_month)} de {self.selected_year}"
        return self.selected_year or "-"

    def _selection_description(self) -> str:
        if self.active_scope == "year":
            return "Leitura anual com foco em entradas, saídas, saldo, origem e destino do dinheiro."
        if self.active_scope == "month":
            return "Leitura mensal com evolução por dia, categorias principais e registros do período."
        return "Leitura diária com fechamento do caixa, origem do dinheiro, destino do dinheiro e registros completos."

    def _scope_label_word(self) -> str:
        return {"year": "ano", "month": "mês", "day": "dia"}[self.active_scope]

    def _show_selection_screen(self) -> None:
        self.detail_visible = False
        self.detail_screen.grid_remove()
        self.selection_screen.grid()
        self._bind_history_mousewheel(self.selection_screen)
        self._render_selection_preview()

    def _show_detail_screen(self) -> None:
        self.detail_visible = True
        self.selection_screen.grid_remove()
        self.detail_screen.grid()
        self._bind_history_mousewheel(self.detail_screen)
        self._bind_history_mousewheel(self.tab_container)

    def _show_tab(self, name: str) -> None:
        self.active_tab_name = name
        self.tab_selector.set(name)
        for tab_name, frame in self.tab_frames.items():
            if tab_name == name:
                frame.grid()
            else:
                frame.grid_remove()
        self._render_active_tab()

    def _open_scope(self, *, reset_tab: bool) -> None:
        if not self._scope_ready():
            return
        if self._active_period_dropdown is not None:
            self._active_period_dropdown.close()
            self._active_period_dropdown = None

        month = self.selected_month if self.active_scope in {"month", "day"} else None
        day = self.selected_day if self.active_scope == "day" else None
        self.current_scope_data = self.service.get_history_scope_data(
            year=self.selected_year,
            month=month,
            day=day,
        )
        self._mark_tabs_dirty()
        self._show_detail_screen()
        if reset_tab:
            self._show_tab("Resumo")
        else:
            self._render_scope_data()

    def _render_scope_data(self) -> None:
        if not self.current_scope_data:
            return

        label = str(self.current_scope_data["label"])
        start_date = self._display_date(str(self.current_scope_data["start_date"]))
        end_date = self._display_date(str(self.current_scope_data["end_date"]))
        summary = dict(self.current_scope_data["summary"])
        movements = list(self.current_scope_data["movements"])

        self.detail_title.configure(text=label)
        if start_date == end_date:
            self.detail_subtitle.configure(text=f"Período: {start_date}")
        else:
            self.detail_subtitle.configure(text=f"Período: {start_date} a {end_date}")
        self._render_active_tab()
        self._bind_history_mousewheel(self.detail_screen)
        self._bind_history_mousewheel(self.tab_container)

    def _mark_tabs_dirty(self) -> None:
        for key in self._tab_dirty:
            self._tab_dirty[key] = True

    def _render_active_tab(self) -> None:
        if not self.current_scope_data:
            return
        movements = list(self.current_scope_data["movements"])
        summary = dict(self.current_scope_data["summary"])
        timeline = list(self.current_scope_data["timeline"])

        if self.active_tab_name == "Resumo":
            if self._tab_dirty["Resumo"]:
                self._render_summary_tab(movements, summary)
                self._tab_dirty["Resumo"] = False
            self._bind_history_mousewheel(self.summary_tab)
            return
        if self.active_tab_name == "Análise":
            if self._tab_dirty["Análise"]:
                self._render_analysis_tab(movements, summary)
                self._tab_dirty["Análise"] = False
            return
        if self.active_tab_name == "Gráfico":
            if self._tab_dirty["Gráfico"]:
                self._render_chart_tab(movements, summary, timeline)
                self._tab_dirty["Gráfico"] = False
            return
        if self.active_tab_name == "Registros":
            if self._tab_dirty["Registros"]:
                self._render_records_tab(movements)
                self._tab_dirty["Registros"] = False
            return

    def _render_summary_tab(self, movements: list[Movement], summary: dict[str, object]) -> None:
        self._clear_container(self.summary_tab)

        entradas = self._movements_by_type(movements, MovementType.ENTRADA)
        saidas = self._movements_by_type(movements, MovementType.SAIDA)
        saldo = float(summary["saldo"])
        tone = "positivo" if saldo >= 0 else "negativo"

        metrics = self._info_card(self.summary_tab, "Resumo do período")
        metrics.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        metrics.grid_columnconfigure(0, weight=1)
        metrics.grid_columnconfigure(1, weight=1)
        metrics.grid_columnconfigure(2, weight=1)
        metrics.grid_columnconfigure(3, weight=1)
        metric_items = [
            ("Entradas", self._currency(float(summary["entradas"])), COLORS["success"]),
            ("Saídas", self._currency(float(summary["saidas"])), COLORS["danger"]),
            ("Saldo líquido", self._currency(float(summary["saldo"])), COLORS["primary"]),
            ("Movimentações", str(int(summary["quantidade"])), COLORS["text"]),
        ]
        for index, (title, value, color) in enumerate(metric_items):
            block = tk.Frame(metrics, bg=COLORS["surface_alt"], highlightbackground=COLORS["border"], highlightthickness=1, bd=0)
            block.grid(row=1, column=index, sticky="ew", padx=(18 if index == 0 else 8, 18 if index == 3 else 8), pady=(0, 14))
            tk.Label(block, text=title, font=FONTS["small"], fg=COLORS["muted"], bg=COLORS["surface_alt"], anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
            tk.Label(block, text=value, font=("Segoe UI Semibold", 18), fg=color, bg=COLORS["surface_alt"], anchor="w").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        reading = self._info_card(self.summary_tab, "Leitura do período")
        reading.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(
            reading,
            text=(
                f"No período selecionado, o caixa fechou com saldo {tone} de {self._currency(saldo)}. "
                f"As entradas somaram {self._currency(float(summary['entradas']))} e as saídas {self._currency(float(summary['saidas']))}."
            ),
            font=FONTS["body"],
            text_color=COLORS["text"],
            anchor="w",
            justify="left",
            wraplength=980,
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))

        left = self._info_card(self.summary_tab, "Destaques das entradas")
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(0, 14))
        self._fill_simple_lines(
            left,
            [
                f"Maior entrada: {self._movement_line(self._largest_movement(entradas))}",
                f"Categoria com mais entradas: {self._top_group(entradas, 'categoria')}",
            ],
        )

        right = self._info_card(self.summary_tab, "Destaques das saídas")
        right.grid(row=2, column=1, sticky="nsew", padx=(10, 0), pady=(0, 14))
        self._fill_simple_lines(
            right,
            [
                f"Maior saída: {self._movement_line(self._largest_movement(saidas))}",
                f"Categoria com mais saídas: {self._top_group(saidas, 'categoria')}",
            ],
        )

        origin = self._info_card(self.summary_tab, "Origem do dinheiro")
        origin.grid(row=3, column=0, sticky="nsew", padx=(0, 10), pady=(0, 14))
        self._fill_simple_lines(
            origin,
            [
                f"Categoria principal: {self._top_group(entradas, 'categoria')}",
                f"Pessoa / empresa: {self._top_group(entradas, 'pessoa')}",
                f"Método principal: {self._top_group(entradas, 'metodo')}",
            ],
        )

        destination = self._info_card(self.summary_tab, "Destino do dinheiro")
        destination.grid(row=3, column=1, sticky="nsew", padx=(10, 0), pady=(0, 14))
        self._fill_simple_lines(
            destination,
            [
                f"Categoria principal: {self._top_group(saidas, 'categoria')}",
                f"Pessoa / empresa: {self._top_group(saidas, 'pessoa')}",
                f"Método principal: {self._top_group(saidas, 'metodo')}",
            ],
        )

        closure = self._info_card(self.summary_tab, "Síntese do fechamento")
        closure.grid(row=4, column=0, columnspan=2, sticky="ew")
        self._fill_simple_lines(
            closure,
            [
                f"Entradas: {self._currency(float(summary['entradas']))}",
                f"Saídas: {self._currency(float(summary['saidas']))}",
                f"Saldo resultante: {self._currency(float(summary['saldo']))}",
                f"Dia com maior movimento: {self._day_with_highest_volume(list(self.current_scope_data['timeline']))}",
            ],
        )
        self._bind_history_mousewheel(self.summary_tab)

    def _render_analysis_tab(self, movements: list[Movement], summary: dict[str, object]) -> None:
        self._clear_container(self.analysis_tab)

        entradas = self._movements_by_type(movements, MovementType.ENTRADA)
        saidas = self._movements_by_type(movements, MovementType.SAIDA)
        total_entradas = float(summary["entradas"])
        total_saidas = float(summary["saidas"])
        ratio = (total_saidas / total_entradas * 100) if total_entradas else 0.0
        avg_entry = (total_entradas / len(entradas)) if entradas else 0.0
        avg_exit = (total_saidas / len(saidas)) if saidas else 0.0

        items = [
            ("Saldo líquido", self._currency(float(summary["saldo"])), COLORS["primary"]),
            ("Saídas / entradas", f"{ratio:.1f}%".replace(".", ","), COLORS["warning"]),
            ("Média de entrada", self._currency(avg_entry), COLORS["success"]),
            ("Média de saída", self._currency(avg_exit), COLORS["danger"]),
            ("Quantidade de entradas", str(len(entradas)), COLORS["text"]),
            ("Quantidade de saídas", str(len(saidas)), COLORS["text"]),
        ]

        for index, (title, value, color) in enumerate(items):
            row = index // 2
            column = index % 2
            card = self._metric_card(self.analysis_tab, title, value, color)
            card.grid(row=row, column=column, sticky="ew", padx=((0, 10) if column == 0 else (10, 0)), pady=(0, 14))

        categories = self._info_card(self.analysis_tab, "Categorias com maior peso")
        categories.grid(row=3, column=0, sticky="nsew", padx=(0, 10))
        self._fill_simple_lines(
            categories,
            [
                f"Entradas: {self._top_group(entradas, 'categoria')}",
                f"Saídas: {self._top_group(saidas, 'categoria')}",
                f"Movimento mais forte: {self._movement_line(self._largest_movement(movements))}",
            ],
        )

        people = self._info_card(self.analysis_tab, "Pessoas / empresas mais presentes")
        people.grid(row=3, column=1, sticky="nsew", padx=(10, 0))
        self._fill_simple_lines(
            people,
            [
                f"Entradas: {self._top_group(entradas, 'pessoa')}",
                f"Saídas: {self._top_group(saidas, 'pessoa')}",
                f"Principal método: {self._top_group(movements, 'metodo')}",
            ],
        )
        self._bind_history_mousewheel(self.analysis_tab)

    def _render_chart_tab(self, movements: list[Movement], summary: dict[str, object], timeline: list[dict[str, object]]) -> None:
        self._clear_container(self.chart_tab)

        entradas = self._movements_by_type(movements, MovementType.ENTRADA)
        saidas = self._movements_by_type(movements, MovementType.SAIDA)

        comparison = SectionFrame(self.chart_tab, title="Entradas x saídas")
        comparison.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        comparison.grid_columnconfigure(0, weight=1)
        max_total = max(float(summary["entradas"]), float(summary["saidas"]), 1.0)
        self._bar_row(comparison, 2, "Entradas", float(summary["entradas"]), max_total, COLORS["success"])
        self._bar_row(comparison, 3, "Saídas", float(summary["saidas"]), max_total, COLORS["danger"])
        self._bar_row(comparison, 4, "Saldo líquido", abs(float(summary["saldo"])), max_total, COLORS["primary"])

        evolution = SectionFrame(self.chart_tab, title="Evolução do saldo")
        evolution.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 14))
        evolution.grid_columnconfigure(0, weight=1)
        max_balance = max((abs(float(item["saldo"])) for item in timeline), default=1.0)
        if timeline:
            for index, item in enumerate(timeline[:18], start=2):
                color = COLORS["success"] if float(item["saldo"]) >= 0 else COLORS["danger"]
                self._bar_row(evolution, index, str(item["label"]), abs(float(item["saldo"])), max_balance, color, value_prefix=self._currency(float(item["saldo"])))
        else:
            self._empty_state(evolution, 2, "Sem dados para este período.")

        incoming = SectionFrame(self.chart_tab, title="Entradas por categoria")
        incoming.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 14))
        incoming.grid_columnconfigure(0, weight=1)
        self._render_group_bars(incoming, self._group_values(entradas, "categoria"), COLORS["success"])

        outgoing = SectionFrame(self.chart_tab, title="Saídas por categoria")
        outgoing.grid(row=2, column=0, columnspan=2, sticky="ew")
        outgoing.grid_columnconfigure(0, weight=1)
        self._render_group_bars(outgoing, self._group_values(saidas, "categoria"), COLORS["danger"])
        self._bind_history_mousewheel(self.chart_tab)

    def _render_records_tab(self, movements: list[Movement]) -> None:
        categories = ["Todas as categorias"] + sorted({movement.categoria for movement in movements})
        people = ["Todas as pessoas"] + sorted({movement.pessoa for movement in movements})
        methods = ["Todos os métodos"] + sorted({movement.metodo for movement in movements})

        self.category_menu.configure(values=categories)
        if self.record_category_filter not in categories:
            self.record_category_filter = categories[0]
        self.category_menu.set(self.record_category_filter)

        self.person_menu.configure(values=people)
        if self.record_person_filter not in people:
            self.record_person_filter = people[0]
        self.person_menu.set(self.record_person_filter)

        self.method_menu.configure(values=methods)
        if self.record_method_filter not in methods:
            self.record_method_filter = methods[0]
        self.method_menu.set(self.record_method_filter)

        self.type_menu.set(self.record_type_filter)
        self._refresh_record_headings()

        self._apply_record_filters()
        self._bind_history_mousewheel(self.records_tab)

    def _apply_record_filters(self) -> None:
        movements = list(self.current_scope_data["movements"]) if self.current_scope_data else []
        search = self.search_entry.get().strip().lower()

        filtered: list[Movement] = []
        for movement in movements:
            if self.record_type_filter == "Entrada" and movement.movement_type is not MovementType.ENTRADA:
                continue
            if self.record_type_filter == "Saída" and movement.movement_type is not MovementType.SAIDA:
                continue
            if self.record_category_filter != "Todas as categorias" and movement.categoria != self.record_category_filter:
                continue
            if self.record_person_filter != "Todas as pessoas" and movement.pessoa != self.record_person_filter:
                continue
            if self.record_method_filter != "Todos os métodos" and movement.metodo != self.record_method_filter:
                continue
            haystack = " ".join([movement.descricao, movement.categoria, movement.pessoa, movement.metodo, movement.formatted_date]).lower()
            if search and search not in haystack:
                continue
            filtered.append(movement)

        if self.record_sort_by is not None:
            field = self.SORT_FIELDS[self.record_sort_by]
            filtered.sort(key=lambda movement: self._sort_value(movement, field), reverse=self.record_sort_desc)
        self._filtered_movements = filtered
        self._refresh_record_headings()
        self._render_records()

    def _render_records(self) -> None:
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        self._movement_map.clear()

        for movement in self._filtered_movements:
            item_id = str(movement.id or len(self._movement_map) + 1)
            self._movement_map[item_id] = movement
            self.records_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    movement.formatted_date,
                    movement.movement_type.label,
                    self._signed_currency(movement),
                    movement.categoria,
                    movement.descricao,
                    movement.pessoa,
                    movement.metodo,
                    attachment_name(movement.anexo),
                ),
            )

        self.records_status.configure(text=f"{len(self._filtered_movements)} registro(s) no período.")
        if self.selected_movement_id is not None and str(self.selected_movement_id) in self._movement_map:
            self.records_tree.selection_set(str(self.selected_movement_id))
            self.records_tree.focus(str(self.selected_movement_id))
            self._render_selected_movement(self._movement_map[str(self.selected_movement_id)])
        else:
            self.selected_movement_id = None
            self._render_selected_movement(None)

    def _handle_record_selection(self, _event=None) -> None:
        selection = self.records_tree.selection()
        if not selection:
            self.selected_movement_id = None
            self._render_selected_movement(None)
            return
        item_id = selection[0]
        movement = self._movement_map.get(item_id)
        self.selected_movement_id = movement.id if movement and movement.id else None
        self._render_selected_movement(movement)

    def _render_selected_movement(self, movement: Movement | None) -> None:
        self._clear_container(self.record_detail)

        if movement is None:
            self.edit_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")
            self.open_attachment_button.configure(state="disabled")
            ctk.CTkLabel(
                self.record_detail,
                text="Selecione um registro para ver os detalhes.",
                font=FONTS["body"],
                text_color=COLORS["muted"],
                anchor="w",
            ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 18))
            return

        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        self.open_attachment_button.configure(state="normal" if movement.anexo else "disabled")
        summary_line = f"{movement.formatted_date} · {movement.movement_type.label} · {movement.categoria}"
        value_color = COLORS["success"] if movement.movement_type is MovementType.ENTRADA else COLORS["danger"]

        ctk.CTkLabel(
            self.record_detail,
            text=summary_line,
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            anchor="w",
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 6))

        ctk.CTkLabel(
            self.record_detail,
            text=self._signed_currency(movement),
            font=("Segoe UI Semibold", 22),
            text_color=value_color,
            anchor="w",
        ).grid(row=3, column=0, sticky="w", padx=18, pady=(0, 14))

        details_grid = ctk.CTkFrame(self.record_detail, fg_color=COLORS["surface_alt"], corner_radius=14)
        details_grid.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 14))
        details_grid.grid_columnconfigure(0, weight=1)
        details_grid.grid_columnconfigure(1, weight=1)

        compact_fields = [
            ("Pessoa / empresa", movement.pessoa or "-"),
            ("Método", movement.metodo or "-"),
            ("Descrição", movement.descricao or "-"),
            ("Anexo", attachment_name(movement.anexo)),
        ]

        for index, (label, value) in enumerate(compact_fields):
            row = index // 2
            column = index % 2
            block = ctk.CTkFrame(details_grid, fg_color="transparent")
            block.grid(row=row, column=column, sticky="ew", padx=((14, 10) if column == 0 else (10, 14)), pady=(12 if row == 0 else 6, 6 if row == 0 else 12))
            block.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                block,
                text=label,
                font=FONTS["small"],
                text_color=COLORS["muted"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                block,
                text=value,
                font=FONTS["body"],
                text_color=COLORS["text"],
                anchor="w",
                justify="left",
                wraplength=420,
            ).grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._bind_history_mousewheel(self.record_detail)

    def _reset_record_filters(self) -> None:
        self.search_entry.delete(0, "end")
        self.record_type_filter = "Todos"
        self.record_category_filter = "Todas as categorias"
        self.record_person_filter = "Todas as pessoas"
        self.record_method_filter = "Todos os métodos"
        self._render_records_tab(list(self.current_scope_data["movements"]) if self.current_scope_data else [])

    def _sort_records_by_column(self, column_key: str) -> None:
        label = self._column_label(column_key)
        if self.record_sort_by != label:
            self.record_sort_by = label
            self.record_sort_desc = False
        elif not self.record_sort_desc:
            self.record_sort_desc = True
        else:
            self.record_sort_by = None
            self.record_sort_desc = False
        self._apply_record_filters()

    def _refresh_record_headings(self) -> None:
        active_field = self.SORT_FIELDS.get(self.record_sort_by) if self.record_sort_by else None
        for key in self.columns:
            label = self._column_label(key)
            indicator = ""
            if active_field == key:
                indicator = " ↓" if self.record_sort_desc else " ↑"
            self.records_tree.heading(
                key,
                text=f"{label}{indicator}",
                command=lambda column=key: self._sort_records_by_column(column),
            )

    def _column_label(self, column_key: str) -> str:
        for label, field in self.SORT_FIELDS.items():
            if field == column_key:
                return label
        return column_key.title()

    def _edit_selected_movement(self) -> None:
        movement = self._selected_movement()
        if movement is None:
            return
        dialog = MovementEditorDialog(self, self.service, movement, on_saved=self._handle_dialog_saved)
        dialog.focus()

    def _handle_dialog_saved(self, movement: Movement) -> None:
        self._on_changed()
        self.selected_movement_id = movement.id
        self._open_scope(reset_tab=False)
        self._show_tab("Registros")

    def _delete_selected_movement(self) -> None:
        movement = self._selected_movement()
        if movement is None or movement.id is None:
            return
        if not messagebox.askyesno("Excluir registro", "Deseja excluir o registro selecionado?"):
            return
        self.service.delete_movement(movement.id)
        self.selected_movement_id = None
        self._on_changed()
        self._open_scope(reset_tab=False)
        self._show_tab("Registros")

    def _open_selected_attachment(self) -> None:
        movement = self._selected_movement()
        if movement and movement.anexo:
            open_attachment(movement.anexo)

    def _export_excel_scope(self) -> None:
        if not self.current_scope_data:
            return
        output = filedialog.asksaveasfilename(
            title="Salvar Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=self._scope_filename("xlsx"),
        )
        if not output:
            return
        exportar_excel(
            output_path=output,
            movements=self._export_scope_movements(),
            title=str(self.current_scope_data["label"]),
            **self._export_metadata("Excel"),
        )
        messagebox.showinfo("Exportação concluída", "Arquivo Excel gerado com sucesso.")

    def _export_pdf_scope(self) -> None:
        if not self.current_scope_data:
            return
        output = filedialog.asksaveasfilename(
            title="Salvar PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=self._scope_filename("pdf"),
        )
        if not output:
            return
        gerar_pdf(
            output_path=output,
            movements=self._export_scope_movements(),
            title=str(self.current_scope_data["label"]),
            **self._export_metadata("PDF"),
        )
        messagebox.showinfo("Exportação concluída", "Arquivo PDF gerado com sucesso.")

    def _export_scope_movements(self) -> list[Movement]:
        if self.current_scope_data:
            return list(self.current_scope_data["movements"])
        return []

    def _export_metadata(self, file_kind: str) -> dict[str, object]:
        if not self.current_scope_data:
            return {}
        scope = str(self.current_scope_data.get("scope", ""))
        export_type = {
            "day": f"Exportação {file_kind} · Visão diária",
            "month": f"Exportação {file_kind} · Visão mensal",
            "year": f"Exportação {file_kind} · Visão anual",
        }.get(scope, f"Exportação {file_kind}")
        return {
            "export_type": export_type,
            "period_label": str(self.current_scope_data.get("label", "")),
            "generated_at": datetime.now(),
            "summary": dict(self.current_scope_data.get("summary", {})),
        }

    def _selected_movement(self) -> Movement | None:
        selection = self.records_tree.selection()
        if not selection:
            return None
        return self._movement_map.get(selection[0])

    def _render_group_bars(self, master, grouped: list[tuple[str, float]], color: str) -> None:
        if not grouped:
            self._empty_state(master, 2, "Sem dados para exibir.")
            return
        maximum = max(value for _, value in grouped) or 1.0
        for index, (label, value) in enumerate(grouped[:8], start=2):
            self._bar_row(master, index, label, value, maximum, color)

    def _metric_card(self, master, title: str, value: str, color: str) -> ctk.CTkFrame:
        card = tk.Frame(master, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1, bd=0)
        card.grid_columnconfigure(0, weight=1)
        tk.Label(card, text=title, font=FONTS["small"], fg=COLORS["muted"], bg=COLORS["surface"], anchor="w").grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))
        tk.Label(card, text=value, font=("Segoe UI Semibold", 18), fg=color, bg=COLORS["surface"], anchor="w").grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))
        return card

    def _info_card(self, master, title: str) -> ctk.CTkFrame:
        card = tk.Frame(master, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1, bd=0)
        card.grid_columnconfigure(0, weight=1)
        tk.Label(card, text=title, font=FONTS["subtitle"], fg=COLORS["text"], bg=COLORS["surface"], anchor="w").grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        return card

    def _fill_simple_lines(self, card, lines: list[str]) -> None:
        for index, line in enumerate(lines, start=1):
            tk.Label(
                card,
                text=line,
                font=FONTS["body"],
                fg=COLORS["text"],
                bg=COLORS["surface"],
                anchor="w",
                justify="left",
                wraplength=460,
            ).grid(row=index, column=0, sticky="ew", padx=18, pady=(0, 8))
        last_row = len(lines) + 1
        tk.Label(card, text="", font=FONTS["small"], fg=COLORS["surface"], bg=COLORS["surface"]).grid(row=last_row, column=0, pady=(0, 10))

    def _bar_row(self, master, row: int, label: str, value: float, maximum: float, color: str, *, value_prefix: str | None = None) -> None:
        wrap = ctk.CTkFrame(master, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 10))
        wrap.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=label, font=FONTS["body_bold"], text_color=COLORS["text"], anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text=value_prefix or self._currency(value), font=FONTS["small"], text_color=COLORS["muted"], anchor="e").grid(row=0, column=1, sticky="e")

        progress = ctk.CTkProgressBar(wrap, height=14, progress_color=color, fg_color="#dfe7f2")
        progress.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        progress.set(0 if maximum <= 0 else min(value / maximum, 1.0))

    def _empty_state(self, master, row: int, text: str) -> None:
        background = COLORS["surface_alt"] if isinstance(master, tk.Frame) else COLORS["surface"]
        tk.Label(master, text=text, font=FONTS["body"], fg=COLORS["muted"], bg=background, anchor="w").grid(row=row, column=0, sticky="w", padx=18, pady=(0, 18))

    def _movements_by_type(self, movements: list[Movement], movement_type: MovementType) -> list[Movement]:
        return [movement for movement in movements if movement.movement_type is movement_type]

    def _sum_values(self, movements: list[Movement]) -> float:
        return round(sum(movement.valor for movement in movements), 2)

    def _largest_movement(self, movements: list[Movement]) -> Movement | None:
        if not movements:
            return None
        return max(movements, key=lambda movement: movement.valor)

    def _movement_line(self, movement: Movement | None) -> str:
        if movement is None:
            return "Sem registros"
        return f"{movement.categoria} · {self._currency(movement.valor)} em {movement.formatted_date}"

    def _group_values(self, movements: list[Movement], field: str) -> list[tuple[str, float]]:
        grouped: dict[str, float] = defaultdict(float)
        for movement in movements:
            grouped[getattr(movement, field)] += movement.valor
        return sorted(grouped.items(), key=lambda item: item[1], reverse=True)

    def _top_group(self, movements: list[Movement], field: str) -> str:
        grouped = self._group_values(movements, field)
        if not grouped:
            return "Sem dados"
        label, value = grouped[0]
        return f"{label} · {self._currency(value)}"

    def _day_with_highest_volume(self, timeline: list[dict[str, object]]) -> str:
        if not timeline:
            return "Sem dados"
        peak = max(timeline, key=lambda item: float(item["entradas"]) + float(item["saidas"]))
        total = float(peak["entradas"]) + float(peak["saidas"])
        return f"{peak['label']} · {self._currency(total)}"

    def _signed_currency(self, movement: Movement) -> str:
        signal = "+" if movement.movement_type is MovementType.ENTRADA else "-"
        return f"{signal} {self._currency(movement.valor)}"

    def _sort_value(self, movement: Movement, field: str):
        if field == "valor":
            return movement.valor
        if field == "data":
            try:
                return datetime.strptime(movement.data, "%Y-%m-%d")
            except ValueError:
                return datetime.min
        if field == "tipo":
            return movement.movement_type.label.lower()
        if field == "anexo":
            return attachment_name(movement.anexo).lower()
        return str(getattr(movement, field, "") or "").lower()

    def _month_display(self, month: str | None) -> str:
        if not month:
            return "Selecione"
        return f"{month} · {self.MONTH_NAMES.get(month, month)}"

    def _day_display(self, day: str | None) -> str:
        if not day:
            return "Selecione"
        if not self.selected_month or not self.selected_year:
            return day
        return f"{day}/{self.selected_month}/{self.selected_year}"

    def _scope_filename(self, extension: str) -> str:
        if not self.current_scope_data:
            return f"historico.{extension}"
        raw = str(self.current_scope_data["label"]).lower()
        sanitized = raw.replace("histórico de ", "historico_").replace("/", "-").replace(" ", "_")
        sanitized = "".join(character for character in sanitized if character.isalnum() or character in {"_", "-"})
        return f"{sanitized}.{extension}"

    def _display_date(self, iso_date: str) -> str:
        try:
            return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return iso_date

    @staticmethod
    def _clear_container(container) -> None:
        for child in container.winfo_children():
            child.destroy()

    @staticmethod
    def _currency(value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def destroy(self) -> None:
        if self._active_period_dropdown is not None:
            self._active_period_dropdown.close()
            self._active_period_dropdown = None
        super().destroy()


class MovementEditorDialog(ctk.CTkToplevel):
    """Modal de edição de movimentação."""

    def __init__(
        self,
        master,
        service: CashService,
        movement: Movement,
        *,
        on_saved: Callable[[Movement], None],
    ) -> None:
        super().__init__(master)
        self.service = service
        self.movement = movement
        self.on_saved = on_saved
        self.attachment_path = movement.anexo or ""

        self.title("Editar registro")
        self.configure(fg_color=COLORS["bg"])
        self.minsize(760, 640)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self.after(0, self._maximize_window)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"])
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll.grid_columnconfigure(0, weight=1)
        _bind_scrollable_mousewheel(self.scroll, units_per_step=4)

        ctk.CTkLabel(self.scroll, text="Editar registro", font=FONTS["title"], text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", pady=(0, 14))

        section = SectionFrame(self.scroll, title="Dados do registro")
        section.grid(row=1, column=0, sticky="ew")
        section.grid_columnconfigure(0, weight=1)
        section.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(section, text="Tipo", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(row=2, column=0, columnspan=2, sticky="w", padx=18)
        self.type_selector = ctk.CTkSegmentedButton(section, values=[MovementType.ENTRADA.value, MovementType.SAIDA.value], height=40)
        self.type_selector.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(8, 18))

        self.value_entry = self._entry(section, 4, 0, "Valor", "0,00")
        self.description_entry = self._entry(section, 4, 1, "Descrição", "Ex.: ajuste do lançamento")

        self.category_selector = self._combo(section, 6, 0, "Categoria")
        self.person_selector = self._combo(section, 6, 1, "Pessoa / empresa")

        self.date_entry = self._date_field(section, 8, 0, "Data")
        self.method_selector = self._combo(section, 8, 1, "Método", values=PAYMENT_METHODS)

        ctk.CTkLabel(section, text="Anexo", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(row=10, column=0, columnspan=2, sticky="w", padx=18)
        attachment_row = ctk.CTkFrame(section, fg_color="transparent")
        attachment_row.grid(row=11, column=0, columnspan=2, sticky="ew", padx=18, pady=(8, 18))
        attachment_row.grid_columnconfigure(0, weight=1)
        self.attachment_label = ctk.CTkLabel(attachment_row, text="Sem anexo", font=FONTS["body"], text_color=COLORS["muted"], anchor="w", justify="left")
        self.attachment_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(attachment_row, text="Selecionar arquivo", command=self._choose_attachment, height=38, fg_color=COLORS["surface_alt"], hover_color="#dfe7f3", text_color=COLORS["text"]).grid(row=0, column=1, padx=(0, 10))
        ctk.CTkButton(attachment_row, text="Limpar", command=self._clear_attachment, height=38, fg_color=COLORS["surface_alt"], hover_color="#dfe7f3", text_color=COLORS["text"]).grid(row=0, column=2)
        self.open_attachment_button = ctk.CTkButton(
            attachment_row,
            text="Abrir anexo",
            command=self._open_attachment,
            height=38,
            width=120,
            state="disabled",
            fg_color=COLORS["surface_alt"],
            hover_color="#dfe7f3",
            text_color=COLORS["text"],
        )
        self.open_attachment_button.grid(row=0, column=3, padx=(10, 0))

        actions = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg"])
        actions.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(actions, text="Cancelar", command=self.destroy, height=42, fg_color=COLORS["surface_alt"], hover_color="#dfe7f3", text_color=COLORS["text"]).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(actions, text="Salvar alterações", command=self._save, height=42, fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"]).grid(row=0, column=1, sticky="ew", padx=(10, 0))

        self._populate()

    def _entry(self, master, row: int, column: int, label: str, placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(master, text=label, font=FONTS["body_bold"], text_color=COLORS["text"]).grid(row=row, column=column, sticky="w", padx=(18 if column == 0 else 10, 18))
        entry = ctk.CTkEntry(master, height=42, placeholder_text=placeholder, fg_color=COLORS["surface_alt"], border_width=0)
        entry.grid(row=row + 1, column=column, sticky="ew", padx=((18, 10) if column == 0 else (10, 18)), pady=(8, 18))
        return entry

    def _combo(self, master, row: int, column: int, label: str, *, values: list[str] | None = None) -> ctk.CTkComboBox:
        ctk.CTkLabel(master, text=label, font=FONTS["body_bold"], text_color=COLORS["text"]).grid(row=row, column=column, sticky="w", padx=(18 if column == 0 else 10, 18))
        combo = ctk.CTkComboBox(master, height=42, fg_color=COLORS["surface_alt"], border_width=0, values=values or [""])
        combo.grid(row=row + 1, column=column, sticky="ew", padx=((18, 10) if column == 0 else (10, 18)), pady=(8, 18))
        return combo

    def _date_field(self, master, row: int, column: int, label: str) -> DateMaskEntry:
        ctk.CTkLabel(master, text=label, font=FONTS["body_bold"], text_color=COLORS["text"]).grid(row=row, column=column, sticky="w", padx=(18, 18))
        entry = DateMaskEntry(master, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        entry.grid(row=row + 1, column=column, sticky="ew", padx=(18, 10), pady=(8, 18))
        return entry

    def _populate(self) -> None:
        categories = [item.nome for item in self.service.list_categories()] or [self.movement.categoria]
        people = [item.nome for item in self.service.list_people()] or [self.movement.pessoa]
        self.category_selector.configure(values=categories)
        self.person_selector.configure(values=people)

        self.type_selector.set(self.movement.movement_type.value)
        self.value_entry.insert(0, str(self.movement.valor).replace(".", ","))
        self.description_entry.insert(0, self.movement.descricao)
        self.category_selector.set(self.movement.categoria)
        self.person_selector.set(self.movement.pessoa)
        self.date_entry.set(self.movement.formatted_date)
        self.method_selector.set(self.movement.metodo)
        self.attachment_label.configure(text=attachment_name(self.attachment_path))
        self.open_attachment_button.configure(state="normal" if self.attachment_path else "disabled")

    def _choose_attachment(self) -> None:
        path = filedialog.askopenfilename(title="Selecionar arquivo")
        if path:
            self.attachment_path = path
            self.attachment_label.configure(text=attachment_name(path))
            self.open_attachment_button.configure(state="normal")

    def _clear_attachment(self) -> None:
        self.attachment_path = ""
        self.attachment_label.configure(text="Sem anexo")
        self.open_attachment_button.configure(state="disabled")

    def _open_attachment(self) -> None:
        try:
            open_attachment(self.attachment_path)
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Anexo indisponível", str(exc))

    def _save(self) -> None:
        try:
            movement = self.service.update_movement(
                self.movement.id,
                tipo=self.type_selector.get(),
                valor=self.value_entry.get(),
                descricao=self.description_entry.get(),
                categoria=self.category_selector.get(),
                metodo=self.method_selector.get(),
                pessoa=self.person_selector.get(),
                data_movimento=self.date_entry.get(),
                anexo=self.attachment_path,
            )
        except ValueError as exc:
            messagebox.showerror("Não foi possível salvar", str(exc))
            return

        self.on_saved(movement)
        self.destroy()

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except tk.TclError:
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
