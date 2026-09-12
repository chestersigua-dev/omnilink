# OmniLink: Universal IoT Orchestration Platform

OmniLink is a monolithic, self-bootstrapping web application built for Capstone project presentation and embedded IoT deployment. It delivers zero-configuration, single-command launch across Windows, macOS, and Linux, unified multi-brand IoT controls, automated network discovery, custom group orchestration, and complete user profile management.

---

## Supported Brand Ecosystems & Protocols

| Brand | Target Hardware | Real Network Protocol | Default Port | Simulation Protocol |
| :--- | :--- | :--- | :--- | :--- |
| **Xiaomi** | Smart Air Purifiers, Desk Lamps, Plugs | `miio` UDP JSON-RPC | `54321` | `miio-udp-jsonrpc` |
| **TP-Link Tapo** | L530 Smart Bulbs, P110 Plugs | KLAP HTTP Handshake & JSON | `80` / `443` | `klap-http` |
| **Samsung** | Tizen Smart TVs, SmartThings | WebSocket Remote Key Events & REST | `8001` / `8002` | `tizen-ws-remote` |
| **LG** | webOS Smart TVs, ThinQ | `ssap://` WebSockets & UPnP | `3000` / `3001` | `webos-ssap-ws` |
| **TCL** | Android TV, FreshIN ACs | ADB Shell over TCP (`input keyevent`) | `5555` / `6466` | `adb-tcp-keyevent` |

---

## ⚡ Quick Start: Single-Command Universal Bootstrappers

OmniLink features self-bootstrapping launchers that automatically check for Python, set up isolated virtual environments (`.venv`), quietly install pinned dependencies, initialize SQLite databases and asset directories, and launch the server on **`http://localhost:8000`**.

### 1. Windows (Zero Configuration)
Double-click `run.bat` or run in PowerShell/cmd:
```cmd
run.bat
```

### 2. macOS / Linux (POSIX)
Make executable and run:
```bash
chmod +x run.sh
./run.sh
```

### 3. Docker Container (Host Network Mode for Subnet Discovery)
```bash
docker compose up --build
```
> **Note**: Uses `network_mode: "host"` so mDNS (`zeroconf`) and SSDP UDP broadcast packets reach physical IoT hardware on the host LAN.

---

## 🛰️ Network Discovery & Capstone Simulation Mode

OmniLink provides dual-mode IoT discovery via `/api/iot/scan`:
1. **Live Network Scan**: Broadcasts mDNS announcements (`zeroconf`) and SSDP UPnP queries (`239.255.255.250:1900`) across the local subnet.
2. **Demonstration / Simulation Mode (`SIMULATION_MODE=true`)**: Enabled by default in `.env` to guarantee a flawless live presentation. When physical hardware is offline, OmniLink serves 5 responsive virtual devices across Xiaomi, Tapo, Samsung, LG, and TCL.

---

## 🏛️ System Architecture

```
omnilink/
├── backend/
│   ├── main.py              # Monolithic entrypoint (serves API, SPA, and uploads)
│   ├── config.py            # Environment variables, security keys, and path mappings
│   ├── database.py          # SQLite engine and session lifecycle
│   ├── models.py            # Relational models (Users, Devices, Groups, Members)
│   ├── auth.py              # JWT authentication and bcrypt password hashing
│   ├── scanner.py           # mDNS zeroconf + SSDP UDP scanner + mock catalog
│   ├── adapters/            # Unified Multi-Brand Adapters
│   │   ├── base.py          # Standardized BaseIoTAdapter interface
│   │   ├── xiaomi.py        # Xiaomi miio UDP JSON-RPC adapter
│   │   ├── tapo.py          # TP-Link Tapo KLAP HTTP adapter
│   │   ├── samsung.py       # Samsung WebSocket Remote adapter
│   │   ├── lg.py            # LG webOS ssap:// WebSocket adapter
│   │   └── tcl.py           # TCL Android TV ADB TCP adapter
│   └── routes/              # FastAPI REST endpoints
│       ├── auth_routes.py   # Register, Login, Current User
│       ├── user_routes.py   # Profile update, avatar upload, account deletion
│       ├── iot_routes.py    # Scan, device CRUD, unified control
│       └── group_routes.py  # Groups CRUD, device assignment, batch controls
├── static/                  # Single Page Application
│   ├── index.html           # Tailwind CSS glassmorphic dashboard
│   ├── css/styles.css       # Radar pulse animations, dark mode, custom sliders
│   ├── js/api.js            # REST client with JWT storage and toast helpers
│   └── js/app.js            # Reactive UI controller and state manager
├── uploads/
│   └── avatars/             # User avatar photo storage
├── tests/
│   └── test_system.py       # Comprehensive pytest test suite (100% pass)
├── run.bat                  # Windows auto-installer and bootstrapper
├── run.sh                   # POSIX auto-installer and bootstrapper
├── Dockerfile               # Container definition
├── docker-compose.yml       # Host-network compose configuration
└── requirements.txt         # Pinned production dependencies
```

---

## 🔐 REST API Reference

### Authentication & Users
- `POST /api/auth/register` - Create new user account (bcrypt password hashing).
- `POST /api/auth/login` - Authenticate user and receive signed JWT bearer token.
- `GET /api/auth/me` - Retrieve current authenticated profile.
- `PUT /api/users/profile` - Update user full name, email, and bio.
- `POST /api/users/avatar` - Upload avatar photo (`.png`, `.jpg`, `.webp` MIME validation).
- `DELETE /api/users/account` - Permanently delete account with cascading database cleanup.

### IoT Devices & Scanner
- `GET /api/iot/scan?force_simulation={bool}` - Subnet scan using mDNS and SSDP.
- `GET /api/iot/devices` - List registered devices for current user.
- `POST /api/iot/devices` - Register a discovered device into dashboard.
- `POST /api/iot/devices/{id}/control` - Send `turn_on`, `turn_off`, or `set_level` to adapter.
- `POST /api/iot/devices/{id}/sync` - Poll live hardware status.
- `DELETE /api/iot/devices/{id}` - Remove device from dashboard.

### Groups & Batch Orchestration
- `GET /api/groups` - List user custom groups.
- `POST /api/groups` - Create a group with assigned device IDs.
- `PUT /api/groups/{id}/devices` - Update assigned device memberships.
- `POST /api/groups/{id}/batch-control` - Dispatches parallel asynchronous commands (`turn_all_on`, `turn_all_off`, `set_level`) across all group members via `asyncio.gather`.
- `DELETE /api/groups/{id}` - Delete group.

---

## 🧪 Running Automated Tests

Run the full pytest suite inside the virtual environment:
```bash
.\.venv\Scripts\python.exe -m pytest tests/ -v
```
All 5 test suites pass:
1. `test_health_check`
2. `test_auth_and_user_profile_crud`
3. `test_iot_discovery_and_5_brand_adapters`
4. `test_custom_groups_and_parallel_batch_orchestration`
5. `test_account_deletion_cascade`
