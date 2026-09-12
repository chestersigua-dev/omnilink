import os
import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base, engine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # Fresh database tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "xiaomi" in data["supported_brands"]
    assert "tapo" in data["supported_brands"]
    assert "samsung" in data["supported_brands"]
    assert "lg" in data["supported_brands"]
    assert "tcl" in data["supported_brands"]

def test_auth_and_user_profile_crud():
    # 1. Register
    reg_payload = {
        "username": "engineer_alex",
        "email": "alex@capstone.iot",
        "password": "SecurePassword123!",
        "full_name": "Alex Vance"
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Duplicate registration rejection
    dup_resp = client.post("/api/auth/register", json=reg_payload)
    assert dup_resp.status_code == 400

    # 3. Login
    login_resp = client.post("/api/auth/login", json={"username": "engineer_alex", "password": "SecurePassword123!"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # 4. Get Profile (Me)
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "engineer_alex"

    # 5. Update Profile
    update_resp = client.put(
        "/api/users/profile",
        json={"full_name": "Dr. Alex Vance", "bio": "IoT Systems Architect"},
        headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["user"]["full_name"] == "Dr. Alex Vance"
    assert update_resp.json()["user"]["bio"] == "IoT Systems Architect"

    # 6. Upload Avatar (Valid PNG)
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    avatar_resp = client.post(
        "/api/users/avatar",
        files={"file": ("test_avatar.png", io.BytesIO(dummy_png), "image/png")},
        headers=headers
    )
    assert avatar_resp.status_code == 200
    assert "/uploads/avatars/" in avatar_resp.json()["avatar_url"]

    # 7. Reject Invalid MIME type (e.g. text/plain or executable)
    bad_file_resp = client.post(
        "/api/users/avatar",
        files={"file": ("exploit.txt", io.BytesIO(b"malicious script"), "text/plain")},
        headers=headers
    )
    assert bad_file_resp.status_code == 400

def test_iot_discovery_and_5_brand_adapters():
    # Login as engineer_alex
    login_resp = client.post("/api/auth/login", json={"username": "engineer_alex", "password": "SecurePassword123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Network Scan (Simulation mode active)
    scan_resp = client.get("/api/iot/scan?force_simulation=true", headers=headers)
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data["count"] >= 5
    
    discovered_brands = {d["brand"].lower() for d in scan_data["devices"]}
    assert {"xiaomi", "tapo", "samsung", "lg", "tcl"}.issubset(discovered_brands)

    # 2. Add all 5 discovered units to dashboard
    added_device_ids = []
    for dev in scan_data["devices"]:
        add_resp = client.post("/api/iot/devices", json=dev, headers=headers)
        assert add_resp.status_code == 200
        added_device_ids.append(add_resp.json()["id"])

    assert len(added_device_ids) >= 5

    # 3. Test Unified Adapter Controls on each device
    list_resp = client.get("/api/iot/devices", headers=headers)
    devices = list_resp.json()

    for dev in devices:
        dev_id = dev["id"]
        brand = dev["brand"]

        # Turn ON
        on_resp = client.post(
            f"/api/iot/devices/{dev_id}/control",
            json={"action": "turn_on"},
            headers=headers
        )
        assert on_resp.status_code == 200
        assert on_resp.json()["device"]["power_state"] is True
        assert on_resp.json()["adapter_execution"]["brand"] == brand

        # Set Level (Brightness / Temp / Volume)
        level_resp = client.post(
            f"/api/iot/devices/{dev_id}/control",
            json={"action": "set_level", "parameter": "level", "value": 77},
            headers=headers
        )
        assert level_resp.status_code == 200
        assert level_resp.json()["device"]["level"] == 77

        # Turn OFF
        off_resp = client.post(
            f"/api/iot/devices/{dev_id}/control",
            json={"action": "turn_off"},
            headers=headers
        )
        assert off_resp.status_code == 200
        assert off_resp.json()["device"]["power_state"] is False

def test_custom_groups_and_parallel_batch_orchestration():
    login_resp = client.post("/api/auth/login", json={"username": "engineer_alex", "password": "SecurePassword123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch user's registered devices
    devices = client.get("/api/iot/devices", headers=headers).json()
    device_ids = [d["id"] for d in devices[:3]]

    # 1. Create Custom Group
    group_payload = {
        "name": "Living Room Master Zone",
        "description": "Smart appliances for main family lounge",
        "device_ids": device_ids
    }
    create_group_resp = client.post("/api/groups", json=group_payload, headers=headers)
    assert create_group_resp.status_code == 200
    group_data = create_group_resp.json()
    group_id = group_data["id"]
    assert group_data["device_count"] == len(device_ids)

    # 2. Batch Control: Turn All On
    batch_on_resp = client.post(
        f"/api/groups/{group_id}/batch-control",
        json={"action": "turn_all_on"},
        headers=headers
    )
    assert batch_on_resp.status_code == 200
    assert batch_on_resp.json()["dispatched_count"] == len(device_ids)
    for res in batch_on_resp.json()["results"]:
        assert res["success"] is True

    # 3. Batch Control: Turn All Off
    batch_off_resp = client.post(
        f"/api/groups/{group_id}/batch-control",
        json={"action": "turn_all_off"},
        headers=headers
    )
    assert batch_off_resp.status_code == 200
    assert batch_off_resp.json()["dispatched_count"] == len(device_ids)

    # 4. Delete Group
    del_group_resp = client.delete(f"/api/groups/{group_id}", headers=headers)
    assert del_group_resp.status_code == 200

def test_account_deletion_cascade():
    # Create temporary user
    temp_user_payload = {
        "username": "delete_me_user",
        "email": "deleteme@capstone.iot",
        "password": "Password123!",
        "full_name": "Temporary User"
    }
    reg = client.post("/api/auth/register", json=temp_user_payload).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add a device and group
    dev_resp = client.post(
        "/api/iot/devices",
        json={
            "device_uid": "TEMP_DEV_999",
            "name": "Temp Plug",
            "brand": "tapo",
            "model": "P110"
        },
        headers=headers
    )
    dev_id = dev_resp.json()["id"]

    client.post(
        "/api/groups",
        json={"name": "Temp Zone", "device_ids": [dev_id]},
        headers=headers
    )

    # Delete Account
    del_resp = client.delete("/api/users/account", headers=headers)
    assert del_resp.status_code == 200

    # Verify user cannot login anymore
    relogin = client.post("/api/auth/login", json={"username": "delete_me_user", "password": "Password123!"})
    assert relogin.status_code == 401

def test_disable_simulation_and_physical_iot_scan():
    # Login as engineer_alex
    login_resp = client.post("/api/auth/login", json={"username": "engineer_alex", "password": "SecurePassword123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Query simulation endpoint
    sim_status = client.get("/api/iot/simulation")
    assert sim_status.status_code == 200
    assert "simulation_mode" in sim_status.json()

    # 2. Perform scan with simulation explicitly DISABLED
    phys_scan = client.get("/api/iot/scan?disable_simulation=true", headers=headers)
    assert phys_scan.status_code == 200
    phys_data = phys_scan.json()
    assert phys_data["mode"] == "physical"
    assert phys_data["simulation_disabled"] is True
    # Verify no fake simulated devices are injected
    for dev in phys_data["devices"]:
        assert not dev["device_uid"].startswith("SIM_")

    # 3. Toggle global simulation to FALSE
    toggle_off = client.post("/api/iot/simulation", json={"simulation_mode": False}, headers=headers)
    assert toggle_off.status_code == 200
    assert toggle_off.json()["simulation_mode"] is False

    # Scan without flags now runs physical scan
    auto_scan = client.get("/api/iot/scan", headers=headers)
    assert auto_scan.status_code == 200
    assert auto_scan.json()["mode"] == "physical"
    for dev in auto_scan.json()["devices"]:
        assert not dev["device_uid"].startswith("SIM_")

    # 4. Toggle global simulation back to TRUE
    toggle_on = client.post("/api/iot/simulation", json={"simulation_mode": True}, headers=headers)
    assert toggle_on.status_code == 200
    assert toggle_on.json()["simulation_mode"] is True

    # Scan with force_simulation=true or default returns simulated devices
    sim_scan = client.get("/api/iot/scan?force_simulation=true", headers=headers)
    assert sim_scan.status_code == 200
    assert sim_scan.json()["count"] >= 5
    assert any(d["device_uid"].startswith("SIM_") for d in sim_scan.json()["devices"])
