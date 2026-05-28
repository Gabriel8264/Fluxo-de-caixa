from __future__ import annotations
"""Tela de cadastros auxiliares.

Centraliza a manutencao de categorias e pessoas/empresas usadas nas
movimentacoes do fluxo de caixa.
"""

import customtkinter as ctk

from services.cash_service import CashService
from ui.theme import COLORS, FONTS
from ui.widgets import RegistryManagerFrame, TechnicianManagerFrame


class RegistriesView(ctk.CTkFrame):
    """View de gerenciamento dos cadastros auxiliares do sistema."""

    def __init__(self, master, service: CashService) -> None:
        """Monta abas independentes para categorias e pessoas/empresas."""
        super().__init__(master, fg_color="transparent")
        self.service = service

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Cadastros auxiliares", font=FONTS["title"], text_color=COLORS["text"]).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        ctk.CTkLabel(
            self,
            text="Gerencie listas usadas nos lançamentos.",
            font=FONTS["body"],
            text_color=COLORS["muted"],
            wraplength=1040,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 18))

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
        self.tabs.add("Categorias")
        self.tabs.add("Pessoas e empresas")
        self.tabs.add("Técnicos e comissões")

        categories_tab = self.tabs.tab("Categorias")
        categories_tab.grid_columnconfigure(0, weight=1)
        people_tab = self.tabs.tab("Pessoas e empresas")
        people_tab.grid_columnconfigure(0, weight=1)
        technicians_tab = self.tabs.tab("Técnicos e comissões")
        technicians_tab.grid_columnconfigure(0, weight=1)

        self.category_manager = RegistryManagerFrame(
            categories_tab,
            title="Categorias",
            subtitle="Adicionar, editar e excluir.",
            add_callback=self.service.add_category,
            update_callback=self.service.update_category,
            delete_callback=self.service.delete_category,
            list_callback=self.service.list_categories,
            item_label="Categoria",
        )
        self.category_manager.grid(row=0, column=0, sticky="nsew", pady=(12, 0))

        self.people_manager = RegistryManagerFrame(
            people_tab,
            title="Pessoas e empresas",
            subtitle="Adicionar, editar e excluir.",
            add_callback=self.service.add_person,
            update_callback=self.service.update_person,
            delete_callback=self.service.delete_person,
            list_callback=self.service.list_people,
            item_label="Pessoa/empresa",
        )
        self.people_manager.grid(row=0, column=0, sticky="nsew", pady=(12, 0))

        self.technician_manager = TechnicianManagerFrame(
            technicians_tab,
            title="Técnicos e comissões",
            subtitle="Nome, comissão, empresa e status.",
            add_callback=self.service.add_technician,
            update_callback=self.service.update_technician,
            delete_callback=self.service.delete_technician,
            list_callback=self.service.list_technicians,
        )
        self.technician_manager.grid(row=0, column=0, sticky="nsew", pady=(12, 0))

    def refresh(self) -> None:
        """Atualiza as listas exibidas nas duas abas de cadastro."""
        self.category_manager.refresh()
        self.people_manager.refresh()
        self.technician_manager.refresh()
