import unittest
import json
import os
from datetime import datetime, date, time
from backend import create_app
from backend.database import db
from backend.models import HRUser, Employee, Department, Attendance, LeaveRequest, Payroll

class EMSTestCase(unittest.TestCase):
    def setUp(self):
        """Set up in-memory database and test client"""
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        self.app = create_app()
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        db.create_all()
        self.seed_test_data()

    def tearDown(self):
        """Teardown database session"""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def seed_test_data(self):
        """Seed minimum mock HRUser and Department for tests"""
        # 1. HR User
        hr = HRUser(username='HR Admin', email='hr@test.com')
        hr.set_password('HrPass123')
        db.session.add(hr)
        db.session.flush()

        # 2. Department
        eng_dept = Department(department_name='Engineering', budget=500000.00, description='Devs')
        db.session.add(eng_dept)
        db.session.flush()

        # 3. Employee
        emp_record = Employee(
            employee_id='EMP9999',
            full_name='Test User',
            email='emp@test.com',
            department_id=eng_dept.id,
            designation='Developer',
            salary=100000.00,
            joining_date=date(2025, 1, 1),
            status='Active'
        )
        db.session.add(emp_record)
        db.session.commit()

    def get_jwt_token(self, email, password):
        """Helper to fetch valid JWT token for request headers"""
        res = self.client.post('/api/login', json={
            'email': email,
            'password': password
        })
        data = json.loads(res.data)
        return data.get('token')

    # ----------------- Test Cases -----------------

    def test_auth_login_success(self):
        """Verify successful login returns user details and token"""
        res = self.client.post('/api/login', json={
            'email': 'hr@test.com',
            'password': 'HrPass123'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('token', data)
        self.assertEqual(data['user']['email'], 'hr@test.com')

    def test_auth_login_invalid_password(self):
        """Verify login fails with wrong password"""
        res = self.client.post('/api/login', json={
            'email': 'hr@test.com',
            'password': 'WrongPassword'
        })
        self.assertEqual(res.status_code, 401)

    def test_employee_creation_and_jwt_guard(self):
        """Verify JWT protection and employee CRUD creation endpoints"""
        payload = {
            'email': 'new_candidate@test.com',
            'full_name': 'Candidate One',
            'designation': 'QA Engineer',
            'department_id': 1,
            'salary': 70000.00,
            'joining_date': '2026-06-01'
        }

        # 1. POST without auth header should fail with 401
        res = self.client.post('/api/employees', json=payload)
        self.assertEqual(res.status_code, 401)

        # 2. POST with valid auth header should succeed with 201
        hr_token = self.get_jwt_token('hr@test.com', 'HrPass123')
        headers = {'Authorization': f'Bearer {hr_token}'}
        res_with_auth = self.client.post('/api/employees', json=payload, headers=headers)
        self.assertEqual(res_with_auth.status_code, 201)
        data = json.loads(res_with_auth.data)
        self.assertEqual(data['full_name'], 'Candidate One')
        self.assertEqual(data['email'], 'new_candidate@test.com')
        self.assertTrue(data['employee_id'].startswith('EMP'))

    def test_attendance_check_in_and_out(self):
        """Verify HR-initiated check-in, check-out and work hours calculation"""
        hr_token = self.get_jwt_token('hr@test.com', 'HrPass123')
        headers = {'Authorization': f'Bearer {hr_token}'}
        
        emp = Employee.query.filter_by(email='emp@test.com').first()

        # Check-in
        res = self.client.post('/api/attendance/check-in', json={'employee_id': emp.id}, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        expected_status = 'Half Day' if datetime.now().time().hour >= 13 else 'Present'
        self.assertEqual(data['status'], expected_status)
        self.assertIsNotNone(data['check_in'])

        # Double check-in fails
        res2 = self.client.post('/api/attendance/check-in', json={'employee_id': emp.id}, headers=headers)
        self.assertEqual(res2.status_code, 400)

        # Check-out
        res3 = self.client.post('/api/attendance/check-out', json={'employee_id': emp.id}, headers=headers)
        self.assertEqual(res3.status_code, 200)
        data_out = json.loads(res3.data)
        self.assertIsNotNone(data_out['check_out'])
        self.assertGreaterEqual(data_out['working_hours'], 0.0)

    def test_payroll_calculations(self):
        """Verify basic, allowances, PF deductions, net take-home mathematical breakdowns"""
        hr_token = self.get_jwt_token('hr@test.com', 'HrPass123')
        headers = {'Authorization': f'Bearer {hr_token}'}
        
        emp = Employee.query.filter_by(email='emp@test.com').first()
        payload = {
            'employee_id': emp.id,
            'month': 5,
            'year': 2026,
            'bonus': 3000.0,
            'incentives': 2000.0
        }

        res = self.client.post('/api/payroll/calculate', json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        
        # Verify calculation formulas
        # gross = 100000.00
        # basic = gross * 0.6 = 60000.00
        # allowances = gross * 0.4 = 40000.00
        # bonus = 3000 + 2000 = 5000.00
        # deductions = basic * 0.22 = 13200.00
        # Net = basic(60000) + allowances(40000) + bonus(5000) - deductions(13200) = 91800.00
        self.assertEqual(data['basic_salary'], 60000.00)
        self.assertEqual(data['allowances'], 40000.00)
        self.assertEqual(data['deductions'], 13200.00)
        self.assertEqual(data['net_salary'], 91800.00)

if __name__ == '__main__':
    unittest.main()
