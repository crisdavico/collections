# Copyright 2026 Seedian
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import xlsxwriter

from odoo import api, models

NAVY = "#1F4E79"
NAVY_DARK = "#1F3864"
HDR_BLUE = "#DBE5F1"
GREY_FILL = "#F2F2F2"
SUB_FILL = "#EDEDED"
MONEY = "#,##0.00"
INT = "#,##0"
PCT = "0.0%"
MONEY_BIG = '"$" #,##0.00'
COLUMN_WIDTHS = (13, 32, 19, 17, 14, 14, 15, 15)
_KIND_TITLES = {"invoice": "Facturas", "quotation": "Presupuestos"}
_BANNER_FILL = {
    "balanced": ("#C6EFCE", "#006100"),
    "in_favor": ("#FFEB9C", "#9C6500"),
    "outstanding": ("#FFC7CE", "#9C0006"),
}
_VOUCHER_BLOCK_COLUMNS = {
    "check": {
        "headers": (
            ("Código", 0, 0),
            ("Cliente", 1, 1),
            ("Fecha de Emisión", 2, 2),
            ("Nº Cheque", 3, 3),
            ("Banco", 4, 4),
            ("Tipo", 5, 5),
            ("Fecha de Pago", 6, 6),
            ("Importe", 7, 7),
        ),
        "merge_number": False,
    },
}
_DEFAULT_VOUCHER_COLUMNS = {
    "headers": (
        ("Código", 0, 0),
        ("Cliente", 1, 1),
        ("Fecha", 2, 2),
        ("Nº Comprobante", 3, 6),
        ("Importe", 7, 7),
    ),
    "merge_number": True,
}


def _a1(row, col):
    """Return an A1 cell reference (row is 1-based, col is 0-based)."""
    return f"{chr(65 + col)}{row}"


def _text(value):
    if value is False or value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _formats(workbook):
    def fmt(**kwargs):
        return workbook.add_format(kwargs)

    thin = {"border": 1, "border_color": "#D0D0D0"}
    return {
        "title": fmt(bold=True, font_size=18, font_color=NAVY_DARK, valign="vcenter"),
        "subtitle": fmt(
            bold=True,
            font_size=12,
            font_color=NAVY,
            align="right",
            valign="vcenter",
        ),
        "muted": fmt(font_size=9, font_color="#808080"),
        "muted_right": fmt(font_size=9, font_color="#808080", align="right"),
        "bar": fmt(bg_color=NAVY),
        "section": fmt(
            bold=True,
            font_color="#FFFFFF",
            font_size=11,
            bg_color=NAVY,
            valign="vcenter",
        ),
        "label": fmt(bold=True, bg_color=GREY_FILL, **thin),
        "value": fmt(**thin),
        "value_int": fmt(num_format=INT, align="right", **thin),
        "value_money": fmt(num_format=MONEY, align="right", **thin),
        "value_pct": fmt(
            num_format=PCT, align="right", bold=True, font_color=NAVY, **thin
        ),
        "value_money_bold": fmt(
            num_format=MONEY, align="right", bold=True, font_color=NAVY, **thin
        ),
        "header": fmt(
            bold=True,
            font_color=NAVY_DARK,
            bg_color=HDR_BLUE,
            border=1,
            border_color="#8EA9DB",
            valign="vcenter",
            text_wrap=True,
        ),
        "data": fmt(**thin),
        "data_money": fmt(num_format=MONEY, align="right", **thin),
        "sub": fmt(bold=True, bg_color=SUB_FILL, align="right", **thin),
        "sub_money": fmt(
            bold=True,
            bg_color=SUB_FILL,
            num_format=MONEY,
            align="right",
            **thin,
        ),
        "total": fmt(
            bold=True,
            font_color="#FFFFFF",
            bg_color=NAVY,
            align="right",
            border=1,
            border_color=NAVY,
        ),
        "total_money": fmt(
            bold=True,
            font_color="#FFFFFF",
            bg_color=NAVY,
            num_format=MONEY,
            align="right",
            border=1,
            border_color=NAVY,
        ),
        "recon_label": fmt(bold=True, font_size=12, font_color=NAVY_DARK, **thin),
        "recon_hint": fmt(italic=True, font_size=9, font_color="#808080", **thin),
        "recon_value": fmt(
            bold=True, font_size=13, num_format=MONEY_BIG, align="right", **thin
        ),
        "recon_total_label": fmt(
            bold=True,
            font_size=14,
            font_color="#FFFFFF",
            bg_color=NAVY,
            border=1,
            border_color=NAVY,
        ),
        "recon_total_hint": fmt(
            italic=True,
            font_size=9,
            font_color="#D6E4F7",
            bg_color=NAVY,
            border=1,
            border_color=NAVY,
        ),
        "recon_total_value": fmt(
            bold=True,
            font_size=16,
            font_color="#FFFFFF",
            bg_color=NAVY,
            num_format=MONEY_BIG,
            align="right",
            border=1,
            border_color=NAVY,
        ),
    }


def _merge(ws, row, c1, c2, value, fmt):
    ws.merge_range(row - 1, c1, row - 1, c2, value, fmt)


def _write(ws, row, col, value, fmt):
    ws.write(row - 1, col, value, fmt)


def _formula(ws, row, col, formula, fmt, cached):
    ws.write_formula(row - 1, col, formula, fmt, cached)


def _merge_formula(ws, row, c1, c2, formula, fmt, cached):
    _merge(ws, row, c1, c2, "", fmt)
    _formula(ws, row, c1, formula, fmt, cached)


def _sum_or_zero(ws, row, col, first, last, fmt, cached):
    if first is None:
        _write(ws, row, col, 0, fmt)
        return
    _formula(
        ws,
        row,
        col,
        f"=SUM({_a1(first, col)}:{_a1(last, col)})",
        fmt,
        cached,
    )


def _write_membrete(ws, fmt, payload):
    _merge(ws, 1, 0, 4, payload.get("company") or "", fmt["title"])
    _merge(ws, 1, 5, 7, "Planilla de Cobranza", fmt["subtitle"])
    ws.set_row(0, 26)
    _merge(ws, 2, 0, 4, "", fmt["muted"])
    _merge(ws, 2, 5, 7, payload.get("reference") or "", fmt["muted_right"])
    ws.set_row(1, 14)
    _merge(ws, 3, 0, 7, "", fmt["bar"])
    ws.set_row(2, 4)
    printed = _text(payload.get("printed_on"))
    _merge(ws, 4, 0, 7, printed, fmt["muted"])
    ws.set_row(3, 14)
    ws.set_row(4, 8)


def _write_field_row(
    ws, fmt, row, left, left_val, right, right_val, left_fmt, right_fmt
):
    _merge(ws, row, 0, 1, left, fmt["label"])
    _merge(ws, row, 2, 3, left_val, left_fmt)
    _merge(ws, row, 4, 5, right, fmt["label"])
    _merge(ws, row, 6, 7, right_val, right_fmt)


def _write_section(ws, fmt, row, title):
    _merge(ws, row, 0, 7, title, fmt["section"])
    ws.set_row(row - 1, 20)


def _write_headers(ws, fmt, row, cells):
    for title, c1, c2 in cells:
        if c1 == c2:
            _write(ws, row, c1, title, fmt["header"])
        else:
            _merge(ws, row, c1, c2, title, fmt["header"])
    ws.set_row(row - 1, 26)


def _write_resumen(ws, fmt, payload, applied_ref, collected_ref, commission_refs):
    _write_section(ws, fmt, 6, "Resumen")
    _write_field_row(
        ws,
        fmt,
        7,
        "Referencia",
        payload.get("reference") or "",
        "Estado",
        payload.get("state_label") or "",
        fmt["value"],
        fmt["value"],
    )
    _write_field_row(
        ws,
        fmt,
        8,
        "Vendedor",
        payload.get("seller_name") or "",
        "Impreso el",
        _text(payload.get("printed_on")),
        fmt["value"],
        fmt["value"],
    )
    _write_field_row(
        ws,
        fmt,
        9,
        "Desde",
        _text(payload.get("date_from")),
        "Hasta",
        _text(payload.get("date_to")),
        fmt["value"],
        fmt["value"],
    )
    _write_field_row(
        ws,
        fmt,
        10,
        "Cantidad de Clientes",
        payload.get("customer_count") or 0,
        "Cantidad de Comprobantes",
        payload.get("voucher_count") or 0,
        fmt["value_int"],
        fmt["value_int"],
    )
    collected = payload.get("collected_total") or 0.0
    applied = payload.get("applied_total") or 0.0
    residual = (payload.get("customer_totals") or {}).get("residual") or 0.0
    commission = sum(
        block.get("subtotal_commission") or 0.0
        for block in payload.get("document_blocks") or ()
    )
    _merge(ws, 11, 0, 1, "Total Cobrado", fmt["label"])
    if collected_ref:
        _merge_formula(ws, 11, 2, 3, f"={collected_ref}", fmt["value_money"], collected)
    else:
        _merge(ws, 11, 2, 3, collected, fmt["value_money"])
    _merge(ws, 11, 4, 5, "Total Aplicado", fmt["label"])
    if applied_ref:
        _merge_formula(ws, 11, 6, 7, f"={applied_ref}", fmt["value_money"], applied)
    else:
        _merge(ws, 11, 6, 7, applied, fmt["value_money"])
    _merge(ws, 12, 0, 1, "Remanente", fmt["label"])
    _merge_formula(ws, 12, 2, 3, "=C11-G11", fmt["value_money"], residual)
    _merge(ws, 12, 4, 5, "Moneda", fmt["label"])
    _merge(ws, 12, 6, 7, "", fmt["value"])
    percent = (payload.get("commission_percent") or 0.0) / 100.0
    _merge(ws, 13, 0, 1, "% Comisión Vendedor", fmt["label"])
    _merge(ws, 13, 2, 3, percent, fmt["value_pct"])
    _merge(ws, 13, 4, 5, "Total Comisión Devengada", fmt["label"])
    if commission_refs:
        _merge_formula(
            ws,
            13,
            6,
            7,
            "=" + "+".join(commission_refs),
            fmt["value_money_bold"],
            commission,
        )
    else:
        _merge(ws, 13, 6, 7, commission, fmt["value_money_bold"])
    ws.set_row(13, 8)


def _write_customers(ws, fmt, payload, start):
    rows = payload.get("customers") or []
    totals = payload.get("customer_totals") or {}
    _write_section(ws, fmt, start, "Clientes")
    _write_headers(
        ws,
        fmt,
        start + 1,
        (
            ("Código", 0, 0),
            ("Cliente", 1, 1),
            ("Cobrado", 2, 2),
            ("Aplicado", 3, 3),
            ("Remanente", 4, 4),
            ("Motivo del Remanente", 5, 7),
        ),
    )
    first = start + 2 if rows else None
    last = start + 1 + len(rows) if rows else None
    for index, item in enumerate(rows):
        row = start + 2 + index
        _write(ws, row, 0, item.get("code") or "", fmt["data"])
        _write(ws, row, 1, item.get("name") or "", fmt["data"])
        _write(ws, row, 2, item.get("collected") or 0.0, fmt["data_money"])
        _write(ws, row, 3, item.get("applied") or 0.0, fmt["data_money"])
        _write(ws, row, 4, item.get("residual") or 0.0, fmt["data_money"])
        _merge(
            ws,
            row,
            5,
            7,
            item.get("residual_reason") or "",
            fmt["data"],
        )
    total_row = start + 2 + len(rows)
    _merge(ws, total_row, 0, 1, "Total", fmt["total"])
    _sum_or_zero(
        ws,
        total_row,
        2,
        first,
        last,
        fmt["total_money"],
        totals.get("collected") or 0.0,
    )
    _sum_or_zero(
        ws,
        total_row,
        3,
        first,
        last,
        fmt["total_money"],
        totals.get("applied") or 0.0,
    )
    _sum_or_zero(
        ws,
        total_row,
        4,
        first,
        last,
        fmt["total_money"],
        totals.get("residual") or 0.0,
    )
    _merge(ws, total_row, 5, 7, "", fmt["total"])
    return total_row + 2, _a1(total_row, 2), _a1(total_row, 3), _a1(total_row, 4)


def _write_documents(ws, fmt, payload, start):
    applied_refs = []
    commission_refs = []
    row = start
    for block in payload.get("document_blocks") or ():
        title = _KIND_TITLES.get(block.get("kind"), block.get("kind") or "")
        rows = block.get("rows") or []
        _write_section(ws, fmt, row, title)
        _write_headers(
            ws,
            fmt,
            row + 1,
            (
                ("Código", 0, 0),
                ("Cliente", 1, 1),
                ("Documento", 2, 2),
                ("Vencimiento", 3, 3),
                ("Saldo", 4, 4),
                ("Aplicado", 5, 5),
                ("Comisión", 6, 7),
            ),
        )
        first = row + 2 if rows else None
        last = row + 1 + len(rows) if rows else None
        for index, item in enumerate(rows):
            data_row = row + 2 + index
            _write(ws, data_row, 0, item.get("code") or "", fmt["data"])
            _write(ws, data_row, 1, item.get("name") or "", fmt["data"])
            _write(ws, data_row, 2, item.get("invoice_number") or "", fmt["data"])
            _write(ws, data_row, 3, _text(item.get("due_date")), fmt["data"])
            _write(ws, data_row, 4, "", fmt["data_money"])
            _write(
                ws, data_row, 5, item.get("amount_applied") or 0.0, fmt["data_money"]
            )
            _merge(
                ws,
                data_row,
                6,
                7,
                item.get("commission") or 0.0,
                fmt["data_money"],
            )
        sub_row = row + 2 + len(rows)
        _merge(ws, sub_row, 0, 4, "Subtotal", fmt["sub"])
        _sum_or_zero(
            ws,
            sub_row,
            5,
            first,
            last,
            fmt["sub_money"],
            block.get("subtotal_applied") or 0.0,
        )
        if first is None:
            _merge(ws, sub_row, 6, 7, 0, fmt["sub_money"])
        else:
            _merge_formula(
                ws,
                sub_row,
                6,
                7,
                f"=SUM({_a1(first, 6)}:{_a1(last, 6)})",
                fmt["sub_money"],
                block.get("subtotal_commission") or 0.0,
            )
        applied_refs.append(_a1(sub_row, 5))
        commission_refs.append(_a1(sub_row, 6))
        row = sub_row + 2
    total_row = row
    applied = payload.get("applied_total") or 0.0
    commission = sum(
        block.get("subtotal_commission") or 0.0
        for block in payload.get("document_blocks") or ()
    )
    _merge(ws, total_row, 0, 4, "Total Aplicado", fmt["total"])
    if applied_refs:
        _formula(
            ws, total_row, 5, "=" + "+".join(applied_refs), fmt["total_money"], applied
        )
        _merge_formula(
            ws,
            total_row,
            6,
            7,
            "=" + "+".join(commission_refs),
            fmt["total_money"],
            commission,
        )
    else:
        _write(ws, total_row, 5, 0, fmt["total_money"])
        _merge(ws, total_row, 6, 7, 0, fmt["total_money"])
    return (
        total_row + 2,
        _a1(total_row, 5),
        commission_refs,
    )


def _write_vouchers(ws, fmt, payload, start):
    subtotals = {}
    refs = []
    row = start
    for block in payload.get("voucher_blocks") or ():
        code = block.get("code") or ""
        label = block.get("label") or code
        rows = block.get("rows") or []
        columns = _VOUCHER_BLOCK_COLUMNS.get(code, _DEFAULT_VOUCHER_COLUMNS)
        _write_section(ws, fmt, row, f"Comprobantes — {label}")
        _write_headers(ws, fmt, row + 1, columns["headers"])
        first = row + 2 if rows else None
        last = row + 1 + len(rows) if rows else None
        for index, item in enumerate(rows):
            data_row = row + 2 + index
            _write(ws, data_row, 0, item.get("code") or "", fmt["data"])
            _write(ws, data_row, 1, item.get("name") or "", fmt["data"])
            _write(ws, data_row, 2, _text(item.get("date")), fmt["data"])
            if columns.get("merge_number"):
                _merge(
                    ws,
                    data_row,
                    3,
                    6,
                    item.get("number") or "",
                    fmt["data"],
                )
            else:
                _write(ws, data_row, 3, item.get("number") or "", fmt["data"])
                _write(ws, data_row, 4, "", fmt["data"])
                _write(ws, data_row, 5, "", fmt["data"])
                _write(ws, data_row, 6, "", fmt["data"])
            _write(ws, data_row, 7, item.get("amount") or 0.0, fmt["data_money"])
        sub_row = row + 2 + len(rows)
        _merge(ws, sub_row, 0, 6, "Subtotal", fmt["sub"])
        _sum_or_zero(
            ws,
            sub_row,
            7,
            first,
            last,
            fmt["sub_money"],
            block.get("subtotal") or 0.0,
        )
        cell = _a1(sub_row, 7)
        subtotals[code] = cell
        refs.append(cell)
        row = sub_row + 2
    total_row = row
    collected = payload.get("collected_total") or 0.0
    _merge(ws, total_row, 0, 6, "Total Cobrado", fmt["total"])
    if refs:
        _formula(
            ws,
            total_row,
            7,
            "=" + "+".join(refs),
            fmt["total_money"],
            collected,
        )
    else:
        _write(ws, total_row, 7, 0, fmt["total_money"])
    return total_row + 2, _a1(total_row, 7), subtotals


def _banner_format(workbook, status):
    bg_color, fg_color = _BANNER_FILL.get(status, _BANNER_FILL["balanced"])
    return workbook.add_format(
        {
            "bold": True,
            "font_size": 14,
            "font_color": fg_color,
            "bg_color": bg_color,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": NAVY,
        }
    )


def _write_recon(ws, workbook, fmt, payload, start, voucher_subtotals):
    tendered = payload.get("tendered") or {}
    recon = payload.get("recon") or {}
    _write_section(ws, fmt, start, "Conciliación del Vendedor")
    _write_headers(
        ws,
        fmt,
        start + 1,
        (
            ("Composición de lo Rendido", 0, 2),
            ("Efectivo en Caja", 3, 3),
            ("Depósitos", 4, 4),
            ("Cheques", 5, 5),
            ("Transferencias", 6, 6),
            ("Total Rendido", 7, 7),
        ),
    )
    data_row = start + 2
    _merge(ws, data_row, 0, 2, "", fmt["data"])
    _write(ws, data_row, 3, tendered.get("cash") or 0.0, fmt["data_money"])
    for col, code, key in (
        (4, "cash_deposit", "deposits"),
        (5, "check", "checks"),
        (6, "bank_transfer", "transfers"),
    ):
        amount = tendered.get(key) or 0.0
        ref = voucher_subtotals.get(code)
        if ref:
            _formula(ws, data_row, col, f"={ref}", fmt["data_money"], amount)
        else:
            _write(ws, data_row, col, amount, fmt["data_money"])

    _formula(
        ws,
        data_row,
        7,
        f"=SUM({_a1(data_row, 3)}:{_a1(data_row, 6)})",
        fmt["data_money"],
        tendered.get("total") or 0.0,
    )
    collected_row = data_row + 2
    withheld_row = collected_row + 1
    net_row = withheld_row + 1
    tendered_row = net_row + 2
    diff_row = tendered_row + 1
    banner_row = diff_row + 2

    def _recon_line(row, label, hint, formula, cached, total=False):
        label_fmt = fmt["recon_total_label"] if total else fmt["recon_label"]
        hint_fmt = fmt["recon_total_hint"] if total else fmt["recon_hint"]
        value_fmt = fmt["recon_total_value"] if total else fmt["recon_value"]
        _merge(ws, row, 0, 2, label, label_fmt)
        _merge(ws, row, 3, 5, hint, hint_fmt)
        if formula:
            _merge_formula(ws, row, 6, 7, formula, value_fmt, cached)
        else:
            _merge(ws, row, 6, 7, cached, value_fmt)
        ws.set_row(row - 1, 30 if total else 22)

    _recon_line(
        collected_row,
        "Total Cobrado",
        "lo que pagaron los clientes",
        None,
        recon.get("collected") or 0.0,
    )
    _recon_line(
        withheld_row,
        "(−) Comisión Retenida por el Vendedor",
        "la que descuenta en el acto; 0 si se liquida aparte",
        None,
        recon.get("withheld") or 0.0,
    )
    _recon_line(
        net_row,
        "(=) Neto a Rendir",
        "lo que tenía que entregar a la empresa",
        f"={_a1(collected_row, 6)}-{_a1(withheld_row, 6)}",
        recon.get("net_due") or 0.0,
        total=True,
    )
    _recon_line(
        tendered_row,
        "Total Rendido",
        "lo que entregó — efectivo, depósitos, cheques y transferencias",
        f"={_a1(data_row, 7)}",
        recon.get("tendered") or 0.0,
    )
    _recon_line(
        diff_row,
        "(=) Diferencia",
        "Rendido − Neto a Rendir",
        f"={_a1(tendered_row, 6)}-{_a1(net_row, 6)}",
        recon.get("difference") or 0.0,
        total=True,
    )
    message = recon.get("status_message") or ""
    _merge(
        ws,
        banner_row,
        0,
        7,
        message,
        _banner_format(workbook, recon.get("status") or "balanced"),
    )
    ws.set_row(banner_row - 1, 34)
    return banner_row


def _build_xlsx(payload):
    """Render a Planilla workbook from payload primitives. No ORM access."""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    try:
        ws = workbook.add_worksheet("Planilla de Cobranza")
        for index, width in enumerate(COLUMN_WIDTHS):
            ws.set_column(index, index, width)
        fmt = _formats(workbook)
        _write_membrete(ws, fmt, payload)
        # Document/voucher sections are written first so resumen can cache
        # forward-looking totals; row numbers match the template cursor.
        customer_start = 15
        next_row, _c_ref, _a_ref, _r_ref = _write_customers(
            ws, fmt, payload, customer_start
        )
        next_row, applied_ref, commission_refs = _write_documents(
            ws, fmt, payload, next_row
        )
        next_row, collected_ref, voucher_subtotals = _write_vouchers(
            ws, fmt, payload, next_row
        )
        last_row = _write_recon(ws, workbook, fmt, payload, next_row, voucher_subtotals)
        _write_resumen(ws, fmt, payload, applied_ref, collected_ref, commission_refs)
        ws.freeze_panes(5, 0)
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 0)
        ws.repeat_rows(0, 3)
        ws.print_area(0, 0, last_row - 1, 7)
        ws.set_margins(0.3, 0.3, 0.4, 0.4)
    finally:
        workbook.close()
    return _align_workbook_xml(output.getvalue())


_TEMPLATE_COLS = (
    "<cols>"
    '<col min="1" max="1" width="13" customWidth="1"/>'
    '<col min="2" max="2" width="32" customWidth="1"/>'
    '<col min="3" max="3" width="19" customWidth="1"/>'
    '<col min="4" max="4" width="17" customWidth="1"/>'
    '<col min="5" max="5" width="14" customWidth="1"/>'
    '<col min="6" max="6" width="14" customWidth="1"/>'
    '<col min="7" max="7" width="15" customWidth="1"/>'
    '<col min="8" max="8" width="15" customWidth="1"/>'
    "</cols>"
)


def _align_workbook_xml(content):
    """Match template col widths and fitToWidth so openpyxl reads them exactly.

    xlsxwriter stores a converted character width (32 → 32.71) and omits the
    default fitToWidth=1 attribute.
    """
    source = ZipFile(BytesIO(content), "r")
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as dest:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.startswith("xl/worksheets/") and info.filename.endswith(
                ".xml"
            ):
                xml = data.decode("utf-8")
                if "fitToWidth=" not in xml:
                    xml = xml.replace("<pageSetup ", '<pageSetup fitToWidth="1" ', 1)
                xml = re.sub(
                    r"<cols>.*?</cols>", _TEMPLATE_COLS, xml, count=1, flags=re.DOTALL
                )
                data = xml.encode("utf-8")
            dest.writestr(info, data)
    source.close()
    return output.getvalue()


class CollectionSheetXlsx(models.AbstractModel):
    _name = "collection.sheet.xlsx"
    _description = "Collection Sheet XLSX"

    @api.model
    def _render_xlsx(self, payload):
        """Return .xlsx bytes for a shared Planilla payload (no ORM)."""
        return _build_xlsx(payload)
