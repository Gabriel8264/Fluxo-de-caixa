from __future__ import annotations
"""Tela de consultas e filtros do extrato.

Mantem a configuracao dos filtros separada da leitura dos resultados para
reduzir excesso de informacao na mesma area.
"""

from tkinter import messagebox, ttk

import customtkinter as ctk

from core.models import MovementType
from services.attachments import attachment_name, open_attachment
from services.cash_service import CashService
from ui.theme import COLORS, FONTS
from ui.widgets import DateMaskEntry, DetailMarqueeBar, SectionFrame, build_treeview_style


class StatementView(ctk.CTkFrame):
    """View de extrato com filtros multiplos e leitura de anexos."""

    columns = ("data", "tipo", "valor", "categoria", "metodo", "pessoa", "descricao")

    def __init__(self, master, service: CashService) -> None:
        """Inicializa filtros, tabela e estado de selecao do extrato."""
        super().__init__(master, fg_color="transparent")
        self.service = service
        self._movement_map: dict[str, object] = {}
        build_treeview_style(self)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_tabs()

    def _build_header(self) -> None:
        """Cria o cabecalho introdutorio da tela de consultas."""
        ctk.CTkLabel(self, text="Consultas e filtros", font=FONTS["title"], text_color=COLORS["text"]).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        ctk.CTkLabel(
            self,
            text="Filtre e consulte o extrato.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            wraplength=1000,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 18))

    def _build_tabs(self) -> None:
        """Separa a tela entre configuracao da consulta e resultados."""
        self.tabs = ctk.CTkTabview(
            self,
            fg_color="transparent",
            segmented_button_fg_color=COLORS["surface_alt"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_selected_hover_color=COLORS["primary_hover"],
            segmented_button_unselected_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
        )
        self.tabs.grid(row=2, column=0, sticky="nsew")
        self.tabs.add("Filtros")
        self.tabs.add("Resultados")

        self.filter_tab = self.tabs.tab("Filtros")
        self.filter_tab.grid_columnconfigure(0, weight=1)

        self.results_tab = self.tabs.tab("Resultados")
        self.results_tab.grid_columnconfigure(0, weight=1)
        self.results_tab.grid_rowconfigure(0, weight=1)

        self._build_filters()
        self._build_table()

    def _build_filters(self) -> None:
        """Monta o bloco de filtros por texto, periodo e seletores."""
        filters = SectionFrame(
            self.filter_tab,
            title="Configurar consulta",
            subtitle="Use os filtros que precisar.",
            subtitle_wraplength=840,
        )
        filters.grid(row=0, column=0, sticky="nsew", pady=(12, 0))
        for column in range(12):
            filters.grid_columnconfigure(column, weight=1)

        self.search_entry = ctk.CTkEntry(filters, placeholder_text="Buscar", height=42)
        self.search_entry.grid(row=2, column=0, columnspan=6, padx=20, pady=(0, 14), sticky="ew")

        self.start_entry = DateMaskEntry(filters, placeholder_text="Início dd/mm/aaaa", height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.start_entry.grid(row=2, column=6, columnspan=2, padx=(0, 12), pady=(0, 14), sticky="ew")
        self.end_entry = DateMaskEntry(filters, placeholder_text="Fim dd/mm/aaaa", height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.end_entry.grid(row=2, column=8, columnspan=2, padx=(0, 12), pady=(0, 14), sticky="ew")

        self.category_selector = ctk.CTkComboBox(filters, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.category_selector.grid(row=3, column=0, columnspan=4, padx=20, pady=(0, 14), sticky="ew")
        self.person_selector = ctk.CTkComboBox(filters, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.person_selector.grid(row=3, column=4, columnspan=4, padx=(0, 12), pady=(0, 14), sticky="ew")
        self.type_selector = ctk.CTkSegmentedButton(filters, values=["Todos", *[item.value.capitalize() for item in MovementType]])
        self.type_selector.grid(row=3, column=8, columnspan=4, padx=(0, 20), pady=(0, 14), sticky="ew")
        self.type_selector.set("Todos")

        ctk.CTkButton(filters, text="Fluxo do dia", command=self.apply_active_day_filter, width=140).grid(
            row=4, column=0, columnspan=2, padx=20, pady=(0, 18), sticky="ew"
        )
        ctk.CTkButton(filters, text="Aplicar filtros", command=self.apply_filters, width=140).grid(
            row=4, column=2, columnspan=2, padx=(0, 12), pady=(0, 18), sticky="ew"
        )
        ctk.CTkButton(
            filters,
            text="Limpar",
            command=self.clear_filters,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
            width=120,
        ).grid(row=4, column=4, columnspan=2, padx=(0, 12), pady=(0, 18), sticky="ew")

    def _build_table(self) -> None:
        """Monta a tabela do extrato com detalhe textual e acesso a anexo."""
        table_section = SectionFrame(
            self.results_tab,
            title="Extrato do fluxo",
            subtitle="Resultados da consulta.",
            subtitle_wraplength=840,
        )
        table_section.grid(row=0, column=0, sticky="nsew", pady=(12, 0))
        table_section.grid_columnconfigure(0, weight=1)
        table_section.grid_rowconfigure(4, weight=1)

        self.detail_bar = DetailMarqueeBar(table_section)
        self.detail_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.detail_bar.set_text("Selecione um registro.")

        self.attachment_row = ctk.CTkFrame(table_section, fg_color="transparent")
        self.attachment_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.attachment_row.grid_columnconfigure(0, weight=1)
        self.attachment_label = ctk.CTkLabel(
            self.attachment_row,
            text="Anexo: sem anexo",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
        )
        self.attachment_label.grid(row=0, column=0, sticky="ew")
        self.open_attachment_button = ctk.CTkButton(
            self.attachment_row,
            text="Abrir anexo",
            width=132,
            height=34,
            state="disabled",
            command=self._open_selected_attachment,
        )
        self.open_attachment_button.grid(row=0, column=1, padx=(12, 0))

        container = ctk.CTkFrame(table_section, fg_color="transparent")
        container.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 16))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(container, columns=self.columns, show="headings", style="Cash.Treeview")
        headings = {
            "data": "Data",
            "tipo": "Tipo",
            "valor": "Valor",
            "categoria": "Categoria",
            "metodo": "Método",
            "pessoa": "Pessoa / empresa",
            "descricao": "Descrição",
        }
        widths = {"data": 110, "tipo": 100, "valor": 120, "categoria": 220, "metodo": 145, "pessoa": 270, "descricao": 520}
        for key in self.columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="w", stretch=True)

        y_scroll = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._update_selected_detail)

    def refresh(self) -> None:
        """Atualiza seletores e reaplica a consulta atual."""
        self._refresh_selectors()
        self.apply_filters(switch_tab=False)

    def apply_filters(self, *, switch_tab: bool = True) -> None:
        """Consulta o servico com os filtros atuais e preenche a tabela."""
        self._refresh_selectors()
        try:
            movement_type = self.type_selector.get().lower()
            if movement_type == "todos":
                movement_type = None
            movements = self.service.list_movements(
                search=self.search_entry.get(),
                start_date=self.start_entry.get().strip() or None,
                end_date=self.end_entry.get().strip() or None,
                category=None if self.category_selector.get() == "Todas as categorias" else self.category_selector.get(),
                movement_type=movement_type,
                person=None if self.person_selector.get() == "Todas as pessoas" else self.person_selector.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Filtro inválido", str(exc))
            return

        self._movement_map.clear()
        for row_id in self.tree.get_children():
            self.tree.delete(row_id)
        for movement in movements:
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    movement.formatted_date,
                    movement.display_type.capitalize(),
                    self._currency(movement.valor),
                    movement.categoria,
                    movement.metodo,
                    movement.pessoa,
                    movement.descricao,
                ),
            )
            self._movement_map[item_id] = movement
        self.detail_bar.set_text("Selecione um registro.")
        self.attachment_label.configure(text="Anexo: sem anexo")
        self.open_attachment_button.configure(state="disabled")
        if switch_tab:
            self.tabs.set("Resultados")

    def _update_selected_detail(self, _event=None) -> None:
        """Atualiza barra de detalhe e estado do botao de anexo."""
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        detail = " | ".join(str(value) for value in values)
        self.detail_bar.set_text(detail)
        movement = self._movement_map.get(selected[0])
        attachment_value = "" if movement is None else movement.anexo
        self.attachment_label.configure(text=f"Anexo: {attachment_name(attachment_value)}")
        self.open_attachment_button.configure(state="normal" if attachment_value else "disabled")

    def _open_selected_attachment(self) -> None:
        """Abre o anexo do movimento selecionado na tabela."""
        selected = self.tree.selection()
        if not selected:
            return
        movement = self._movement_map.get(selected[0])
        if movement is None:
            return
        try:
            open_attachment(movement.anexo)
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Anexo indisponível", str(exc))

    def apply_active_day_filter(self) -> None:
        """Atalho para consultar apenas o fluxo do dia ativo."""
        year, month, day = self.service.get_active_day().split("-")
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, f"{day}/{month}/{year}")
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, f"{day}/{month}/{year}")
        self.apply_filters()

    def clear_filters(self) -> None:
        """Limpa filtros visiveis e volta ao extrato amplo."""
        self.search_entry.delete(0, "end")
        self.start_entry.delete(0, "end")
        self.end_entry.delete(0, "end")
        self.type_selector.set("Todos")
        self._refresh_selectors(force_reset=True)
        self.apply_filters()

    def _refresh_selectors(self, force_reset: bool = False) -> None:
        """Recarrega categorias e pessoas mantendo selecoes validas quando possivel."""
        categories = ["Todas as categorias", *[item.nome for item in self.service.list_categories()]]
        people = ["Todas as pessoas", *[item.nome for item in self.service.list_people()]]
        current_category = self.category_selector.get()
        current_person = self.person_selector.get()
        self.category_selector.configure(values=categories)
        self.person_selector.configure(values=people)
        self.category_selector.set(current_category if current_category in categories and not force_reset else categories[0])
        self.person_selector.set(current_person if current_person in people and not force_reset else people[0])

    @staticmethod
    def _currency(value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
