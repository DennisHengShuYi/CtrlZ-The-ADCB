"""
PDF Service — generates professional invoice PDFs using ReportLab.
"""

import io
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


def generate_invoice_pdf(invoice: dict, company: dict | None = None) -> bytes:
    """
    Generate a clean, professional invoice PDF.
    Returns the PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#000000"),
        spaceAfter=4 * mm,
        fontName="Helvetica-Bold",
    )

    subtitle_style = ParagraphStyle(
        "InvoiceSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=2 * mm,
    )

    normal_style = ParagraphStyle(
        "InvoiceNormal",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        leading=14,
    )

    bold_style = ParagraphStyle(
        "InvoiceBold",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#000000"),
        fontName="Helvetica-Bold",
    )

    # ── Header ──
    elements.append(Paragraph("INVOICE", title_style))

    # Invoice info
    elements.append(
        Paragraph(f"Invoice #: {invoice.get('invoice_number', 'N/A')}", subtitle_style)
    )
    elements.append(Paragraph(f"Date: {invoice.get('date', 'N/A')}", subtitle_style))
    elements.append(Paragraph(f"Month: {invoice.get('month', 'N/A')}", subtitle_style))
    elements.append(
        Paragraph(
            f"Status: {invoice.get('status', 'unpaid').upper()}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 4 * mm))

    # ── Company Info ──
    if company:
        elements.append(Paragraph("From:", bold_style))
        elements.append(Paragraph(company.get("name", ""), normal_style))
        if company.get("address"):
            elements.append(Paragraph(company["address"], normal_style))
        if company.get("business_reg"):
            elements.append(Paragraph(f"Reg: {company['business_reg']}", normal_style))
        elements.append(Spacer(1, 4 * mm))

    # ── Client Info ──
    elements.append(Paragraph("Bill To:", bold_style))
    elements.append(
        Paragraph(invoice.get("client_name", "Unknown Client"), normal_style)
    )
    elements.append(Spacer(1, 6 * mm))

    # ── Items Table ──
    items = invoice.get("items", [])
    table_data = [["#", "Description", "Qty", "Price", "Subtotal"]]

    for i, item in enumerate(items, 1):
        price = Decimal(str(item.get("price", 0)))
        qty = item.get("quantity", 0)
        subtotal = item.get("subtotal", float(price * qty))
        table_data.append(
            [
                str(i),
                item.get("description", ""),
                str(qty),
                f"${price:,.2f}",
                f"${Decimal(str(subtotal)):,.2f}",
            ]
        )

    # Total row
    total = Decimal(str(invoice.get("total_amount", 0)))
    table_data.append(["", "", "", "TOTAL", f"${total:,.2f}"])

    table = Table(table_data, colWidths=[15 * mm, 80 * mm, 20 * mm, 30 * mm, 30 * mm])
    table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000000")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                # Body rows
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -2), 9),
                ("BOTTOMPADDING", (0, 1), (-1, -2), 6),
                ("TOPPADDING", (0, 1), (-1, -2), 6),
                # Total row
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 11),
                ("TOPPADDING", (0, -1), (-1, -1), 10),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#000000")),
                # Alignment
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                # Grid
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E5E5E5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    # ── Footer ──
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
    )
    elements.append(
        Paragraph("Generated by FinanceFlow — AI-Powered Invoice System", footer_style)
    )

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
