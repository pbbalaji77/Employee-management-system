import re
from datetime import datetime, date
from sqlalchemy import func
from backend.database import db
from backend.models import Employee, Department, Attendance, LeaveRequest, PerformanceReview, Payroll

def ai_employee_search(query):
    """
    NLP query parser that maps natural queries to employee records.
    Example queries:
      - "Show software engineers in Engineering department"
      - "List employees earning more than 50000"
      - "Who is reporting to Manager John?"
      - "Show active employees"
    """
    query_lower = query.lower()
    filters = []
    
    # 1. Status check
    if "inactive" in query_lower:
        filters.append(Employee.status == 'Inactive')
    elif "active" in query_lower:
        filters.append(Employee.status == 'Active')

    # 2. Department matching
    departments = Department.query.all()
    matched_dept_id = None
    for dept in departments:
        if dept.department_name.lower() in query_lower:
            matched_dept_id = dept.id
            filters.append(Employee.department_id == dept.id)
            break

    # 3. Salary constraints
    sal_more = re.findall(r"(?:earning|salary|earn|more than|above|>)\s*(\d+)", query_lower)
    sal_less = re.findall(r"(?:less than|below|<)\s*(\d+)", query_lower)
    
    if sal_more:
        filters.append(Employee.salary >= float(sal_more[0]))
    if sal_less:
        filters.append(Employee.salary <= float(sal_less[0]))

    # 4. Designation matching
    designations = ["software engineer", "developer", "manager", "lead", "hr", "analyst", "director", "associate"]
    for desg in designations:
        if desg in query_lower:
            filters.append(Employee.designation.ilike(f"%{desg}%"))
            break

    # 5. Gender check
    if "female" in query_lower or "women" in query_lower:
        filters.append(Employee.gender.ilike("female"))
    elif "male" in query_lower or " men " in query_lower:
        filters.append(Employee.gender.ilike("male"))

    # Execute query
    results = Employee.query.filter(*filters).all()
    
    # Fallback keyword matching
    if not results and len(query.split()) <= 4:
        results = Employee.query.filter(
            db.or_(
                Employee.full_name.ilike(f"%{query}%"),
                Employee.designation.ilike(f"%{query}%")
            )
        ).all()

    return [emp.to_dict() for emp in results]

def ai_dashboard_assistant(question):
    """
    Answers questions related to dashboard statistics and operations.
    """
    q_lower = question.lower().strip()
    
    # Question 1: Who joined this month?
    if "joined this month" in q_lower or "new hires this month" in q_lower or "who joined" in q_lower:
        today = date.today()
        new_hires = Employee.query.filter(
            func.strftime('%Y', Employee.joining_date) == str(today.year),
            func.strftime('%m', Employee.joining_date) == f"{today.month:02d}"
        ).all()
        if not new_hires:
            return "No new employees joined this month."
        names = [f"{e.full_name} ({e.designation})" for e in new_hires]
        return f"The following employees joined this month: {', '.join(names)}."

    # Question 2: Top performers?
    if "top performer" in q_lower or "best performer" in q_lower or "highest rating" in q_lower:
        top_reviews = PerformanceReview.query.filter(PerformanceReview.rating >= 4).all()
        if not top_reviews:
            return "No top performers recorded yet (rating >= 4)."
        unique_emps = {}
        for r in top_reviews:
            unique_emps[r.employee_id] = (r.employee.full_name, r.rating, r.review_period)
        
        lines = [f"{name} (Rating: {rating}/5 for {period})" for _, (name, rating, period) in unique_emps.items()]
        return "Top performers based on recent appraisals: <br>" + "<br>".join(lines)

    # Question 3: Employees absent today?
    if "absent today" in q_lower or "who is absent" in q_lower or "missing attendance" in q_lower:
        today = date.today()
        active_emps = Employee.query.filter(Employee.status == 'Active').all()
        attendance_today = Attendance.query.filter(Attendance.date == today).all()
        checked_in_ids = {a.employee_id for a in attendance_today}
        
        absent_emps = [e for e in active_emps if e.id not in checked_in_ids]
        if not absent_emps:
            return "All active employees have checked in today."
        names = [f"{e.full_name} ({e.designation})" for e in absent_emps]
        return f"Currently absent today ({len(absent_emps)} employees): {', '.join(names)}."

    # Question 4: Total payroll budget?
    if "payroll cost" in q_lower or "salary budget" in q_lower or "spend on salaries" in q_lower:
        total_salary = db.session.query(func.sum(Employee.salary)).scalar() or 0
        return f"The monthly salary cost for all active employees is INR {total_salary:,.2f}."

    # Question 5: Headcount or count of employees
    if "how many employees" in q_lower or "total headcount" in q_lower or "employee count" in q_lower:
        total = Employee.query.count()
        active = Employee.query.filter(Employee.status == 'Active').count()
        return f"There are a total of {total} employees in the system, out of which {active} are active."

    return ("I can help you analyze employee metrics. Try asking: <br>"
            "- 'Who joined this month?'<br>"
            "- 'Who are the top performers?'<br>"
            "- 'Employees absent today?'<br>"
            "- 'What is the monthly payroll cost?'")

def ai_resume_screening(resume_text, target_role="Software Engineer"):
    """
    Screens resume text against key skills, education, and experience.
    """
    resume_lower = resume_text.lower()
    score = 0
    strengths = []
    weaknesses = []
    
    # 1. Skills Matching (Max 40 points)
    tech_skills = {
        'python': 8, 'flask': 8, 'django': 5, 'javascript': 6, 'js': 4,
        'html': 4, 'css': 4, 'react': 7, 'angular': 5, 'vue': 5,
        'sql': 6, 'postgresql': 5, 'sqlite': 4, 'mongodb': 4,
        'docker': 7, 'aws': 6, 'kubernetes': 5, 'git': 4,
        'bootstrap': 4, 'rest api': 6, 'jwt': 6
    }
    
    skills_score = 0
    matched_skills = []
    for skill, points in tech_skills.items():
        if re.search(r'\b' + re.escape(skill) + r'\b', resume_lower):
            skills_score += points
            matched_skills.append(skill.upper())
            
    skills_score = min(skills_score, 40)
    score += skills_score
    if matched_skills:
        strengths.append(f"Technical skills matched: {', '.join(matched_skills)}")
    else:
        weaknesses.append("No common tech stack keywords matched")

    # 2. Education Check (Max 30 points)
    edu_score = 0
    degrees = {
        'phd': 30, 'doctorate': 30,
        'master': 25, 'mtech': 25, 'm.tech': 25, 'mca': 25, 'ms ': 22,
        'bachelor': 20, 'btech': 20, 'b.tech': 20, 'bsc': 18, 'b.sc': 18, 'bca': 18
    }
    for deg, pts in degrees.items():
        if deg in resume_lower:
            edu_score = max(edu_score, pts)
            
    score += edu_score
    if edu_score >= 20:
        strengths.append("Possesses higher education degree")
    else:
        weaknesses.append("Higher education degree not explicitly found")

    # 3. Experience Scoring (Max 30 points)
    exp_patterns = [
        r'(\d+)\s*\+?\s*years?\s+of?\s+experience',
        r'(\d+)\s*\+?\s*yrs?\s+of?\s+experience',
        r'experience\s*:\s*(\d+)\s*\+?\s*years?',
        r'worked\s+for\s+(\d+)\s+years?'
    ]
    
    years_found = 0
    for pattern in exp_patterns:
        matches = re.findall(pattern, resume_lower)
        if matches:
            years_found = max(years_found, int(matches[0]))
            
    if years_found == 0:
        if "senior" in resume_lower or "lead" in resume_lower:
            years_found = 5
        elif "junior" in resume_lower or "intern" in resume_lower:
            years_found = 1
        elif "experience" in resume_lower:
            years_found = 3
            
    exp_score = min(years_found * 6, 30)
    score += exp_score
    
    if years_found > 0:
        strengths.append(f"Has approximately {years_found}+ years of professional experience")
    else:
        weaknesses.append("No professional years of experience could be parsed")

    if score >= 75:
        decision = "Strong Shortlist (Proceed to Interview)"
    elif score >= 50:
        decision = "Review (Pending Manual Screening)"
    else:
        decision = "Reject (Does not meet minimum requirements)"

    return {
        'score': score,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'decision': decision,
        'parsed_experience': f"{years_found} years",
        'matched_skills_count': len(matched_skills)
    }

def ai_employee_insights():
    """
    Calculates attrition risk and gathers statistical insights for active employees.
    """
    employees = Employee.query.filter(Employee.status == 'Active').all()
    insights = []
    
    if not employees:
        return []

    dept_salaries = {}
    for emp in employees:
        if emp.department_id not in dept_salaries:
            dept_salaries[emp.department_id] = []
        if emp.salary:
            dept_salaries[emp.department_id].append(float(emp.salary))
            
    dept_medians = {}
    for d_id, sals in dept_salaries.items():
        if sals:
            sals.sort()
            n = len(sals)
            if n % 2 == 1:
                dept_medians[d_id] = sals[n//2]
            else:
                dept_medians[d_id] = (sals[n//2 - 1] + sals[n//2]) / 2
        else:
            dept_medians[d_id] = 0

    for emp in employees:
        attrition_score = 10
        reasons = []
        
        # 1. Appraisals Check
        reviews = PerformanceReview.query.filter(PerformanceReview.employee_id == emp.id).all()
        avg_rating = 3.0
        if reviews:
            avg_rating = sum(r.rating for r in reviews) / len(reviews)
            
        if avg_rating <= 2.0:
            attrition_score += 30
            reasons.append("Low performance rating (under 2/5) indicates role mismatch")
        elif avg_rating <= 3.0:
            attrition_score += 15
            reasons.append("Average performance rating (2-3/5)")

        # 2. Peer Salaries Check
        median = dept_medians.get(emp.department_id, 0)
        emp_salary = float(emp.salary) if emp.salary else 0
        if emp_salary > 0 and median > 0:
            if emp_salary < (median * 0.85):
                attrition_score += 25
                reasons.append(f"Salary is more than 15% below the department median (INR {emp_salary:,.2f} vs median INR {median:,.2f})")

        # 3. Overtime burnout
        overtime_recs = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.overtime_hours > 0
        ).all()
        total_overtime = sum(float(o.overtime_hours) for o in overtime_recs)
        if total_overtime > 15:
            attrition_score += 20
            reasons.append(f"High cumulative overtime ({total_overtime:.1f} hours) indicates potential burnout")

        # 4. Tenure check
        years_worked = (date.today() - emp.joining_date).days / 365.25 if emp.joining_date else 0
        if years_worked > 3.0:
            attrition_score += 15
            reasons.append(f"Long company tenure ({years_worked:.1f} years) without recent role progression")

        attrition_score = min(attrition_score, 100)
        
        if attrition_score >= 60:
            risk_level = "High"
        elif attrition_score >= 35:
            risk_level = "Medium"
        else:
            risk_level = "Low"
            
        insights.append({
            'employee_id': emp.id,
            'employee_code': emp.employee_id,
            'full_name': emp.full_name,
            'designation': emp.designation,
            'department_name': emp.department.department_name if emp.department else "N/A",
            'attrition_score': attrition_score,
            'risk_level': risk_level,
            'reasons': reasons if reasons else ["Employee shows high alignment and low-risk signals."]
        })

    insights.sort(key=lambda x: x['attrition_score'], reverse=True)
    return insights
