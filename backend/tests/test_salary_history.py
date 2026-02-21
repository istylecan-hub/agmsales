"""
Salary History API Tests
Tests for Monthly Salary History feature:
- POST /api/salary/save - saves monthly salary data
- GET /api/salary/history - returns list of saved months
- GET /api/salary/history/{year}/{month} - returns salary data for specific month
- PUT /api/salary/history/{year}/{month}/{emp_code} - updates employee salary
- DELETE /api/salary/history/{year}/{month} - deletes a salary record
- GET /api/salary/compare/{year1}/{month1}/{year2}/{month2} - compares two months
- GET /api/salary/employee/{emp_code}/growth - returns employee growth tracking
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestSalaryHistoryHealthCheck:
    """Verify API is running"""
    
    def test_api_health(self, api_client):
        """Test API health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API health check passed")


class TestSalaryHistoryList:
    """Test GET /api/salary/history endpoint"""
    
    def test_get_salary_history_list(self, api_client):
        """Test retrieving list of saved salary records"""
        response = api_client.get(f"{BASE_URL}/api/salary/history")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Verify existing test records exist
        records = data["data"]
        record_ids = [r["record_id"] for r in records]
        
        # Check structure of records
        if len(records) > 0:
            first_record = records[0]
            assert "record_id" in first_record
            assert "month" in first_record
            assert "year" in first_record
            assert "totalPayout" in first_record
            assert "employeeCount" in first_record
            assert "savedAt" in first_record
            print(f"✓ Salary history list retrieved with {len(records)} records")
            print(f"  Records: {record_ids}")


class TestSalaryHistoryDetail:
    """Test GET /api/salary/history/{year}/{month} endpoint"""
    
    def test_get_salary_for_existing_month(self, api_client):
        """Test retrieving salary data for existing month (2026-01)"""
        response = api_client.get(f"{BASE_URL}/api/salary/history/2026/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        
        record = data["data"]
        assert record["record_id"] == "2026-01"
        assert record["month"] == 1
        assert record["year"] == 2026
        assert "employees" in record
        assert isinstance(record["employees"], list)
        assert "totalPayout" in record
        assert record["totalPayout"] == 16500.0
        
        # Verify employee data structure
        if len(record["employees"]) > 0:
            emp = record["employees"][0]
            assert "code" in emp
            assert "name" in emp
            assert "totalSalary" in emp
            assert "presentDays" in emp
            print(f"✓ Salary record for 2026-01 retrieved with {len(record['employees'])} employees")
    
    def test_get_salary_for_dec_2025(self, api_client):
        """Test retrieving salary data for 2025-12"""
        response = api_client.get(f"{BASE_URL}/api/salary/history/2025/12")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["data"]["record_id"] == "2025-12"
        assert data["data"]["totalPayout"] == 14500.0
        print("✓ Salary record for 2025-12 retrieved successfully")
    
    def test_get_salary_for_nonexistent_month(self, api_client):
        """Test retrieving salary data for non-existent month"""
        response = api_client.get(f"{BASE_URL}/api/salary/history/1999/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "message" in data
        assert "No salary record found" in data["message"]
        print("✓ Non-existent month returns proper error message")


class TestSalarySave:
    """Test POST /api/salary/save endpoint"""
    
    def test_save_new_salary_record(self, api_client):
        """Test saving a new salary record"""
        # Use a unique test month that we can safely delete later
        test_month = 6
        test_year = 2024
        
        payload = {
            "month": test_month,
            "year": test_year,
            "daysInMonth": 30,
            "employees": [
                {
                    "code": "TEST_E001",
                    "name": "Test Employee 1",
                    "department": "Testing",
                    "baseSalary": 25000,
                    "presentDays": 25,
                    "absentDays": 5,
                    "sandwichDays": 0,
                    "sundayWorking": 2,
                    "otHours": 10,
                    "shortHours": 2,
                    "netOTHours": 8,
                    "totalPayableDays": 27,
                    "totalSalary": 22500,
                    "perDaySalary": 833.33,
                    "otAmount": 1000,
                    "deductions": 500
                },
                {
                    "code": "TEST_E002",
                    "name": "Test Employee 2",
                    "department": "QA",
                    "baseSalary": 30000,
                    "presentDays": 28,
                    "absentDays": 2,
                    "sandwichDays": 1,
                    "sundayWorking": 0,
                    "otHours": 0,
                    "shortHours": 0,
                    "netOTHours": 0,
                    "totalPayableDays": 27,
                    "totalSalary": 27000,
                    "perDaySalary": 1000,
                    "otAmount": 0,
                    "deductions": 0
                }
            ],
            "totalPayout": 49500,
            "config": {"otRate": 1.5, "sandwichRule": True}
        }
        
        response = api_client.post(f"{BASE_URL}/api/salary/save", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "record_id" in data
        assert data["record_id"] == "2024-06"
        print(f"✓ New salary record saved: {data['record_id']}")
        
        # Verify by fetching back
        verify_response = api_client.get(f"{BASE_URL}/api/salary/history/{test_year}/{test_month}")
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["success"] == True
        assert verify_data["data"]["employeeCount"] == 2
        assert verify_data["data"]["totalPayout"] == 49500
        print("✓ Saved record verified via GET")
    
    def test_upsert_existing_salary_record(self, api_client):
        """Test updating an existing salary record (upsert)"""
        test_month = 6
        test_year = 2024
        
        # Update with different data
        payload = {
            "month": test_month,
            "year": test_year,
            "daysInMonth": 30,
            "employees": [
                {
                    "code": "TEST_E001",
                    "name": "Test Employee 1 Updated",
                    "department": "Testing",
                    "baseSalary": 26000,
                    "presentDays": 26,
                    "absentDays": 4,
                    "sandwichDays": 0,
                    "sundayWorking": 2,
                    "otHours": 12,
                    "shortHours": 0,
                    "netOTHours": 12,
                    "totalPayableDays": 28,
                    "totalSalary": 24000,
                    "perDaySalary": 866.67,
                    "otAmount": 1200,
                    "deductions": 0
                }
            ],
            "totalPayout": 24000,
            "config": {"otRate": 1.5}
        }
        
        response = api_client.post(f"{BASE_URL}/api/salary/save", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "updated" in data["message"].lower() or "saved" in data["message"].lower()
        print("✓ Existing salary record updated (upsert)")
        
        # Verify update
        verify_response = api_client.get(f"{BASE_URL}/api/salary/history/{test_year}/{test_month}")
        verify_data = verify_response.json()
        assert verify_data["data"]["employeeCount"] == 1
        assert verify_data["data"]["totalPayout"] == 24000
        print("✓ Upsert verified - employee count and total updated")


class TestSalaryUpdate:
    """Test PUT /api/salary/history/{year}/{month}/{emp_code} endpoint"""
    
    def test_update_employee_salary_in_record(self, api_client):
        """Test updating a specific employee's salary in saved record"""
        # Use the test record we created
        year = 2024
        month = 6
        emp_code = "TEST_E001"
        
        update_payload = {
            "presentDays": 27,
            "totalSalary": 25000,
            "otHours": 15
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/salary/history/{year}/{month}/{emp_code}",
            json=update_payload
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert emp_code in data["message"]
        print(f"✓ Employee {emp_code} salary updated in {month}/{year}")
        
        # Verify update persisted
        verify_response = api_client.get(f"{BASE_URL}/api/salary/history/{year}/{month}")
        verify_data = verify_response.json()
        employees = verify_data["data"]["employees"]
        
        updated_emp = next((e for e in employees if e["code"] == emp_code), None)
        assert updated_emp is not None
        assert updated_emp["presentDays"] == 27
        assert updated_emp["totalSalary"] == 25000
        assert updated_emp["otHours"] == 15
        print("✓ Employee update verified via GET")
    
    def test_update_nonexistent_employee(self, api_client):
        """Test updating non-existent employee returns error"""
        response = api_client.put(
            f"{BASE_URL}/api/salary/history/2024/6/NONEXISTENT",
            json={"presentDays": 20}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "not found" in data["message"].lower()
        print("✓ Non-existent employee update returns proper error")
    
    def test_update_nonexistent_record(self, api_client):
        """Test updating employee in non-existent record"""
        response = api_client.put(
            f"{BASE_URL}/api/salary/history/1999/1/TEST_E001",
            json={"presentDays": 20}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "not found" in data["message"].lower()
        print("✓ Update on non-existent record returns proper error")


class TestSalaryCompare:
    """Test GET /api/salary/compare/{year1}/{month1}/{year2}/{month2} endpoint"""
    
    def test_compare_two_existing_months(self, api_client):
        """Test comparing two existing salary months (2025-12 vs 2026-01)"""
        response = api_client.get(f"{BASE_URL}/api/salary/compare/2025/12/2026/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        
        comparison = data["data"]
        assert "month1" in comparison
        assert "month2" in comparison
        assert "summary" in comparison
        assert "employees" in comparison
        
        # Verify summary structure
        summary = comparison["summary"]
        assert "totalPayout1" in summary
        assert "totalPayout2" in summary
        assert "difference" in summary
        assert summary["totalPayout1"] == 14500.0
        assert summary["totalPayout2"] == 16500.0
        assert summary["difference"] == 2000.0
        
        # Verify month labels
        assert comparison["month1"]["year"] == 2025
        assert comparison["month1"]["month"] == 12
        assert comparison["month2"]["year"] == 2026
        assert comparison["month2"]["month"] == 1
        
        print(f"✓ Comparison successful: 12/2025 (₹{summary['totalPayout1']}) vs 1/2026 (₹{summary['totalPayout2']})")
        print(f"  Difference: ₹{summary['difference']}")
        
        # Verify employee comparison
        if len(comparison["employees"]) > 0:
            emp = comparison["employees"][0]
            assert "code" in emp
            assert "name" in emp
            assert "salary1" in emp
            assert "salary2" in emp
            assert "difference" in emp
            print(f"  Employees compared: {len(comparison['employees'])}")
    
    def test_compare_with_missing_month(self, api_client):
        """Test comparing when one month is missing"""
        response = api_client.get(f"{BASE_URL}/api/salary/compare/2025/12/1999/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "Missing records" in data["message"]
        print("✓ Compare with missing month returns proper error")
    
    def test_compare_both_months_missing(self, api_client):
        """Test comparing when both months are missing"""
        response = api_client.get(f"{BASE_URL}/api/salary/compare/1998/1/1999/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "Missing records" in data["message"]
        print("✓ Compare with both months missing returns proper error")


class TestEmployeeGrowth:
    """Test GET /api/salary/employee/{emp_code}/growth endpoint"""
    
    def test_get_employee_growth_existing(self, api_client):
        """Test getting growth data for existing employee E001"""
        response = api_client.get(f"{BASE_URL}/api/salary/employee/E001/growth")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        
        growth = data["data"]
        assert growth["employeeCode"] == "E001"
        assert "history" in growth
        assert "totalGrowth" in growth
        assert "avgMonthlyGrowth" in growth
        assert "monthsTracked" in growth
        
        # Verify history structure
        assert isinstance(growth["history"], list)
        if len(growth["history"]) > 0:
            month_entry = growth["history"][0]
            assert "month" in month_entry
            assert "year" in month_entry
            assert "label" in month_entry
            assert "totalSalary" in month_entry
            assert "presentDays" in month_entry
            
        print(f"✓ Growth data for E001 retrieved")
        print(f"  Months tracked: {growth['monthsTracked']}")
        print(f"  Total growth: ₹{growth['totalGrowth']}")
        print(f"  Avg monthly growth: ₹{growth['avgMonthlyGrowth']}")
    
    def test_get_employee_growth_nonexistent(self, api_client):
        """Test getting growth data for non-existent employee"""
        response = api_client.get(f"{BASE_URL}/api/salary/employee/NONEXISTENT/growth")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "No salary history found" in data["message"]
        print("✓ Non-existent employee growth returns proper error")


class TestSalaryDelete:
    """Test DELETE /api/salary/history/{year}/{month} endpoint"""
    
    def test_delete_salary_record(self, api_client):
        """Test deleting a salary record (using test record from save tests)"""
        year = 2024
        month = 6
        
        # Ensure record exists first
        check_response = api_client.get(f"{BASE_URL}/api/salary/history/{year}/{month}")
        if check_response.json().get("success") == False:
            # Create it if it doesn't exist
            payload = {
                "month": month,
                "year": year,
                "daysInMonth": 30,
                "employees": [{"code": "TEST_DEL", "name": "Delete Test", "department": "Test",
                              "baseSalary": 10000, "presentDays": 25, "absentDays": 5,
                              "sandwichDays": 0, "sundayWorking": 0, "otHours": 0, "shortHours": 0,
                              "netOTHours": 0, "totalPayableDays": 25, "totalSalary": 8333,
                              "perDaySalary": 333.33, "otAmount": 0, "deductions": 0}],
                "totalPayout": 8333,
                "config": {}
            }
            api_client.post(f"{BASE_URL}/api/salary/save", json=payload)
        
        # Delete the record
        response = api_client.delete(f"{BASE_URL}/api/salary/history/{year}/{month}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "Deleted" in data["message"]
        print(f"✓ Salary record {month}/{year} deleted")
        
        # Verify deletion
        verify_response = api_client.get(f"{BASE_URL}/api/salary/history/{year}/{month}")
        verify_data = verify_response.json()
        assert verify_data["success"] == False
        print("✓ Deletion verified - record no longer exists")
    
    def test_delete_nonexistent_record(self, api_client):
        """Test deleting non-existent record"""
        response = api_client.delete(f"{BASE_URL}/api/salary/history/1999/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "not found" in data["message"].lower()
        print("✓ Delete non-existent record returns proper error")


class TestCleanup:
    """Cleanup test data after tests"""
    
    def test_cleanup_test_data(self, api_client):
        """Clean up any test records created during testing"""
        # Delete test records if they exist
        test_records = [
            (2024, 6),  # From save tests
        ]
        
        for year, month in test_records:
            response = api_client.delete(f"{BASE_URL}/api/salary/history/{year}/{month}")
            if response.json().get("success"):
                print(f"✓ Cleaned up test record {month}/{year}")
            else:
                print(f"  Test record {month}/{year} already deleted or didn't exist")
        
        print("✓ Cleanup completed")
