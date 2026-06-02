from __future__ import annotations

"""Geracao de arquivos Excel sem dependencias externas.

Este modulo escreve um `.xlsx` diretamente via ZIP e XML, agora com um layout
mais profissional para leitura administrativa.
"""

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from core.models import Movement, MovementType
from services.cash_service import CashService


SYSTEM_NAME = "Fluxo de caixa diário"
TABLE_HEADERS = ["Data", "Tipo", "Valor", "Categoria", "Técnico(s)", "Método", "Pessoa / empresa", "Descrição", "Anexo"]


def exportar_excel(
    service: CashService | None = None,
    output_path: str | Path = "relatorio.xlsx",
    movements: list[Movement] | None = None,
    title: str = "Fluxo de Caixa",
    *,
    export_type: str = "Exportação",
    period_label: str | None = None,
    generated_at: datetime | None = None,
    summary: dict[str, object] | None = None,
) -> Path:
    """Gera planilha Excel a partir dos movimentos informados."""
    service = service or CashService()
    dados = list(movements) if movements is not None else service.list_movements()
    generated_at = generated_at or datetime.now()
    summary_data = summary or _summarize(dados)
    period_label = period_label or title

    worksheet_xml = _build_worksheet_xml(
        dados,
        title=title,
        export_type=export_type,
        period_label=period_label,
        generated_at=generated_at,
        summary=summary_data,
    )
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


def _build_worksheet_xml(
    movements: list[Movement],
    *,
    title: str,
    export_type: str,
    period_label: str,
    generated_at: datetime,
    summary: dict[str, object],
) -> str:
    """Monta o XML da planilha com cabecalho, resumo e tabela principal."""
    last_column = _column_letter(len(TABLE_HEADERS))
    table_header_row = 9
    data_start_row = table_header_row + 1
    current_row = data_start_row

    row_xml_parts: list[str] = []
    merge_refs = [f"A1:{last_column}1", f"A2:{last_column}2", f"A3:{last_column}3", f"A4:{last_column}4"]
    width_samples = [[SYSTEM_NAME], [export_type], [period_label], [generated_at.strftime("%d/%m/%Y %H:%M")], TABLE_HEADERS.copy()]

    # Header institucional
    row_xml_parts.append(_row_xml(1, [_inline_string_cell("A1", SYSTEM_NAME, style=2)]))
    row_xml_parts.append(_row_xml(2, [_inline_string_cell("A2", export_type, style=3)]))
    row_xml_parts.append(_row_xml(3, [_inline_string_cell("A3", f"Período exportado: {period_label}", style=4)]))
    row_xml_parts.append(_row_xml(4, [_inline_string_cell("A4", f"Gerado em: {generated_at.strftime('%d/%m/%Y %H:%M')}", style=4)]))
    row_xml_parts.append(_row_xml(5, []))

    # Resumo
    summary_labels = ["Total de entradas", "Total de saídas", "Saldo líquido", "Movimentações"]
    summary_values = [
        float(summary.get("entradas", 0.0)),
        float(summary.get("saidas", 0.0)),
        float(summary.get("saldo", 0.0)),
        int(summary.get("quantidade", len(movements))),
    ]
    width_samples.append(summary_labels)
    width_samples.append([_format_currency(summary_values[0]), _format_currency(summary_values[1]), _format_currency(summary_values[2]), str(summary_values[3])])

    label_cells: list[str] = []
    value_cells: list[str] = []
    summary_columns = [(1, 2), (3, 4), (5, 6), (7, 9)]
    for index, (start_col, end_col) in enumerate(summary_columns):
        start_ref = f"{_column_letter(start_col)}6"
        end_ref = f"{_column_letter(end_col)}6"
        merge_refs.append(f"{start_ref}:{end_ref}")
        label_cells.append(_inline_string_cell(start_ref, summary_labels[index], style=5))

        value_ref = f"{_column_letter(start_col)}7"
        end_value_ref = f"{_column_letter(end_col)}7"
        merge_refs.append(f"{value_ref}:{end_value_ref}")
        style = 6 if index == 0 else 7 if index == 1 else 8 if index == 2 else 9
        if index < 3:
            value_cells.append(_number_cell(value_ref, float(summary_values[index]), style=style))
        else:
            value_cells.append(_number_cell(value_ref, int(summary_values[index]), style=style))

    row_xml_parts.append(_row_xml(6, label_cells, height=22))
    row_xml_parts.append(_row_xml(7, value_cells, height=28))
    row_xml_parts.append(_row_xml(8, []))

    # Tabela principal
    header_cells = [
        _inline_string_cell(f"{_column_letter(column_index)}{table_header_row}", value, style=1)
        for column_index, value in enumerate(TABLE_HEADERS, start=1)
    ]
    row_xml_parts.append(_row_xml(table_header_row, header_cells, height=24))

    for movement in movements:
        row_style = _row_styles_for_movement(movement)
        row_values = [
            movement.formatted_date,
            movement.display_type.capitalize(),
            movement.valor,
            movement.categoria,
            movement.tecnico,
            movement.metodo,
            movement.pessoa,
            movement.descricao,
            "Com anexo" if movement.anexo else "Sem anexo",
        ]
        width_samples.append(
            [
                row_values[0],
                row_values[1],
                _format_currency(float(row_values[2])),
                str(row_values[3]),
                str(row_values[4]),
                str(row_values[5]),
                str(row_values[6]),
                str(row_values[7]),
                str(row_values[8]),
            ]
        )

        cells = [
            _inline_string_cell(f"A{current_row}", str(row_values[0]), style=row_style["date"]),
            _inline_string_cell(f"B{current_row}", str(row_values[1]), style=row_style["type"]),
            _number_cell(f"C{current_row}", float(row_values[2]), style=row_style["currency"]),
            _inline_string_cell(f"D{current_row}", str(row_values[3]), style=row_style["text"]),
            _inline_string_cell(f"E{current_row}", str(row_values[4]), style=row_style["text"]),
            _inline_string_cell(f"F{current_row}", str(row_values[5]), style=row_style["text"]),
            _inline_string_cell(f"G{current_row}", str(row_values[6]), style=row_style["text"]),
            _inline_string_cell(f"H{current_row}", str(row_values[7]), style=row_style["wrap"]),
            _inline_string_cell(f"I{current_row}", str(row_values[8]), style=row_style["text"]),
        ]
        row_xml_parts.append(_row_xml(current_row, cells, height=_movement_row_height(movement)))
        current_row += 1

    last_row = max(table_header_row, current_row - 1)
    dimension = f"A1:{last_column}{last_row}"
    columns_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(_column_widths(width_samples), start=1)
    )
    merges_xml = "".join(f'<mergeCell ref="{reference}"/>' for reference in merge_refs)

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        f'<pane ySplit="{table_header_row}" topLeftCell="A{data_start_row}" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="20"/>'
        f"<cols>{columns_xml}</cols>"
        f"<sheetData>{''.join(row_xml_parts)}</sheetData>"
        f'<mergeCells count="{len(merge_refs)}">{merges_xml}</mergeCells>'
        f'<autoFilter ref="A{table_header_row}:{last_column}{last_row}"/>'
        '<pageMargins left="0.35" right="0.35" top="0.55" bottom="0.55" header="0.25" footer="0.25"/>'
        "</worksheet>"
    )


def _row_styles_for_movement(movement: Movement) -> dict[str, int]:
    """Retorna estilos visuais por tipo de movimentacao."""
    if movement.movement_type is MovementType.ENTRADA:
        return {"date": 10, "type": 11, "currency": 12, "text": 13, "wrap": 14}
    return {"date": 15, "type": 16, "currency": 17, "text": 18, "wrap": 19}


def _row_xml(row_index: int, cells: list[str], *, height: int | None = None) -> str:
    """Serializa uma linha de planilha."""
    if not cells:
        return f'<row r="{row_index}"></row>'
    height_attr = f' ht="{height}" customHeight="1"' if height else ""
    return f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>'


def _inline_string_cell(reference: str, value: str, *, style: int = 0) -> str:
    """Serializa uma celula de texto inline."""
    text = _xml_text(value)
    return f'<c r="{reference}" t="inlineStr" s="{style}"><is>{text}</is></c>'


def _number_cell(reference: str, value: float | int, *, style: int) -> str:
    """Serializa uma celula numerica."""
    return f'<c r="{reference}" s="{style}"><v>{value}</v></c>'


def _xml_text(value: str) -> str:
    """Escapa texto para XML preservando espacos relevantes."""
    cleaned = "".join(character if character in "\t\n\r" or ord(character) >= 32 else " " for character in str(value))
    escaped = escape(cleaned)
    if cleaned != cleaned.strip() or "\n" in cleaned:
        return f'<t xml:space="preserve">{escaped}</t>'
    return f"<t>{escaped}</t>"


def _column_widths(samples: list[list[str]]) -> list[int]:
    """Calcula larguras simples das colunas."""
    widths: list[int] = []
    for index in range(len(TABLE_HEADERS)):
        max_length = max(len(str(row[index])) if index < len(row) else 0 for row in samples)
        widths.append(max(14, min(max_length + 4, 36 if index != 7 else 48)))
    return widths


def _movement_row_height(movement: Movement) -> int:
    """Define altura da linha conforme descricao."""
    base = 22
    extra_lines = max(0, len(str(movement.descricao)) // 40)
    return min(46, base + (extra_lines * 12))


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
    """Define estilos usados pela planilha exportada."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="1"><numFmt numFmtId="164" formatCode="[$R$-416] #,##0.00"/></numFmts>'
        "<fonts count=\"7\">"
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF10233B"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FFFFFFFF"/></font>'
        '<font><b/><sz val="16"/><name val="Calibri"/><family val="2"/><color rgb="FF10233B"/></font>'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF1A9B5E"/></font>'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FFD64562"/></font>'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF1F6FEB"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF10233B"/></font>'
        "</fonts>"
        "<fills count=\"10\">"
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF10233B"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFEFF4FA"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFEAF7F0"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFCEEEF"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFEEF4FF"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF8FBFE"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF6FAF8"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFEF8F8"/><bgColor indexed="64"/></patternFill></fill>'
        "</fills>"
        "<borders count=\"2\">"
        '<border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"><color rgb="FFD7E2EF"/></left><right style="thin"><color rgb="FFD7E2EF"/></right><top style="thin"><color rgb="FFD7E2EF"/></top><bottom style="thin"><color rgb="FFD7E2EF"/></bottom><diagonal/></border>'
        "</borders>"
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="20">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="6" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="6" fillId="3" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="3" fillId="8" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="4" fillId="9" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="5" fillId="6" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="6" fillId="3" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="8" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="3" fillId="8" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="9" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="4" fillId="9" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="4" fillId="9" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="9" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="9" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )


def _column_letter(index: int) -> str:
    """Converte indice numerico em letra de coluna Excel."""
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _format_currency(value: float) -> str:
    """Formata valor monetario em padrao brasileiro."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sanitize_sheet_title(value: str) -> str:
    """Normaliza titulo da aba para as restricoes do Excel."""
    cleaned = value.strip() or "Fluxo de Caixa"
    for char in ("\\", "/", "*", "?", ":", "[", "]"):
        cleaned = cleaned.replace(char, "-")
    return cleaned[:31]
