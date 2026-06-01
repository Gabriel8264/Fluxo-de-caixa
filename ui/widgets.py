from __future__ import annotations
"""Componentes reutilizaveis da interface.

Concentra widgets customizados e estilos compartilhados entre as telas para
reduzir duplicacao de layout e comportamento.
"""

from collections.abc import Callable
from datetime import date
import tkinter as tk
from tkinter import font as tkfont, ttk

import customtkinter as ctk

from ui.theme import COLORS, FONTS


def _mousewheel_steps(event) -> int:
    """Normaliza a intensidade da roda do mouse para widgets Tk."""

    delta = getattr(event, "delta", 0)
    if delta:
        steps = int(-delta / 120)
        return steps if steps != 0 else (-1 if delta > 0 else 1)
    num = getattr(event, "num", None)
    if num == 4:
        return -1
    if num == 5:
        return 1
    return 0


def _bind_scrollable_mousewheel(scrollable_frame: ctk.CTkScrollableFrame, *, units_per_step: int = 4) -> None:
    """Liga a roda do mouse ao canvas interno do CTkScrollableFrame."""

    canvas = getattr(scrollable_frame, "_parent_canvas", None)
    if canvas is None:
        return

    def on_mousewheel(event) -> str | None:
        try:
            steps = _mousewheel_steps(event)
            if steps == 0:
                return None
            canvas.yview_scroll(steps * units_per_step, "units")
            return "break"
        except tk.TclError:
            return None

    def bind_tree(widget) -> None:
        try:
            if not getattr(widget, "_codex_mousewheel_bound", False):
                widget.bind("<MouseWheel>", on_mousewheel, add="+")
                widget.bind("<Button-4>", on_mousewheel, add="+")
                widget.bind("<Button-5>", on_mousewheel, add="+")
                widget._codex_mousewheel_bound = True
        except Exception:
            return
        for child in widget.winfo_children():
            bind_tree(child)

    bind_tree(scrollable_frame)


def bind_treeview_mousewheel(tree: ttk.Treeview, *, units_per_step: int = 3) -> None:
    """Garante rolagem consistente da roda do mouse em tabelas ttk."""

    if getattr(tree, "_codex_mousewheel_bound", False):
        return

    def on_mousewheel(event) -> str | None:
        try:
            steps = _mousewheel_steps(event)
            if steps == 0:
                return None
            tree.yview_scroll(steps * units_per_step, "units")
            return "break"
        except tk.TclError:
            return None

    tree.bind("<MouseWheel>", on_mousewheel, add="+")
    tree.bind("<Button-4>", on_mousewheel, add="+")
    tree.bind("<Button-5>", on_mousewheel, add="+")
    tree._codex_mousewheel_bound = True


class MarqueeLabel(ctk.CTkFrame):
    """Label com rolagem horizontal automatica para textos longos."""

    def __init__(
        self,
        master,
        *,
        text: str = "",
        text_color: str | None = None,
        font: tuple | None = None,
        height: int = 28,
        speed: int = 2,
        pause_ms: int = 1200,
        fg_color: str = "transparent",
        corner_radius: int = 0,
    ) -> None:
        super().__init__(master, fg_color=fg_color, corner_radius=corner_radius)
        self._text = text
        self._text_color = text_color or COLORS["text"]
        self._font = font or FONTS["body"]
        self._height = height
        self._speed = speed
        self._pause_ms = pause_ms
        self._text_id: int | None = None
        self._job: str | None = None
        self._needs_scroll = False

        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            height=height,
            bg=self._resolve_color(fg_color),
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.canvas.grid(row=0, column=0, sticky="ew")
        self.bind("<Configure>", self._redraw)
        self.canvas.bind("<Configure>", self._redraw)
        self.after(60, self._redraw)

    def configure_text(self, text: str) -> None:
        """Atualiza o texto exibido e recalcula a necessidade de rolagem."""
        self._text = text
        self._redraw()

    def _resolve_color(self, color: str) -> str:
        resolved = self.winfo_toplevel().cget("fg_color") if color == "transparent" else color
        if isinstance(resolved, (tuple, list)):
            return resolved[0]
        return resolved

    def _redraw(self, _event=None) -> None:
        self._cancel_job()
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), self.winfo_width(), 40)
        text_font = tkfont.Font(family=self._font[0], size=self._font[1], weight="bold" if "Semibold" in self._font[0] else "normal")
        text_width = text_font.measure(self._text)
        self._text_id = self.canvas.create_text(0, self._height // 2, anchor="w", text=self._text, fill=self._text_color, font=self._font)
        if text_width <= width - 8:
            self.canvas.coords(self._text_id, 4, self._height // 2)
            self._needs_scroll = False
            return

        self._needs_scroll = True
        self.canvas.coords(self._text_id, 4, self._height // 2)
        self._job = self.after(self._pause_ms, lambda: self._animate(width, text_width))

    def _animate(self, canvas_width: int, text_width: int) -> None:
        if not self._needs_scroll or self._text_id is None:
            return
        x, y = self.canvas.coords(self._text_id)
        min_x = -(text_width - canvas_width + 12)
        if x <= min_x:
            self.canvas.coords(self._text_id, 4, y)
            self._job = self.after(self._pause_ms, lambda: self._animate(canvas_width, text_width))
            return
        self.canvas.move(self._text_id, -self._speed, 0)
        self._job = self.after(35, lambda: self._animate(canvas_width, text_width))

    def _cancel_job(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def destroy(self) -> None:
        self._cancel_job()
        super().destroy()


class Card(ctk.CTkFrame):
    """Card simples para exibir titulo, valor e subtitulo."""

    def __init__(self, master, *, title: str, value: str, accent: str, subtitle: str = "") -> None:
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=title, text_color=COLORS["muted"], font=FONTS["small"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 4)
        )
        ctk.CTkLabel(self, text=value, text_color=accent, font=("Segoe UI Semibold", 26)).grid(
            row=1, column=0, sticky="w", padx=18
        )
        ctk.CTkLabel(
            self,
            text=subtitle,
            text_color=COLORS["muted"],
            font=FONTS["small"],
            wraplength=240,
            justify="left",
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(4, 16))


class SectionFrame(ctk.CTkFrame):
    """Container visual padrao com titulo e subtitulo opcionais."""

    def __init__(self, master, *, title: str, subtitle: str | None = None, subtitle_wraplength: int = 720) -> None:
        super().__init__(master, fg_color=COLORS["surface"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title, text_color=COLORS["text"], font=FONTS["subtitle"], anchor="w", justify="left").grid(
            row=0, column=0, sticky="w", padx=20, pady=(18, 2)
        )
        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                text_color=COLORS["muted"],
                font=FONTS["small"],
                wraplength=subtitle_wraplength,
                justify="left",
                anchor="w",
            ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))


class MetricBadge(ctk.CTkFrame):
    """Badge compacto para destacar metricas de apoio."""

    def __init__(self, master, *, title: str, value: str, accent: str) -> None:
        super().__init__(master, fg_color=COLORS["surface_alt"], corner_radius=16)
        ctk.CTkLabel(self, text=title, font=FONTS["small"], text_color=COLORS["muted"], anchor="w", justify="left").pack(
            anchor="w", fill="x", padx=14, pady=(12, 2)
        )
        ctk.CTkLabel(self, text=value, font=("Segoe UI Semibold", 16), text_color=accent).pack(anchor="w", padx=14, pady=(0, 12))


class DetailMarqueeBar(ctk.CTkFrame):
    """Barra de detalhe com suporte a texto deslizante."""

    def __init__(self, master, *, fg_color: str | None = None) -> None:
        super().__init__(master, fg_color=fg_color or COLORS["surface_alt"], corner_radius=14)
        self.grid_columnconfigure(0, weight=1)
        self.label = MarqueeLabel(
            self,
            text="",
            text_color=COLORS["text"],
            font=FONTS["body"],
            height=30,
            fg_color=fg_color or COLORS["surface_alt"],
        )
        self.label.grid(row=0, column=0, sticky="ew", padx=12, pady=8)

    def set_text(self, text: str) -> None:
        """Atualiza o conteudo textual da barra de detalhe."""
        self.label.configure_text(text)


class DateMaskEntry(ctk.CTkEntry):
    """Campo de entrada com mascara automatica para data brasileira."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.bind("<KeyRelease>", self._on_change)

    def _on_change(self, _event=None) -> None:
        raw = "".join(char for char in self.get() if char.isdigit())[:8]
        parts = []
        if len(raw) >= 2:
            parts.append(raw[:2])
        elif raw:
            parts.append(raw)
        if len(raw) >= 4:
            parts.append(raw[2:4])
        elif len(raw) > 2:
            parts.append(raw[2:])
        if len(raw) > 4:
            parts.append(raw[4:])
        formatted = "/".join(parts)
        self.delete(0, "end")
        self.insert(0, formatted)
        self.icursor(len(formatted))

    def set_today(self) -> None:
        """Preenche o campo com a data atual no formato dd/mm/aaaa."""
        self.delete(0, "end")
        self.insert(0, date.today().strftime("%d/%m/%Y"))


def build_treeview_style(root) -> ttk.Style:
    """Configura o estilo padrao das tabelas ttk usadas pela aplicacao."""
    style = ttk.Style(root)
    style.theme_use("default")
    style.configure(
        "Cash.Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        rowheight=40,
        borderwidth=0,
        font=("Segoe UI", 11),
    )
    style.configure(
        "Cash.Treeview.Heading",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        relief="flat",
        font=("Segoe UI Semibold", 11),
        padding=8,
    )
    style.map("Cash.Treeview", background=[("selected", "#d8e7ff")], foreground=[("selected", COLORS["text"])])
    style.map("Cash.Treeview.Heading", background=[("active", COLORS["surface_alt"])])
    return style


class RegistryManagerFrame(SectionFrame):
    """Bloco reutilizavel para CRUD simples de cadastros auxiliares."""

    def __init__(
        self,
        master,
        *,
        title: str,
        subtitle: str,
        add_callback: Callable[[str], object],
        update_callback: Callable[[int, str], None],
        delete_callback: Callable[[int], None],
        list_callback: Callable[[], list[object]],
        item_label: str,
    ) -> None:
        super().__init__(master, title=title, subtitle=subtitle)
        self.add_callback = add_callback
        self.update_callback = update_callback
        self.delete_callback = delete_callback
        self.list_callback = list_callback
        self.item_label = item_label
        self.selected_id: int | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(0, weight=1)

        self.name_entry = ctk.CTkEntry(form, placeholder_text=f"Nome da {item_label.lower()}", height=42)
        self.name_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(actions, text="Salvar", width=96, command=self.save_item).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Novo",
            width=80,
            command=self.clear_selection,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        ).grid(row=0, column=1)

        self.feedback = MarqueeLabel(self, text="", text_color=COLORS["muted"], font=FONTS["small"], height=24, fg_color=COLORS["surface"])
        self.feedback.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 8))

        self.list_area = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface_alt"], corner_radius=18)
        self.list_area.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.list_area.grid_columnconfigure(0, weight=1)
        _bind_scrollable_mousewheel(self.list_area, units_per_step=48)

    def refresh(self) -> None:
        """Reconstroi a lista visual de itens cadastrados."""
        for child in self.list_area.winfo_children():
            child.destroy()

        for item in self.list_callback():
            row = ctk.CTkFrame(self.list_area, fg_color=COLORS["surface"], corner_radius=14)
            row.grid(sticky="ew", pady=6)
            row.grid_columnconfigure(0, weight=1)
            MarqueeLabel(
                row,
                text=item.nome,
                text_color=COLORS["text"],
                font=FONTS["body_bold"],
                height=28,
                fg_color=COLORS["surface"],
            ).grid(row=0, column=0, padx=14, pady=12, sticky="ew")
            ctk.CTkButton(
                row,
                text="Editar",
                width=74,
                height=32,
                command=lambda current=item: self.select_item(current.id, current.nome),
                fg_color=COLORS["surface_alt"],
                text_color=COLORS["text"],
                hover_color="#dfe7f3",
            ).grid(row=0, column=1, padx=6, pady=8)
            ctk.CTkButton(
                row,
                text="Excluir",
                width=74,
                height=32,
                command=lambda current=item: self.delete_item(current.id),
                fg_color="#fee2e2",
                text_color="#a33434",
                hover_color="#fecaca",
            ).grid(row=0, column=2, padx=(0, 10), pady=8)
        _bind_scrollable_mousewheel(self.list_area, units_per_step=48)

    def select_item(self, item_id: int, name: str) -> None:
        """Carrega um item existente no formulario para edicao."""
        self.selected_id = item_id
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, name)
        self.feedback.configure_text(f"Editando {self.item_label.lower()}: {name}")

    def clear_selection(self) -> None:
        """Limpa a selecao atual e volta o formulario para modo novo item."""
        self.selected_id = None
        self.name_entry.delete(0, "end")
        self.feedback.configure_text("")

    def save_item(self) -> None:
        """Decide entre criar ou atualizar item conforme a selecao atual."""
        name = self.name_entry.get().strip()
        if not name:
            self.feedback.configure_text(f"Informe o nome da {self.item_label.lower()}.")
            return
        try:
            if self.selected_id is None:
                self.add_callback(name)
                self.feedback.configure_text(f"{self.item_label} cadastrada com sucesso.")
            else:
                self.update_callback(self.selected_id, name)
                self.feedback.configure_text(f"{self.item_label} atualizada com sucesso.")
        except ValueError as exc:
            self.feedback.configure_text(str(exc))
            return
        self.clear_selection()
        self.refresh()

    def delete_item(self, item_id: int) -> None:
        """Exclui item do cadastro e atualiza a lista visual."""
        self.delete_callback(item_id)
        if self.selected_id == item_id:
            self.clear_selection()
        self.feedback.configure_text(f"{self.item_label} removida.")
        self.refresh()


class TechnicianManagerFrame(SectionFrame):
    """CRUD visual para técnicos e regras de comissão."""

    def __init__(
        self,
        master,
        *,
        title: str,
        subtitle: str,
        add_callback: Callable[[str, str, str], object],
        update_callback: Callable[[int, str, str, str], None],
        delete_callback: Callable[[int], None],
        list_callback: Callable[[], list[object]],
    ) -> None:
        super().__init__(master, title=title, subtitle=subtitle)
        self.add_callback = add_callback
        self.update_callback = update_callback
        self.delete_callback = delete_callback
        self.list_callback = list_callback
        self.selected_id: int | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(0, weight=2)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=1)
        form.grid_columnconfigure(3, weight=1)

        self.name_entry = ctk.CTkEntry(form, placeholder_text="Nome do técnico", height=42)
        self.name_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 12))

        self.commission_entry = ctk.CTkEntry(form, placeholder_text="Comissão (%)", height=42)
        self.commission_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(0, 12))
        self.commission_entry.bind("<KeyRelease>", lambda _event: self._refresh_company_percent())

        self.company_label = ctk.CTkLabel(
            form,
            text="Empresa: 100%",
            font=FONTS["body_bold"],
            text_color=COLORS["muted"],
            anchor="w",
        )
        self.company_label.grid(row=0, column=2, sticky="w", padx=(0, 10), pady=(0, 12))

        self.status_selector = ctk.CTkOptionMenu(
            form,
            values=["ativo", "inativo"],
            height=42,
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
        )
        self.status_selector.grid(row=0, column=3, sticky="ew", pady=(0, 12))
        self.status_selector.set("ativo")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        actions.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(actions, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(left, text="Salvar", width=96, command=self.save_item).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            left,
            text="Novo",
            width=80,
            command=self.clear_selection,
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            hover_color="#dfe7f3",
        ).grid(row=0, column=1)

        self.feedback = MarqueeLabel(self, text="", text_color=COLORS["muted"], font=FONTS["small"], height=24, fg_color=COLORS["surface"])
        self.feedback.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 8))

        self.list_area = ctk.CTkScrollableFrame(self, fg_color=COLORS["surface_alt"], corner_radius=18)
        self.list_area.grid(row=5, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.list_area.grid_columnconfigure(0, weight=1)
        _bind_scrollable_mousewheel(self.list_area, units_per_step=48)

    def _refresh_company_percent(self) -> None:
        raw = self.commission_entry.get().strip().replace("%", "").replace(",", ".")
        if not raw:
            self.company_label.configure(text="Empresa: 100%")
            return
        try:
            technician_percent = float(raw)
        except ValueError:
            self.company_label.configure(text="Empresa: --")
            return
        company_percent = 100 - technician_percent
        self.company_label.configure(text=f"Empresa: {company_percent:.2f}%")

    def refresh(self) -> None:
        """Reconstroi a lista visual de técnicos cadastrados."""
        for child in self.list_area.winfo_children():
            child.destroy()

        for item in self.list_callback():
            row = ctk.CTkFrame(self.list_area, fg_color=COLORS["surface"], corner_radius=14)
            row.grid(sticky="ew", pady=6)
            row.grid_columnconfigure(0, weight=1)

            title = f"{item.nome} · {item.percentual_comissao:.2f}% técnico · {item.percentual_empresa:.2f}% empresa"
            MarqueeLabel(
                row,
                text=title,
                text_color=COLORS["text"],
                font=FONTS["body_bold"],
                height=28,
                fg_color=COLORS["surface"],
            ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="ew")
            ctk.CTkLabel(
                row,
                text=f"Status: {item.status}",
                font=FONTS["small"],
                text_color=COLORS["muted"],
                anchor="w",
            ).grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")
            ctk.CTkButton(
                row,
                text="Editar",
                width=74,
                height=32,
                command=lambda current=item: self.select_item(current),
                fg_color=COLORS["surface_alt"],
                text_color=COLORS["text"],
                hover_color="#dfe7f3",
            ).grid(row=0, column=1, rowspan=2, padx=6, pady=8)
            ctk.CTkButton(
                row,
                text="Excluir",
                width=74,
                height=32,
                command=lambda current=item: self.delete_item(current.id),
                fg_color="#fee2e2",
                text_color="#a33434",
                hover_color="#fecaca",
            ).grid(row=0, column=2, rowspan=2, padx=(0, 10), pady=8)
        _bind_scrollable_mousewheel(self.list_area, units_per_step=48)

    def select_item(self, technician) -> None:
        """Carrega técnico no formulário para edição."""
        self.selected_id = technician.id
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, technician.nome)
        self.commission_entry.delete(0, "end")
        self.commission_entry.insert(0, f"{technician.percentual_comissao:.2f}")
        self.status_selector.set(technician.status)
        self._refresh_company_percent()
        self.feedback.configure_text(f"Editando técnico: {technician.nome}")

    def clear_selection(self) -> None:
        """Limpa o formulário e volta ao modo de novo técnico."""
        self.selected_id = None
        self.name_entry.delete(0, "end")
        self.commission_entry.delete(0, "end")
        self.status_selector.set("ativo")
        self.company_label.configure(text="Empresa: 100%")
        self.feedback.configure_text("")

    def save_item(self) -> None:
        """Cria ou atualiza técnico conforme a seleção atual."""
        name = self.name_entry.get().strip()
        commission = self.commission_entry.get().strip()
        status = self.status_selector.get()
        if not name:
            self.feedback.configure_text("Informe o nome do técnico.")
            return
        if not commission:
            self.feedback.configure_text("Informe a comissão do técnico.")
            return
        try:
            if self.selected_id is None:
                self.add_callback(name, commission, status)
                self.feedback.configure_text("Técnico cadastrado com sucesso.")
            else:
                self.update_callback(self.selected_id, name, commission, status)
                self.feedback.configure_text("Técnico atualizado com sucesso.")
        except ValueError as exc:
            self.feedback.configure_text(str(exc))
            return
        self.clear_selection()
        self.refresh()

    def delete_item(self, technician_id: int | None) -> None:
        """Exclui técnico e atualiza a lista."""
        if technician_id is None:
            return
        self.delete_callback(technician_id)
        if self.selected_id == technician_id:
            self.clear_selection()
        self.feedback.configure_text("Técnico removido.")
        self.refresh()
