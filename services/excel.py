from __future__ import annotations
"""Geracao de arquivos Excel sem dependencias externas.

Este modulo escreve um `.xlsx` minimo diretamente via ZIP e XML para manter a
portabilidade do projeto.
"""

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from core.models import Movement
from services.cash_service import CashService


def exportar_excel(
    service: CashService | None = None,
    output_path: str | Path = "relatorio.xlsx",
    movements: list[Movement] | None = None,
    title: str = "Fluxo de Caixa",
) -> Path:
    """Gera planilha Excel a partir de movimentos informados ou do servico."""
    service = service or CashService()
    dados = list(movements) if movements is not None else service.list_movements()

    rows = [_headers()]
    for movement in dados:
        rows.append(
            [
                movement.formatted_date,
                movement.display_type.capitalize(),
                _format_currency(movement.valor),
                movement.categoria,
                movement.metodo,
                movement.pessoa,
                movement.descricao,
                movement.anexo,
            ]
        )

    worksheet_xml = _build_worksheet_xml(rows)
    workbook_title = _sanitize_sheet_title(title)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(workbook_title))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    return output


def _headers() -> list[str]:
    """Retorna o cabecalho padrao da planilha exportada."""
    return ["Data", "Tipo", "Valor", "Categoria", "Método", "Pessoa / empresa", "Descrição", "Anexo"]


def _build_worksheet_xml(rows: list[list[str]]) -> str:
    """Monta o XML principal da planilha com dimensoes, linhas e colunas."""
    column_count = len(rows[0])
    last_column = _column_letter(column_count)
    dimension = f"A1:{last_column}{len(rows)}"
    columns_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(_column_widths(rows), start=1)
    )

    row_xml_parts: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        row_height = ' ht="24" customHeight="1"' if row_index == 1 else ""
        cells_xml = "".join(
            _inline_string_cell(f"{_column_letter(column_index)}{row_index}", value, header=row_index == 1)
            for column_index, value in enumerate(row, start=1)
        )
        row_xml_parts.append(f'<row r="{row_index}"{row_height}>{cells_xml}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        f"<cols>{columns_xml}</cols>"
        f"<sheetData>{''.join(row_xml_parts)}</sheetData>"
        f'<autoFilter ref="{dimension}"/>'
        '<pageMargins left="0.5" right="0.5" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        "</worksheet>"
    )


def _inline_string_cell(reference: str, value: str, *, header: bool = False) -> str:
    """Serializa uma celula de texto inline para o XML da planilha."""
    style = "1" if header else "0"
    text = _xml_text(value)
    return f'<c r="{reference}" t="inlineStr" s="{style}"><is>{text}</is></c>'


def _xml_text(value: str) -> str:
    """Escapa texto para XML preservando espacos e quebras relevantes."""
    cleaned = "".join(character if character in "\t\n\r" or ord(character) >= 32 else " " for character in str(value))
    escaped = escape(cleaned)
    if cleaned != cleaned.strip() or "\n" in cleaned:
        return f'<t xml:space="preserve">{escaped}</t>'
    return f"<t>{escaped}</t>"


def _column_widths(rows: list[list[str]]) -> list[int]:
    """Calcula larguras simples de coluna com base no maior conteudo."""
    widths: list[int] = []
    for index in range(len(rows[0])):
        max_length = max(len(str(row[index])) for row in rows)
        widths.append(max(14, min(max_length + 4, 42)))
    return widths


def _column_letter(index: int) -> str:
    """Converte indice numerico para letra de coluna Excel."""
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _content_types_xml() -> str:
    """Gera o manifesto de content types do pacote XLSX."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )


def _root_relationships_xml() -> str:
    """Gera relacionamentos raiz do pacote Open XML."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(title: str) -> str:
    """Gera o XML do workbook apontando para a planilha principal."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<bookViews><workbookView activeTab="0"/></bookViews>'
        f'<sheets><sheet name="{escape(title)}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def _workbook_relationships_xml() -> str:
    """Gera relacionamentos internos do workbook."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )


def _styles_xml() -> str:
    """Define estilos minimos usados na planilha exportada."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<fonts count=\"2\">"
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>'
        "</fonts>"
        "<fills count=\"3\">"
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF1F6FEB"/><bgColor indexed="64"/></patternFill></fill>'
        "</fills>"
        "<borders count=\"1\"><border><left/><right/><top/><bottom/><diagonal/></border></borders>"
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1">'
        '<alignment vertical="top" wrapText="1"/>'
        "</xf>"
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" '
        'applyFill="1" applyFont="1" applyAlignment="1">'
        '<alignment horizontal="center" vertical="center" wrapText="1"/>'
        "</xf>"
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


def _format_currency(value: float) -> str:
    """Formata valor monetario em padrao brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sanitize_sheet_title(value: str) -> str:
    """Normaliza titulo da aba para as restricoes do Excel."""
    cleaned = value.strip() or "Fluxo de Caixa"
    for char in ('\\', '/', '*', '?', ':', '[', ']'):
        cleaned = cleaned.replace(char, "-")
    return cleaned[:31]
