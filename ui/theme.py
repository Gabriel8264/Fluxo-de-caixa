import customtkinter as ctk


COLORS = {
    "bg": "#eef3f8",
    "surface": "#ffffff",
    "surface_alt": "#f4f7fb",
    "text": "#102033",
    "muted": "#5d6b7c",
    "primary": "#1d73d4",
    "primary_hover": "#1458a9",
    "success": "#1f9d66",
    "danger": "#d14b67",
    "warning": "#b27a15",
    "border": "#d7e1ec",
    "ink": "#0d1726",
    "night": "#122033",
}

FONTS = {
    "title": ("Segoe UI Semibold", 28),
    "subtitle": ("Segoe UI Semibold", 20),
    "body": ("Segoe UI", 13),
    "body_bold": ("Segoe UI Semibold", 13),
    "small": ("Segoe UI", 11),
}


def configure_theme() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
