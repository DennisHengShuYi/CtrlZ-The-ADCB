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
    Generate a clean, professional invoice PDF matching requested letterhead format.
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
    letterhead_name_style = ParagraphStyle(
        "LetterheadName",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#000000"),
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=2 * mm,
    )
    letterhead_normal = ParagraphStyle(
        "LetterheadNormal",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#000000"),
        alignment=TA_CENTER,
        leading=12,
    )

    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#000000"),
        spaceAfter=6 * mm,
        fontName="Helvetica-Bold",
    )

    bill_to_style = ParagraphStyle(
        "BillToParams",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=2 * mm,
    )
    client_name_style = ParagraphStyle(
        "ClientName",
        parent=styles["Normal"],
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#000000"),
        spaceAfter=2 * mm,
    )
    info_label_style = ParagraphStyle(
        "InfoLabel", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#666666"), alignment=2
    )
    info_value_style = ParagraphStyle(
        "InfoValue", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#000000"), alignment=0
    )


    # ── Header (Letterhead) ──
    if company:
        name = company.get("name", "").upper()
        if name:
            elements.append(Paragraph(name, letterhead_name_style))
        if company.get("business_reg"):
            elements.append(Paragraph(f"Business Reg No: {company['business_reg']}", letterhead_normal))
        if company.get("address"):
            elements.append(Paragraph(company["address"], letterhead_normal))
        elements.append(Spacer(1, 15 * mm))


    # ── Top Section: Title, Bill To & Invoice Info ──
    invoice_info_data = [
        [Paragraph("Date Generated:", info_label_style), Paragraph(invoice.get("date", "N/A"), info_value_style)],
        [Paragraph("Invoice #:", info_label_style), Paragraph(invoice.get("invoice_number", "N/A"), info_value_style)],
        [Paragraph("Status:", info_label_style), Paragraph(invoice.get("status", "unpaid").upper(), info_value_style)],
    ]
    invoice_info_table = Table(invoice_info_data, colWidths=[35*mm, 35*mm])
    invoice_info_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (0,-1), "RIGHT"),
        ("ALIGN", (1,0), (1,-1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))

    left_block = []
    left_block.append(Paragraph("INVOICE", title_style))
    left_block.append(Paragraph("BILL TO:", bill_to_style))
    left_block.append(Paragraph(invoice.get("client_name", "Unknown Client") or "Unknown Client", client_name_style))

    top_table_data = [[left_block, invoice_info_table]]
    top_table = Table(top_table_data, colWidths=[90*mm, 80*mm])
    top_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (0,0), "LEFT"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
    ]))
    
    elements.append(top_table)
    elements.append(Spacer(1, 10 * mm))

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
                f"{price:,.2f}",
                f"{Decimal(str(subtotal)):,.2f}",
            ]
        )

    table = Table(table_data, colWidths=[10 * mm, 80 * mm, 20 * mm, 30 * mm, 30 * mm])
    table.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F9FAFB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#000000")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#000000")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#000000")),
                
                # Body rows
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                
                # Alignment
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                
                # Grid
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#E5E5E5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    # ── Total Box ──
    subtotal = sum(Decimal(str(item.get("price", 0))) * item.get("quantity", 0) for item in items)
    tariff = Decimal(str(invoice.get("tariff", 0)))
    total = Decimal(str(invoice.get("total_amount", 0)))
    currency = invoice.get('currency', 'USD')
    
    total_data = []
    if tariff > 0:
        total_data.append([f"Subtotal ({currency}):", f"{subtotal:,.2f}"])
        total_data.append([f"Tariff / Duty ({currency}):", f"{tariff:,.2f}"])
    
    total_data.append([f"TOTAL ({currency}):", f"{total:,.2f}"])

    total_table = Table(total_data, colWidths=[40*mm, 35*mm])
    total_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#000000")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    
    # Wrap total table to position it on the right
    wrapper_data = [["", total_table]]
    wrapper_table = Table(wrapper_data, colWidths=[115*mm, 55*mm])
    wrapper_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (1, 0), (1, 0), "TOP"),
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#000000")),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
    ]))
    
    elements.append(wrapper_table)
    elements.append(Spacer(1, 15 * mm))

    # ── Footer ──
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#333333"),
        alignment=2, # Right aligned
    )
    elements.append(
        Paragraph("This is a computer-generated invoice. No signature is required.", footer_style)
    )

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_receipt_pdf(
    payment: dict, invoice: dict, company: dict | None = None
) -> bytes:
    """
    Generate a clean, professional payment receipt PDF.
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

    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#000000"),
        spaceAfter=4 * mm,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=2 * mm,
    )
    bold_style = ParagraphStyle(
        "ReceiptBold",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#000000"),
        fontName="Helvetica-Bold",
    )

    elements.append(Paragraph("PAYMENT RECEIPT", title_style))
    elements.append(
        Paragraph(f"Receipt ID: {payment.get('id', 'N/A')[:8].upper()}", subtitle_style)
    )
    elements.append(
        Paragraph(f"Date Paid: {payment.get('date', 'N/A')}", subtitle_style)
    )
    elements.append(
        Paragraph(
            f"Payment Method: {payment.get('method', 'Bank Transfer')}", subtitle_style
        )
    )
    elements.append(Spacer(1, 4 * mm))

    if company:
        elements.append(Paragraph("Issued By:", bold_style))
        elements.append(Paragraph(company.get("name", ""), subtitle_style))
        if company.get("business_reg"):
            elements.append(
                Paragraph(f"Reg: {company['business_reg']}", subtitle_style)
            )
        elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Received From:", bold_style))
    elements.append(
        Paragraph(invoice.get("client_name", "Unknown Client"), subtitle_style)
    )
    elements.append(Spacer(1, 6 * mm))

    # Applied to invoice
    amount = Decimal(str(payment.get("amount", 0)))
    table_data = [
        ["Description", "Invoice #", "Amount Paid"],
        [
            "Payment against Invoice",
            invoice.get("invoice_number", "N/A"),
            f"{invoice.get('currency', 'USD')} {amount:,.2f}",
        ],
    ]

    table = Table(table_data, colWidths=[85 * mm, 45 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000000")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E5E5")),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
    )
    elements.append(
        Paragraph(
            "Thank you for your business. Generated by FinanceFlow.", footer_style
        )
    )

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
