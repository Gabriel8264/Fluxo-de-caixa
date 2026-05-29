from __future__ import annotations
"""Janela principal da aplicação.

Coordena tema, barra superior, navegação entre views e atualização global do
estado do fluxo ativo.
"""

import customtkinter as ctk
from tkinter import messagebox

from core.app_paths import resource_file
from services.cash_service import CashService
from ui.cadastros import RegistriesView
from ui.dashboard import DashboardView
from ui.extrato import StatementView
from ui.historico import HistoryView
from ui.registro import RegisterView
from ui.theme import COLORS, FONTS, configure_theme


class App(ctk.CTk):
    """Container principal da interface desktop."""

    def __init__(self, service: CashService | None = None) -> None:
        """Inicializa serviços, layout base e tela inicial."""
        configure_theme()
        super().__init__()

        self.service = service or CashService()
        self.service.initialize()

        self.title("Fluxo de caixa diário")
        self.geometry("1480x900")
        self.minsize(1320, 780)
        self.configure(fg_color=COLORS["bg"])
        self._apply_window_icon()
        self.after(0, self._maximize_window)

        self.current_view: ctk.CTkFrame | None = None
        self.nav_buttons: dict[str, ctk.CTkButton] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_content()
        self.show_view("dashboard")

    def _apply_window_icon(self) -> None:
        """Aplica o ícone da aplicação quando o recurso estiver disponível."""
        icon_path = resource_file("assets/fluxo_caixa.ico")
        if not icon_path.exists():
            return
        try:
            self.iconbitmap(icon_path)
        except Exception:
            pass

    def _build_topbar(self) -> None:
        """Monta o topo azul já no formato compacto padrão da aplicação."""
        self.topbar = ctk.CTkFrame(self, fg_color=COLORS["night"], corner_radius=0)
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_columnconfigure(0, weight=1)

        self.nav_bar = ctk.CTkFrame(self.topbar, fg_color="#16283f", corner_radius=18)
        self.nav_bar.grid(row=0, column=0, sticky="ew", padx=24, pady=(10, 10))
        for column in range(5):
            self.nav_bar.grid_columnconfigure(column, weight=1)
        self.nav_bar.grid_columnconfigure(5, weight=0)

        items = [
            ("dashboard", "Painel diário"),
            ("register", "Novo registro"),
            ("statement", "Consultas e filtros"),
            ("registries", "Cadastros"),
            ("history", "Histórico"),
        ]
        for column, (key, label) in enumerate(items):
            button = ctk.CTkButton(
                self.nav_bar,
                text=label,
                command=lambda name=key: self.show_view(name),
                fg_color="transparent",
                hover_color="#28405f",
                text_color="#d6e0ec",
                height=34,
                corner_radius=12,
                font=("Segoe UI Semibold", 12),
                anchor="center",
                border_spacing=0,
            )
            button.grid(row=0, column=column, padx=6, pady=6, sticky="ew")
            self.nav_buttons[key] = button

        self.nav_controls = ctk.CTkFrame(self.nav_bar, fg_color="transparent")
        self.nav_controls.grid(row=0, column=5, padx=(12, 8), pady=6, sticky="e")

        self.nav_day_status = ctk.CTkLabel(
            self.nav_controls,
            text="",
            text_color="#b7c7da",
            font=FONTS["small"],
            anchor="e",
        )
        self.nav_day_status.grid(row=0, column=0, sticky="e")

    def _build_content(self) -> None:
        """Instancia as views principais e prepara a área de conteúdo."""
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(2, 24))
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.views = {
            "dashboard": DashboardView(
                self.content,
                self.service,
                on_create=self.open_register_view,
                on_start_day=self.handle_start_day,
            ),
            "statement": StatementView(self.content, self.service),
            "register": RegisterView(
                self.content,
                self.service,
                on_saved=self.handle_record_saved,
                on_open_registries=self.open_registries,
            ),
            "registries": RegistriesView(self.content, self.service),
            "history": HistoryView(self.content, self.service, on_changed=self._refresh_all_views),
        }

    def show_view(self, name: str) -> None:
        """Troca a view ativa, atualiza destaque da navegação e chama refresh."""
        if self.current_view is not None:
            self.current_view.grid_forget()

        self.current_view = self.views[name]
        self.current_view.grid(row=0, column=0, sticky="nsew")

        for key, button in self.nav_buttons.items():
            is_active = key == name
            button.configure(
                fg_color="#2c4567" if is_active else "transparent",
                text_color="white" if is_active else "#d6e0ec",
            )

        self._refresh_status()
        refresh = getattr(self.current_view, "refresh", None)
        if callable(refresh):
            refresh()

    def _refresh_status(self) -> None:
        """Atualiza o indicador do dia ativo exibido no topo compacto."""
        year, month, day = self.service.get_active_day().split("-")
        self.nav_day_status.configure(text=f"Fluxo ativo do dia: {day}/{month}/{year}")

    def open_register_view(self, movement_type: str | None = None) -> None:
        """Abre a tela de registro, opcionalmente já focada em um tipo."""
        register_view: RegisterView = self.views["register"]  # type: ignore[assignment]
        if movement_type:
            register_view.set_type(movement_type)
        self.show_view("register")

    def open_registries(self) -> None:
        """Abre a tela de cadastros auxiliares."""
        self.show_view("registries")

    def handle_start_day(self) -> None:
        """Inicia um novo dia ativo e propaga a atualização para todas as views."""
        new_day = self.service.start_new_day()
        self._refresh_all_views()
        year, month, day = new_day.split("-")
        messagebox.showinfo(
            "Novo fluxo diário",
            f"O fluxo ativo agora é {day}/{month}/{year}. Os dias anteriores permanecem disponíveis no histórico.",
        )
        self.show_view("dashboard")

    def handle_record_saved(self, _: object = None) -> None:
        """Reage ao salvamento de lançamento recarregando as views dependentes."""
        self._refresh_all_views()
        if self.current_view is not self.views["register"]:
            self.show_view("register")

    def _refresh_all_views(self) -> None:
        """Dispara refresh em todas as telas e atualiza o topo."""
        self._refresh_status()
        for view in self.views.values():
            refresh = getattr(view, "refresh", None)
            if callable(refresh):
                refresh()

    def _maximize_window(self) -> None:
        """Maximiza a janela ao abrir, com fallback por geometry."""
        try:
            self.state("zoomed")
        except Exception:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            self.geometry(f"{screen_width}x{screen_height}+0+0")
