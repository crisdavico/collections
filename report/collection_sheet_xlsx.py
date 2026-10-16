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
COLUMN_WIDTHS = (13, 32, 19, 17, 14, 14, 15, 15, 14, 16, 15)
# Every text cell holds data (customer names, document and voucher numbers,
# banks): xlsxwriter must not turn a leading "=" into a live formula nor a
# URL-looking string into a hyperlink. Intentional formulas use write_formula.
WORKBOOK_OPTIONS = {"strings_to_formulas": False, "strings_to_urls": False}
# Hidden column right of the printed area: a per-customer number the Clientes
# SUMIFs key on, so two customers never match by name (duplicates, or names
# holding the SUMIF wildcards * and ?).
KEY_COL = len(COLUMN_WIDTHS)
_KIND_TITLES = {"invoice": "Facturas", "quotation": "Presupuestos"}
_KIND_LABELS = {"invoice": "Factura", "quotation": "Presupuesto"}
# The verdict block opens the sheet right below the frozen header (rows 1-5).
VERDICT_START = 6
_DEPOSITS_NOTE = (
    "Depósitos de clientes: el cliente depositó en la cuenta de la empresa. "
    "Depósitos del vendedor: el vendedor depositó en el banco el efectivo cobrado."
)
# Flat sheets: one row per line, no merges, so they filter, sort and copy cleanly.
_DOCUMENT_TABLE_COLUMNS = (
    ("Código", 12, "data"),
    ("Cliente", 36, "data"),
    ("Tipo", 14, "data"),
    ("Documento", 18, "data"),
    ("Vencimiento", 13, "data_date"),
    ("Saldo", 15, "data_money"),
    ("Aplicado", 15, "data_money"),
    ("Comisión", 15, "data_money"),
)
_VOUCHER_TABLE_COLUMNS = (
    ("Código", 12, "data"),
    ("Cliente", 36, "data"),
    ("Medio de Pago", 22, "data"),
    ("Fecha", 13, "data_date"),
    ("Nº Comprobante", 20, "data"),
    ("Banco", 20, "data"),
    ("Tipo de Cheque", 15, "data"),
    ("Fecha de Pago", 14, "data_date"),
    ("Importe", 15, "data_money"),
)
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
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return value


def _date_cell(value):
    if value is False or value is None:
        return ""
    return value


def _formats(workbook):
    def fmt(**kwargs):
        return workbook.add_format(kwargs)

    thin = {"border": 1, "border_color": "#D0D0D0"}
    return {
        "title": fmt(bold=True, font_size=18, font_color=NAVY_DARK, valign="vcenter"),
        "muted": fmt(font_size=9, font_color="#808080"),
        "bar": fmt(bg_color=NAVY),
        "section": fmt(
            bold=True,
            font_color="#FFFFFF",
            font_size=11,
            bg_color=NAVY,
            valign="vcenter",
        ),
        "label": fmt(bold=True, bg_color=GREY_FILL, align="right", **thin),
        "value": fmt(align="right", **thin),
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
        "data_date": fmt(num_format="DD/MM/YYYY", align="center", **thin),
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
        "verdict_label": fmt(
            bold=True,
            font_color=NAVY_DARK,
            bg_color=HDR_BLUE,
            align="center",
            valign="vcenter",
            border=1,
            border_color="#8EA9DB",
        ),
        "verdict_value": fmt(
            bold=True,
            font_size=16,
            font_color=NAVY_DARK,
            num_format=MONEY_BIG,
            align="center",
            valign="vcenter",
            border=1,
            border_color="#8EA9DB",
        ),
        "mismatch": fmt(
            bold=True,
            font_color="#9C6500",
            bg_color="#FFEB9C",
            text_wrap=True,
            valign="vcenter",
            border=1,
            border_color="#9C6500",
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


def _section_span(start, n_rows):
    """Return (first, last, footer, next_row) for title + header + n data + footer."""
    first = start + 2 if n_rows else None
    last = start + 1 + n_rows if n_rows else None
    footer = start + 2 + n_rows
    return first, last, footer, footer + 2


def _data_ranges(start, counts):
    """Return data ranges and the total row for stacked section blocks."""
    cursor = start
    ranges = []
    for n_rows in counts:
        first, last, _footer, cursor = _section_span(cursor, n_rows)
        if first is not None:
            ranges.append((first, last))
    return ranges, cursor


def _abs_range(first, last, col):
    letter = chr(65 + col)
    return f"${letter}${first}:${letter}${last}"


def _sumif_formula(criteria_row, ranges, sum_col):
    """SUMIF each data range by the hidden customer key on ``criteria_row``."""
    if not ranges:
        return "=0"
    criteria = _a1(criteria_row, KEY_COL)
    parts = [
        (
            f"SUMIF({_abs_range(first, last, KEY_COL)},"
            f"{criteria},{_abs_range(first, last, sum_col)})"
        )
        for first, last in ranges
    ]
    return "=" + "+".join(parts)


def _customer_keys(payload):
    """Number each Clientes row 1..n by partner (name only for bare payloads)."""
    keys = {}
    for item in payload.get("customers") or ():
        keys.setdefault(item.get("partner_id") or item.get("name") or "", len(keys) + 1)
    return keys


def _write_key(ws, row, keys, item):
    """Write the hidden customer key of a Clientes, document or voucher row."""
    key = keys.get(item.get("partner_id") or item.get("name") or "")
    if key:
        ws.write_number(row - 1, KEY_COL, key)


def _customer_detail_ranges(payload, customer_start):
    """Document/voucher data ranges that sit below the Clientes section."""
    n_customers = len(payload.get("customers") or [])
    _, _, _, after_customers = _section_span(customer_start, n_customers)
    document_counts = [
        len(block.get("rows") or []) for block in payload.get("document_blocks") or ()
    ]
    document_ranges, document_total = _data_ranges(after_customers, document_counts)
    voucher_counts = [
        len(block.get("rows") or []) for block in payload.get("voucher_blocks") or ()
    ]
    voucher_ranges, _ = _data_ranges(document_total + 2, voucher_counts)
    return document_ranges, voucher_ranges


def _write_membrete(ws, fmt, payload):
    _merge(ws, 1, 0, 7, "Planilla de Cobranza", fmt["title"])
    ws.set_row(0, 26)
    _merge(ws, 2, 0, 7, payload.get("reference") or "", fmt["muted"])
    ws.set_row(1, 14)
    _merge(ws, 3, 0, 7, "", fmt["bar"])
    ws.set_row(2, 4)
    _merge(ws, 4, 0, 7, _seller_period(payload), fmt["muted"])
    ws.set_row(3, 14)
    ws.set_row(4, 8)


def _seller_period(payload):
    """Row 4 of the repeated print header: who and which dates."""
    parts = []
    if payload.get("seller_name"):
        parts.append(f"Vendedor: {payload['seller_name']}")
    if payload.get("date_from") or payload.get("date_to"):
        period = f"{_text(payload.get('date_from'))} – {_text(payload.get('date_to'))}"
        parts.append(f"Período: {period}")
    return " · ".join(parts)


def _money_text(amount):
    return f"{amount or 0.0:,.2f}"


def _mismatch_message(payload):
    allocated = payload.get("allocated_collected") or 0.0
    collected = payload.get("collected_total") or 0.0
    return (
        f"Atención: lo cobrado según las asignaciones ({_money_text(allocated)}) "
        "no coincide con el total de comprobantes de la planilla "
        f"({_money_text(collected)}). "
        f"Diferencia: {_money_text(abs(collected - allocated))}."
    )


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


def _verdict_rows(payload):
    """Rows the verdict block takes: section, headers, values, banner, mismatch."""
    return 5 if payload.get("mismatch") else 4


def _write_verdict(ws, workbook, fmt, payload, refs):
    """The answer first: what was due, what was handed in, and the banner."""
    recon = payload.get("recon") or {}
    _write_section(ws, fmt, VERDICT_START, "Resultado")
    columns = ((0, 1), (2, 4), (5, 7))
    labels = ("Neto a Rendir", "Total Rendido", "Diferencia")
    keys = ("net_due", "tendered", "difference")
    for (c1, c2), label in zip(columns, labels, strict=True):
        _merge(ws, VERDICT_START + 1, c1, c2, label, fmt["verdict_label"])
    for (c1, c2), key in zip(columns, keys, strict=True):
        cached = recon.get(key) or 0.0
        _merge_formula(
            ws,
            VERDICT_START + 2,
            c1,
            c2,
            f"={refs[key]}",
            fmt["verdict_value"],
            cached,
        )
    ws.set_row(VERDICT_START, 18)
    ws.set_row(VERDICT_START + 1, 28)
    banner_row = VERDICT_START + 3
    _merge(
        ws,
        banner_row,
        0,
        7,
        recon.get("status_message") or "",
        _banner_format(workbook, recon.get("status") or "balanced"),
    )
    ws.set_row(banner_row - 1, 30)
    if payload.get("mismatch"):
        _merge(ws, banner_row + 1, 0, 7, _mismatch_message(payload), fmt["mismatch"])
        ws.set_row(banner_row, 32)


def _write_datos(
    ws, fmt, payload, start, applied_ref, collected_ref, commission_refs, residual_ref
):
    _write_section(ws, fmt, start, "Datos de la Planilla")
    _write_field_row(
        ws,
        fmt,
        start + 1,
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
        start + 2,
        "Vendedor",
        payload.get("seller_name") or "",
        "Moneda",
        payload.get("currency_name") or "",
        fmt["value"],
        fmt["value"],
    )
    _write_field_row(
        ws,
        fmt,
        start + 3,
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
        start + 4,
        "Cantidad de Clientes",
        payload.get("customer_count") or 0,
        "Cantidad de Comprobantes",
        payload.get("voucher_count") or 0,
        fmt["value_int"],
        fmt["value_int"],
    )
    percent = (payload.get("commission_percent") or 0.0) / 100.0
    _merge(ws, start + 5, 0, 1, "% Comisión Vendedor", fmt["label"])
    _merge(ws, start + 5, 2, 3, percent, fmt["value_pct"])
    ws.set_row(start + 5, 8)

    totals = start + 7
    _write_section(ws, fmt, totals, "Totales")
    collected = payload.get("collected_total") or 0.0
    applied = payload.get("applied_total") or 0.0
    residual = (payload.get("customer_totals") or {}).get("residual") or 0.0
    commission = sum(
        block.get("subtotal_commission") or 0.0
        for block in payload.get("document_blocks") or ()
    )
    _merge(ws, totals + 1, 0, 1, "Total Cobrado", fmt["label"])
    if collected_ref:
        _merge_formula(
            ws, totals + 1, 2, 3, f"={collected_ref}", fmt["value_money"], collected
        )
    else:
        _merge(ws, totals + 1, 2, 3, collected, fmt["value_money"])
    _merge(ws, totals + 1, 4, 5, "Total Aplicado", fmt["label"])
    if applied_ref:
        _merge_formula(
            ws, totals + 1, 6, 7, f"={applied_ref}", fmt["value_money"], applied
        )
    else:
        _merge(ws, totals + 1, 6, 7, applied, fmt["value_money"])
    _merge(ws, totals + 2, 0, 1, "Remanente", fmt["label"])
    if residual_ref:
        _merge_formula(
            ws, totals + 2, 2, 3, f"={residual_ref}", fmt["value_money"], residual
        )
    else:
        _merge_formula(
            ws,
            totals + 2,
            2,
            3,
            f"={_a1(totals + 1, 2)}-{_a1(totals + 1, 6)}",
            fmt["value_money"],
            residual,
        )
    _merge(ws, totals + 2, 4, 5, "Total Comisión Devengada", fmt["label"])
    if commission_refs:
        _merge_formula(
            ws,
            totals + 2,
            6,
            7,
            "=" + "+".join(commission_refs),
            fmt["value_money_bold"],
            commission,
        )
    else:
        _merge(ws, totals + 2, 6, 7, commission, fmt["value_money_bold"])
    ws.set_row(totals + 2, 8)


def _write_customers(ws, fmt, payload, start):
    rows = payload.get("customers") or []
    totals = payload.get("customer_totals") or {}
    keys = _customer_keys(payload)
    document_ranges, voucher_ranges = _customer_detail_ranges(payload, start)
    first, last, total_row, next_row = _section_span(start, len(rows))
    _write_section(ws, fmt, start, "Clientes")
    _write_headers(
        ws,
        fmt,
        start + 1,
        (
            ("Código", 0, 0),
            ("Cliente", 1, 1),
            ("Saldo Total", 2, 2),
            ("Cobrado", 3, 3),
            ("Aplicado", 4, 4),
            ("Remanente", 5, 5),
        ),
    )
    for index, item in enumerate(rows):
        row = first + index
        _write(ws, row, 0, item.get("code") or "", fmt["data"])
        _write(ws, row, 1, item.get("name") or "", fmt["data"])
        _write_key(ws, row, keys, item)
        _formula(
            ws,
            row,
            2,
            _sumif_formula(row, document_ranges, 4),
            fmt["data_money"],
            item.get("debt") or 0.0,
        )
        _formula(
            ws,
            row,
            3,
            _sumif_formula(row, voucher_ranges, 7),
            fmt["data_money"],
            item.get("collected") or 0.0,
        )
        _formula(
            ws,
            row,
            4,
            _sumif_formula(row, document_ranges, 5),
            fmt["data_money"],
            item.get("applied") or 0.0,
        )
        _formula(
            ws,
            row,
            5,
            f"={_a1(row, 2)}-{_a1(row, 4)}",
            fmt["data_money"],
            item.get("residual") or 0.0,
        )
    _merge(ws, total_row, 0, 1, "Total", fmt["total"])
    _sum_or_zero(
        ws,
        total_row,
        2,
        first,
        last,
        fmt["total_money"],
        totals.get("debt") or 0.0,
    )
    _sum_or_zero(
        ws,
        total_row,
        3,
        first,
        last,
        fmt["total_money"],
        totals.get("collected") or 0.0,
    )
    _sum_or_zero(
        ws,
        total_row,
        4,
        first,
        last,
        fmt["total_money"],
        totals.get("applied") or 0.0,
    )
    _sum_or_zero(
        ws,
        total_row,
        5,
        first,
        last,
        fmt["total_money"],
        totals.get("residual") or 0.0,
    )
    return next_row, _a1(total_row, 5)


def _write_documents(ws, fmt, payload, start):
    applied_refs = []
    commission_refs = []
    keys = _customer_keys(payload)
    cursor = start
    for block in payload.get("document_blocks") or ():
        title = _KIND_TITLES.get(block.get("kind"), block.get("kind") or "")
        rows = block.get("rows") or []
        block_start = cursor
        first, last, sub_row, cursor = _section_span(block_start, len(rows))
        _write_section(ws, fmt, block_start, title)
        _write_headers(
            ws,
            fmt,
            block_start + 1,
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
        for index, item in enumerate(rows):
            data_row = first + index
            _write(ws, data_row, 0, item.get("code") or "", fmt["data"])
            _write(ws, data_row, 1, item.get("name") or "", fmt["data"])
            _write_key(ws, data_row, keys, item)
            _write(ws, data_row, 2, item.get("invoice_number") or "", fmt["data"])
            _write(ws, data_row, 3, _date_cell(item.get("due_date")), fmt["data_date"])
            _write(
                ws,
                data_row,
                4,
                item.get("invoice_balance") or 0.0,
                fmt["data_money"],
            )
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
    total_row = cursor
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
    keys = _customer_keys(payload)
    cursor = start
    for block in payload.get("voucher_blocks") or ():
        code = block.get("code") or ""
        label = block.get("label") or code
        rows = block.get("rows") or []
        columns = _VOUCHER_BLOCK_COLUMNS.get(code, _DEFAULT_VOUCHER_COLUMNS)
        block_start = cursor
        first, last, sub_row, cursor = _section_span(block_start, len(rows))
        _write_section(ws, fmt, block_start, f"Comprobantes — {label}")
        _write_headers(ws, fmt, block_start + 1, columns["headers"])
        for index, item in enumerate(rows):
            data_row = first + index
            _write(ws, data_row, 0, item.get("code") or "", fmt["data"])
            _write(ws, data_row, 1, item.get("name") or "", fmt["data"])
            _write_key(ws, data_row, keys, item)
            _write(ws, data_row, 2, _date_cell(item.get("date")), fmt["data_date"])
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
                _write(ws, data_row, 4, item.get("check_bank") or "", fmt["data"])
                _write(ws, data_row, 5, item.get("check_type") or "", fmt["data"])
                _write(
                    ws,
                    data_row,
                    6,
                    _date_cell(item.get("check_payment_date")),
                    fmt["data_date"],
                )
            _write(ws, data_row, 7, item.get("amount") or 0.0, fmt["data_money"])
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
    total_row = cursor
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


def _write_recon(ws, fmt, payload, start, voucher_subtotals):
    tendered = payload.get("tendered") or {}
    recon = payload.get("recon") or {}
    _merge(ws, start, 0, 10, "Conciliación del Vendedor", fmt["section"])
    ws.set_row(start - 1, 20)
    _write_headers(
        ws,
        fmt,
        start + 1,
        (
            ("Composición de lo Rendido", 0, 2),
            ("Efectivo en Caja", 3, 3),
            ("Depósitos de clientes", 4, 4),
            ("Cheques", 5, 5),
            ("Transferencias", 6, 6),
            ("Echeqs", 7, 7),
            ("Retenciones", 8, 8),
            ("Depósitos del vendedor", 9, 9),
            ("Total Rendido", 10, 10),
        ),
    )
    data_row = start + 2
    _merge(ws, data_row, 0, 2, "", fmt["data"])
    _write(ws, data_row, 3, tendered.get("cash") or 0.0, fmt["data_money"])
    for col, code, key in (
        (4, "cash_deposit", "deposits"),
        (5, "check", "checks"),
        (6, "bank_transfer", "transfers"),
        (7, "echeck", "echecks"),
        (8, "retention_certificate", "retentions"),
        (9, "seller_deposit", "seller_deposits"),
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
        10,
        f"=SUM({_a1(data_row, 3)}:{_a1(data_row, 9)})",
        fmt["data_money"],
        tendered.get("total") or 0.0,
    )
    _merge(ws, data_row + 1, 0, 10, _DEPOSITS_NOTE, fmt["recon_hint"])
    collected_row = data_row + 2
    withheld_row = collected_row + 1
    net_row = withheld_row + 1
    tendered_row = net_row + 2
    diff_row = tendered_row + 1

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
        f"={_a1(data_row, 10)}",
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
    refs = {
        "net_due": _a1(net_row, 6),
        "tendered": _a1(tendered_row, 6),
        "difference": _a1(diff_row, 6),
    }
    return diff_row, refs


def _write_table(workbook, fmt, name, columns, rows):
    """Add a flat worksheet holding one Excel table with a frozen header."""
    ws = workbook.add_worksheet(name)
    for index, (_title, width, _style) in enumerate(columns):
        ws.set_column(index, index, width)
    # An Excel table needs a data row; an empty sheet keeps one blank row.
    data = rows or [[""] * len(columns)]
    ws.add_table(
        0,
        0,
        len(data),
        len(columns) - 1,
        {
            "name": name,
            "style": "Table Style Light 9",
            "data": data,
            "columns": [
                {"header": title, "format": fmt[style]}
                for title, _width, style in columns
            ],
        },
    )
    ws.freeze_panes(1, 0)
    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 0)
    ws.repeat_rows(0)
    return ws


def _document_table_rows(payload):
    rows = []
    for block in payload.get("document_blocks") or ():
        kind = _KIND_LABELS.get(block.get("kind"), block.get("kind") or "")
        for item in block.get("rows") or ():
            rows.append(
                [
                    item.get("code") or "",
                    item.get("name") or "",
                    kind,
                    item.get("invoice_number") or "",
                    _date_cell(item.get("due_date")),
                    item.get("invoice_balance") or 0.0,
                    item.get("amount_applied") or 0.0,
                    item.get("commission") or 0.0,
                ]
            )
    return rows


def _voucher_table_rows(payload):
    rows = []
    for block in payload.get("voucher_blocks") or ():
        label = block.get("label") or block.get("code") or ""
        for item in block.get("rows") or ():
            rows.append(
                [
                    item.get("code") or "",
                    item.get("name") or "",
                    label,
                    _date_cell(item.get("date")),
                    item.get("number") or "",
                    item.get("check_bank") or "",
                    item.get("check_type") or "",
                    _date_cell(item.get("check_payment_date")),
                    item.get("amount") or 0.0,
                ]
            )
    return rows


def _build_xlsx(payload):
    """Render a Planilla workbook from payload primitives. No ORM access."""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True, **WORKBOOK_OPTIONS})
    try:
        ws = workbook.add_worksheet("Planilla de Cobranza")
        for index, width in enumerate(COLUMN_WIDTHS):
            ws.set_column(index, index, width)
        ws.set_column(KEY_COL, KEY_COL, None, None, {"hidden": True})
        fmt = _formats(workbook)
        _write_membrete(ws, fmt, payload)
        # Clientes SUMIF formulas forward-ref Facturas/Comprobantes rows; the
        # verdict and Datos/Totales are written last so they can reference
        # and cache those totals.
        datos_start = VERDICT_START + _verdict_rows(payload) + 1
        customer_start = datos_start + 11
        next_row, residual_ref = _write_customers(ws, fmt, payload, customer_start)
        next_row, applied_ref, commission_refs = _write_documents(
            ws, fmt, payload, next_row
        )
        next_row, collected_ref, voucher_subtotals = _write_vouchers(
            ws, fmt, payload, next_row
        )
        last_row, recon_refs = _write_recon(
            ws, fmt, payload, next_row, voucher_subtotals
        )
        _write_datos(
            ws,
            fmt,
            payload,
            datos_start,
            applied_ref,
            collected_ref,
            commission_refs,
            residual_ref,
        )
        _write_verdict(ws, workbook, fmt, payload, recon_refs)
        ws.freeze_panes(5, 0)
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 0)
        ws.repeat_rows(0, 3)
        ws.print_area(0, 0, last_row - 1, 10)
        ws.set_margins(0.3, 0.3, 0.4, 0.4)
        _write_table(
            workbook,
            fmt,
            "Documentos",
            _DOCUMENT_TABLE_COLUMNS,
            _document_table_rows(payload),
        )
        _write_table(
            workbook,
            fmt,
            "Comprobantes",
            _VOUCHER_TABLE_COLUMNS,
            _voucher_table_rows(payload),
        )
    finally:
        workbook.close()
    return _align_workbook_xml(output.getvalue())


_TEMPLATE_COLS = "<cols>{}{}</cols>".format(
    "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(COLUMN_WIDTHS, start=1)
    ),
    f'<col min="{KEY_COL + 1}" max="{KEY_COL + 1}" width="0" hidden="1" '
    'customWidth="1"/>',
)


def _align_workbook_xml(content):
    """Match template col widths and fitToWidth so openpyxl reads them exactly.

    xlsxwriter stores a converted character width (32 → 32.71) and omits the
    default fitToWidth=1 attribute. The hidden customer-key column stays hidden.
    Only the Planilla (sheet1) takes the template columns; the flat sheets keep
    their own widths.
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
                if info.filename == "xl/worksheets/sheet1.xml":
                    xml = re.sub(
                        r"<cols>.*?</cols>",
                        _TEMPLATE_COLS,
                        xml,
                        count=1,
                        flags=re.DOTALL,
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
