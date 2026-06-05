from __future__ import annotations
"""Tela de cadastro de novas movimentacoes.

Separa o fluxo em formulario principal e orientacoes de apoio para manter o
uso diario simples e legivel.
"""

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.models import MovementType, PAYMENT_METHODS, Technician
from services.attachments import open_attachment
from services.cash_service import CashService
from ui.theme import COLORS, FONTS
from ui.widgets import DateMaskEntry, MarqueeLabel, MoneyMaskEntry, SectionFrame, _bind_scrollable_mousewheel


class RegisterView(ctk.CTkScrollableFrame):
    """View de registro de entradas e saidas com suporte a anexos."""

    DEFAULT_PERSON = "Clientes diversos"
    SERVICE_OPERATION = "serviço técnico"

    def __init__(
        self,
        master,
        service: CashService,
        on_saved: Callable[[object], None],
        on_open_registries: Callable[[], None],
    ) -> None:
        """Inicializa formulario, callbacks externos e estado de anexo."""
        super().__init__(master, fg_color="transparent")
        self.service = service
        self.on_saved = on_saved
        self.on_open_registries = on_open_registries
        self.attachment_path = ""
        self._technician_map: dict[str, Technician] = {}
        self._selected_technicians: list[Technician] = []

        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_form()
        _bind_scrollable_mousewheel(self, units_per_step=32)

    def _build_header(self) -> None:
        """Cria o cabecalho explicativo da tela de registro."""
        spacer = ctk.CTkFrame(self, fg_color="transparent", height=2)
        spacer.grid(row=0, column=0, sticky="ew")

    def _build_form(self) -> None:
        """Monta o formulario principal de cadastro da movimentacao."""
        section = SectionFrame(
            self,
            title="Dados da movimentação",
            subtitle=None,
            subtitle_wraplength=840,
        )
        section.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        section.grid_columnconfigure(0, weight=1)
        section.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(section, text="Operação", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=2, column=0, padx=20, sticky="w"
        )
        self.type_selector = ctk.CTkSegmentedButton(
            section,
            values=[MovementType.ENTRADA.value, MovementType.SAIDA.value, self.SERVICE_OPERATION],
            command=lambda _value: self._handle_operation_change(),
        )
        self.type_selector.grid(row=3, column=0, columnspan=2, padx=20, pady=(8, 18), sticky="ew")
        self.type_selector.set(MovementType.ENTRADA.value)

        self.value_label = ctk.CTkLabel(section, text="Valor", font=FONTS["body_bold"], text_color=COLORS["text"])
        self.value_label.grid(row=4, column=0, padx=20, sticky="w")
        self.value_entry = MoneyMaskEntry(section, placeholder_text="0,00", height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.value_entry.grid(row=5, column=0, padx=20, pady=(8, 18), sticky="ew")
        self.value_entry.bind("<KeyRelease>", lambda _event: self._update_service_summary(), add="+")
        self.description_entry = self._build_entry(section, row=4, column=1, label="Descrição (opcional)", placeholder="Ex.: venda no balcão")

        self.category_label = ctk.CTkLabel(section, text="Categoria", font=FONTS["body_bold"], text_color=COLORS["text"])
        self.category_label.grid(row=6, column=0, padx=20, sticky="w")
        self.category_selector = ctk.CTkComboBox(section, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.category_selector.grid(row=7, column=0, padx=20, pady=(8, 18), sticky="ew")

        self.person_label = ctk.CTkLabel(section, text="Pessoa / empresa", font=FONTS["body_bold"], text_color=COLORS["text"])
        self.person_label.grid(row=6, column=1, padx=20, sticky="w")
        self.person_selector = ctk.CTkComboBox(section, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        self.person_selector.grid(row=7, column=1, padx=20, pady=(8, 18), sticky="ew")

        self.service_panel = ctk.CTkFrame(section, fg_color=COLORS["surface_alt"], corner_radius=18)
        self.service_panel.grid(row=8, column=0, columnspan=2, padx=20, pady=(0, 18), sticky="ew")
        self.service_panel.grid_columnconfigure(0, weight=1)
        self.service_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self.service_panel,
            text="Serviço técnico",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 2), sticky="w")
        ctk.CTkLabel(
            self.service_panel,
            text="Selecione um ou mais técnicos e confira a divisão da comissão.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 10), sticky="w")

        ctk.CTkLabel(self.service_panel, text="Técnicos responsáveis", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=2, column=0, padx=16, pady=(0, 4), sticky="w"
        )
        picker_row = ctk.CTkFrame(self.service_panel, fg_color="transparent")
        picker_row.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
        picker_row.grid_columnconfigure(0, weight=1)
        self.technician_selector = ctk.CTkComboBox(
            picker_row,
            height=40,
            fg_color=COLORS["surface"],
            border_width=0,
        )
        self.technician_selector.grid(row=0, column=0, sticky="ew")
        self.add_technician_button = ctk.CTkButton(
            picker_row,
            text="Adicionar",
            width=120,
            height=38,
            command=self._add_selected_technician,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        )
        self.add_technician_button.grid(row=0, column=1, padx=(10, 0))

        self.no_technician_label = ctk.CTkLabel(
            self.service_panel,
            text="Cadastre ao menos um técnico ativo para lançar este serviço.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
        )
        self.no_technician_label.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 10), sticky="w")

        self.selected_technicians_frame = ctk.CTkFrame(self.service_panel, fg_color="transparent")
        self.selected_technicians_frame.grid(row=5, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="ew")
        self.selected_technicians_frame.grid_columnconfigure(0, weight=1)

        summary_frame = ctk.CTkFrame(self.service_panel, fg_color="transparent")
        summary_frame.grid(row=6, column=0, columnspan=2, padx=16, pady=(0, 10), sticky="ew")
        summary_frame.grid_columnconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(1, weight=1)

        self.technician_card = self._build_service_metric(summary_frame, 0, 0, "Comissão total")
        self.company_card = self._build_service_metric(summary_frame, 0, 1, "Valor da empresa")
        self.technician_value_label = self.technician_card["value"]
        self.technician_percent_label = self.technician_card["secondary"]
        self.company_value_label = self.company_card["value"]
        self.company_percent_label = self.company_card["secondary"]

        self.service_split_frame = ctk.CTkFrame(self.service_panel, fg_color=COLORS["surface"], corner_radius=14)
        self.service_split_frame.grid(row=7, column=0, columnspan=2, padx=16, pady=(0, 14), sticky="ew")
        self.service_split_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(section, text="Data", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=10, column=0, padx=20, sticky="w"
        )
        date_row = ctk.CTkFrame(section, fg_color="transparent")
        date_row.grid(row=11, column=0, padx=20, pady=(8, 18), sticky="ew")
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
            row=10, column=1, padx=20, sticky="w"
        )
        self.method_selector = ctk.CTkOptionMenu(
            section,
            values=PAYMENT_METHODS,
            height=42,
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
        )
        self.method_selector.grid(row=11, column=1, padx=20, pady=(8, 18), sticky="ew")
        self.method_selector.set(PAYMENT_METHODS[0])

        ctk.CTkLabel(section, text="Anexo", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=12, column=0, padx=20, sticky="w"
        )
        attachment_row = ctk.CTkFrame(section, fg_color="transparent")
        attachment_row.grid(row=13, column=0, columnspan=2, padx=20, pady=(8, 18), sticky="ew")
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
            command=self.select_attachment,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        ).grid(row=0, column=1, padx=(10, 0))
        ctk.CTkButton(
            attachment_row,
            text="Limpar",
            width=96,
            height=38,
            command=self.clear_attachment,
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
            command=self.open_current_attachment,
        )
        self.open_attachment_button.grid(row=0, column=3, padx=(10, 0))

        ctk.CTkButton(
            section,
            text="Salvar movimentação",
            command=self.save,
            height=50,
            corner_radius=16,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
        ).grid(row=14, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="ew")
        self._handle_operation_change()

    def _build_service_metric(self, master, row: int, column: int, title: str) -> dict[str, ctk.CTkLabel]:
        """Cria um bloco de resumo para o fluxo financeiro do serviço técnico."""
        box = ctk.CTkFrame(master, fg_color=COLORS["surface"], corner_radius=14)
        box.grid(row=row, column=column, sticky="ew", padx=6, pady=6)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text=title, font=FONTS["small"], text_color=COLORS["muted"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 2)
        )
        value_label = ctk.CTkLabel(box, text="R$ 0,00", font=("Segoe UI Semibold", 20), text_color=COLORS["text"], anchor="w")
        value_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 2))
        secondary_label = ctk.CTkLabel(box, text="0%", font=FONTS["small"], text_color=COLORS["muted"], anchor="w")
        secondary_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))
        return {"value": value_label, "secondary": secondary_label}

    def _handle_operation_change(self) -> None:
        """Mostra ou esconde os campos extras do serviço técnico."""
        is_service = self.type_selector.get() == self.SERVICE_OPERATION
        self.value_label.configure(text="Valor do serviço" if is_service else "Valor")
        if is_service:
            self.service_panel.grid()
            self.category_label.grid_remove()
            self.category_selector.grid_remove()
        else:
            self.service_panel.grid_remove()
            self.category_label.grid()
            self.category_selector.grid()
        self._update_service_summary()

    def _add_selected_technician(self) -> None:
        """Adiciona o técnico escolhido à lista do serviço técnico."""
        technician = self._technician_map.get(self.technician_selector.get())
        if technician is None:
            return
        if any(item.id == technician.id for item in self._selected_technicians):
            return
        self._selected_technicians.append(technician)
        self._render_selected_technicians()
        self._update_service_summary()

    def _remove_selected_technician(self, technician_id: int | None) -> None:
        """Remove um técnico já selecionado do serviço técnico."""
        self._selected_technicians = [item for item in self._selected_technicians if item.id != technician_id]
        self._render_selected_technicians()
        self._update_service_summary()

    def _selected_technician_ids(self) -> list[int]:
        """Devolve os identificadores dos técnicos selecionados."""
        return [technician.id for technician in self._selected_technicians if technician.id is not None]

    def _render_selected_technicians(self) -> None:
        """Mostra técnicos selecionados em chips compactos."""
        for child in self.selected_technicians_frame.winfo_children():
            child.destroy()

        if not self._selected_technicians:
            ctk.CTkLabel(
                self.selected_technicians_frame,
                text="Nenhum técnico selecionado.",
                font=FONTS["small"],
                text_color=COLORS["muted"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return

        row = ctk.CTkFrame(self.selected_technicians_frame, fg_color="transparent")
        row.grid(row=0, column=0, sticky="w")
        for index, technician in enumerate(self._selected_technicians):
            chip = ctk.CTkFrame(row, fg_color=COLORS["surface"], corner_radius=14)
            chip.grid(row=0, column=index, padx=(0, 8), pady=2, sticky="w")
            ctk.CTkLabel(
                chip,
                text=technician.nome,
                font=FONTS["small"],
                text_color=COLORS["text"],
                anchor="w",
            ).grid(row=0, column=0, padx=(12, 6), pady=8)
            ctk.CTkButton(
                chip,
                text="×",
                width=28,
                height=28,
                corner_radius=12,
                command=lambda technician_id=technician.id: self._remove_selected_technician(technician_id),
                fg_color="transparent",
                hover_color="#e5edf7",
                text_color=COLORS["muted"],
            ).grid(row=0, column=1, padx=(0, 8), pady=6)

    def _update_service_summary(self) -> None:
        """Atualiza a prévia de comissão, divisão e valor da empresa."""
        technicians = list(self._selected_technicians)
        raw_value = self.value_entry.get().strip() or "0"

        try:
            service_value = self.service._normalize_amount(raw_value)
        except ValueError:
            service_value = 0.0

        if not technicians:
            self.technician_value_label.configure(text="R$ 0,00")
            self.company_value_label.configure(text=self._currency(service_value))
            self.technician_percent_label.configure(text="0,00% comissão")
            self.company_percent_label.configure(text="100,00% empresa")
            self._render_service_split([], service_value)
            return

        try:
            split = self.service.calculate_technical_service_split(raw_value, technicians)
        except ValueError as exc:
            self.technician_value_label.configure(text="R$ 0,00")
            self.company_value_label.configure(text="R$ 0,00")
            self.technician_percent_label.configure(text="0,00% comissão")
            self.company_percent_label.configure(text="0,00% empresa")
            self._render_service_split([], 0.0, message=str(exc))
            return

        self.technician_percent_label.configure(
            text=f"{float(split['percentual_total_comissao']):.2f}% comissão"
        )
        self.company_percent_label.configure(
            text=f"{float(split['percentual_empresa']):.2f}% empresa"
        )
        self.technician_value_label.configure(text=self._currency(float(split["valor_comissao_total"])))
        self.company_value_label.configure(text=self._currency(float(split["valor_empresa"])))
        self._render_service_split(list(split["divisao_tecnicos"]), float(split["valor_empresa"]))

    def _render_service_split(
        self,
        commission_shares: list[tuple[Technician, float]],
        company_value: float,
        message: str | None = None,
    ) -> None:
        """Renderiza a divisão da comissão entre os técnicos selecionados."""
        for child in self.service_split_frame.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self.service_split_frame,
            text="Divisão da comissão",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        if message:
            ctk.CTkLabel(
                self.service_split_frame,
                text=message,
                font=FONTS["small"],
                text_color=COLORS["danger"],
                anchor="w",
                justify="left",
            ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
            return

        if not commission_shares:
            ctk.CTkLabel(
                self.service_split_frame,
                text="Selecione técnicos para ver a divisão.",
                font=FONTS["small"],
                text_color=COLORS["muted"],
                anchor="w",
            ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
            return

        total_commission = 0.0
        for index, (technician, share) in enumerate(commission_shares, start=1):
            total_commission += share
            line = ctk.CTkFrame(self.service_split_frame, fg_color="transparent")
            line.grid(row=index, column=0, sticky="ew", padx=12, pady=(0, 4))
            line.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                line,
                text=f"{technician.nome} · {technician.percentual_comissao:.2f}%",
                font=FONTS["body"],
                text_color=COLORS["text"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                line,
                text=self._currency(share),
                font=FONTS["body_bold"],
                text_color=COLORS["success"],
                anchor="e",
            ).grid(row=0, column=1, sticky="e")

        footer = ctk.CTkFrame(self.service_split_frame, fg_color="transparent")
        footer.grid(row=len(commission_shares) + 1, column=0, sticky="ew", padx=12, pady=(4, 2))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, text="Comissão total", font=FONTS["small"], text_color=COLORS["muted"], anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(footer, text=self._currency(total_commission), font=FONTS["body_bold"], text_color=COLORS["success"], anchor="e").grid(row=0, column=1, sticky="e")

        company_footer = ctk.CTkFrame(self.service_split_frame, fg_color="transparent")
        company_footer.grid(row=len(commission_shares) + 2, column=0, sticky="ew", padx=12, pady=(2, 10))
        company_footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(company_footer, text="Empresa", font=FONTS["small"], text_color=COLORS["muted"], anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(company_footer, text=self._currency(company_value), font=FONTS["body_bold"], text_color=COLORS["text"], anchor="e").grid(row=0, column=1, sticky="e")

    def _build_entry(self, master, *, row: int, column: int, label: str, placeholder: str) -> ctk.CTkEntry:
        """Cria campo padronizado do formulario."""
        ctk.CTkLabel(master, text=label, font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=row, column=column, padx=20, sticky="w"
        )
        entry = ctk.CTkEntry(master, placeholder_text=placeholder, height=42, fg_color=COLORS["surface_alt"], border_width=0)
        entry.grid(row=row + 1, column=column, padx=20, pady=(8, 18), sticky="ew")
        return entry

    def set_type(self, movement_type: str) -> None:
        """Permite abrir a tela ja focada em entrada ou saida."""
        self.type_selector.set(MovementType.from_db(movement_type).value)
        self._handle_operation_change()
        self._apply_default_person()

    def refresh(self) -> None:
        """Recarrega categorias, pessoas e técnicos disponíveis."""
        self._ensure_default_person()
        categories = [item.nome for item in self.service.list_categories()]
        people = [item.nome for item in self.service.list_people()]
        technicians = self.service.list_technicians(include_inactive=False)
        previous_ids = {technician.id for technician in self._selected_technicians if technician.id is not None}
        self._technician_map = {item.nome: item for item in technicians}
        current_category = self.category_selector.get()
        current_picker = self.technician_selector.get()

        self.category_selector.configure(values=categories or ["Sem categorias"])
        self.person_selector.configure(values=people or ["Sem cadastros"])
        technician_values = list(self._technician_map) or ["Sem técnicos ativos"]
        self.technician_selector.configure(values=technician_values)

        if categories:
            preferred_category = current_category if current_category in categories else categories[0]
            self.category_selector.set(preferred_category)
        if people:
            self._apply_default_person()

        if self._technician_map:
            preferred_picker = current_picker if current_picker in self._technician_map else next(iter(self._technician_map))
            self.technician_selector.set(preferred_picker)
            self._selected_technicians = [
                technician for technician in technicians if technician.id in previous_ids
            ]
            self.no_technician_label.grid_remove()
            self.add_technician_button.configure(state="normal")
        else:
            self.technician_selector.set("Sem técnicos ativos")
            self._selected_technicians = []
            self.no_technician_label.grid()
            self.add_technician_button.configure(state="disabled")

        self._render_selected_technicians()
        self._handle_operation_change()

    def select_attachment(self) -> None:
        """Abre seletor de arquivo para anexar ao lancamento."""
        selected = filedialog.askopenfilename(title="Selecionar arquivo para o registro")
        if not selected:
            return
        self.attachment_path = selected
        self.attachment_label.configure_text(Path(selected).name)
        self.open_attachment_button.configure(state="normal")

    def clear_attachment(self) -> None:
        """Remove o anexo atual do formulario."""
        self.attachment_path = ""
        self.attachment_label.configure_text("Nenhum arquivo anexado")
        self.open_attachment_button.configure(state="disabled")

    def open_current_attachment(self) -> None:
        """Abre o arquivo anexado atualmente no formulario."""
        try:
            open_attachment(self.attachment_path)
        except (ValueError, FileNotFoundError) as exc:
            messagebox.showerror("Anexo indisponível", str(exc))

    def save(self) -> None:
        """Valida e salva a movimentação, depois limpa o formulário."""
        is_service = self.type_selector.get() == self.SERVICE_OPERATION
        self.value_entry.format_current()
        if not is_service and self.category_selector.get() == "Sem categorias":
            messagebox.showerror("Cadastro inválido", "Cadastre ao menos uma categoria antes de lançar movimentações.")
            return
        if self.person_selector.get() == "Sem cadastros":
            messagebox.showerror("Cadastro inválido", "Cadastre ao menos uma pessoa ou empresa antes de lançar movimentações.")
            return
        try:
            if is_service:
                technician_ids = self._selected_technician_ids()
                if not technician_ids:
                    raise ValueError("Selecione ao menos um técnico ativo.")
                movement, commissions = self.service.register_technical_service(
                    valor_servico=self.value_entry.get(),
                    descricao=self.description_entry.get(),
                    categoria="Serviços",
                    metodo=self.method_selector.get(),
                    pessoa=self.person_selector.get(),
                    tecnico_ids=technician_ids,
                    data_movimento=self.date_entry.get().strip() or None,
                    anexo=self.attachment_path,
                )
            else:
                movement = self.service.register_movement(
                    tipo=self.type_selector.get(),
                    valor=self.value_entry.get(),
                    descricao=self.description_entry.get(),
                    categoria=self.category_selector.get(),
                    metodo=self.method_selector.get(),
                    pessoa=self.person_selector.get(),
                    data_movimento=self.date_entry.get().strip() or None,
                    anexo=self.attachment_path,
                )
                commissions = []
        except ValueError as exc:
            messagebox.showerror("Cadastro inválido", str(exc))
            return

        if movement.valor >= 1000:
            messagebox.showwarning("Atenção", "Movimentação de valor alto registrada.")

        self._clear_form()
        self.refresh()
        if not commissions:
            messagebox.showinfo("Sucesso", "Movimentação registrada com sucesso.")
            self.on_saved(movement)
        else:
            messagebox.showinfo(
                "Sucesso",
                (
                    "Serviço técnico registrado com sucesso.\n\n"
                    f"Entrada: {self._currency(movement.valor)}\n"
                    f"Comissão total: {self._currency(sum(item.valor for item in commissions))}\n"
                    f"Empresa: {self._currency(movement.valor_empresa)}"
                ),
            )
            self.on_saved((movement, commissions))

    def _clear_form(self) -> None:
        """Restaura o formulário ao estado inicial para novo registro."""
        current_operation = self.type_selector.get()
        for entry in [self.value_entry, self.description_entry, self.date_entry]:
            entry.delete(0, "end")
        self.method_selector.set(PAYMENT_METHODS[0])
        self.clear_attachment()
        self.type_selector.set(current_operation)
        self._selected_technicians = []
        self._apply_default_person()
        self._render_selected_technicians()
        self._handle_operation_change()

    def _ensure_default_person(self) -> None:
        """Garante que o cadastro padrão de cliente exista antes de montar o combo."""
        people = [item.nome for item in self.service.list_people()]
        if self.DEFAULT_PERSON in people:
            return
        self.service.add_person(self.DEFAULT_PERSON)

    def _apply_default_person(self) -> None:
        """Define o cliente padrão em toda reinicialização do formulário."""
        values = list(self.person_selector.cget("values") or [])
        if self.DEFAULT_PERSON in values:
            self.person_selector.set(self.DEFAULT_PERSON)
        elif values and values[0] != "Sem cadastros":
            self.person_selector.set(values[0])

    @staticmethod
    def _currency(value: float) -> str:
        """Formata valor em real brasileiro."""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
