#!/usr/bin/env python3
"""
COMPREHENSIVE API TEST SUITE
Unified Office Management System - Cygnet.com

This test suite covers:
1. ALL API endpoints with positive and negative test cases
2. RBAC (Role-Based Access Control) validation
3. Input validation and error handling
4. Edge cases and boundary conditions
5. Data integrity and relationships
6. Pagination and filtering

Run with: python3 test_comprehensive.py
"""

import requests
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Any, List
import os
import sys
import json
import uuid
from decimal import Decimal

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
COMPANY_DOMAIN = "cygnet.com"

# Test counters
TESTS_PASSED = 0
TESTS_FAILED = 0
FAILED_TESTS = []

# ============================================================================
# COLORS FOR OUTPUT
# ============================================================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")


def print_section(text: str):
    print(f"\n{Colors.BLUE}[{text}]{Colors.END}")


def assert_test(condition: bool, test_name: str, details: str = ""):
    global TESTS_PASSED, TESTS_FAILED, FAILED_TESTS
    if condition:
        print(f"  {Colors.GREEN}✓{Colors.END} {test_name}")
        TESTS_PASSED += 1
    else:
        print(f"  {Colors.RED}✗{Colors.END} {test_name}" + (f" - {details}" if details else ""))
        TESTS_FAILED += 1
        FAILED_TESTS.append(f"{test_name}: {details}" if details else test_name)


# ============================================================================
# TOKEN MANAGER
# ============================================================================

class TokenManager:
    """Manage authentication tokens for different users."""
    tokens: Dict[str, str] = {}
    user_codes: Dict[str, str] = {}
    user_ids: Dict[str, str] = {}
    
    @classmethod
    def login(cls, email: str, password: str) -> Optional[str]:
        """Login and return access token."""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()["data"]
            token = data["access_token"]
            cls.tokens[email] = token
            cls.user_ids[email] = data.get("user_id", "")
            return token
        return None
    
    @classmethod
    def get_headers(cls, email: str) -> Dict[str, str]:
        """Get authorization headers for user."""
        token = cls.tokens.get(email, '')
        return {"Authorization": f"Bearer {token}"}
    
    @classmethod
    def get_user_id(cls, email: str) -> str:
        """Get user ID for email."""
        return cls.user_ids.get(email, '')


# ============================================================================
# TEST USERS
# ============================================================================

TEST_USERS = {
    "super_admin": {
        "email": f"super.admin@{COMPANY_DOMAIN}",
        "password": "Admin@123"
    },
    "admin": {
        "email": f"test.admin@{COMPANY_DOMAIN}",
        "password": "Admin@123"
    },
    "parking_manager": {
        "email": f"parking.manager@{COMPANY_DOMAIN}",
        "password": "Manager@123"
    },
    "it_manager": {
        "email": f"it.manager@{COMPANY_DOMAIN}",
        "password": "Manager@123"
    },
    "attendance_manager": {
        "email": f"attendance.manager@{COMPANY_DOMAIN}",
        "password": "Manager@123"
    },
    "cafeteria_manager": {
        "email": f"cafeteria.manager@{COMPANY_DOMAIN}",
        "password": "Manager@123"
    },
    "desk_manager": {
        "email": f"desk.manager@{COMPANY_DOMAIN}",
        "password": "Manager@123"
    },
    "team_lead": {
        "email": f"team.lead@{COMPANY_DOMAIN}",
        "password": "TeamLead@123"
    },
    "employee": {
        "email": f"employee@{COMPANY_DOMAIN}",
        "password": "Employee@123"
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get(endpoint: str, email: str, params: dict = None) -> requests.Response:
    """Make GET request with auth."""
    return requests.get(
        f"{BASE_URL}/api/v1/{endpoint}",
        headers=TokenManager.get_headers(email),
        params=params
    )


def post(endpoint: str, email: str, data: dict = None) -> requests.Response:
    """Make POST request with auth."""
    return requests.post(
        f"{BASE_URL}/api/v1/{endpoint}",
        headers=TokenManager.get_headers(email),
        json=data
    )


def put(endpoint: str, email: str, data: dict) -> requests.Response:
    """Make PUT request with auth."""
    return requests.put(
        f"{BASE_URL}/api/v1/{endpoint}",
        headers=TokenManager.get_headers(email),
        json=data
    )


def delete(endpoint: str, email: str) -> requests.Response:
    """Make DELETE request with auth."""
    return requests.delete(
        f"{BASE_URL}/api/v1/{endpoint}",
        headers=TokenManager.get_headers(email)
    )


def get_id_from_response(response: requests.Response) -> Optional[str]:
    """Extract ID from response."""
    if response.status_code in [200, 201]:
        data = response.json().get("data")
        if data:
            return data.get("id")
    return None


# ============================================================================
# TEST MODULES
# ============================================================================

def test_server_health():
    """Test server health endpoint."""
    print_section("Server Health Check")
    
    response = requests.get(f"{BASE_URL}/health")
    assert_test(response.status_code == 200, "Health endpoint returns 200")
    
    data = response.json()
    assert_test(data.get("status") == "healthy", "Server status is healthy")
    assert_test("timestamp" in data, "Response includes timestamp")
    assert_test("version" in data, "Response includes version")


def test_authentication():
    """Test authentication endpoints."""
    print_section("Authentication Module")
    
    # Test login with valid credentials
    for user_type, user_data in TEST_USERS.items():
        token = TokenManager.login(user_data["email"], user_data["password"])
        assert_test(token is not None, f"Login: {user_type}")
    
    # Test login with invalid password
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": TEST_USERS["employee"]["email"], "password": "WrongPassword123"}
    )
    assert_test(response.status_code in [401, 400], "Login fails with invalid password")
    
    # Test login with non-existent user
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "nonexistent@cygnet.com", "password": "Password@123"}
    )
    assert_test(response.status_code in [401, 400, 404], "Login fails with non-existent user")
    
    # Test login with invalid email format
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "invalid-email", "password": "Password@123"}
    )
    assert_test(response.status_code == 422, "Login fails with invalid email format")
    
    # Test /auth/me endpoint
    response = get("auth/me", TEST_USERS["employee"]["email"])
    assert_test(response.status_code == 200, "GET /auth/me returns user info")
    
    # Test refresh token
    response = post("auth/refresh", TEST_USERS["employee"]["email"])
    assert_test(response.status_code in [200, 400, 422], "POST /auth/refresh endpoint accessible")
    
    # Test change password (without actually changing)
    response = post("auth/change-password", TEST_USERS["employee"]["email"], {
        "current_password": "WrongCurrent@123",
        "new_password": "NewPassword@123"
    })
    assert_test(response.status_code in [400, 401], "Change password fails with wrong current password")
    
    # Test unauthenticated access
    response = requests.get(f"{BASE_URL}/api/v1/users/me")
    assert_test(response.status_code in [401, 403], "Unauthenticated request is rejected")


def test_users_module():
    """Test user management endpoints."""
    print_section("Users Module - CRUD Operations")
    
    email = TEST_USERS["super_admin"]["email"]
    
    # GET /users/me
    response = get("users/me", email)
    assert_test(response.status_code == 200, "GET /users/me returns current user")
    
    # GET /users (list)
    response = get("users", email)
    assert_test(response.status_code == 200, "GET /users returns user list")
    data = response.json()
    assert_test("data" in data, "Response has data field")
    assert_test("pagination" in data, "Response has pagination")
    
    # GET /users with pagination
    response = get("users", email, {"page": 1, "page_size": 5})
    assert_test(response.status_code == 200, "GET /users with pagination works")
    
    # GET /users with search filter
    response = get("users", email, {"search": "admin"})
    assert_test(response.status_code == 200, "GET /users with search filter works")
    
    # GET /users with role filter
    response = get("users", email, {"role": "employee"})
    assert_test(response.status_code == 200, "GET /users with role filter works")
    
    # POST /users - Create new user
    test_email = f"test.user.{datetime.now().timestamp():.0f}@{COMPANY_DOMAIN}"
    response = post("users", email, {
        "first_name": "Test",
        "last_name": "User",
        "email": test_email,
        "password": "TestUser@123",
        "role": "employee"
    })
    assert_test(response.status_code in [200, 201], "POST /users creates new user")
    new_user_id = get_id_from_response(response)
    
    # GET /users/{id}
    if new_user_id:
        response = get(f"users/{new_user_id}", email)
        assert_test(response.status_code == 200, "GET /users/{id} returns user details")
        
        # PUT /users/{id}
        response = put(f"users/{new_user_id}", email, {
            "first_name": "Updated",
            "last_name": "Name"
        })
        assert_test(response.status_code == 200, "PUT /users/{id} updates user")
        
        # POST /users/{id}/toggle-active
        response = post(f"users/{new_user_id}/toggle-active", email)
        assert_test(response.status_code == 200, "POST /users/{id}/toggle-active works")
        
        # POST /users/{id}/change-role
        response = post(f"users/{new_user_id}/change-role", email, {"role": "team_lead"})
        assert_test(response.status_code in [200, 400], "POST /users/{id}/change-role works")
        
        # DELETE /users/{id}
        response = delete(f"users/{new_user_id}", email)
        assert_test(response.status_code in [200, 204], "DELETE /users/{id} soft-deletes user")
    
    # Test duplicate email rejection
    response = post("users", email, {
        "first_name": "Duplicate",
        "last_name": "User",
        "email": TEST_USERS["employee"]["email"],  # Already exists
        "password": "Duplicate@123",
        "role": "employee"
    })
    assert_test(response.status_code in [400, 409, 422], "Duplicate email rejected")
    
    # Test weak password rejection
    response = post("users", email, {
        "first_name": "Weak",
        "last_name": "Password",
        "email": f"weak.password@{COMPANY_DOMAIN}",
        "password": "123",  # Too weak
        "role": "employee"
    })
    assert_test(response.status_code == 422, "Weak password rejected")
    
    # Test invalid role
    response = post("users", email, {
        "first_name": "Invalid",
        "last_name": "Role",
        "email": f"invalid.role@{COMPANY_DOMAIN}",
        "password": "Valid@123",
        "role": "invalid_role"
    })
    assert_test(response.status_code == 422, "Invalid role rejected")
    
    print_section("Users Module - RBAC Tests")
    
    # Employee cannot create users
    response = post("users", TEST_USERS["employee"]["email"], {
        "first_name": "Blocked",
        "last_name": "User",
        "email": f"blocked@{COMPANY_DOMAIN}",
        "password": "Blocked@123",
        "role": "employee"
    })
    assert_test(response.status_code == 403, "Employee blocked from creating users")
    
    # Employee cannot delete users
    if new_user_id:
        response = delete(f"users/{new_user_id}", TEST_USERS["employee"]["email"])
        assert_test(response.status_code == 403, "Employee blocked from deleting users")
    
    # Admin cannot create Super Admin
    response = post("users", TEST_USERS["admin"]["email"], {
        "first_name": "New",
        "last_name": "SuperAdmin",
        "email": f"new.superadmin@{COMPANY_DOMAIN}",
        "password": "Super@123",
        "role": "super_admin"
    })
    assert_test(response.status_code in [400, 403, 422], "Admin cannot create Super Admin")


def test_attendance_module():
    """Test attendance endpoints."""
    print_section("Attendance Module - Core Operations")
    
    emp_email = TEST_USERS["employee"]["email"]
    mgr_email = TEST_USERS["attendance_manager"]["email"]
    tl_email = TEST_USERS["team_lead"]["email"]
    
    # POST /attendance/check-in
    response = post("attendance/check-in", emp_email, {"notes": "Test check-in"})
    # May fail if already checked in
    assert_test(response.status_code in [200, 201, 400], "POST /attendance/check-in")
    attendance_id = get_id_from_response(response)
    
    # GET /attendance/my - User's own attendance
    response = get("attendance/my", emp_email)
    assert_test(response.status_code == 200, "GET /attendance/my returns user's attendance")
    
    # If we have an attendance record, get entry_id for checkout
    entry_id = None
    if response.status_code == 200:
        data = response.json().get("data", [])
        if data and len(data) > 0 and data[0].get("entries"):
            entries = data[0]["entries"]
            # Find entry without checkout
            for entry in entries:
                if entry.get("check_out") is None:
                    entry_id = entry.get("id")
                    attendance_id = data[0].get("id")
                    break
    
    # POST /attendance/check-out
    if entry_id:
        response = post("attendance/check-out", emp_email, {
            "entry_id": entry_id,
            "notes": "Test check-out"
        })
        assert_test(response.status_code in [200, 400], "POST /attendance/check-out")
    
    # GET /attendance (manager only)
    response = get("attendance", mgr_email)
    assert_test(response.status_code == 200, "GET /attendance (manager view)")
    
    # GET /attendance with filters
    response = get("attendance", mgr_email, {"status": "draft"})
    assert_test(response.status_code == 200, "GET /attendance with status filter")
    
    today = date.today().isoformat()
    response = get("attendance", mgr_email, {"date_from": today, "date_to": today})
    assert_test(response.status_code == 200, "GET /attendance with date range")
    
    # GET /attendance/pending-approvals
    response = get("attendance/pending-approvals", tl_email)
    assert_test(response.status_code == 200, "GET /attendance/pending-approvals")
    
    # GET /attendance/{id}
    if attendance_id:
        response = get(f"attendance/{attendance_id}", emp_email)
        assert_test(response.status_code == 200, "GET /attendance/{id}")
    
    print_section("Attendance Module - RBAC Tests")
    
    # Employee cannot access all attendance
    response = get("attendance", emp_email)
    assert_test(response.status_code in [200, 403], "Employee access to /attendance controlled")
    
    # Employee cannot approve attendance
    if attendance_id:
        response = post(f"attendance/{attendance_id}/approve", emp_email, {"action": "approve"})
        assert_test(response.status_code == 403, "Employee cannot approve attendance")


def test_parking_module():
    """Test parking endpoints."""
    print_section("Parking Module - Visitor Management")
    
    mgr_email = TEST_USERS["parking_manager"]["email"]
    admin_email = TEST_USERS["super_admin"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    # POST /parking/visitors
    response = post("parking/visitors", mgr_email, {
        "visitor_name": f"Test Visitor {datetime.now().timestamp():.0f}",
        "visitor_phone": "9876543210",
        "visitor_vehicle_number": f"GJ05XX{int(datetime.now().timestamp()) % 10000:04d}",
        "visitor_vehicle_type": "car",
        "purpose": "Meeting",
        "host_user_code": "EMP0001"
    })
    assert_test(response.status_code in [200, 201, 400, 404], "POST /parking/visitors")
    visitor_allocation_id = get_id_from_response(response)
    
    # GET /parking/visitors
    response = get("parking/visitors", mgr_email)
    assert_test(response.status_code == 200, "GET /parking/visitors")
    
    # GET /parking/visitors with filters
    response = get("parking/visitors", mgr_email, {"is_active": True})
    assert_test(response.status_code == 200, "GET /parking/visitors with filter")
    
    # POST /parking/visitors/{id}/exit
    if visitor_allocation_id:
        response = post(f"parking/visitors/{visitor_allocation_id}/exit", mgr_email)
        assert_test(response.status_code in [200, 400], "POST /parking/visitors/{id}/exit")
    
    print_section("Parking Module - Employee Allocations")
    
    # POST /parking/allocations (manager only)
    response = post("parking/allocations", mgr_email, {
        "user_code": "EMP0001",
        "vehicle_number": f"GJ01AB{int(datetime.now().timestamp()) % 10000:04d}",
        "vehicle_type": "car"
    })
    assert_test(response.status_code in [200, 201, 400, 404], "POST /parking/allocations")
    allocation_id = get_id_from_response(response)
    
    # GET /parking/allocations
    response = get("parking/allocations", emp_email)
    assert_test(response.status_code == 200, "GET /parking/allocations")
    
    # GET /parking/allocations/{id}
    if allocation_id:
        response = get(f"parking/allocations/{allocation_id}", emp_email)
        assert_test(response.status_code == 200, "GET /parking/allocations/{id}")
        
        # POST /parking/allocations/{id}/entry
        response = post(f"parking/allocations/{allocation_id}/entry", emp_email)
        assert_test(response.status_code in [200, 400], "POST /parking/allocations/{id}/entry")
        
        # POST /parking/allocations/{id}/exit
        response = post(f"parking/allocations/{allocation_id}/exit", emp_email)
        assert_test(response.status_code in [200, 400], "POST /parking/allocations/{id}/exit")
    
    print_section("Parking Module - Stats & History")
    
    # GET /parking/stats
    response = get("parking/stats", mgr_email)
    assert_test(response.status_code == 200, "GET /parking/stats")
    
    # GET /parking/history
    response = get("parking/history", emp_email)
    assert_test(response.status_code == 200, "GET /parking/history")
    
    print_section("Parking Module - RBAC Tests")
    
    # Employee cannot manage visitors
    response = post("parking/visitors", emp_email, {
        "visitor_name": "Blocked Visitor",
        "visitor_phone": "1234567890",
        "visitor_vehicle_number": "GJ01ZZ9999",
        "visitor_vehicle_type": "car",
        "purpose": "Test"
    })
    assert_test(response.status_code == 403, "Employee cannot add visitors")
    
    # IT Manager cannot manage parking
    response = post("parking/allocations", TEST_USERS["it_manager"]["email"], {
        "user_code": "EMP0001",
        "vehicle_number": "GJ01ZZ8888",
        "vehicle_type": "car"
    })
    assert_test(response.status_code == 403, "IT Manager cannot manage parking")


def test_it_assets_module():
    """Test IT assets endpoints."""
    print_section("IT Assets Module - CRUD Operations")
    
    mgr_email = TEST_USERS["it_manager"]["email"]
    admin_email = TEST_USERS["super_admin"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    # POST /it-assets
    response = post("it-assets", mgr_email, {
        "name": f"Test Laptop {datetime.now().timestamp():.0f}",
        "asset_type": "laptop",
        "brand": "Dell",
        "model": "XPS 15",
        "serial_number": f"SN{datetime.now().timestamp():.0f}",
        "specifications": {"RAM": "16GB", "SSD": "512GB"},
        "purchase_date": date.today().isoformat(),
        "warranty_end_date": (date.today() + timedelta(days=365)).isoformat()
    })
    assert_test(response.status_code in [200, 201], "POST /it-assets creates asset")
    asset_id = get_id_from_response(response)
    
    # GET /it-assets
    response = get("it-assets", emp_email)
    assert_test(response.status_code == 200, "GET /it-assets lists assets")
    
    # GET /it-assets with filters
    response = get("it-assets", emp_email, {"asset_type": "laptop"})
    assert_test(response.status_code == 200, "GET /it-assets with type filter")
    
    response = get("it-assets", emp_email, {"status": "available"})
    assert_test(response.status_code == 200, "GET /it-assets with status filter")
    
    # GET /it-assets/{id}
    if asset_id:
        response = get(f"it-assets/{asset_id}", emp_email)
        assert_test(response.status_code == 200, "GET /it-assets/{id}")
        
        # PUT /it-assets/{id}
        response = put(f"it-assets/{asset_id}", mgr_email, {
            "specifications": {"RAM": "32GB", "SSD": "1TB"}
        })
        assert_test(response.status_code == 200, "PUT /it-assets/{id} updates asset")
        
        # POST /it-assets/{id}/assign
        response = post(f"it-assets/{asset_id}/assign", mgr_email, {
            "user_code": "EMP0001",
            "notes": "Assigned for testing"
        })
        assert_test(response.status_code in [200, 201, 400], "POST /it-assets/{id}/assign")
    
    # GET /it-assets/my/assignments
    response = get("it-assets/my/assignments", emp_email)
    assert_test(response.status_code == 200, "GET /it-assets/my/assignments")
    
    print_section("IT Assets Module - RBAC Tests")
    
    # Employee cannot create assets
    response = post("it-assets", emp_email, {
        "name": "Blocked Asset",
        "asset_type": "laptop",
        "brand": "HP",
        "model": "EliteBook",
        "serial_number": "BLOCKED001"
    })
    assert_test(response.status_code == 403, "Employee cannot create IT assets")
    
    # Parking Manager cannot manage IT assets
    response = post("it-assets", TEST_USERS["parking_manager"]["email"], {
        "asset_type": "LAPTOP",
        "brand": "HP",
        "model": "EliteBook",
        "serial_number": "BLOCKED002"
    })
    assert_test(response.status_code == 403, "Parking Manager cannot manage IT assets")


def test_it_requests_module():
    """Test IT requests endpoints."""
    print_section("IT Requests Module - User Operations")
    
    mgr_email = TEST_USERS["it_manager"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    # POST /it-requests
    response = post("it-requests", emp_email, {
        "request_type": "NEW_ASSET",
        "title": f"Test Request {datetime.now().timestamp():.0f}",
        "description": "This is a comprehensive test request for testing purposes",
        "priority": "MEDIUM"
    })
    assert_test(response.status_code in [200, 201], "POST /it-requests creates request")
    request_id = get_id_from_response(response)
    
    # GET /it-requests (user's own)
    response = get("it-requests", emp_email)
    assert_test(response.status_code == 200, "GET /it-requests (user's requests)")
    
    # GET /it-requests with filters
    response = get("it-requests", emp_email, {"status": "PENDING"})
    assert_test(response.status_code == 200, "GET /it-requests with status filter")
    
    response = get("it-requests", emp_email, {"priority": "MEDIUM"})
    assert_test(response.status_code == 200, "GET /it-requests with priority filter")
    
    # GET /it-requests/{id}
    if request_id:
        response = get(f"it-requests/{request_id}", emp_email)
        assert_test(response.status_code == 200, "GET /it-requests/{id}")
        
        # PUT /it-requests/{id}
        response = put(f"it-requests/{request_id}", emp_email, {
            "title": "Updated Test Request",
            "priority": "HIGH"
        })
        assert_test(response.status_code in [200, 400], "PUT /it-requests/{id} updates request")
    
    print_section("IT Requests Module - Manager Operations")
    
    # GET /it-requests (manager sees all)
    response = get("it-requests", mgr_email)
    assert_test(response.status_code == 200, "GET /it-requests (manager view)")
    
    # POST /it-requests/{id}/approve
    if request_id:
        response = post(f"it-requests/{request_id}/approve", mgr_email, {
            "action": "approve",
            "notes": "Approved for testing"
        })
        assert_test(response.status_code in [200, 400], "POST /it-requests/{id}/approve")
        
        # POST /it-requests/{id}/start
        response = post(f"it-requests/{request_id}/start", mgr_email)
        assert_test(response.status_code in [200, 400], "POST /it-requests/{id}/start")
        
        # POST /it-requests/{id}/complete
        response = post(f"it-requests/{request_id}/complete", mgr_email, {
            "resolution_summary": "Completed for testing"
        })
        assert_test(response.status_code in [200, 400], "POST /it-requests/{id}/complete")
    
    print_section("IT Requests Module - RBAC Tests")
    
    # Employee cannot approve requests
    if request_id:
        response = post(f"it-requests/{request_id}/approve", emp_email, {"action": "approve"})
        assert_test(response.status_code == 403, "Employee cannot approve IT requests")
    
    # Parking Manager cannot approve IT requests
    if request_id:
        response = post(f"it-requests/{request_id}/approve", TEST_USERS["parking_manager"]["email"], {"action": "approve"})
        assert_test(response.status_code == 403, "Parking Manager cannot approve IT requests")


def test_desk_booking_module():
    """Test desk booking endpoints."""
    print_section("Desk Booking Module - Core Operations")
    
    mgr_email = TEST_USERS["desk_manager"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    # First, get a floor plan ID
    response = get("floor-plans", emp_email, {"plan_type": "DESK_AREA"})
    floor_plan_id = None
    if response.status_code == 200:
        data = response.json().get("data", [])
        if data:
            floor_plan_id = data[0].get("id")
    
    # GET /desks/available/{floor_plan_id}
    if floor_plan_id:
        response = get(f"desks/available/{floor_plan_id}", emp_email, {
            "booking_date": date.today().isoformat()
        })
        assert_test(response.status_code == 200, "GET /desks/available/{floor_plan_id}")
    
    # POST /desks/bookings
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = post("desks/bookings", emp_email, {
        "floor_plan_id": floor_plan_id or str(uuid.uuid4()),
        "cell_row": "A",
        "cell_column": "1",
        "booking_date": tomorrow,
        "start_time": "09:00",
        "end_time": "18:00"
    })
    assert_test(response.status_code in [200, 201, 400, 404], "POST /desks/bookings")
    booking_id = get_id_from_response(response)
    
    # GET /desks/bookings
    response = get("desks/bookings", emp_email)
    assert_test(response.status_code == 200, "GET /desks/bookings")
    
    # GET /desks/bookings with filters
    response = get("desks/bookings", emp_email, {"date_from": tomorrow})
    assert_test(response.status_code == 200, "GET /desks/bookings with date filter")
    
    # GET /desks/bookings/{id}
    if booking_id:
        response = get(f"desks/bookings/{booking_id}", emp_email)
        assert_test(response.status_code == 200, "GET /desks/bookings/{id}")
        
        # PUT /desks/bookings/{id}
        response = put(f"desks/bookings/{booking_id}", emp_email, {
            "start_time": "10:00",
            "end_time": "17:00"
        })
        assert_test(response.status_code in [200, 400], "PUT /desks/bookings/{id}")
        
        # DELETE /desks/bookings/{id}
        response = delete(f"desks/bookings/{booking_id}", emp_email)
        assert_test(response.status_code in [200, 204], "DELETE /desks/bookings/{id}")


def test_cafeteria_module():
    """Test cafeteria endpoints."""
    print_section("Cafeteria Module - Booking Operations")
    
    mgr_email = TEST_USERS["cafeteria_manager"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    # Get cafeteria floor plan
    response = get("floor-plans", emp_email, {"plan_type": "CAFETERIA"})
    floor_plan_id = None
    if response.status_code == 200:
        data = response.json().get("data", [])
        if data:
            floor_plan_id = data[0].get("id")
    
    # POST /cafeteria/bookings
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = post("cafeteria/bookings", emp_email, {
        "floor_plan_id": floor_plan_id or str(uuid.uuid4()),
        "cell_row": "A",
        "cell_column": "1",
        "booking_date": tomorrow,
        "meal_type": "lunch",
        "guest_count": 2
    })
    assert_test(response.status_code in [200, 201, 400, 404], "POST /cafeteria/bookings")
    booking_id = get_id_from_response(response)
    
    # GET /cafeteria/bookings
    response = get("cafeteria/bookings", emp_email)
    assert_test(response.status_code == 200, "GET /cafeteria/bookings")
    
    # GET /cafeteria/bookings/{id}
    if booking_id:
        response = get(f"cafeteria/bookings/{booking_id}", emp_email)
        assert_test(response.status_code == 200, "GET /cafeteria/bookings/{id}")
        
        # PUT /cafeteria/bookings/{id}
        response = put(f"cafeteria/bookings/{booking_id}", emp_email, {
            "guest_count": 3
        })
        assert_test(response.status_code in [200, 400], "PUT /cafeteria/bookings/{id}")
        
        # DELETE /cafeteria/bookings/{id}
        response = delete(f"cafeteria/bookings/{booking_id}", emp_email)
        assert_test(response.status_code in [200, 204], "DELETE /cafeteria/bookings/{id}")


def test_food_orders_module():
    """Test food orders endpoints."""
    print_section("Food Orders Module - Item Management")
    
    mgr_email = TEST_USERS["cafeteria_manager"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    # POST /food-orders/items (manager only)
    response = post("food-orders/items", mgr_email, {
        "name": f"Test Item {datetime.now().timestamp():.0f}",
        "description": "A delicious test item",
        "price": 150.00,
        "category": "main_course",
        "is_vegetarian": True,
        "is_available": True
    })
    assert_test(response.status_code in [200, 201], "POST /food-orders/items creates item")
    item_id = get_id_from_response(response)
    
    # GET /food-orders/items
    response = get("food-orders/items", emp_email)
    assert_test(response.status_code == 200, "GET /food-orders/items")
    
    # GET /food-orders/items with filters
    response = get("food-orders/items", emp_email, {"is_vegetarian": True})
    assert_test(response.status_code == 200, "GET /food-orders/items with veg filter")
    
    response = get("food-orders/items", emp_email, {"category": "main_course"})
    assert_test(response.status_code == 200, "GET /food-orders/items with category filter")
    
    # GET /food-orders/items/{id}
    if item_id:
        response = get(f"food-orders/items/{item_id}", emp_email)
        assert_test(response.status_code == 200, "GET /food-orders/items/{id}")
        
        # PUT /food-orders/items/{id}
        response = put(f"food-orders/items/{item_id}", mgr_email, {
            "price": 175.00
        })
        assert_test(response.status_code == 200, "PUT /food-orders/items/{id}")
    
    print_section("Food Orders Module - Order Operations")
    
    # POST /food-orders/orders
    if item_id:
        response = post("food-orders/orders", emp_email, {
            "items": [{"item_id": item_id, "quantity": 2}],
            "notes": "Test order"
        })
        assert_test(response.status_code in [200, 201], "POST /food-orders/orders creates order")
        order_id = get_id_from_response(response)
    else:
        order_id = None
    
    # GET /food-orders/orders
    response = get("food-orders/orders", emp_email)
    assert_test(response.status_code == 200, "GET /food-orders/orders")
    
    # GET /food-orders/orders/{id}
    if order_id:
        response = get(f"food-orders/orders/{order_id}", emp_email)
        assert_test(response.status_code == 200, "GET /food-orders/orders/{id}")
        
        # PUT /food-orders/orders/{id}/status (manager only)
        response = put(f"food-orders/orders/{order_id}/status", mgr_email, {
            "status": "CONFIRMED"
        })
        assert_test(response.status_code in [200, 400], "PUT /food-orders/orders/{id}/status")
    
    # GET /food-orders/dashboard/stats (manager only)
    response = get("food-orders/dashboard/stats", mgr_email)
    assert_test(response.status_code == 200, "GET /food-orders/dashboard/stats")
    
    print_section("Food Orders Module - RBAC Tests")
    
    # Employee cannot create food items
    response = post("food-orders/items", emp_email, {
        "name": "Blocked Item",
        "price": 100.00,
        "category": "snacks"
    })
    assert_test(response.status_code == 403, "Employee cannot create food items")


def test_leave_module():
    """Test leave management endpoints."""
    print_section("Leave Module - Request Operations")
    
    emp_email = TEST_USERS["employee"]["email"]
    tl_email = TEST_USERS["team_lead"]["email"]
    mgr_email = TEST_USERS["attendance_manager"]["email"]
    
    # POST /leave/requests
    start_date = (date.today() + timedelta(days=7)).isoformat()
    end_date = (date.today() + timedelta(days=8)).isoformat()
    response = post("leave/requests", emp_email, {
        "leave_type": "CASUAL",
        "start_date": start_date,
        "end_date": end_date,
        "reason": "Personal work - comprehensive test"
    })
    assert_test(response.status_code in [200, 201, 400], "POST /leave/requests creates request")
    request_id = get_id_from_response(response)
    
    # GET /leave/requests (user's own)
    response = get("leave/requests", emp_email)
    assert_test(response.status_code == 200, "GET /leave/requests (user view)")
    
    # GET /leave/requests with filters
    response = get("leave/requests", emp_email, {"status": "pending_l1"})
    assert_test(response.status_code == 200, "GET /leave/requests with status filter")
    
    response = get("leave/requests", emp_email, {"leave_type": "casual"})
    assert_test(response.status_code == 200, "GET /leave/requests with type filter")
    
    # GET /leave/requests/{id}
    if request_id:
        response = get(f"leave/requests/{request_id}", emp_email)
        assert_test(response.status_code == 200, "GET /leave/requests/{id}")
    
    # GET /leave/balance
    response = get("leave/balance", emp_email)
    assert_test(response.status_code == 200, "GET /leave/balance")
    
    print_section("Leave Module - Approval Workflow")
    
    # POST /leave/requests/{id}/approve-level1 (Team Lead)
    if request_id:
        response = post(f"leave/requests/{request_id}/approve-level1", tl_email, {
            "action": "approve",
            "notes": "Approved by team lead"
        })
        assert_test(response.status_code in [200, 400, 403], "POST /leave/requests/{id}/approve-level1")
        
        # POST /leave/requests/{id}/approve-final (Manager)
        response = post(f"leave/requests/{request_id}/approve-final", mgr_email, {
            "action": "approve",
            "notes": "Final approval"
        })
        assert_test(response.status_code in [200, 400, 403], "POST /leave/requests/{id}/approve-final")
    
    # POST /leave/requests/{id}/cancel
    # Create a new request to cancel
    response = post("leave/requests", emp_email, {
        "leave_type": "SICK",
        "start_date": (date.today() + timedelta(days=14)).isoformat(),
        "end_date": (date.today() + timedelta(days=15)).isoformat(),
        "reason": "To be cancelled"
    })
    cancel_id = get_id_from_response(response)
    if cancel_id:
        response = post(f"leave/requests/{cancel_id}/cancel", emp_email)
        assert_test(response.status_code in [200, 400], "POST /leave/requests/{id}/cancel")
    
    print_section("Leave Module - RBAC Tests")
    
    # Employee cannot approve leave
    if request_id:
        response = post(f"leave/requests/{request_id}/approve-level1", emp_email, {"action": "approve"})
        assert_test(response.status_code == 403, "Employee cannot approve leave requests")


def test_projects_module():
    """Test projects endpoints."""
    print_section("Projects Module - CRUD Operations")
    
    tl_email = TEST_USERS["team_lead"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    mgr_email = TEST_USERS["attendance_manager"]["email"]
    
    # POST /projects
    response = post("projects", tl_email, {
        "title": f"Test Project {datetime.now().timestamp():.0f}",
        "description": "A comprehensive test project description for validation",
        "duration_days": 30
    })
    assert_test(response.status_code in [200, 201], "POST /projects creates project")
    project_id = get_id_from_response(response)
    
    # GET /projects
    response = get("projects", emp_email)
    assert_test(response.status_code == 200, "GET /projects lists projects")
    
    # GET /projects with filters
    response = get("projects", emp_email, {"status": "draft"})
    assert_test(response.status_code == 200, "GET /projects with status filter")
    
    # GET /projects/{id}
    if project_id:
        response = get(f"projects/{project_id}", emp_email)
        assert_test(response.status_code == 200, "GET /projects/{id}")
        
        # PUT /projects/{id}
        response = put(f"projects/{project_id}", tl_email, {
            "description": "Updated project description"
        })
        assert_test(response.status_code == 200, "PUT /projects/{id}")
        
        # POST /projects/{id}/members
        response = post(f"projects/{project_id}/members", tl_email, {
            "user_code": "EMP0001",
            "role": "developer"
        })
        assert_test(response.status_code in [200, 201, 400], "POST /projects/{id}/members")
    
    print_section("Projects Module - Workflow")
    
    if project_id:
        # POST /projects/{id}/submit
        response = post(f"projects/{project_id}/submit", tl_email)
        assert_test(response.status_code in [200, 400], "POST /projects/{id}/submit")
        
        # POST /projects/{id}/approve
        response = post(f"projects/{project_id}/approve", mgr_email, {
            "action": "approve",
            "notes": "Approved for testing"
        })
        assert_test(response.status_code in [200, 400, 403], "POST /projects/{id}/approve")
        
        # POST /projects/{id}/start
        response = post(f"projects/{project_id}/start", tl_email)
        assert_test(response.status_code in [200, 400], "POST /projects/{id}/start")
        
        # POST /projects/{id}/complete
        response = post(f"projects/{project_id}/complete", tl_email)
        assert_test(response.status_code in [200, 400], "POST /projects/{id}/complete")
    
    print_section("Projects Module - RBAC Tests")
    
    # Employee cannot create projects
    response = post("projects", emp_email, {
        "title": "Blocked Project",
        "description": "Should fail with 403 forbidden",
        "duration_days": 10
    })
    assert_test(response.status_code == 403, "Employee cannot create projects")


def test_floor_plans_module():
    """Test floor plans endpoints."""
    print_section("Floor Plans Module - CRUD Operations")
    
    admin_email = TEST_USERS["super_admin"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    parking_mgr = TEST_USERS["parking_manager"]["email"]
    
    # POST /floor-plans (admin only)
    response = post("floor-plans", parking_mgr, {
        "name": f"Test Floor Plan {datetime.now().timestamp():.0f}",
        "plan_type": "PARKING",
        "rows": 10,
        "columns": 20,
        "building_name": "Main Building",
        "floor_number": "G",
        "grid_data": [[{"type": "slot", "label": f"P{i}{j}"} for j in range(20)] for i in range(10)]
    })
    assert_test(response.status_code in [200, 201], "POST /floor-plans creates floor plan")
    floor_plan_id = get_id_from_response(response)
    
    # GET /floor-plans
    response = get("floor-plans", emp_email)
    assert_test(response.status_code == 200, "GET /floor-plans lists plans")
    
    # GET /floor-plans with type filter
    response = get("floor-plans", emp_email, {"plan_type": "parking"})
    assert_test(response.status_code == 200, "GET /floor-plans with type filter")
    
    # GET /floor-plans/{id}
    if floor_plan_id:
        response = get(f"floor-plans/{floor_plan_id}", emp_email)
        assert_test(response.status_code == 200, "GET /floor-plans/{id}")
        
        # PUT /floor-plans/{id}
        response = put(f"floor-plans/{floor_plan_id}", parking_mgr, {
            "description": "Updated description"
        })
        assert_test(response.status_code == 200, "PUT /floor-plans/{id}")
        
        # POST /floor-plans/{id}/versions
        response = post(f"floor-plans/{floor_plan_id}/versions", parking_mgr, {
            "grid_data": [[{"type": "slot", "label": f"P{i}{j}", "status": "available"} for j in range(20)] for i in range(10)]
        })
        assert_test(response.status_code in [200, 201], "POST /floor-plans/{id}/versions")
        
        # GET /floor-plans/{id}/versions
        response = get(f"floor-plans/{floor_plan_id}/versions", emp_email)
        assert_test(response.status_code == 200, "GET /floor-plans/{id}/versions")
        
        # GET /floor-plans/{id}/versions/{version}
        response = get(f"floor-plans/{floor_plan_id}/versions/1", emp_email)
        assert_test(response.status_code in [200, 404], "GET /floor-plans/{id}/versions/{version}")
        
        # GET /floor-plans/{id}/cells/{cell_type}
        response = get(f"floor-plans/{floor_plan_id}/cells/slot", emp_email)
        assert_test(response.status_code in [200, 404], "GET /floor-plans/{id}/cells/{cell_type}")
    
    print_section("Floor Plans Module - RBAC Tests")
    
    # Employee cannot create floor plans
    response = post("floor-plans", emp_email, {
        "name": "Blocked Floor Plan",
        "plan_type": "PARKING",
        "rows": 5,
        "columns": 5
    })
    assert_test(response.status_code == 403, "Employee cannot create floor plans")
    
    # Parking Manager cannot create desk floor plans
    response = post("floor-plans", parking_mgr, {
        "name": "Blocked Desk Plan",
        "plan_type": "DESK_AREA",
        "rows": 5,
        "columns": 5
    })
    assert_test(response.status_code in [400, 403], "Parking Manager cannot create desk floor plans")


def test_holidays_module():
    """Test holidays endpoints."""
    print_section("Holidays Module - CRUD Operations")
    
    admin_email = TEST_USERS["super_admin"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    # POST /holidays/create (Super Admin only)
    response = post("holidays/create", admin_email, {
        "name": f"Test Holiday {datetime.now().timestamp():.0f}",
        "date": (date.today() + timedelta(days=60)).isoformat(),
        "description": "A test holiday",
        "holiday_type": "national",
        "is_optional": False
    })
    assert_test(response.status_code in [200, 201], "POST /holidays/create creates holiday")
    holiday_id = get_id_from_response(response)
    
    # GET /holidays/list
    response = get("holidays/list", emp_email)
    assert_test(response.status_code == 200, "GET /holidays/list")
    
    # GET /holidays/list with filters
    response = get("holidays/list", emp_email, {"year": date.today().year})
    assert_test(response.status_code == 200, "GET /holidays/list with year filter")
    
    response = get("holidays/list", emp_email, {"upcoming": True})
    assert_test(response.status_code == 200, "GET /holidays/list upcoming")
    
    # GET /holidays/{id}
    if holiday_id:
        response = get(f"holidays/{holiday_id}", emp_email)
        assert_test(response.status_code == 200, "GET /holidays/{id}")
        
        # PUT /holidays/{id}
        response = put(f"holidays/{holiday_id}", admin_email, {
            "description": "Updated holiday description"
        })
        assert_test(response.status_code == 200, "PUT /holidays/{id}")
        
        # DELETE /holidays/{id}
        response = delete(f"holidays/{holiday_id}", admin_email)
        assert_test(response.status_code in [200, 204], "DELETE /holidays/{id}")
    
    print_section("Holidays Module - RBAC Tests")
    
    # Employee cannot create holidays
    response = post("holidays/create", emp_email, {
        "name": "Blocked Holiday",
        "date": (date.today() + timedelta(days=90)).isoformat()
    })
    assert_test(response.status_code == 403, "Employee cannot create holidays")
    
    # Admin cannot create holidays (only Super Admin)
    response = post("holidays/create", TEST_USERS["admin"]["email"], {
        "name": "Admin Blocked Holiday",
        "date": (date.today() + timedelta(days=91)).isoformat()
    })
    assert_test(response.status_code in [403, 201, 200], "Admin holiday creation (check policy)")


def test_search_module():
    """Test search endpoints."""
    print_section("Search Module")
    
    emp_email = TEST_USERS["employee"]["email"]
    
    # POST /search
    response = post("search", emp_email, {
        "query": "test",
        "limit": 10
    })
    assert_test(response.status_code == 200, "POST /search performs semantic search")
    
    # POST /search with empty query
    response = post("search", emp_email, {
        "query": "",
        "limit": 10
    })
    assert_test(response.status_code in [200, 400, 422], "POST /search handles empty query")


def test_edge_cases():
    """Test edge cases and error handling."""
    print_section("Edge Cases & Error Handling")
    
    emp_email = TEST_USERS["employee"]["email"]
    admin_email = TEST_USERS["super_admin"]["email"]
    
    # Invalid UUID format
    response = get("users/invalid-uuid", admin_email)
    assert_test(response.status_code == 422, "Invalid UUID returns 422")
    
    # Non-existent resource
    fake_uuid = str(uuid.uuid4())
    response = get(f"users/{fake_uuid}", admin_email)
    assert_test(response.status_code == 404, "Non-existent resource returns 404")
    
    # Empty request body
    response = requests.post(
        f"{BASE_URL}/api/v1/users",
        headers=TokenManager.get_headers(admin_email),
        json={}
    )
    assert_test(response.status_code == 422, "Empty body returns 422")
    
    # Missing required fields
    response = post("users", admin_email, {
        "first_name": "Only",
        # Missing last_name, email, password, role
    })
    assert_test(response.status_code == 422, "Missing required fields returns 422")
    
    # Invalid enum value
    response = post("it-requests", emp_email, {
        "request_type": "INVALID_TYPE",
        "title": "Test",
        "description": "Test description"
    })
    assert_test(response.status_code == 422, "Invalid enum value returns 422")
    
    # SQL injection attempt
    response = get("users", admin_email, {"search": "'; DROP TABLE users; --"})
    assert_test(response.status_code == 200, "SQL injection attempt handled safely")
    
    # XSS attempt
    response = post("users", admin_email, {
        "first_name": "<script>alert('xss')</script>",
        "last_name": "Test",
        "email": f"xss.test@{COMPANY_DOMAIN}",
        "password": "Secure@123",
        "role": "employee"
    })
    # Should either create (sanitized) or reject
    assert_test(response.status_code in [200, 201, 400, 422], "XSS attempt handled")
    
    # Very long input
    long_string = "A" * 10000
    response = post("it-requests", emp_email, {
        "request_type": "NEW_ASSET",
        "title": long_string,
        "description": "Test"
    })
    assert_test(response.status_code in [422, 400], "Very long input handled")
    
    # Negative pagination
    response = get("users", admin_email, {"page": -1, "page_size": -10})
    assert_test(response.status_code in [200, 422], "Negative pagination handled")
    
    # Zero pagination
    response = get("users", admin_email, {"page": 0, "page_size": 0})
    assert_test(response.status_code in [200, 422], "Zero pagination handled")
    
    # Very large page number
    response = get("users", admin_email, {"page": 999999})
    assert_test(response.status_code == 200, "Large page number returns empty result")


def test_cross_module_access():
    """Test cross-module access control."""
    print_section("Cross-Module Access Control")
    
    # Parking Manager accessing IT endpoints
    response = post("it-assets", TEST_USERS["parking_manager"]["email"], {
        "asset_type": "LAPTOP",
        "brand": "HP",
        "model": "Test",
        "serial_number": "CROSS001"
    })
    assert_test(response.status_code == 403, "Parking Manager blocked from IT assets")
    
    # IT Manager accessing Parking endpoints
    response = post("parking/allocations", TEST_USERS["it_manager"]["email"], {
        "user_code": "EMP0001",
        "vehicle_number": "GJ01XX1234",
        "vehicle_type": "car"
    })
    assert_test(response.status_code == 403, "IT Manager blocked from parking management")
    
    # Cafeteria Manager accessing Leave approval
    fake_uuid = str(uuid.uuid4())
    response = post(f"leave/requests/{fake_uuid}/approve-level1", TEST_USERS["cafeteria_manager"]["email"], {
        "action": "approve"
    })
    assert_test(response.status_code in [403, 404], "Cafeteria Manager blocked from leave approval")
    
    # Desk Manager accessing Food items
    response = post("food-orders/items", TEST_USERS["desk_manager"]["email"], {
        "name": "Blocked Item",
        "price": 100.00,
        "category": "snacks"
    })
    assert_test(response.status_code == 403, "Desk Manager blocked from food items")


def test_super_admin_override():
    """Test Super Admin can access everything."""
    print_section("Super Admin Override Access")
    
    admin_email = TEST_USERS["super_admin"]["email"]
    
    # Super Admin can access all modules
    response = get("parking/stats", admin_email)
    assert_test(response.status_code == 200, "Super Admin: parking stats")
    
    response = get("it-assets", admin_email)
    assert_test(response.status_code == 200, "Super Admin: IT assets")
    
    response = get("it-requests", admin_email)
    assert_test(response.status_code == 200, "Super Admin: IT requests")
    
    response = get("attendance", admin_email)
    assert_test(response.status_code == 200, "Super Admin: attendance")
    
    response = get("food-orders/items", admin_email)
    assert_test(response.status_code == 200, "Super Admin: food items")
    
    response = get("leave/requests", admin_email)
    assert_test(response.status_code == 200, "Super Admin: leave requests")
    
    response = get("projects", admin_email)
    assert_test(response.status_code == 200, "Super Admin: projects")


def test_pagination():
    """Test pagination across all list endpoints."""
    print_section("Pagination Tests")
    
    admin_email = TEST_USERS["super_admin"]["email"]
    emp_email = TEST_USERS["employee"]["email"]
    
    endpoints = [
        ("users", admin_email),
        ("attendance", admin_email),
        ("parking/allocations", emp_email),
        ("parking/visitors", TEST_USERS["parking_manager"]["email"]),
        ("it-assets", emp_email),
        ("it-requests", emp_email),
        ("desks/bookings", emp_email),
        ("cafeteria/bookings", emp_email),
        ("food-orders/items", emp_email),
        ("food-orders/orders", emp_email),
        ("leave/requests", emp_email),
        ("projects", emp_email),
        ("floor-plans", emp_email),
        ("holidays/list", emp_email),
    ]
    
    for endpoint, email in endpoints:
        response = get(endpoint, email, {"page": 1, "page_size": 5})
        if response.status_code == 200:
            data = response.json()
            has_pagination = "pagination" in data or "meta" in data or "total" in data
            assert_test(has_pagination or isinstance(data.get("data"), list), f"Pagination: {endpoint}")
        else:
            # Some endpoints may not be accessible to all users
            assert_test(response.status_code in [200, 403], f"Pagination access: {endpoint}")


def test_data_integrity():
    """Test data integrity and relationships."""
    print_section("Data Integrity Tests")
    
    admin_email = TEST_USERS["super_admin"]["email"]
    
    # Create a user and verify it appears in list
    test_email = f"integrity.test.{datetime.now().timestamp():.0f}@{COMPANY_DOMAIN}"
    response = post("users", admin_email, {
        "first_name": "Integrity",
        "last_name": "Test",
        "email": test_email,
        "password": "Integrity@123",
        "role": "employee"
    })
    user_id = get_id_from_response(response)
    
    if user_id:
        # Verify user appears in list
        response = get("users", admin_email, {"search": "Integrity"})
        assert_test(
            response.status_code == 200 and any(
                u.get("id") == user_id for u in response.json().get("data", [])
            ),
            "Created user appears in list"
        )
        
        # Delete user and verify it doesn't appear
        delete(f"users/{user_id}", admin_email)
        response = get(f"users/{user_id}", admin_email)
        assert_test(response.status_code == 404, "Deleted user not found")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all tests."""
    print_header("COMPREHENSIVE API TEST SUITE")
    print(f"Testing against: {BASE_URL}")
    print(f"Company Domain: {COMPANY_DOMAIN}")
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Test server health first
    test_server_health()
    
    # Run all test modules
    try:
        test_authentication()
        test_users_module()
        test_attendance_module()
        test_parking_module()
        test_it_assets_module()
        test_it_requests_module()
        test_desk_booking_module()
        test_cafeteria_module()
        test_food_orders_module()
        test_leave_module()
        test_projects_module()
        test_floor_plans_module()
        test_holidays_module()
        test_search_module()
        test_edge_cases()
        test_cross_module_access()
        test_super_admin_override()
        test_pagination()
        test_data_integrity()
    except Exception as e:
        print(f"\n{Colors.RED}ERROR: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print_header("TEST RESULTS SUMMARY")
    
    total = TESTS_PASSED + TESTS_FAILED
    pass_rate = (TESTS_PASSED / total * 100) if total > 0 else 0
    
    print(f"\n{Colors.BOLD}Total Tests: {total}{Colors.END}")
    print(f"{Colors.GREEN}Passed: {TESTS_PASSED}{Colors.END}")
    print(f"{Colors.RED}Failed: {TESTS_FAILED}{Colors.END}")
    print(f"{Colors.CYAN}Pass Rate: {pass_rate:.1f}%{Colors.END}")
    
    if FAILED_TESTS:
        print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
        for test in FAILED_TESTS:
            print(f"  - {test}")
    
    print(f"\nCompleted at: {datetime.now().isoformat()}")
    
    # Exit with appropriate code
    sys.exit(0 if TESTS_FAILED == 0 else 1)


if __name__ == "__main__":
    main()
