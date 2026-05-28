from __future__ import annotations
"""Geracao de PDF sem bibliotecas externas.

O modulo monta um documento PDF simples por serializacao direta para manter a
portabilidade do executavel.
"""

from pathlib import Path
from textwrap import wrap

from core.models import Movement
from services.cash_service import CashService


PAGE_WIDTH = 842
PAGE_HEIGHT = 595
MARGIN = 36
TITLE_FONT_SIZE = 18
BODY_FONT_SIZE = 10
LINE_HEIGHT = 14
MAX_TEXT_WIDTH = 118


def gerar_pdf(
    service: CashService | None = None,
    output_path: str | Path = "relatorio.pdf",
    movements: list[Movement] | None = None,
    title: str = "Fluxo de Caixa",
) -> Path:
    """Gera PDF a partir de movimentos informados ou consultados no servico."""
    service = service or CashService()
    dados = list(movements) if movements is not None else service.list_movements(limit=100)

    lines = _build_report_lines(dados)
    pages = _paginate_lines(lines)
    pdf_bytes = _build_pdf_document(title, pages)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pdf_bytes)
    return output


def _build_report_lines(movements: list[Movement]) -> list[str]:
    """Converte movimentos em linhas de texto adequadas ao relatorio."""
    if not movements:
        return ["Nenhuma movimentação encontrada para este fluxo."]

    lines: list[str] = []
    for movement in movements:
        lines.extend(
            [
                f"Data: {movement.formatted_date}   Tipo: {movement.display_type.capitalize()}   Valor: {_format_currency(movement.valor)}",
                f"Categoria: {movement.categoria}   Método: {movement.metodo}",
                f"Pessoa / empresa: {movement.pessoa}",
                f"Descrição: {movement.descricao}",
            ]
        )
        if movement.anexo:
            lines.append(f"Anexo: {movement.anexo}")
        lines.append("")
    return lines[:-1] if lines and not lines[-1] else lines


def _paginate_lines(lines: list[str]) -> list[list[str]]:
    """Quebra o relatorio em paginas considerando largura e altura uteis."""
    usable_height = PAGE_HEIGHT - (MARGIN * 2) - 34
    max_lines_per_page = max(1, usable_height // LINE_HEIGHT)
    wrapped_lines: list[str] = []
    for line in lines:
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(wrap(line, width=MAX_TEXT_WIDTH) or [""])

    pages: list[list[str]] = []
    for index in range(0, len(wrapped_lines), max_lines_per_page):
        pages.append(wrapped_lines[index : index + max_lines_per_page])
    return pages or [["Nenhuma movimentação encontrada para este fluxo."]]


def _build_pdf_document(title: str, pages: list[list[str]]) -> bytes:
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
    for page_number, page_lines in enumerate(pages, start=1):
        stream_id = add_stream(_page_stream(title, page_lines, page_number, len(pages)))
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


def _page_stream(title: str, lines: list[str], page_number: int, total_pages: int) -> bytes:
    """Gera o stream de desenho de uma pagina do PDF."""
    title_text = _pdf_escape(title)
    footer_text = _pdf_escape(f"Página {page_number}/{total_pages}")
    body_lines = "\n".join(f"({_pdf_escape(line)}) Tj" if index == 0 else f"T*\n({_pdf_escape(line)}) Tj" for index, line in enumerate(lines))
    if not body_lines:
        body_lines = "() Tj"

    stream = (
        "q\n"
        "0.12 0.44 0.86 rg\n"
        f"{MARGIN} {PAGE_HEIGHT - MARGIN - 8} {PAGE_WIDTH - (MARGIN * 2)} 26 re f\n"
        "BT\n"
        f"/F2 {TITLE_FONT_SIZE} Tf\n"
        "1 1 1 rg\n"
        f"{MARGIN + 10} {PAGE_HEIGHT - MARGIN + 1} Td\n"
        f"({title_text}) Tj\n"
        "ET\n"
        "Q\n"
        "BT\n"
        f"/F1 {BODY_FONT_SIZE} Tf\n"
        "0 0 0 rg\n"
        f"{LINE_HEIGHT} TL\n"
        f"{MARGIN} {PAGE_HEIGHT - MARGIN - 30} Td\n"
        f"{body_lines}\n"
        "ET\n"
        "BT\n"
        "/F1 9 Tf\n"
        "0.4 0.45 0.52 rg\n"
        f"{PAGE_WIDTH - MARGIN - 70} {MARGIN - 6} Td\n"
        f"({footer_text}) Tj\n"
        "ET\n"
    )
    return stream.encode("cp1252", "replace")


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

    trailer = (
        f"trailer\n<< /Size {len(objects)} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii")
    )
    return b"".join(content_parts + xref_parts + [trailer])


def _pdf_escape(value: str) -> str:
    """Escapa texto para o conjunto minimo esperado no stream PDF."""
    text = value.encode("cp1252", "replace").decode("cp1252")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_currency(value: float) -> str:
    """Formata valor monetario em padrao brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
