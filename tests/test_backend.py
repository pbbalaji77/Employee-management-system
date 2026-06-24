import unittest
import json
import os
from datetime import datetime, date, time
from backend import create_app
from backend.database import db
from backend.models import Role, User, Employee, Department, Attendance, LeaveRequest, Payroll

class EMSTestCase(unittest.TestCase):
    def setUp(self):
        """Set up in-memory database and test client"""
        # Override database to in-memory sqlite
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
        """Seed minimum mock roles and departments for tests"""
        # 1. Roles
        admin_role = Role(name='Super Admin', description='Admin')
        emp_role = Role(name='Employee', description='Employee')
        db.session.add_all([admin_role, emp_role])
        db.session.flush()

        # 2. Users
        admin_user = User(email='admin@test.com', role_id=admin_role.id)
        admin_user.set_password('AdminPass123')
        emp_user = User(email='emp@test.com', role_id=emp_role.id)
        emp_user.set_password('EmpPass123')
        db.session.add_all([admin_user, emp_user])
        db.session.flush()

        # 3. Department
        eng_dept = Department(department_name='Engineering', budget=500000.00, description='Devs')
        db.session.add(eng_dept)
        db.session.flush()

        # 4. Employee linked to emp_user
        emp_record = Employee(
            user_id=emp_user.id,
            employee_id='EMP9999',
            first_name='Test',
            last_name='User',
            email='emp@test.com',
            department_id=eng_dept.id,
            designation='Developer',
            salary=100000.00, # 100k gross
            joining_date=date(2025, 1, 1),
            employment_type='Full-Time',
            active_status=True
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
            'email': 'admin@test.com',
            'password': 'AdminPass123'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('token', data)
        self.assertEqual(data['user']['email'], 'admin@test.com')

    def test_auth_login_invalid_password(self):
        """Verify login fails with wrong password"""
        res = self.client.post('/api/login', json={
            'email': 'admin@test.com',
            'password': 'WrongPassword'
        })
        self.assertEqual(res.status_code, 401)

    def test_employee_creation_and_jwt_guard(self):
        """Verify JWT protection and employee CRUD creation endpoints"""
        admin_token = self.get_jwt_token('admin@test.com', 'AdminPass123')
        headers = {'Authorization': f'Bearer {admin_token}'}

        payload = {
            'email': 'new_candidate@test.com',
            'first_name': 'Candidate',
            'last_name': 'One',
            'designation': 'QA Engineer',
            'department_id': 1,
            'salary': 70000.00,
            'joining_date': '2026-06-01',
            'employment_type': 'Full-Time'
        }

        # POST without auth header should fail
        res = self.client.post('/api/employees', json=payload)
        self.assertEqual(res.status_code, 401)

        # POST with auth header succeeds
        res = self.client.post('/api/employees', json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data['first_name'], 'Candidate')
        self.assertEqual(data['email'], 'new_candidate@test.com')
        self.assertTrue(data['employee_id'].startswith('EMP'))

    def test_attendance_check_in_and_out(self):
        """Verify check-in, check-out and work hours calculation"""
        emp_token = self.get_jwt_token('emp@test.com', 'EmpPass123')
        headers = {'Authorization': f'Bearer {emp_token}'}

        # Check-in
        res = self.client.post('/api/attendance/check-in', headers=headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        expected_status = 'Half Day' if datetime.now().time().hour >= 13 else 'Present'
        self.assertEqual(data['status'], expected_status)
        self.assertIsNotNone(data['check_in'])

        # Double check-in fails
        res2 = self.client.post('/api/attendance/check-in', headers=headers)
        self.assertEqual(res2.status_code, 400)

        # Check-out
        res3 = self.client.post('/api/attendance/check-out', headers=headers)
        self.assertEqual(res3.status_code, 200)
        data_out = json.loads(res3.data)
        self.assertIsNotNone(data_out['check_out'])
        self.assertGreaterEqual(data_out['working_hours'], 0.0)

    def test_payroll_calculations(self):
        """Verify HRA, PF deductions, tax withholdings and net take-home mathematical breakdowns"""
        admin_token = self.get_jwt_token('admin@test.com', 'AdminPass123')
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        emp = Employee.query.filter_by(email='emp@test.com').first()
        payload = {
            'employee_id': emp.id,
            'month': 5,
            'year': 2026,
            'bonus': 5000.0,
            'incentives': 2000.0
        }

        res = self.client.post('/api/payroll/calculate', json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        
        # Verify calculation formulas
        # gross = 100000.00
        # basic = gross * 0.5 = 50000.00
        # HRA = gross * 0.2 = 20000.00
        # deduction = basic * 0.12 = 6000.00
        # tax = basic * 0.10 = 5000.00
        # Net = basic(50000) + HRA(20000) + bonus(5000) + incentives(2000) - deduct(6000) - tax(5000)
        # Net = 77000 - 11000 = 66000
        self.assertEqual(data['basic_salary'], 50000.00)
        self.assertEqual(data['hra'], 20000.00)
        self.assertEqual(data['deductions'], 6000.00)
        self.assertEqual(data['tax'], 5000.00)
        self.assertEqual(data['net_salary'], 66000.00)

if __name__ == '__main__':
    unittest.main()
