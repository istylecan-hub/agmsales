"""
OrderHub Admin API Tests
Tests for data management and reset control endpoints:
- GET /api/orderhub/admin/data-summary
- POST /api/orderhub/admin/reset-orders (with/without confirm)
- POST /api/orderhub/admin/reset-master (with/without confirm)
- POST /api/orderhub/admin/delete-upload/{file_id} (with/without confirm)
- DELETE /api/orderhub/admin/reset-all (with/without proper confirm)
- POST /api/orderhub/admin/remap-unmapped
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


class TestOrderHubAdminDataSummary:
    """Tests for data summary endpoint"""
    
    def test_data_summary_returns_counts(self):
        """GET /api/orderhub/admin/data-summary - should return counts and file list"""
        response = requests.get(f"{BASE_URL}/api/orderhub/admin/data-summary")
        assert response.status_code == 200
        
        data = response.json()
        # Verify required fields exist
        assert "total_orders" in data
        assert "total_files" in data
        assert "unmapped_skus" in data
        assert "master_skus" in data
        assert "files" in data
        
        # Verify data types
        assert isinstance(data["total_orders"], int)
        assert isinstance(data["total_files"], int)
        assert isinstance(data["master_skus"], int)
        assert isinstance(data["files"], list)
        
        # If files exist, verify file structure
        if data["files"]:
            file = data["files"][0]
            assert "id" in file
            assert "original_filename" in file
            assert "platform" in file


class TestResetOrdersEndpoint:
    """Tests for POST /api/orderhub/admin/reset-orders"""
    
    def test_reset_orders_without_confirm_returns_warning(self):
        """POST /api/orderhub/admin/reset-orders without confirm - should return warning"""
        response = requests.post(f"{BASE_URL}/api/orderhub/admin/reset-orders")
        assert response.status_code == 200
        
        data = response.json()
        # Verify warning response structure
        assert "warning" in data
        assert "action_required" in data
        assert "tables_affected" in data
        assert "tables_NOT_affected" in data
        
        # Verify warning text mentions confirm
        assert "confirm=true" in data["action_required"]
        
        # Verify tables are correctly listed
        assert "orderhub_orders" in data["tables_affected"]
        assert "orderhub_uploads" in data["tables_affected"]
        assert "orderhub_unmapped_skus" in data["tables_affected"]
        
        # Master SKUs should NOT be affected
        assert "orderhub_master_skus" in data["tables_NOT_affected"]
    
    def test_reset_orders_with_confirm_false_returns_warning(self):
        """POST /api/orderhub/admin/reset-orders?confirm=false - should return warning"""
        response = requests.post(f"{BASE_URL}/api/orderhub/admin/reset-orders?confirm=false")
        assert response.status_code == 200
        
        data = response.json()
        assert "warning" in data
        assert "action_required" in data


class TestResetMasterEndpoint:
    """Tests for POST /api/orderhub/admin/reset-master"""
    
    def test_reset_master_without_confirm_returns_warning(self):
        """POST /api/orderhub/admin/reset-master without confirm - should return warning"""
        response = requests.post(f"{BASE_URL}/api/orderhub/admin/reset-master")
        assert response.status_code == 200
        
        data = response.json()
        # Verify warning response structure
        assert "warning" in data
        assert "action_required" in data
        assert "tables_affected" in data
        assert "side_effects" in data
        
        # Verify warning text mentions confirm
        assert "confirm=true" in data["action_required"]
        
        # Verify master SKUs table is in affected list
        assert "orderhub_master_skus" in data["tables_affected"]
        
        # Verify side effects mention UNMAPPED
        assert any("UNMAPPED" in effect for effect in data["side_effects"])


class TestDeleteUploadEndpoint:
    """Tests for POST /api/orderhub/admin/delete-upload/{file_id}"""
    
    def test_delete_upload_nonexistent_file_returns_404(self):
        """POST /api/orderhub/admin/delete-upload/{file_id} - nonexistent returns 404"""
        response = requests.post(f"{BASE_URL}/api/orderhub/admin/delete-upload/nonexistent-file-id")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_delete_upload_without_confirm_returns_warning(self):
        """POST /api/orderhub/admin/delete-upload/{file_id} without confirm - should return warning"""
        # First get list of files to find a valid file_id
        summary_response = requests.get(f"{BASE_URL}/api/orderhub/admin/data-summary")
        summary = summary_response.json()
        
        if not summary["files"]:
            pytest.skip("No uploaded files to test with")
        
        file_id = summary["files"][0]["id"]
        filename = summary["files"][0]["original_filename"]
        
        response = requests.post(f"{BASE_URL}/api/orderhub/admin/delete-upload/{file_id}")
        assert response.status_code == 200
        
        data = response.json()
        # Verify warning response structure
        assert "warning" in data
        assert "action_required" in data
        assert "upload_details" in data
        
        # Verify warning contains filename
        assert filename in data["warning"]
        
        # Verify upload details
        assert data["upload_details"]["file_id"] == file_id
        assert "orders_to_delete" in data["upload_details"]


class TestResetAllEndpoint:
    """Tests for DELETE /api/orderhub/admin/reset-all"""
    
    def test_reset_all_without_proper_confirm_returns_warning(self):
        """DELETE /api/orderhub/admin/reset-all without proper confirm - should return warning"""
        response = requests.delete(f"{BASE_URL}/api/orderhub/admin/reset-all?confirm=wrong_value")
        assert response.status_code == 200
        
        data = response.json()
        # Verify warning response structure
        assert "warning" in data
        assert "action_required" in data
        assert "tables_affected" in data
        
        # Verify it requires CONFIRM_DELETE_ALL
        assert "CONFIRM_DELETE_ALL" in data["action_required"]
        
        # Verify all OrderHub tables listed
        assert "orderhub_orders" in data["tables_affected"]
        assert "orderhub_uploads" in data["tables_affected"]
        assert "orderhub_unmapped_skus" in data["tables_affected"]
        assert "orderhub_master_skus" in data["tables_affected"]
    
    def test_reset_all_with_empty_confirm_returns_error(self):
        """DELETE /api/orderhub/admin/reset-all with no confirm param - should return 422"""
        response = requests.delete(f"{BASE_URL}/api/orderhub/admin/reset-all")
        # confirm is a required query param
        assert response.status_code == 422


class TestRemapUnmappedEndpoint:
    """Tests for POST /api/orderhub/admin/remap-unmapped"""
    
    def test_remap_unmapped_works(self):
        """POST /api/orderhub/admin/remap-unmapped - should work"""
        response = requests.post(f"{BASE_URL}/api/orderhub/admin/remap-unmapped")
        assert response.status_code == 200
        
        data = response.json()
        # Verify response has remap statistics
        assert "total_unmapped" in data or "total_mapped_now" in data or "remaining_unmapped" in data


class TestConfirmMechanismSafety:
    """Tests to verify the confirm=true safety mechanism works correctly"""
    
    def test_all_destructive_endpoints_have_safety(self):
        """Verify all destructive endpoints require confirmation"""
        destructive_endpoints = [
            ("POST", "/api/orderhub/admin/reset-orders", {}),
            ("POST", "/api/orderhub/admin/reset-master", {}),
        ]
        
        for method, endpoint, params in destructive_endpoints:
            if method == "POST":
                response = requests.post(f"{BASE_URL}{endpoint}", params=params)
            elif method == "DELETE":
                response = requests.delete(f"{BASE_URL}{endpoint}", params=params)
            
            assert response.status_code == 200, f"Endpoint {endpoint} returned {response.status_code}"
            data = response.json()
            
            # All should return warning when confirm not set
            assert "warning" in data, f"Endpoint {endpoint} missing warning"
            assert "action_required" in data, f"Endpoint {endpoint} missing action_required"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
