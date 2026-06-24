import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_payslip_pdf(payroll_record, employee_record, output_dir='static/uploads/payslips'):
    """
    Generate a professional PDF payslip for an employee based on the standard schema.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"payslip_{employee_record.employee_id}_{payroll_record.year}_{payroll_record.month}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'PayslipTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor("#1A365D"),
        alignment=1, # Center
        spaceAfter=15
    )
    section_style = ParagraphStyle(
        'PayslipSection',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'PayslipBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#2D3748")
    )
    bold_style = ParagraphStyle(
        'PayslipBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    # 1. Company Header
    story.append(Paragraph("ENTERPRISE CORP LTD.", title_style))
    story.append(Paragraph("100 Corporate Parkway, Tech District, Bangalore - 560001", ParagraphStyle('Sub', parent=body_style, alignment=1)))
    story.append(Spacer(1, 20))

    # 2. Employee Info Table
    info_data = [
        [
            Paragraph("<b>Employee ID:</b>", body_style), Paragraph(employee_record.employee_id, body_style),
            Paragraph("<b>Month/Year:</b>", body_style), Paragraph(f"{payroll_record.month:02d} / {payroll_record.year}", body_style)
        ],
        [
            Paragraph("<b>Name:</b>", body_style), Paragraph(employee_record.full_name, body_style),
            Paragraph("<b>Designation:</b>", body_style), Paragraph(employee_record.designation or "N/A", body_style)
        ],
        [
            Paragraph("<b>Department:</b>", body_style), Paragraph(employee_record.department.department_name if employee_record.department else "N/A", body_style),
            Paragraph("<b>Joining Date:</b>", body_style), Paragraph(str(employee_record.joining_date) if employee_record.joining_date else "N/A", body_style)
        ],
        [
            Paragraph("<b>Email:</b>", body_style), Paragraph(employee_record.email or "N/A", body_style),
            Paragraph("<b>Bank A/C Details:</b>", body_style), Paragraph("XXXXXXXXX" + employee_record.employee_id[-4:] if len(employee_record.employee_id) >= 4 else "N/A", body_style)
        ]
    ]

    t_info = Table(info_data, colWidths=[100, 170, 100, 170])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 20))

    # 3. Earnings & Deductions Table
    calc_data = [
        [Paragraph("<b>Earnings</b>", bold_style), Paragraph("<b>Amount (INR)</b>", bold_style),
         Paragraph("<b>Deductions</b>", bold_style), Paragraph("<b>Amount (INR)</b>", bold_style)],
        
        [Paragraph("Basic Salary", body_style), Paragraph(f"{payroll_record.basic_salary:.2f}", body_style),
         Paragraph("Standard Deductions", body_style), Paragraph(f"{payroll_record.deductions:.2f}", body_style)],
        
        [Paragraph("Allowances (HRA, LTA, etc.)", body_style), Paragraph(f"{payroll_record.allowances:.2f}", body_style),
         Paragraph("", body_style), Paragraph("", body_style)],
        
        [Paragraph("Bonuses & Incentives", body_style), Paragraph(f"{payroll_record.bonuses:.2f}", body_style),
         Paragraph("", body_style), Paragraph("", body_style)],
        
        # Totals
        [
            Paragraph("<b>Gross Earnings (A)</b>", bold_style),
            Paragraph(f"<b>{(payroll_record.basic_salary + payroll_record.allowances + payroll_record.bonuses):.2f}</b>", bold_style),
            Paragraph("<b>Total Deductions (B)</b>", bold_style),
            Paragraph(f"<b>{payroll_record.deductions:.2f}</b>", bold_style)
        ]
    ]

    t_calc = Table(calc_data, colWidths=[160, 110, 160, 110])
    t_calc.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('BACKGROUND', (0,0), (3,0), colors.HexColor("#EDF2F7")),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor("#EDF2F7")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_calc)
    story.append(Spacer(1, 20))

    # 4. Net Salary Card
    net_data = [
        [
            Paragraph("<b>NET TAKE-HOME SALARY (A - B):</b>", bold_style),
            Paragraph(f"<b>INR {payroll_record.net_salary:.2f}</b>", ParagraphStyle('NetAmt', parent=bold_style, fontSize=12, textColor=colors.HexColor("#2F855A")))
        ]
    ]
    t_net = Table(net_data, colWidths=[250, 290])
    t_net.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#2F855A")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FFF4")),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_net)
    story.append(Spacer(1, 40))

    # 5. Signatures
    sig_data = [
        [Paragraph("_____________________________<br/>Employer Signature", body_style),
         Paragraph("_____________________________<br/>Employee Signature", body_style)]
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_sig)

    doc.build(story)
    return f"uploads/payslips/{filename}"
