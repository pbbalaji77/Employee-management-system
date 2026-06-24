import io
import csv
import os
from flask import Blueprint, render_template, request, send_file, jsonify, session
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from backend.database import db
from backend.models import Employee, Department, Attendance, LeaveRequest, Payroll
from backend.auth import login_required, role_required, token_required, api_role_required
from datetime import datetime, date

report_bp = Blueprint('report', __name__)

@report_bp.route('/reports')
@login_required
@role_required('Super Admin', 'HR Manager')
def reports_view():
    departments = Department.query.all()
    return render_template('reports.html', departments=departments)

# ----------------- Export REST API -----------------

@report_bp.route('/api/reports/export', methods=['GET'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_export_report():
    report_type = request.args.get('type') # employees, attendance, leaves, payroll, departments
    file_format = request.args.get('format', 'csv').lower() # csv, excel, pdf
    
    # Query parameters
    dept_id = request.args.get('department_id', type=int)
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    # 1. Fetch relevant data
    headers = []
    data_rows = []
    title = f"{report_type.capitalize()} Report"
    
    if report_type == 'employees':
        headers = ['Employee ID', 'Full Name', 'Email', 'Designation', 'Department', 'Employment Type', 'Salary', 'Joining Date', 'Status']
        query = Employee.query
        if dept_id:
            query = query.filter_by(department_id=dept_id)
        records = query.all()
        for r in records:
            data_rows.append([
                r.employee_id, r.full_name, r.email, r.designation,
                r.department.department_name if r.department else 'N/A',
                r.employment_type, f"{float(r.salary):.2f}",
                str(r.joining_date), 'Active' if r.active_status else 'Inactive'
            ])
            
    elif report_type == 'attendance':
        headers = ['Date', 'Employee ID', 'Employee Name', 'Check In', 'Check Out', 'Working Hours', 'Overtime', 'Status']
        query = Attendance.query
        if month and year:
            start = date(year, month, 1)
            end = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
            query = query.filter(Attendance.date >= start, Attendance.date < end)
        records = query.all()
        for r in records:
            emp = Employee.query.get(r.employee_id)
            data_rows.append([
                str(r.date), emp.employee_id if emp else 'N/A', emp.full_name if emp else 'N/A',
                r.check_in.strftime('%H:%M:%S') if r.check_in else 'N/A',
                r.check_out.strftime('%H:%M:%S') if r.check_out else 'N/A',
                f"{float(r.working_hours):.2f}", f"{float(r.overtime_hours):.2f}", r.status
            ])
            
    elif report_type == 'leaves':
        headers = ['Employee ID', 'Employee Name', 'Leave Type', 'Start Date', 'End Date', 'Duration (Days)', 'Reason', 'Status']
        query = LeaveRequest.query
        if month and year:
            start = date(year, month, 1)
            query = query.filter(LeaveRequest.start_date >= start)
        records = query.all()
        for r in records:
            days = (r.end_date - r.start_date).days + 1
            data_rows.append([
                r.employee.employee_id if r.employee else 'N/A',
                r.employee.full_name if r.employee else 'N/A',
                r.leave_type, str(r.start_date), str(r.end_date),
                str(days), r.reason or '', r.status
            ])
            
    elif report_type == 'payroll':
        headers = ['Month/Year', 'Employee ID', 'Employee Name', 'Basic Salary', 'HRA', 'Bonus', 'Incentives', 'Deductions', 'Tax', 'Net Pay']
        query = Payroll.query
        if month:
            query = query.filter_by(month=month)
        if year:
            query = query.filter_by(year=year)
        records = query.all()
        for r in records:
            data_rows.append([
                f"{r.month}/{r.year}", r.employee.employee_id if r.employee else 'N/A',
                r.employee.full_name if r.employee else 'N/A',
                f"{float(r.basic_salary):.2f}", f"{float(r.hra):.2f}", f"{float(r.bonus):.2f}",
                f"{float(r.incentives):.2f}", f"{float(r.deductions):.2f}", f"{float(r.tax):.2f}",
                f"{float(r.net_salary):.2f}"
            ])
            
    elif report_type == 'departments':
        headers = ['Department Name', 'Head of Department', 'Description', 'Budget Allocation (INR)', 'Employee Count']
        records = Department.query.all()
        for r in records:
            head = Employee.query.get(r.department_head_id) if r.department_head_id else None
            data_rows.append([
                r.department_name, head.full_name if head else 'Unassigned',
                r.description or '', f"{float(r.budget):.2f}", str(len(r.employees))
            ])
    else:
        return jsonify({'message': 'Invalid report type'}), 400

    # 2. Output Formatting
    if file_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(data_rows)
        output.seek(0)
        
        mem = io.BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        
        filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.csv"
        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    elif file_format in ['excel', 'xlsx']:
        wb = Workbook()
        ws = wb.active
        ws.title = report_type.capitalize()
        
        ws.append(headers)
        for row in data_rows:
            ws.append(row)
            
        mem = io.BytesIO()
        wb.save(mem)
        mem.seek(0)
        
        filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(
            mem,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    elif file_format == 'pdf':
        mem = io.BytesIO()
        # Custom margins and layout
        doc = SimpleDocTemplate(mem, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
        story = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=15,
            alignment=1
        )
        
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 10))
        
        # Build table. Since table is wide, auto-wrap headers & items
        pdf_data = [headers] + data_rows
        # Set column sizes depending on columns
        col_count = len(headers)
        col_width = (letter[0] - 40) / col_count
        
        table = Table(pdf_data, colWidths=[col_width]*col_count)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(table)
        doc.build(story)
        mem.seek(0)
        
        filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(
            mem,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    else:
        return jsonify({'message': 'Invalid file format requested'}), 400
