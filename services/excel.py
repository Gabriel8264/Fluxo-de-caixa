from __future__ import annotations

"""Exportação Excel completa do sistema, sem dependências externas."""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from core.models import Movement, MovementType
from services.cash_service import CashService


SYSTEM_NAME = "Fluxo de caixa diário"
SHEET_NAMES = [
    "Dashboard",
    "Movimentações",
    "Categorias",
    "Técnicos",
    "Métodos",
    "Dados brutos",
]
MOVEMENTS_HEADERS = [
    "Data",
    "Tipo",
    "Valor",
    "Categoria",
    "Pessoa / empresa",
    "Método",
    "Descrição",
    "Técnicos",
    "Comissão",
    "Valor empresa",
    "Anexo",
]
RAW_HEADERS = [
    "ID",
    "Data armazenada",
    "Data formatada",
    "Tipo",
    "Valor",
    "Categoria",
    "Pessoa / empresa",
    "Método",
    "Descrição",
    "Técnicos",
    "Divisão técnicos",
    "Percentual comissão",
    "Valor comissão",
    "Valor empresa",
    "Grupo serviço",
    "Papel serviço",
    "Anexo",
]


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
    """Gera workbook Excel completo com visão executiva e auditoria."""
    service = service or CashService()
    data = list(movements) if movements is not None else service.list_movements()
    generated_at = generated_at or datetime.now()
    period_label = period_label or title
    summary_data = _summarize(data)
    analysis = _analyze_movements(data)

    dashboard_xml = _build_dashboard_sheet_xml(
        export_type=export_type,
        period_label=period_label,
        generated_at=generated_at,
        summary=summary_data,
        analysis=analysis,
    )
    movements_xml, movements_table_ref = _build_movements_sheet_xml(data)
    categories_xml = _build_categories_sheet_xml(analysis)
    technicians_xml = _build_technicians_sheet_xml(analysis)
    methods_xml = _build_methods_sheet_xml(analysis)
    raw_xml = _build_raw_sheet_xml(data)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", dashboard_xml)
        archive.writestr("xl/worksheets/sheet2.xml", movements_xml)
        archive.writestr("xl/worksheets/sheet3.xml", categories_xml)
        archive.writestr("xl/worksheets/sheet4.xml", technicians_xml)
        archive.writestr("xl/worksheets/sheet5.xml", methods_xml)
        archive.writestr("xl/worksheets/sheet6.xml", raw_xml)
        archive.writestr("xl/worksheets/_rels/sheet2.xml.rels", _sheet2_relationships_xml())
        archive.writestr("xl/tables/table1.xml", _table_xml(movements_table_ref, MOVEMENTS_HEADERS))

    return output


def _build_dashboard_sheet_xml(
    *,
    export_type: str,
    period_label: str,
    generated_at: datetime,
    summary: dict[str, object],
    analysis: dict[str, object],
) -> str:
    rows: list[str] = []
    merges: list[str] = []
    samples: list[list[str]] = []

    rows.append(_row_xml(1, [_inline_string_cell("A1", SYSTEM_NAME, style=2)], height=28))
    rows.append(_row_xml(2, [_inline_string_cell("A2", export_type, style=3)], height=20))
    rows.append(_row_xml(3, [_inline_string_cell("A3", f"Período exportado: {period_label}", style=4)], height=18))
    rows.append(_row_xml(4, [_inline_string_cell("A4", f"Gerado em: {generated_at.strftime('%d/%m/%Y %H:%M')}", style=4)], height=18))
    merges.extend(["A1:H1", "A2:H2", "A3:H3", "A4:H4"])
    samples.extend([
        [SYSTEM_NAME] + [""] * 7,
        [export_type] + [""] * 7,
        [f"Período exportado: {period_label}"] + [""] * 7,
        [f"Gerado em: {generated_at.strftime('%d/%m/%Y %H:%M')}"] + [""] * 7,
    ])
    rows.append(_row_xml(5, []))

    labels = ["Entradas", "Saídas", "Saldo", "Movimentações"]
    values = [
        float(summary["entradas"]),
        float(summary["saidas"]),
        float(summary["saldo"]),
        int(summary["quantidade"]),
    ]
    for col in (1, 3, 5, 7):
        end_col = col + 1
        label_ref = f"{_column_letter(col)}6"
        value_ref = f"{_column_letter(col)}7"
        merges.extend([f"{label_ref}:{_column_letter(end_col)}6", f"{value_ref}:{_column_letter(end_col)}7"])
    rows.append(
        _row_xml(
            6,
            [
                _inline_string_cell("A6", labels[0], style=5),
                _inline_string_cell("C6", labels[1], style=5),
                _inline_string_cell("E6", labels[2], style=5),
                _inline_string_cell("G6", labels[3], style=5),
            ],
            height=20,
        )
    )
    rows.append(
        _row_xml(
            7,
            [
                _number_cell("A7", values[0], style=6),
                _number_cell("C7", values[1], style=7),
                _number_cell("E7", values[2], style=8),
                _number_cell("G7", values[3], style=9),
            ],
            height=30,
        )
    )
    samples.extend([
        ["Entradas", "", "Saídas", "", "Saldo", "", "Movimentações", ""],
        [_format_currency(values[0]), "", _format_currency(values[1]), "", _format_currency(values[2]), "", str(values[3]), ""],
    ])
    rows.append(_row_xml(8, []))

    sections = [
        ("Entradas x Saídas", [
            ("Entradas", _format_currency(float(summary["entradas"])), _spark(float(summary["entradas"]), max(float(summary["entradas"]), float(summary["saidas"]), 1.0))),
            ("Saídas", _format_currency(float(summary["saidas"])), _spark(float(summary["saidas"]), max(float(summary["entradas"]), float(summary["saidas"]), 1.0))),
            ("Saldo líquido", _format_currency(float(summary["saldo"])), _spark(abs(float(summary["saldo"])), max(abs(float(summary["saldo"])), float(summary["entradas"]), 1.0))),
        ]),
        ("Categorias", [(label, _format_currency(value), _spark(value, analysis["category_max"])) for label, value in analysis["category_rows"][:8]]),
        ("Métodos", [(label, _format_currency(value), _spark(value, analysis["method_max"])) for label, value in analysis["method_rows"][:8]]),
        ("Técnicos", [(label, _format_currency(value), _spark(value, analysis["technician_max"])) for label, value in analysis["technician_chart_rows"][:8]]),
    ]

    current = 10
    for title, items in sections:
        rows.append(_row_xml(current, [_inline_string_cell(f"A{current}", title, style=10)], height=20))
        merges.append(f"A{current}:H{current}")
        current += 1
        rows.append(
            _row_xml(
                current,
                [
                    _inline_string_cell(f"A{current}", "Indicador", style=11),
                    _inline_string_cell(f"B{current}", "Valor", style=11),
                    _inline_string_cell(f"C{current}", "Visual", style=11),
                ],
                height=18,
            )
        )
        merges.append(f"C{current}:H{current}")
        current += 1
        if not items:
            items = [("Sem dados", "-", "")]
        for label, value, visual in items:
            rows.append(
                _row_xml(
                    current,
                    [
                        _inline_string_cell(f"A{current}", label, style=12),
                        _inline_string_cell(f"B{current}", value, style=13),
                        _inline_string_cell(f"C{current}", visual, style=14),
                    ],
                    height=18,
                )
            )
            merges.append(f"C{current}:H{current}")
            samples.append([label, value, visual, "", "", "", "", ""])
            current += 1
        rows.append(_row_xml(current, []))
        current += 1

    columns_xml = "".join(
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(_column_widths(samples, minimum=14, maximum=36), start=1)
    )
    merge_xml = "".join(f'<mergeCell ref="{ref}"/>' for ref in merges)
    last_row = max(1, current)
    return _worksheet_xml(
        dimension=f"A1:H{last_row}",
        columns_xml=columns_xml,
        sheet_rows="".join(rows),
        merges_xml=merge_xml,
    )


def _build_movements_sheet_xml(movements: list[Movement]) -> tuple[str, str]:
    rows: list[str] = []
    samples = [MOVEMENTS_HEADERS.copy()]
    records = movements if movements else [_empty_movement()]

    rows.append(
        _row_xml(
            1,
            [_inline_string_cell(f"{_column_letter(i)}1", header, style=15) for i, header in enumerate(MOVEMENTS_HEADERS, start=1)],
            height=22,
        )
    )

    for row_index, movement in enumerate(records, start=2):
        movement_styles = _movement_styles(movement)
        row_values = _movement_export_values(movement)
        samples.append([str(value) for value in row_values])
        rows.append(
            _row_xml(
                row_index,
                [
                    _date_or_text_cell(f"A{row_index}", movement.formatted_date, style=movement_styles["date"]),
                    _inline_string_cell(f"B{row_index}", movement.display_type.capitalize(), style=movement_styles["type"]),
                    _number_cell(f"C{row_index}", float(movement.valor), style=movement_styles["currency"]),
                    _inline_string_cell(f"D{row_index}", row_values[3], style=movement_styles["text"]),
                    _inline_string_cell(f"E{row_index}", row_values[4], style=movement_styles["text"]),
                    _inline_string_cell(f"F{row_index}", row_values[5], style=movement_styles["text"]),
                    _inline_string_cell(f"G{row_index}", row_values[6], style=movement_styles["wrap"]),
                    _inline_string_cell(f"H{row_index}", row_values[7], style=movement_styles["wrap"]),
                    _number_cell(f"I{row_index}", float(movement.valor_comissao_tecnico or 0.0), style=movement_styles["neutral_currency"]),
                    _number_cell(f"J{row_index}", float(movement.valor_empresa or 0.0), style=17),
                    _inline_string_cell(f"K{row_index}", row_values[10], style=movement_styles["text"]),
                ],
                height=_movement_row_height(movement),
            )
        )

    last_row = len(records) + 1
    columns_xml = "".join(
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(_movement_widths(samples), start=1)
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:K{last_row}"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane xSplit="1" ySplit="1" topLeftCell="B2" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="20"/>'
        f"<cols>{columns_xml}</cols>"
        f"<sheetData>{''.join(rows)}</sheetData>"
        '<pageMargins left="0.3" right="0.3" top="0.45" bottom="0.45" header="0.2" footer="0.2"/>'
        '<tableParts count="1"><tablePart xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rId1"/></tableParts>'
        "</worksheet>"
    )
    return xml, f"A1:K{last_row}"


def _build_categories_sheet_xml(analysis: dict[str, object]) -> str:
    headers = ["Categoria", "Entradas", "Saídas", "Saldo"]
    rows = [
        _row_xml(1, [_inline_string_cell(f"{_column_letter(i)}1", value, style=15) for i, value in enumerate(headers, start=1)], height=22)
    ]
    samples = [headers.copy()]
    data_rows = analysis["category_detail_rows"] or [("Sem categoria", 0.0, 0.0, 0.0)]
    for index, (label, entries, exits, balance) in enumerate(data_rows, start=2):
        samples.append([label, _format_currency(entries), _format_currency(exits), _format_currency(balance)])
        rows.append(
            _row_xml(
                index,
                [
                    _inline_string_cell(f"A{index}", label, style=12),
                    _number_cell(f"B{index}", entries, style=16),
                    _number_cell(f"C{index}", exits, style=18),
                    _number_cell(f"D{index}", balance, style=17),
                ],
                height=18,
            )
        )
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(_column_widths(samples, minimum=14, maximum=28), start=1))
    return _worksheet_xml(dimension=f"A1:D{len(data_rows)+1}", columns_xml=cols, sheet_rows="".join(rows))


def _build_technicians_sheet_xml(analysis: dict[str, object]) -> str:
    headers = ["Técnico", "Quantidade de serviços", "Comissão recebida", "Participação percentual"]
    rows = [
        _row_xml(1, [_inline_string_cell(f"{_column_letter(i)}1", value, style=15) for i, value in enumerate(headers, start=1)], height=22)
    ]
    samples = [headers.copy()]
    data_rows = analysis["technician_detail_rows"] or [("Sem técnicos", 0, 0.0, 0.0)]
    for index, (name, services, commission, participation) in enumerate(data_rows, start=2):
        samples.append([name, str(services), _format_currency(commission), f"{participation:.2f}%"])
        rows.append(
            _row_xml(
                index,
                [
                    _inline_string_cell(f"A{index}", name, style=12),
                    _number_cell(f"B{index}", services, style=13),
                    _number_cell(f"C{index}", commission, style=17),
                    _inline_string_cell(f"D{index}", f"{participation:.2f}%", style=13),
                ],
                height=18,
            )
        )
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(_column_widths(samples, minimum=14, maximum=30), start=1))
    return _worksheet_xml(dimension=f"A1:D{len(data_rows)+1}", columns_xml=cols, sheet_rows="".join(rows))


def _build_methods_sheet_xml(analysis: dict[str, object]) -> str:
    headers = ["Método", "Quantidade", "Valor total"]
    rows = [
        _row_xml(1, [_inline_string_cell(f"{_column_letter(i)}1", value, style=15) for i, value in enumerate(headers, start=1)], height=22)
    ]
    samples = [headers.copy()]
    data_rows = analysis["method_detail_rows"] or [("Sem método", 0, 0.0)]
    for index, (method, quantity, total) in enumerate(data_rows, start=2):
        samples.append([method, str(quantity), _format_currency(total)])
        rows.append(
            _row_xml(
                index,
                [
                    _inline_string_cell(f"A{index}", method, style=12),
                    _number_cell(f"B{index}", quantity, style=13),
                    _number_cell(f"C{index}", total, style=17),
                ],
                height=18,
            )
        )
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(_column_widths(samples, minimum=14, maximum=28), start=1))
    return _worksheet_xml(dimension=f"A1:C{len(data_rows)+1}", columns_xml=cols, sheet_rows="".join(rows))


def _build_raw_sheet_xml(movements: list[Movement]) -> str:
    rows: list[str] = []
    samples = [RAW_HEADERS.copy()]
    records = movements if movements else [_empty_movement()]
    rows.append(
        _row_xml(
            1,
            [_inline_string_cell(f"{_column_letter(i)}1", header, style=15) for i, header in enumerate(RAW_HEADERS, start=1)],
            height=22,
        )
    )
    for index, movement in enumerate(records, start=2):
        values = [
            str(movement.id or ""),
            movement.data,
            movement.formatted_date,
            movement.display_type.capitalize(),
            _format_currency(float(movement.valor)),
            movement.categoria or "-",
            movement.pessoa or "-",
            movement.metodo or "-",
            movement.descricao or "-",
            movement.tecnico or "-",
            movement.divisao_tecnicos or "-",
            f"{float(movement.percentual_comissao_tecnico or 0.0):.2f}%",
            _format_currency(float(movement.valor_comissao_tecnico or 0.0)),
            _format_currency(float(movement.valor_empresa or 0.0)),
            movement.grupo_servico or "-",
            movement.papel_servico or "-",
            Path(movement.anexo).name if movement.anexo else "Sem anexo",
        ]
        samples.append(values)
        rows.append(
            _row_xml(
                index,
                [_inline_string_cell(f"{_column_letter(col)}{index}", value, style=12 if col not in (9, 10, 11) else 14) for col, value in enumerate(values, start=1)],
                height=18,
            )
        )
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(_column_widths(samples, minimum=12, maximum=34), start=1))
    return _worksheet_xml(dimension=f"A1:Q{len(records)+1}", columns_xml=cols, sheet_rows="".join(rows))


def _worksheet_xml(*, dimension: str, columns_xml: str, sheet_rows: str, merges_xml: str = "") -> str:
    merge_block = f'<mergeCells count="{merges_xml.count("<mergeCell")}">{merges_xml}</mergeCells>' if merges_xml else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="20"/>'
        f"<cols>{columns_xml}</cols>"
        f"<sheetData>{sheet_rows}</sheetData>"
        f"{merge_block}"
        '<pageMargins left="0.35" right="0.35" top="0.45" bottom="0.45" header="0.2" footer="0.2"/>'
        "</worksheet>"
    )


def _movement_export_values(movement: Movement) -> list[str]:
    return [
        movement.formatted_date,
        movement.display_type.capitalize(),
        _format_currency(float(movement.valor)),
        movement.categoria or "-",
        movement.pessoa or "-",
        movement.metodo or "-",
        movement.descricao or "-",
        movement.tecnico or "-",
        _format_currency(float(movement.valor_comissao_tecnico or 0.0)),
        _format_currency(float(movement.valor_empresa or 0.0)),
        Path(movement.anexo).name if movement.anexo else "Sem anexo",
    ]


def _movement_styles(movement: Movement) -> dict[str, int]:
    if movement.movement_type is MovementType.ENTRADA:
        return {"date": 19, "type": 16, "currency": 16, "neutral_currency": 17, "text": 12, "wrap": 14}
    return {"date": 20, "type": 18, "currency": 18, "neutral_currency": 17, "text": 12, "wrap": 14}


def _row_xml(row_index: int, cells: list[str], *, height: int | None = None) -> str:
    if not cells:
        return f'<row r="{row_index}"></row>'
    height_attr = f' ht="{height}" customHeight="1"' if height else ""
    return f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>'


def _inline_string_cell(reference: str, value: str, *, style: int = 0) -> str:
    return f'<c r="{reference}" t="inlineStr" s="{style}"><is>{_xml_text(value)}</is></c>'


def _number_cell(reference: str, value: float | int, *, style: int = 0) -> str:
    return f'<c r="{reference}" s="{style}"><v>{value}</v></c>'


def _date_or_text_cell(reference: str, value: str, *, style: int) -> str:
    serial = _excel_date_serial(value)
    if serial is None:
        return _inline_string_cell(reference, value, style=style)
    return _number_cell(reference, serial, style=style)


def _xml_text(value: str) -> str:
    cleaned = "".join(ch if ch in "\t\n\r" or ord(ch) >= 32 else " " for ch in str(value))
    escaped = escape(cleaned)
    if cleaned != cleaned.strip() or "\n" in cleaned:
        return f'<t xml:space="preserve">{escaped}</t>'
    return f"<t>{escaped}</t>"


def _column_widths(samples: list[list[str]], *, minimum: int, maximum: int) -> list[int]:
    column_count = max((len(row) for row in samples), default=0)
    widths: list[int] = []
    for index in range(column_count):
        max_len = max(len(str(row[index])) if index < len(row) else 0 for row in samples)
        widths.append(max(minimum, min(max_len + 4, maximum)))
    return widths


def _movement_widths(samples: list[list[str]]) -> list[int]:
    mins = [12, 10, 12, 16, 20, 14, 28, 20, 14, 14, 18]
    caps = [14, 12, 14, 20, 24, 18, 42, 24, 16, 16, 22]
    widths: list[int] = []
    for index in range(len(MOVEMENTS_HEADERS)):
        max_len = max(len(str(row[index])) if index < len(row) else 0 for row in samples)
        widths.append(max(mins[index], min(max_len + 4, caps[index])))
    return widths


def _movement_row_height(movement: Movement) -> int:
    longest = max(len(movement.descricao or ""), len(movement.pessoa or ""), len(movement.tecnico or ""))
    return min(36, 20 + max(0, longest // 44) * 8)


def _excel_date_serial(value: str) -> int | None:
    try:
        parsed = datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        try:
            parsed = datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return parsed.toordinal() - datetime(1899, 12, 30).date().toordinal()


def _empty_movement() -> Movement:
    return Movement(
        tipo=MovementType.ENTRADA.value,
        valor=0.0,
        descricao="Sem movimentações no período.",
        categoria="Sem movimentações",
        metodo="-",
        pessoa="-",
        data="-",
        tecnico="-",
    )


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
    category_detail: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"entradas": 0.0, "saidas": 0.0})
    method_totals: defaultdict[str, float] = defaultdict(float)
    method_counts: Counter[str] = Counter()
    person_totals: defaultdict[str, float] = defaultdict(float)
    largest_entry: Movement | None = None
    largest_exit: Movement | None = None

    technician_services: defaultdict[str, set[str]] = defaultdict(set)
    technician_commissions: defaultdict[str, float] = defaultdict(float)
    seen_service_groups: set[str] = set()

    for movement in movements:
        category = movement.categoria or "Sem categoria"
        method = movement.metodo or "Sem método"
        person = movement.pessoa or "Sem pessoa"

        method_totals[method] += float(movement.valor)
        method_counts[method] += 1
        person_totals[person] += abs(float(movement.valor))

        if movement.movement_type is MovementType.ENTRADA:
            entry_categories[category] += float(movement.valor)
            category_detail[category]["entradas"] += float(movement.valor)
            if largest_entry is None or movement.valor > largest_entry.valor:
                largest_entry = movement
        else:
            exit_categories[category] += float(movement.valor)
            category_detail[category]["saidas"] += float(movement.valor)
            if largest_exit is None or movement.valor > largest_exit.valor:
                largest_exit = movement

        if movement.papel_servico == "entrada_servico":
            service_key = movement.grupo_servico or f"entrada:{movement.id or movement.data}"
            if service_key in seen_service_groups:
                continue
            seen_service_groups.add(service_key)
            shares = _technician_shares(movement)
            for share in shares:
                name = share["nome"]
                technician_services[name].add(service_key)
                technician_commissions[name] += share["valor"]

    for movement in movements:
        if movement.papel_servico != "comissao_tecnica":
            continue
        service_key = movement.grupo_servico or f"comissão:{movement.id or movement.data}"
        if service_key in seen_service_groups:
            continue
        shares = _technician_shares(movement)
        for share in shares:
            name = share["nome"]
            technician_services[name].add(service_key)
            technician_commissions[name] += share["valor"]

    category_rows = sorted(
        (
            (label, values["entradas"], values["saidas"], values["entradas"] - values["saidas"])
            for label, values in category_detail.items()
        ),
        key=lambda item: (-abs(item[3]), item[0]),
    )
    method_rows = sorted(method_totals.items(), key=lambda item: (-item[1], item[0]))
    method_detail_rows = [(name, method_counts[name], total) for name, total in method_rows]

    technician_detail_rows = []
    total_commission = sum(technician_commissions.values()) or 1.0
    for technician in sorted(technician_commissions, key=lambda name: (-technician_commissions[name], name)):
        commission = round(technician_commissions[technician], 2)
        technician_detail_rows.append(
            (
                technician,
                len(technician_services[technician]),
                commission,
                round((commission / total_commission) * 100, 2),
            )
        )

    return {
        "largest_entry": largest_entry,
        "largest_exit": largest_exit,
        "top_entry_category": max(entry_categories.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "top_exit_category": max(exit_categories.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "top_method": max(method_totals.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "top_person": max(person_totals.items(), key=lambda item: item[1], default=("Sem dados", 0.0)),
        "top_technicians": [name for name, *_ in technician_detail_rows[:4]],
        "category_rows": [(label, abs(balance)) for label, _entries, _exits, balance in category_rows],
        "category_detail_rows": category_rows,
        "category_max": max((abs(balance) for _, _, _, balance in category_rows), default=1.0),
        "method_rows": method_rows,
        "method_detail_rows": method_detail_rows,
        "method_max": max((value for _, value in method_rows), default=1.0),
        "technician_chart_rows": [(name, commission) for name, _, commission, _ in technician_detail_rows],
        "technician_detail_rows": technician_detail_rows,
        "technician_max": max((commission for _, _, commission, _ in technician_detail_rows), default=1.0),
    }


def _technician_shares(movement: Movement) -> list[dict[str, float | str]]:
    payload = (movement.divisao_tecnicos or "").strip()
    if payload:
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            loaded = []
        shares: list[dict[str, float | str]] = []
        for item in loaded or []:
            name = str(item.get("nome") or "").strip()
            if not name:
                continue
            shares.append({"nome": name, "valor": float(item.get("valor") or 0.0)})
        if shares:
            return shares
    names = [name.strip() for name in (movement.tecnico or "").split(",") if name.strip()]
    if not names:
        return []
    total = float(movement.valor_comissao_tecnico or 0.0)
    if movement.papel_servico == "comissao_tecnica":
        total = float(movement.valor or 0.0)
    portion = round(total / len(names), 2) if names else 0.0
    return [{"nome": name, "valor": portion} for name in names]


def _spark(value: float, maximum: float) -> str:
    if maximum <= 0 or value <= 0:
        return ""
    blocks = max(1, min(16, round((value / maximum) * 16)))
    return "█" * blocks


def _content_types_xml() -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, 7)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f"{sheet_overrides}"
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
        "</Types>"
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml() -> str:
    sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(SHEET_NAMES, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<bookViews><workbookView activeTab="0"/></bookViews>'
        f"<sheets>{sheets}</sheets>"
        "</workbook>"
    )


def _workbook_relationships_xml() -> str:
    sheet_rels = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, 7)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{sheet_rels}"
        '<Relationship Id="rId7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )


def _sheet2_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/>'
        "</Relationships>"
    )


def _table_xml(reference: str, headers: list[str]) -> str:
    columns = "".join(f'<tableColumn id="{i}" name="{escape(label)}"/>' for i, label in enumerate(headers, start=1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'id="1" name="Movimentacoes" displayName="Movimentacoes" '
        f'ref="{reference}" totalsRowShown="0">'
        f'<autoFilter ref="{reference}"/>'
        f'<tableColumns count="{len(headers)}">{columns}</tableColumns>'
        '<tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/>'
        "</table>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="2"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/><numFmt numFmtId="165" formatCode="[$R$-416] #,##0.00"/></numFmts>'
        '<fonts count="7">'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF10233B"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FFFFFFFF"/></font>'
        '<font><b/><sz val="16"/><name val="Calibri"/><family val="2"/><color rgb="FF10233B"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF10233B"/></font>'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF1A9B5E"/></font>'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FFD64562"/></font>'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/><color rgb="FF1F6FEB"/></font>'
        '</fonts>'
        '<fills count="9">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF10233B"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFEFF4FA"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFEAF7F0"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFCEEEF"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFEEF4FF"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFF9FBFD"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFFFFFF"/><bgColor indexed="64"/></patternFill></fill>'
        '</fills>'
        '<borders count="2">'
        '<border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"><color rgb="FFD7E2EF"/></left><right style="thin"><color rgb="FFD7E2EF"/></right><top style="thin"><color rgb="FFD7E2EF"/></top><bottom style="thin"><color rgb="FFD7E2EF"/></bottom><diagonal/></border>'
        '</borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="21">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="8" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="8" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="8" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="165" fontId="4" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="165" fontId="5" fillId="5" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="165" fontId="6" fillId="6" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="7" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="165" fontId="4" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="165" fontId="6" fillId="6" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="165" fontId="5" fillId="5" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="0" fillId="8" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="164" fontId="0" fillId="7" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def _column_letter(index: int) -> str:
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
