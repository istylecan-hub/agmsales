"""
Backend Tests for JWT Authentication and Security Features
- Login flow with JWT token
- Protected endpoints require auth
- Security headers on responses
- CORS configuration check
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123"


class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200 with security headers"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_security_headers_present(self):
        """Test that security headers are present on API responses"""
        response = requests.get(f"{BASE_URL}/api/health")
        headers = response.headers
        
        # Check X-Frame-Options
        assert "X-Frame-Options" in headers, "Missing X-Frame-Options header"
        assert headers["X-Frame-Options"] == "SAMEORIGIN"
        print(f"✓ X-Frame-Options: {headers['X-Frame-Options']}")
        
        # Check X-Content-Type-Options
        assert "X-Content-Type-Options" in headers, "Missing X-Content-Type-Options header"
        assert headers["X-Content-Type-Options"] == "nosniff"
        print(f"✓ X-Content-Type-Options: {headers['X-Content-Type-Options']}")
        
        # Check Referrer-Policy
        assert "Referrer-Policy" in headers, "Missing Referrer-Policy header"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        print(f"✓ Referrer-Policy: {headers['Referrer-Policy']}")
        
        # Check Permissions-Policy
        assert "Permissions-Policy" in headers, "Missing Permissions-Policy header"
        print(f"✓ Permissions-Policy: {headers['Permissions-Policy']}")
        
        # Check Content-Security-Policy
        assert "Content-Security-Policy" in headers, "Missing Content-Security-Policy header"
        print(f"✓ Content-Security-Policy: {headers['Content-Security-Policy'][:50]}...")


class TestAuthentication:
    """JWT Authentication tests"""
    
    def test_login_success(self):
        """Test successful login returns JWT token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "token_type" in data, "Missing token_type in response"
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        print(f"✓ Login successful, token received (length: {len(data['access_token'])})")
        return data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Test login with wrong credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "wrong", "password": "wrong"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_login_missing_fields(self):
        """Test login with missing fields returns error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME}  # Missing password
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Missing fields correctly rejected with 422")
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        token = login_response.json()["access_token"]
        
        # Verify token
        response = requests.get(
            f"{BASE_URL}/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Token verification failed: {response.status_code}"
        data = response.json()
        assert data.get("valid") == True
        assert data.get("username") == TEST_USERNAME
        print(f"✓ Token verification passed: {data}")
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/verify",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid token correctly rejected with 401")
    
    def test_verify_token_missing(self):
        """Test token verification without token"""
        response = requests.get(f"{BASE_URL}/api/auth/verify")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Missing token correctly rejected with 401")


class TestProtectedEndpoints:
    """Test that protected endpoints require authentication"""
    
    @pytest.fixture
    def auth_token(self):
        """Get a valid auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        return response.json()["access_token"]
    
    def test_employees_without_auth(self):
        """Test /api/employees requires auth"""
        response = requests.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/employees correctly requires auth")
    
    def test_employees_with_auth(self, auth_token):
        """Test /api/employees works with auth"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "success" in data
        print(f"✓ /api/employees works with auth: {data.get('message', 'OK')}")
    
    def test_salary_history_without_auth(self):
        """Test /api/salary/history requires auth"""
        response = requests.get(f"{BASE_URL}/api/salary/history")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/salary/history correctly requires auth")
    
    def test_salary_history_with_auth(self, auth_token):
        """Test /api/salary/history works with auth"""
        response = requests.get(
            f"{BASE_URL}/api/salary/history",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "success" in data
        print(f"✓ /api/salary/history works with auth")
    
    def test_advance_list_without_auth(self):
        """Test /api/advance/list requires auth"""
        response = requests.get(f"{BASE_URL}/api/advance/list")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/advance/list correctly requires auth")
    
    def test_advance_list_with_auth(self, auth_token):
        """Test /api/advance/list works with auth"""
        response = requests.get(
            f"{BASE_URL}/api/advance/list",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ /api/advance/list works with auth")


class TestCORSConfiguration:
    """Test CORS is properly configured (not wildcard)"""
    
    def test_cors_not_wildcard(self):
        """Verify CORS is not set to wildcard *"""
        # Read the server.py to check CORS config
        # This is a code review check - we verify the config in server.py
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Read server.py content
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check that allow_origins is NOT "*"
        assert 'allow_origins=["*"]' not in content, "CORS should not be wildcard *"
        assert 'allow_origins=["https://accounts.agmsale.com"' in content, "CORS should be restricted to specific domains"
        print("✓ CORS is properly restricted to specific domains (not wildcard)")


class TestPostHogConfiguration:
    """Test PostHog session recording is disabled"""
    
    def test_posthog_disabled(self):
        """Verify PostHog session recording is disabled in index.html"""
        with open('/app/frontend/public/index.html', 'r') as f:
            content = f.read()
        
        # Check disable_session_recording: true
        assert 'disable_session_recording: true' in content, "PostHog session recording should be disabled"
        print("✓ PostHog disable_session_recording: true is set")
        
        # Check posthog.opt_out_capturing()
        assert 'posthog.opt_out_capturing()' in content, "PostHog opt_out_capturing should be called"
        print("✓ PostHog opt_out_capturing() is called")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
