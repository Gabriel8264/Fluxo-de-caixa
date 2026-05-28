from __future__ import annotations
"""Tela de cadastro de novas movimentacoes.

Separa o fluxo em formulario principal e orientacoes de apoio para manter o
uso diario simples e legivel.
"""

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.models import MovementType, PAYMENT_METHODS
from services.attachments import open_attachment
from services.cash_service import CashService
from ui.theme import COLORS, FONTS
from ui.widgets import DateMaskEntry, MarqueeLabel, SectionFrame


class RegisterView(ctk.CTkScrollableFrame):
    """View de registro de entradas e saidas com suporte a anexos."""

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

        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_tabs()

    def _build_header(self) -> None:
        """Cria o cabecalho explicativo da tela de registro."""
        ctk.CTkLabel(self, text="Novo registro", font=FONTS["title"], text_color=COLORS["text"]).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        ctk.CTkLabel(
            self,
            text="Preencha e salve a movimentação.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            wraplength=980,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 18))

    def _build_tabs(self) -> None:
        """Separa a tela entre lancamento e apoio operacional."""
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
        self.tabs.add("Lançamento")
        self.tabs.add("Apoio")

        self.form_tab = self.tabs.tab("Lançamento")
        self.form_tab.grid_columnconfigure(0, weight=1)

        self.support_tab = self.tabs.tab("Apoio")
        self.support_tab.grid_columnconfigure(0, weight=1)

        self._build_form()
        self._build_support()

    def _build_form(self) -> None:
        """Monta o formulario principal de cadastro da movimentacao."""
        section = SectionFrame(
            self.form_tab,
            title="Dados da movimentação",
            subtitle="Campos do lançamento.",
            subtitle_wraplength=840,
        )
        section.grid(row=0, column=0, sticky="nsew", pady=(12, 0))
        section.grid_columnconfigure(0, weight=1)
        section.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(section, text="Tipo", font=FONTS["body_bold"], text_color=COLORS["text"]).grid(
            row=2, column=0, padx=20, sticky="w"
        )
        self.type_selector = ctk.CTkSegmentedButton(section, values=[movement.value for movement in MovementType])
        self.type_selector.grid(row=3, column=0, columnspan=2, padx=20, pady=(8, 18), sticky="ew")
        self.type_selector.set(MovementType.ENTRADA.value)

        self.value_entry = self._build_entry(section, row=4, column=0, label="Valor", placeholder="0,00")
        self.description_entry = self._build_entry(section, row=4, column=1, label="Descrição", placeholder="Ex.: venda no balcão")

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
            values=PAYMENT_METHODS,
            height=42,
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
        )
        self.method_selector.grid(row=9, column=1, padx=20, pady=(8, 18), sticky="ew")
        self.method_selector.set(PAYMENT_METHODS[0])

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
        ).grid(row=12, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="ew")

    def _build_support(self) -> None:
        """Renderiza orientacoes curtas para uso consistente da tela."""
        support = SectionFrame(
            self.support_tab,
            title="Apoio ao lançamento",
            subtitle="Atalhos úteis.",
            subtitle_wraplength=820,
        )
        support.grid(row=0, column=0, sticky="nsew", pady=(12, 0))
        support.grid_columnconfigure(0, weight=1)

        tips = [
            "Use categoria e pessoa para localizar registros depois.",
            "O botão Hoje preenche a data atual.",
            "Anexos ajudam a guardar comprovantes.",
        ]
        for index, text in enumerate(tips, start=2):
            ctk.CTkLabel(
                support,
                text=f"- {text}",
                wraplength=760,
                justify="left",
                anchor="w",
                text_color=COLORS["text"],
                font=FONTS["body"],
            ).grid(row=index, column=0, sticky="ew", padx=20, pady=8)

        ctk.CTkButton(
            support,
            text="Gerenciar cadastros",
            command=self.on_open_registries,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
            height=44,
        ).grid(row=6, column=0, sticky="ew", padx=20, pady=(18, 20))

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
        self.tabs.set("Lançamento")

    def refresh(self) -> None:
        """Recarrega categorias e pessoas disponiveis para selecao."""
        categories = [item.nome for item in self.service.list_categories()]
        people = [item.nome for item in self.service.list_people()]
        self.category_selector.configure(values=categories or ["Sem categorias"])
        self.person_selector.configure(values=people or ["Sem cadastros"])
        if categories:
            self.category_selector.set(categories[0])
        if people:
            self.person_selector.set(people[0])

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
        """Valida e salva a movimentacao, depois limpa o formulario."""
        if self.category_selector.get() == "Sem categorias":
            messagebox.showerror("Cadastro inválido", "Cadastre ao menos uma categoria antes de lançar movimentações.")
            return
        if self.person_selector.get() == "Sem cadastros":
            messagebox.showerror("Cadastro inválido", "Cadastre ao menos uma pessoa ou empresa antes de lançar movimentações.")
            return
        try:
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
        except ValueError as exc:
            messagebox.showerror("Cadastro inválido", str(exc))
            return

        if movement.valor >= 1000:
            messagebox.showwarning("Atenção", "Movimentação de valor alto registrada.")

        self._clear_form()
        self.refresh()
        messagebox.showinfo("Sucesso", "Movimentação registrada com sucesso.")
        self.on_saved(movement)

    def _clear_form(self) -> None:
        """Restaura o formulario ao estado inicial para novo registro."""
        for entry in [self.value_entry, self.description_entry, self.date_entry]:
            entry.delete(0, "end")
        self.type_selector.set(MovementType.ENTRADA.value)
        self.method_selector.set(PAYMENT_METHODS[0])
        self.clear_attachment()
