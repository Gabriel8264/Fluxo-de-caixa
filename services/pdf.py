from __future__ import annotations

"""Exportação PDF executiva e compacta, sem dependências externas."""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from core.models import Movement, MovementType
from services.cash_service import CashService


SYSTEM_NAME = "Fluxo de caixa diário"
PAGE_WIDTH = 842
PAGE_HEIGHT = 595
MARGIN = 34
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)


def gerar_pdf(
    service: CashService | None = None,
    output_path: str | Path = "relatorio.pdf",
    movements: list[Movement] | None = None,
    title: str = "Fluxo de Caixa",
    *,
    export_type: str = "Exportação",
    period_label: str | None = None,
    generated_at: datetime | None = None,
    summary: dict[str, object] | None = None,
    pdf_variant: str = "executivo",
) -> Path:
    """Gera um relatório financeiro PDF executivo e compacto."""
    del pdf_variant
    service = service or CashService()
    data = list(movements) if movements is not None else service.list_movements(limit=500)
    generated_at = generated_at or datetime.now()
    period_label = period_label or title
    summary_data = _summarize(data)
    analysis = _analyze_movements(data)

    page_stream = _executive_page(
        export_type=export_type,
        period_label=period_label,
        generated_at=generated_at,
        summary=summary_data,
        analysis=analysis,
    )
    pdf_bytes = _build_pdf_document([page_stream.encode("cp1252", "replace")])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pdf_bytes)
    return output


def _executive_page(
    *,
    export_type: str,
    period_label: str,
    generated_at: datetime,
    summary: dict[str, object],
    analysis: dict[str, object],
) -> str:
    commands: list[str] = []
    commands.extend(_header(export_type, period_label, generated_at))
    commands.extend(_summary_cards(summary, top_y=430))
    commands.extend(_narrative(summary, analysis, top_y=348))

    left_x = MARGIN
    right_x = MARGIN + (CONTENT_WIDTH / 2) + 8
    block_width = (CONTENT_WIDTH / 2) - 8

    commands.extend(
        _analysis_block(
            "Entradas e saídas",
            [
                f"Categoria com maior entrada: {_pair_display(analysis['top_entry_category'])}",
                f"Categoria com maior saída: {_pair_display(analysis['top_exit_category'])}",
                f"Maior entrada: {_movement_display(analysis['largest_entry'])}",
                f"Maior saída: {_movement_display(analysis['largest_exit'])}",
            ],
            x=left_x,
            top_y=218,
            width=block_width,
            height=102,
        )
    )
    commands.extend(
        _analysis_block(
            "Métodos e pessoas",
            [
                f"Método mais utilizado: {_pair_display(analysis['top_method'])}",
                f"Pessoa / empresa principal: {_pair_display(analysis['top_person'])}",
                f"Técnicos envolvidos: {analysis['technicians_label']}",
                f"Movimentações registradas: {summary['quantidade']}",
            ],
            x=right_x,
            top_y=218,
            width=block_width,
            height=102,
        )
    )
    commands.extend(
        _mini_bar_block(
            "Indicadores visuais",
            [
                ("Entradas", float(summary["entradas"]), max(float(summary["entradas"]), float(summary["saidas"]), abs(float(summary["saldo"])), 1.0), (0.12, 0.62, 0.37)),
                ("Saídas", float(summary["saidas"]), max(float(summary["entradas"]), float(summary["saidas"]), abs(float(summary["saldo"])), 1.0), (0.84, 0.27, 0.38)),
                ("Saldo", abs(float(summary["saldo"])), max(float(summary["entradas"]), float(summary["saidas"]), abs(float(summary["saldo"])), 1.0), (0.12, 0.43, 0.92)),
            ],
            x=MARGIN,
            top_y=108,
            width=CONTENT_WIDTH,
            height=88,
        )
    )
    return "".join(commands)


def _header(export_type: str, period_label: str, generated_at: datetime) -> list[str]:
    top = PAGE_HEIGHT - MARGIN - 44
    return [
        _fill_rect(MARGIN, top, CONTENT_WIDTH, 44, 0.07, 0.16, 0.27),
        _text(SYSTEM_NAME, MARGIN + 14, top + 27, font="F2", size=18, color=(1, 1, 1)),
        _text("Relatório financeiro PDF", MARGIN + CONTENT_WIDTH - 182, top + 27, font="F2", size=10.5, color=(0.90, 0.94, 0.98)),
        _text(export_type, MARGIN + 14, top - 14, size=9.5, color=(0.11, 0.16, 0.23)),
        _text(f"Período: {period_label}", MARGIN + 230, top - 14, size=9.5, color=(0.11, 0.16, 0.23)),
        _text(f"Gerado em: {generated_at.strftime('%d/%m/%Y %H:%M')}", PAGE_WIDTH - MARGIN - 175, top - 14, size=9.5, color=(0.37, 0.43, 0.52)),
    ]


def _summary_cards(summary: dict[str, object], *, top_y: int) -> list[str]:
    width = (CONTENT_WIDTH - 18) / 4
    positions = [MARGIN + idx * (width + 6) for idx in range(4)]
    cards = [
        ("Entradas", float(summary["entradas"]), (0.10, 0.62, 0.37), (0.92, 0.97, 0.94)),
        ("Saídas", float(summary["saidas"]), (0.84, 0.27, 0.38), (0.99, 0.93, 0.94)),
        ("Saldo líquido", float(summary["saldo"]), (0.12, 0.43, 0.92), (0.93, 0.95, 1.0)),
        ("Movimentações", int(summary["quantidade"]), (0.08, 0.14, 0.22), (0.95, 0.97, 0.99)),
    ]
    commands: list[str] = []
    for idx, (label, value, color, fill) in enumerate(cards):
        x = positions[idx]
        commands.append(_fill_rect(x, top_y, width, 54, *fill))
        commands.append(_stroke_rect(x, top_y, width, 54, 0.84, 0.89, 0.95))
        commands.append(_text(label, x + 10, top_y + 34, size=9, color=(0.36, 0.43, 0.52)))
        display = _format_currency(float(value)) if idx < 3 else str(value)
        commands.append(_text(display, x + 10, top_y + 13, font="F2", size=14.5, color=color))
    return commands


def _narrative(summary: dict[str, object], analysis: dict[str, object], *, top_y: int) -> list[str]:
    saldo = float(summary["saldo"])
    text = (
        f"No período analisado foram registradas {summary['quantidade']} movimentações. "
        f"O caixa encerrou o período com saldo {'positivo' if saldo >= 0 else 'negativo'} de {_format_currency(saldo)}. "
        f"A principal fonte de receita foi {analysis['top_entry_category'][0]}. "
        f"O principal destino dos gastos foi {analysis['top_exit_category'][0]}."
    )
    return [
        _fill_rect(MARGIN, top_y, CONTENT_WIDTH, 54, 0.96, 0.97, 0.99),
        _stroke_rect(MARGIN, top_y, CONTENT_WIDTH, 54, 0.84, 0.89, 0.95),
        _text_block(text, MARGIN + 12, top_y + 33, max_chars=124, size=10, color=(0.12, 0.17, 0.23), leading=12),
    ]


def _analysis_block(title: str, lines: list[str], *, x: float, top_y: int, width: float, height: float) -> list[str]:
    commands = [
        _fill_rect(x, top_y, width, height, 0.985, 0.988, 0.995),
        _stroke_rect(x, top_y, width, height, 0.84, 0.89, 0.95),
        _text(title, x + 12, top_y + height - 20, font="F2", size=11, color=(0.09, 0.14, 0.22)),
    ]
    y = top_y + height - 42
    for line in lines:
        commands.append(_text(line, x + 12, y, size=8.8, color=(0.12, 0.17, 0.23)))
        y -= 16
    return commands


def _mini_bar_block(title: str, bars: list[tuple[str, float, float, tuple[float, float, float]]], *, x: float, top_y: int, width: float, height: float) -> list[str]:
    commands = [
        _fill_rect(x, top_y, width, height, 0.985, 0.988, 0.995),
        _stroke_rect(x, top_y, width, height, 0.84, 0.89, 0.95),
        _text(title, x + 12, top_y + height - 20, font="F2", size=11, color=(0.09, 0.14, 0.22)),
    ]
    bar_y = top_y + height - 44
    label_width = 84
    # Reserva fixa maior para valores monetários longos, evitando risco de corte
    # quando o período tiver números mais altos.
    value_width = 116
    right_padding = 14
    bar_left = x + label_width + 8
    bar_right = x + width - value_width - right_padding
    usable = max(36, bar_right - bar_left)
    for label, value, maximum, color in bars:
        commands.append(_text(label, x + 12, bar_y + 2, size=8.8, color=(0.12, 0.17, 0.23)))
        commands.append(_text(_format_currency(value), x + width - value_width, bar_y + 2, size=8.8, color=(0.36, 0.43, 0.52)))
        commands.append(_fill_rect(bar_left, bar_y - 3, usable, 8, 0.88, 0.92, 0.97))
        ratio = 0.0 if maximum <= 0 else min(1.0, value / maximum)
        commands.append(_fill_rect(bar_left, bar_y - 3, usable * ratio, 8, *color))
        bar_y -= 20
    return commands


def _summarize(movements: list[Movement]) -> dict[str, object]:
    entradas = sum(m.valor for m in movements if m.movement_type is MovementType.ENTRADA)
    saidas = sum(m.valor for m in movements if m.movement_type is MovementType.SAIDA)
    saldo = sum(m.signed_value for m in movements)
    return {
        "entradas": round(entradas, 2),
        "saidas": round(saidas, 2),
        "saldo": round(saldo, 2),
        "quantidade": len(movements),
    }


def _analyze_movements(movements: list[Movement]) -> dict[str, object]:
    entry_categories: defaultdict[str, float] = defaultdict(float)
    exit_categories: defaultdict[str, float] = defaultdict(float)
    method_totals: defaultdict[str, float] = defaultdict(float)
    person_totals: defaultdict[str, float] = defaultdict(float)
    technicians: Counter[str] = Counter()
    largest_entry: Movement | None = None
    largest_exit: Movement | None = None

    for movement in movements:
        category = movement.categoria or "Sem categoria"
        method = movement.metodo or "Sem método"
        person = movement.pessoa or "Sem pessoa"
        method_totals[method] += float(movement.valor)
        person_totals[person] += abs(float(movement.valor))
        for technician in _technician_names(movement):
            technicians[technician] += 1
        if movement.movement_type is MovementType.ENTRADA:
            entry_categories[category] += float(movement.valor)
            if largest_entry is None or movement.valor > largest_entry.valor:
                largest_entry = movement
        else:
            exit_categories[category] += float(movement.valor)
            if largest_exit is None or movement.valor > largest_exit.valor:
                largest_exit = movement

    return {
        "top_entry_category": max(entry_categories.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "top_exit_category": max(exit_categories.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "top_method": max(method_totals.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "top_person": max(person_totals.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "technicians_label": ", ".join(name for name, _ in technicians.most_common(4)) or "Sem técnicos",
        "largest_entry": largest_entry,
        "largest_exit": largest_exit,
    }


def _technician_names(movement: Movement) -> list[str]:
    payload = (movement.divisao_tecnicos or "").strip()
    if payload:
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            loaded = []
        names = [str(item.get("nome") or "").strip() for item in loaded or [] if str(item.get("nome") or "").strip()]
        if names:
            return names
    return [name.strip() for name in (movement.tecnico or "").split(",") if name.strip()]


def _pair_display(item: tuple[str, float]) -> str:
    label, value = item
    return f"{label} · {_format_currency(float(value))}"


def _movement_display(movement: Movement | None) -> str:
    if movement is None:
        return "Sem dados"
    return f"{movement.categoria} · {_format_currency(float(movement.valor))} · {movement.formatted_date}"


def _build_pdf_document(page_streams: list[bytes]) -> bytes:
    objects: list[bytes] = [b""]

    def reserve_object() -> int:
        objects.append(b"")
        return len(objects) - 1

    def set_object(object_id: int, content: bytes) -> None:
        objects[object_id] = content

    def add_object(content: bytes) -> int:
        object_id = reserve_object()
        set_object(object_id, content)
        return object_id

    def add_stream(stream: bytes) -> int:
        header = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
        return add_object(header + stream + b"\nendstream")

    pages_id = reserve_object()
    font_regular_id = add_object(_font_object("Helvetica"))
    font_bold_id = add_object(_font_object("Helvetica-Bold"))

    page_ids: list[int] = []
    for stream in page_streams:
        stream_id = add_stream(stream)
        page_ids.append(
            add_object(
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R "
                    f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                    f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
                    f"/Contents {stream_id} 0 R >>"
                ).encode("ascii")
            )
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    set_object(pages_id, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii"))
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii"))
    return _serialize_pdf(objects, catalog_id)


def _font_object(name: str) -> bytes:
    return f"<< /Type /Font /Subtype /Type1 /BaseFont /{name} /Encoding /WinAnsiEncoding >>".encode("ascii")


def _serialize_pdf(objects: list[bytes], catalog_id: int) -> bytes:
    content_parts = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]
    current_offset = len(content_parts[0])
    for object_id, content in enumerate(objects[1:], start=1):
        offsets.append(current_offset)
        object_bytes = f"{object_id} 0 obj\n".encode("ascii") + content + b"\nendobj\n"
        content_parts.append(object_bytes)
        current_offset += len(object_bytes)
    xref_offset = current_offset
    xref_parts = [f"xref\n0 {len(objects)}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_parts.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = f"trailer\n<< /Size {len(objects)} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
    return b"".join(content_parts + xref_parts + [trailer])


def _fill_rect(x: float, y: float, width: float, height: float, r: float, g: float, b: float) -> str:
    return f"q {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f Q\n"


def _stroke_rect(x: float, y: float, width: float, height: float, r: float, g: float, b: float) -> str:
    return f"q {r:.3f} {g:.3f} {b:.3f} RG 0.6 w {x:.2f} {y:.2f} {width:.2f} {height:.2f} re S Q\n"


def _text(text: str, x: float, y: float, *, font: str = "F1", size: float = 8.5, color: tuple[float, float, float] = (0, 0, 0)) -> str:
    escaped = _pdf_escape(text)
    r, g, b = color
    return f"BT /{font} {size} Tf {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} Td ({escaped}) Tj ET\n"


def _text_block(text: str, x: float, y: float, *, max_chars: int, size: float, color: tuple[float, float, float], leading: float) -> str:
    lines: list[str] = []
    current = ""
    for part in text.split():
        candidate = f"{current} {part}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = part
    if current:
        lines.append(current)
    return "".join(_text(line, x, y - (idx * leading), size=size, color=color) for idx, line in enumerate(lines))


def _pdf_escape(value: str) -> str:
    text = value.encode("cp1252", "replace").decode("cp1252")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
