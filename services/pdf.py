from __future__ import annotations

"""Geracao de PDF sem bibliotecas externas.

O documento e montado por serializacao direta, com foco em clareza visual,
resumo executivo e tabela legivel mesmo com muitos registros.
"""

from datetime import datetime
from pathlib import Path
from textwrap import wrap

from core.models import Movement, MovementType
from services.cash_service import CashService


SYSTEM_NAME = "Fluxo de caixa diário"
PAGE_WIDTH = 842
PAGE_HEIGHT = 595
MARGIN = 34
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)
HEADER_HEIGHT = 42
BODY_FONT_SIZE = 9
SMALL_FONT_SIZE = 8
TITLE_FONT_SIZE = 18
LINE_HEIGHT = 13
ROW_PADDING = 4
FIRST_PAGE_TABLE_TOP = 255
FOLLOWING_PAGE_TABLE_TOP = 86
TABLE_HEADER_HEIGHT = 20
PAGE_BOTTOM = 42
TABLE_COLUMNS = [
    ("data", "Data", 62),
    ("tipo", "Tipo", 52),
    ("valor", "Valor", 72),
    ("categoria", "Categoria", 100),
    ("metodo", "Método", 70),
    ("pessoa", "Pessoa / empresa", 128),
    ("descricao", "Descrição", 260),
    ("anexo", "Anexo", 60),
]


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
) -> Path:
    """Gera PDF a partir dos movimentos informados ou consultados no servico."""
    service = service or CashService()
    dados = list(movements) if movements is not None else service.list_movements(limit=200)
    generated_at = generated_at or datetime.now()
    summary_data = summary or _summarize(dados)
    period_label = period_label or title

    page_streams = _build_page_streams(
        dados,
        title=title,
        export_type=export_type,
        period_label=period_label,
        generated_at=generated_at,
        summary=summary_data,
    )
    pdf_bytes = _build_pdf_document(page_streams)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pdf_bytes)
    return output


def _build_page_streams(
    movements: list[Movement],
    *,
    title: str,
    export_type: str,
    period_label: str,
    generated_at: datetime,
    summary: dict[str, object],
) -> list[bytes]:
    """Monta os streams de desenho de cada pagina."""
    rows = [_movement_row(movement) for movement in movements]
    pages: list[bytes] = []
    page_rows: list[dict[str, object]] = []
    page_number = 1
    available_top = FIRST_PAGE_TABLE_TOP
    current_y = available_top

    for row in rows:
        row_height = int(row["height"])
        if current_y - (TABLE_HEADER_HEIGHT + row_height) < PAGE_BOTTOM and page_rows:
            pages.append(
                _page_stream(
                    page_rows,
                    page_number=page_number,
                    total_pages=0,
                    title=title,
                    export_type=export_type,
                    period_label=period_label,
                    generated_at=generated_at,
                    summary=summary,
                    include_summary=page_number == 1,
                )
            )
            page_rows = []
            page_number += 1
            current_y = FOLLOWING_PAGE_TABLE_TOP
        page_rows.append(row)
        current_y -= row_height

    if not page_rows:
        page_rows = [_empty_row()]

    pages.append(
        _page_stream(
            page_rows,
            page_number=page_number,
            total_pages=0,
            title=title,
            export_type=export_type,
            period_label=period_label,
            generated_at=generated_at,
            summary=summary,
            include_summary=page_number == 1,
        )
    )

    total_pages = len(pages)
    return [
        _page_stream(
            page_rows if index == total_pages - 1 else None,
            page_number=index + 1,
            total_pages=total_pages,
            title=title,
            export_type=export_type,
            period_label=period_label,
            generated_at=generated_at,
            summary=summary,
            include_summary=index == 0,
            prebuilt_stream=pages[index],
        )
        for index in range(total_pages)
    ]


def _page_stream(
    page_rows: list[dict[str, object]] | None,
    *,
    page_number: int,
    total_pages: int,
    title: str,
    export_type: str,
    period_label: str,
    generated_at: datetime,
    summary: dict[str, object],
    include_summary: bool,
    prebuilt_stream: bytes | None = None,
) -> bytes:
    """Gera o stream de uma pagina."""
    if prebuilt_stream is not None and total_pages:
        body = prebuilt_stream.decode("cp1252")
        footer = _footer_commands(page_number, total_pages)
        return (body + footer).encode("cp1252", "replace")

    commands: list[str] = []
    commands.extend(_header_commands(title, export_type, period_label, generated_at))
    if include_summary:
        commands.extend(_summary_commands(summary))
        table_top = FIRST_PAGE_TABLE_TOP
    else:
        table_top = FOLLOWING_PAGE_TABLE_TOP

    commands.extend(_table_header_commands(table_top))
    y_cursor = table_top - TABLE_HEADER_HEIGHT
    for row in page_rows or []:
        commands.extend(_table_row_commands(row, y_cursor))
        y_cursor -= int(row["height"])

    if total_pages:
        commands.append(_footer_commands(page_number, total_pages))
    return "".join(commands).encode("cp1252", "replace")


def _header_commands(title: str, export_type: str, period_label: str, generated_at: datetime) -> list[str]:
    """Desenha o cabecalho institucional do documento."""
    commands = [
        _fill_rect(MARGIN, PAGE_HEIGHT - MARGIN - HEADER_HEIGHT, CONTENT_WIDTH, HEADER_HEIGHT, 0.07, 0.16, 0.27),
        _text(SYSTEM_NAME, MARGIN + 12, PAGE_HEIGHT - MARGIN - 16, font="F2", size=TITLE_FONT_SIZE, color=(1, 1, 1)),
        _text(export_type, MARGIN + 12, PAGE_HEIGHT - MARGIN - 31, font="F1", size=10, color=(0.86, 0.91, 0.97)),
        _text(f"Período: {period_label}", MARGIN, PAGE_HEIGHT - MARGIN - 58, font="F2", size=10, color=(0.11, 0.16, 0.23)),
        _text(f"Gerado em: {generated_at.strftime('%d/%m/%Y %H:%M')}", MARGIN + 230, PAGE_HEIGHT - MARGIN - 58, font="F1", size=10, color=(0.31, 0.38, 0.48)),
    ]
    return commands


def _summary_commands(summary: dict[str, object]) -> list[str]:
    """Desenha o resumo executivo do documento."""
    top = PAGE_HEIGHT - MARGIN - 94
    card_width = (CONTENT_WIDTH - 18) / 4
    positions = [MARGIN + (index * (card_width + 6)) for index in range(4)]
    cards = [
        ("Entradas", float(summary.get("entradas", 0.0)), (0.10, 0.62, 0.37), (0.92, 0.97, 0.94)),
        ("Saídas", float(summary.get("saidas", 0.0)), (0.84, 0.27, 0.38), (0.99, 0.93, 0.94)),
        ("Saldo líquido", float(summary.get("saldo", 0.0)), (0.12, 0.43, 0.92), (0.93, 0.95, 1.0)),
        ("Movimentações", int(summary.get("quantidade", 0)), (0.08, 0.14, 0.22), (0.95, 0.97, 0.99)),
    ]

    commands: list[str] = []
    for index, (label, value, color, fill) in enumerate(cards):
        x = positions[index]
        commands.append(_fill_rect(x, top - 62, card_width, 52, *fill))
        commands.append(_stroke_rect(x, top - 62, card_width, 52, 0.84, 0.89, 0.95))
        commands.append(_text(label, x + 10, top - 20, font="F1", size=9, color=(0.36, 0.43, 0.52)))
        display = _format_currency(float(value)) if index < 3 else str(value)
        commands.append(_text(display, x + 10, top - 40, font="F2", size=15, color=color))

    narrative = (
        f"No período selecionado, o caixa fechou com saldo {'positivo' if float(summary.get('saldo', 0.0)) >= 0 else 'negativo'} "
        f"de {_format_currency(float(summary.get('saldo', 0.0)))}. "
        f"As entradas somaram {_format_currency(float(summary.get('entradas', 0.0)))} e as saídas "
        f"{_format_currency(float(summary.get('saidas', 0.0)))}."
    )
    commands.append(_fill_rect(MARGIN, 286, CONTENT_WIDTH, 34, 0.96, 0.97, 0.99))
    commands.append(_stroke_rect(MARGIN, 286, CONTENT_WIDTH, 34, 0.84, 0.89, 0.95))
    commands.append(_text_block(narrative, MARGIN + 12, 307, max_chars=118, size=10, color=(0.12, 0.17, 0.23), leading=13))
    return commands


def _table_header_commands(table_top: int) -> list[str]:
    """Desenha o cabecalho da tabela de registros."""
    commands = [_fill_rect(MARGIN, table_top - TABLE_HEADER_HEIGHT, CONTENT_WIDTH, TABLE_HEADER_HEIGHT, 0.12, 0.43, 0.92)]
    x = MARGIN
    for _, label, width in TABLE_COLUMNS:
        commands.append(_text(label, x + 4, table_top - 14, font="F2", size=8, color=(1, 1, 1)))
        x += width
    return commands


def _table_row_commands(row: dict[str, object], y_top: int) -> list[str]:
    """Desenha uma linha da tabela com quebra automatica."""
    row_height = int(row["height"])
    fill = (0.96, 0.98, 0.99) if row["tipo"] == "Entrada" else (1.0, 0.97, 0.97)
    value_color = (0.10, 0.62, 0.37) if row["tipo"] == "Entrada" else (0.84, 0.27, 0.38)

    commands = [
        _fill_rect(MARGIN, y_top - row_height, CONTENT_WIDTH, row_height, *fill),
        _stroke_rect(MARGIN, y_top - row_height, CONTENT_WIDTH, row_height, 0.87, 0.91, 0.95),
    ]

    x = MARGIN
    baseline = y_top - 12
    commands.append(_text(str(row["data"]), x + 4, baseline, size=8.5))
    x += TABLE_COLUMNS[0][2]
    commands.append(_text(str(row["tipo"]), x + 4, baseline, size=8.5, color=value_color))
    x += TABLE_COLUMNS[1][2]
    commands.append(_text(_format_currency(float(row["valor"])), x + 4, baseline, font="F2", size=8.5, color=value_color))
    x += TABLE_COLUMNS[2][2]
    commands.append(_text(str(row["categoria"]), x + 4, baseline, size=8.5))
    x += TABLE_COLUMNS[3][2]
    commands.append(_text(str(row["metodo"]), x + 4, baseline, size=8.5))
    x += TABLE_COLUMNS[4][2]
    commands.extend(_text_block_lines(list(row["pessoa_lines"]), x + 4, baseline, size=8.5, leading=11))
    x += TABLE_COLUMNS[5][2]
    commands.extend(_text_block_lines(list(row["descricao_lines"]), x + 4, baseline, size=8.5, leading=11))
    x += TABLE_COLUMNS[6][2]
    commands.extend(_text_block_lines(list(row["anexo_lines"]), x + 4, baseline, size=8.5, leading=11, color=(0.33, 0.39, 0.48)))

    return commands


def _footer_commands(page_number: int, total_pages: int) -> str:
    """Desenha rodape padrao da pagina."""
    return _text(f"Página {page_number}/{total_pages}", PAGE_WIDTH - MARGIN - 60, 22, size=8.5, color=(0.38, 0.44, 0.53))


def _movement_row(movement: Movement) -> dict[str, object]:
    """Converte movimento em linha tabular com altura calculada."""
    pessoa_lines = _wrap_value(movement.pessoa, width=24)
    descricao_lines = _wrap_value(movement.descricao or "-", width=44)
    anexo_lines = _wrap_value("Sim" if movement.anexo else "Não", width=8)
    max_lines = max(1, len(pessoa_lines), len(descricao_lines), len(anexo_lines))
    row_height = max(22, (max_lines * 11) + ROW_PADDING + 6)
    return {
        "data": movement.formatted_date,
        "tipo": movement.display_type.capitalize(),
        "valor": movement.valor,
        "categoria": movement.categoria,
        "metodo": movement.metodo,
        "pessoa_lines": pessoa_lines,
        "descricao_lines": descricao_lines,
        "anexo_lines": anexo_lines,
        "height": row_height,
    }


def _empty_row() -> dict[str, object]:
    """Retorna uma linha vazia amigavel para periodos sem registros."""
    return {
        "data": "-",
        "tipo": "Sem dados",
        "valor": 0.0,
        "categoria": "Nenhuma movimentação",
        "metodo": "-",
        "pessoa_lines": ["-"],
        "descricao_lines": ["Nenhuma movimentação encontrada para este período."],
        "anexo_lines": ["-"],
        "height": 34,
    }


def _wrap_value(value: str, *, width: int) -> list[str]:
    """Quebra texto em linhas curtas para a tabela."""
    text = (value or "-").strip()
    return wrap(text, width=width) or ["-"]


def _summarize(movements: list[Movement]) -> dict[str, object]:
    """Resume a exportacao atual sem novo fetch do banco."""
    entradas = sum(movement.valor for movement in movements if movement.movement_type is MovementType.ENTRADA)
    saidas = sum(movement.valor for movement in movements if movement.movement_type is MovementType.SAIDA)
    saldo = sum(movement.signed_value for movement in movements)
    return {
        "entradas": round(entradas, 2),
        "saidas": round(saidas, 2),
        "saldo": round(saldo, 2),
        "quantidade": len(movements),
    }


def _build_pdf_document(page_streams: list[bytes]) -> bytes:
    """Monta os objetos PDF e devolve o arquivo final em bytes."""
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
    total_pages = len(page_streams)
    for page_number, page_stream in enumerate(page_streams, start=1):
        stream_with_footer = (
            page_stream.decode("cp1252") + _footer_commands(page_number, total_pages)
        ).encode("cp1252", "replace")
        stream_id = add_stream(stream_with_footer)
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
                f"/Contents {stream_id} 0 R >>"
            ).encode("ascii")
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    set_object(pages_id, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii"))
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii"))

    return _serialize_pdf(objects, catalog_id)


def _font_object(name: str) -> bytes:
    """Declara fonte Type1 basica no documento PDF."""
    return f"<< /Type /Font /Subtype /Type1 /BaseFont /{name} /Encoding /WinAnsiEncoding >>".encode("ascii")


def _serialize_pdf(objects: list[bytes], catalog_id: int) -> bytes:
    """Serializa objetos PDF, tabela xref e trailer final."""
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
    return f"q {r:.3f} {g:.3f} {b:.3f} RG 0.7 w {x:.2f} {y:.2f} {width:.2f} {height:.2f} re S Q\n"


def _text(text: str, x: float, y: float, *, font: str = "F1", size: float = BODY_FONT_SIZE, color: tuple[float, float, float] = (0, 0, 0)) -> str:
    escaped = _pdf_escape(text)
    r, g, b = color
    return f"BT /{font} {size} Tf {r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} Td ({escaped}) Tj ET\n"


def _text_block(text: str, x: float, y: float, *, max_chars: int, size: float, color: tuple[float, float, float], leading: float) -> str:
    lines = wrap(text, width=max_chars) or [""]
    return "".join(_text(line, x, y - (index * leading), size=size, color=color) for index, line in enumerate(lines))


def _text_block_lines(lines: list[str], x: float, y: float, *, size: float, leading: float, color: tuple[float, float, float] = (0.09, 0.14, 0.22)) -> list[str]:
    return [_text(line, x, y - (index * leading), size=size, color=color) for index, line in enumerate(lines)]


def _pdf_escape(value: str) -> str:
    """Escapa texto para o conjunto minimo esperado no stream PDF."""
    text = value.encode("cp1252", "replace").decode("cp1252")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_currency(value: float) -> str:
    """Formata valor monetario em padrao brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
