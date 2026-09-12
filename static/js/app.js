/**
 * OmniLink Main Application Controller
 */

// Application State
const state = {
  currentUser: null,
  devices: [],
  groups: [],
  filterBrand: "all",
  searchQuery: "",
  discoveredDevices: [],
  isScanning: false,
  simulationMode: true,
  scanMode: "simulation", // "simulation" | "physical"
  debounceTimers: {}
};

// DOM Content Loaded Handler
document.addEventListener("DOMContentLoaded", async () => {
  initEventListeners();
  await fetchSimulationStatus();
  await checkAuthSession();
});

// Fetch Global Simulation Mode from API
async function fetchSimulationStatus() {
  try {
    const res = await window.api.getSimulationMode();
    state.simulationMode = Boolean(res.simulation_mode);
    state.scanMode = state.simulationMode ? "simulation" : "physical";
    updateSimulationUI();
  } catch (err) {
    console.warn("Could not fetch initial simulation status:", err);
  }
}

function updateSimulationUI() {
  const btn = document.getElementById("globalSimToggleBtn");
  const dot = document.getElementById("globalSimDot");
  const text = document.getElementById("globalSimText");
  if (!btn || !dot || !text) return;

  if (state.simulationMode) {
    btn.className = "flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 transition-all shadow-sm";
    dot.className = "w-2 h-2 rounded-full bg-indigo-400 animate-pulse";
    text.textContent = "Virtual Simulation";
    btn.title = "Simulation active. Click to disable simulation and switch to physical IoT discovery.";
  } else {
    btn.className = "flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 transition-all shadow-sm";
    dot.className = "w-2 h-2 rounded-full bg-emerald-400 animate-pulse";
    text.textContent = "Physical Hardware";
    btn.title = "Physical IoT discovery active. Click to switch to virtual demonstration mode.";
  }
}

async function toggleGlobalSimulationMode() {
  const newMode = !state.simulationMode;
  try {
    const res = await window.api.setSimulationMode(newMode);
    state.simulationMode = Boolean(res.simulation_mode);
    state.scanMode = state.simulationMode ? "simulation" : "physical";
    updateSimulationUI();
    setScanMode(state.scanMode, false);
    window.showToast(
      state.simulationMode 
        ? "Simulation Enabled: 5-Brand Virtual Devices Active" 
        : "Simulation Disabled: Physical IoT Hardware Scan Active", 
      "success"
    );
  } catch (err) {
    window.showToast("Failed to update simulation mode: " + err.message, "error");
  }
}

// Check Session & Bootstrap
async function checkAuthSession() {
  if (window.api.token) {
    try {
      const user = await window.api.getMe();
      setAuthenticatedUser(user);
    } catch (e) {
      console.warn("Session check failed:", e);
      setUnauthenticated();
    }
  } else {
    setUnauthenticated();
  }
}

function setAuthenticatedUser(user) {
  state.currentUser = user;
  document.getElementById("authView").classList.add("hidden");
  document.getElementById("dashboardView").classList.remove("hidden");
  
  // Update Profile UI
  updateNavbarProfile(user);
  updateSimulationUI();
  
  // Load data
  refreshDashboard();
}

function setUnauthenticated() {
  state.currentUser = null;
  document.getElementById("authView").classList.remove("hidden");
  document.getElementById("dashboardView").classList.add("hidden");
}

function updateNavbarProfile(user) {
  const avatarImg = document.getElementById("navUserAvatar");
  const userNameText = document.getElementById("navUserName");
  if (avatarImg) avatarImg.src = user.avatar_url || "/static/images/default_avatar.svg";
  if (userNameText) userNameText.textContent = user.full_name || user.username;
}

// Data Refresh
async function refreshDashboard() {
  try {
    const [devices, groups] = await Promise.all([
      window.api.getDevices(),
      window.api.getGroups()
    ]);
    state.devices = devices;
    state.groups = groups;

    renderStats();
    renderDevices();
    renderGroups();
  } catch (err) {
    console.error("Failed to load dashboard data:", err);
    window.showToast("Failed to sync dashboard: " + err.message, "error");
  }
}

// Render Stats
function renderStats() {
  const total = state.devices.length;
  const online = state.devices.filter(d => d.power_state).length;
  const groupsCount = state.groups.length;

  document.getElementById("statTotalDevices").textContent = total;
  document.getElementById("statPoweredOn").textContent = online;
  document.getElementById("statTotalGroups").textContent = groupsCount;
}

// Render Devices Grid
function renderDevices() {
  const container = document.getElementById("devicesGrid");
  if (!container) return;

  const filtered = state.devices.filter(d => {
    const matchesBrand = state.filterBrand === "all" || d.brand.toLowerCase() === state.filterBrand.toLowerCase();
    const matchesSearch = !state.searchQuery || 
      d.name.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      d.model.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      d.ip_address.includes(state.searchQuery);
    return matchesBrand && matchesSearch;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-16 text-center text-slate-400 glass-panel rounded-2xl p-8">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-400">
          <i data-lucide="cpu" class="w-8 h-8"></i>
        </div>
        <h3 class="text-lg font-semibold text-white mb-1">No Devices Connected</h3>
        <p class="text-sm text-slate-400 max-w-sm mx-auto mb-6">
          Click "Scan Network" to discover Xiaomi, Tapo, Samsung, LG, or TCL smart devices automatically.
        </p>
        <button onclick="openScanModal()" class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-600/30">
          Scan Subnet Now
        </button>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = filtered.map(dev => {
    const brandBadgeClass = `badge-${dev.brand.toLowerCase()}`;
    const isPowerOn = dev.power_state;
    const levelLabel = dev.device_type === "tv" ? "Volume" : dev.device_type === "ac" ? "Temp (°C)" : "Brightness";
    const levelVal = dev.level;

    return `
      <div class="glass-panel glass-panel-hover rounded-2xl p-5 relative flex flex-col justify-between" id="deviceCard-${dev.id}">
        <div>
          <!-- Card Header -->
          <div class="flex items-start justify-between gap-3 mb-4">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-xl flex items-center justify-center ${isPowerOn ? 'bg-indigo-600/20 text-indigo-400 shadow-inner' : 'bg-slate-800 text-slate-500'}">
                <i data-lucide="${getDeviceIcon(dev.device_type)}" class="w-6 h-6"></i>
              </div>
              <div>
                <h4 class="font-semibold text-white text-base leading-tight">${escapeHtml(dev.name)}</h4>
                <div class="flex items-center gap-2 mt-1">
                  <span class="text-xs px-2 py-0.5 rounded-md font-medium uppercase tracking-wider ${brandBadgeClass}">
                    ${dev.brand}
                  </span>
                  <span class="text-xs text-slate-400">${escapeHtml(dev.model || dev.device_type)}</span>
                </div>
              </div>
            </div>
            
            <!-- Power Toggle -->
            <button 
              onclick="toggleDevicePower(${dev.id}, ${!isPowerOn})"
              class="w-10 h-10 rounded-full flex items-center justify-center transition-all ${isPowerOn ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 ring-2 ring-emerald-500/40' : 'bg-slate-800 text-slate-500 hover:bg-slate-700'}"
              title="${isPowerOn ? 'Power Off' : 'Power On'}"
            >
              <i data-lucide="power" class="w-5 h-5"></i>
            </button>
          </div>

          <!-- Network & Protocol Info -->
          <div class="bg-slate-900/60 rounded-xl p-3 mb-4 text-xs font-mono text-slate-400 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full ${dev.is_online ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}"></span>
              <span>${dev.ip_address}:${dev.port || 'default'}</span>
            </div>
            <span class="text-indigo-400">${dev.protocol || 'unified'}</span>
          </div>

          <!-- Level Control Slider -->
          <div class="mb-4">
            <div class="flex items-center justify-between text-xs font-medium text-slate-300 mb-2">
              <span>${levelLabel}</span>
              <span id="levelDisplay-${dev.id}" class="text-indigo-400 font-bold">${levelVal}${dev.device_type === 'ac' ? '°C' : '%'}</span>
            </div>
            <input 
              type="range" 
              min="${dev.device_type === 'ac' ? '16' : '0'}" 
              max="${dev.device_type === 'ac' ? '30' : '100'}" 
              value="${levelVal}"
              oninput="handleLevelInput(${dev.id}, this.value, '${dev.device_type}')"
              class="w-full"
            />
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
          <button 
            onclick="syncDevice(${dev.id})"
            class="flex items-center gap-1.5 text-slate-400 hover:text-indigo-400 transition-colors py-1 px-2 rounded-lg hover:bg-slate-800/50"
          >
            <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
            <span>Sync</span>
          </button>
          <button 
            onclick="confirmDeleteDevice(${dev.id}, '${escapeHtml(dev.name)}')"
            class="text-slate-500 hover:text-rose-400 transition-colors p-1 rounded-lg hover:bg-rose-500/10"
            title="Remove Device"
          >
            <i data-lucide="trash-2" class="w-4 h-4"></i>
          </button>
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

function getDeviceIcon(type) {
  switch (type) {
    case "bulb": return "lightbulb";
    case "plug": return "zap";
    case "tv": return "tv";
    case "ac": return "wind";
    case "purifier": return "fan";
    default: return "cpu";
  }
}

// Render Custom Groups
function renderGroups() {
  const container = document.getElementById("groupsGrid");
  if (!container) return;

  if (state.groups.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-8 text-center text-slate-400 glass-panel rounded-2xl p-6">
        <p class="text-sm">No custom groups created yet. Create zones like "Living Room" or "Cinema Mode" for one-click batch orchestration.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.groups.map(g => {
    return `
      <div class="glass-panel rounded-2xl p-5 flex flex-col justify-between">
        <div>
          <div class="flex items-start justify-between gap-3 mb-2">
            <div>
              <h4 class="font-bold text-white text-base">${escapeHtml(g.name)}</h4>
              <p class="text-xs text-slate-400 mt-0.5">${escapeHtml(g.description || 'Custom Device Zone')}</p>
            </div>
            <button onclick="confirmDeleteGroup(${g.id}, '${escapeHtml(g.name)}')" class="text-slate-500 hover:text-rose-400 transition-colors">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          </div>

          <div class="text-xs text-slate-400 mb-4">
            <span class="inline-flex items-center gap-1.5 bg-indigo-500/10 text-indigo-400 px-2.5 py-1 rounded-lg font-medium">
              <i data-lucide="layers" class="w-3.5 h-3.5"></i>
              ${g.device_count} Assigned Device${g.device_count === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        <!-- Batch Controls -->
        <div class="flex items-center gap-2 pt-3 border-t border-slate-800/80">
          <button 
            onclick="batchControlGroup(${g.id}, 'turn_all_on')"
            class="flex-1 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow-sm"
          >
            <i data-lucide="power" class="w-3.5 h-3.5"></i>
            All On
          </button>
          <button 
            onclick="batchControlGroup(${g.id}, 'turn_all_off')"
            class="flex-1 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all shadow-sm"
          >
            <i data-lucide="power-off" class="w-3.5 h-3.5"></i>
            All Off
          </button>
          <button 
            onclick="openEditGroupDevicesModal(${g.id})"
            class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition-colors"
            title="Edit Group Devices"
          >
            <i data-lucide="settings-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

// --- Device Interactions ---
async function toggleDevicePower(deviceId, newPowerState) {
  const action = newPowerState ? "turn_on" : "turn_off";
  try {
    const res = await window.api.controlDevice(deviceId, action);
    window.showToast(`${res.device.name} powered ${newPowerState ? 'ON' : 'OFF'}`, "success");
    
    // Update local state
    const dev = state.devices.find(d => d.id === deviceId);
    if (dev) {
      dev.power_state = newPowerState;
    }
    renderStats();
    renderDevices();
  } catch (err) {
    window.showToast("Command failed: " + err.message, "error");
  }
}

function handleLevelInput(deviceId, value, deviceType) {
  const display = document.getElementById(`levelDisplay-${deviceId}`);
  if (display) {
    display.textContent = `${value}${deviceType === 'ac' ? '°C' : '%'}`;
  }

  // Debounce network dispatch
  clearTimeout(state.debounceTimers[deviceId]);
  state.debounceTimers[deviceId] = setTimeout(async () => {
    try {
      const param = deviceType === 'tv' ? 'volume' : deviceType === 'ac' ? 'temperature' : 'brightness';
      await window.api.controlDevice(deviceId, "set_level", param, parseInt(value, 10));
      const dev = state.devices.find(d => d.id === deviceId);
      if (dev) dev.level = parseInt(value, 10);
    } catch (err) {
      window.showToast("Level adjustment failed: " + err.message, "error");
    }
  }, 350);
}

async function syncDevice(deviceId) {
  try {
    const updated = await window.api.syncDevice(deviceId);
    window.showToast(`Synced ${updated.name}`, "info");
    const dev = state.devices.find(d => d.id === deviceId);
    if (dev) Object.assign(dev, updated);
    renderDevices();
  } catch (err) {
    window.showToast("Sync failed: " + err.message, "error");
  }
}

async function confirmDeleteDevice(deviceId, deviceName) {
  if (!confirm(`Are you sure you want to remove "${deviceName}" from your dashboard?`)) return;
  try {
    await window.api.deleteDevice(deviceId);
    window.showToast(`Removed "${deviceName}"`, "success");
    state.devices = state.devices.filter(d => d.id !== deviceId);
    renderStats();
    renderDevices();
  } catch (err) {
    window.showToast("Failed to remove device: " + err.message, "error");
  }
}

// --- Group Batch Actions ---
async function batchControlGroup(groupId, action) {
  try {
    window.showToast("Executing batch commands across group...", "info");
    const res = await window.api.batchControlGroup(groupId, action);
    window.showToast(`Dispatched ${action.replace(/_/g, ' ')} to ${res.dispatched_count} devices`, "success");
    await refreshDashboard();
  } catch (err) {
    window.showToast("Batch action failed: " + err.message, "error");
  }
}

async function confirmDeleteGroup(groupId, groupName) {
  if (!confirm(`Delete group "${groupName}"?`)) return;
  try {
    await window.api.deleteGroup(groupId);
    window.showToast(`Group "${groupName}" deleted`, "success");
    state.groups = state.groups.filter(g => g.id !== groupId);
    renderStats();
    renderGroups();
  } catch (err) {
    window.showToast("Failed to delete group: " + err.message, "error");
  }
}

// --- Scanner Logic ---
function openScanModal() {
  const modal = document.getElementById("scanModal");
  modal.classList.remove("hidden");
  // Sync modal buttons with current state
  setScanMode(state.scanMode, false);
  startNetworkScan();
}

function closeScanModal() {
  const modal = document.getElementById("scanModal");
  modal.classList.add("hidden");
}

function setScanMode(mode, triggerScan = false) {
  state.scanMode = mode;
  const physBtn = document.getElementById("scanModePhysicalBtn");
  const simBtn = document.getElementById("scanModeSimBtn");
  const badge = document.getElementById("scanModeBadge");
  const hint = document.getElementById("scanModeHint");

  if (mode === "physical") {
    if (physBtn) {
      physBtn.className = "flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg font-semibold transition-all bg-emerald-600 text-white shadow-md shadow-emerald-600/30";
    }
    if (simBtn) {
      simBtn.className = "flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg font-medium transition-all text-slate-400 hover:text-white";
    }
    if (badge) {
      badge.className = "text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
      badge.textContent = "Physical LAN Discovery";
    }
    if (hint) {
      hint.textContent = "Broadcasts mDNS Zeroconf & SSDP UPnP probes across your subnet. No virtual devices.";
    }
  } else {
    if (physBtn) {
      physBtn.className = "flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg font-medium transition-all text-slate-400 hover:text-white";
    }
    if (simBtn) {
      simBtn.className = "flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg font-semibold transition-all bg-indigo-600 text-white shadow-md shadow-indigo-600/30";
    }
    if (badge) {
      badge.className = "text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30";
      badge.textContent = "Demo Simulation";
    }
    if (hint) {
      hint.textContent = "Simulates responsive Xiaomi, Tapo, Samsung, LG, and TCL devices.";
    }
  }

  lucide.createIcons();

  if (triggerScan) {
    startNetworkScan();
  }
}

async function startNetworkScan() {
  const radarText = document.getElementById("radarScanStatus");
  const resultsContainer = document.getElementById("discoveredList");
  const rescanBtn = document.getElementById("rescanBtn");
  const isPhysical = state.scanMode === "physical";

  if (rescanBtn) rescanBtn.disabled = true;

  if (isPhysical) {
    radarText.textContent = "Broadcasting mDNS & SSDP probes for physical IoT hardware...";
    resultsContainer.innerHTML = `<div class="py-8 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
      <div class="animate-spin text-indigo-400">↻</div>
      <span>Querying local network for physical smart devices...</span>
    </div>`;
  } else {
    radarText.textContent = "Injecting virtual 5-brand IoT catalog...";
    resultsContainer.innerHTML = `<div class="py-8 text-center text-slate-400 text-sm flex flex-col items-center gap-2">
      <div class="animate-spin text-indigo-400">↻</div>
      <span>Loading virtual devices catalog...</span>
    </div>`;
  }

  try {
    const data = await window.api.scanDevices(
      isPhysical ? { disableSimulation: true } : { forceSimulation: true }
    );
    state.discoveredDevices = data.devices || [];
    
    if (isPhysical) {
      radarText.textContent = `Physical Discovery Complete: ${state.discoveredDevices.length} Hardware Device(s) Detected`;
    } else {
      radarText.textContent = `Virtual Catalog Active: ${state.discoveredDevices.length} Device(s) Injected`;
    }
    renderDiscoveredDevices();
  } catch (err) {
    radarText.textContent = "Scan Failed: " + err.message;
    window.showToast("Scanner error: " + err.message, "error");
  } finally {
    if (rescanBtn) rescanBtn.disabled = false;
  }
}

function renderDiscoveredDevices() {
  const container = document.getElementById("discoveredList");
  if (!container) return;

  if (state.discoveredDevices.length === 0) {
    if (state.scanMode === "physical") {
      container.innerHTML = `
        <div class="py-6 text-center space-y-3 px-2">
          <div class="w-11 h-11 rounded-2xl bg-amber-500/10 text-amber-400 mx-auto flex items-center justify-center border border-amber-500/20">
            <i data-lucide="wifi-off" class="w-5 h-5"></i>
          </div>
          <div class="font-semibold text-white text-sm">No Physical IoT Devices Found</div>
          <p class="text-xs text-slate-400 max-w-md mx-auto">
            Zero smart devices responded to mDNS or SSDP broadcast on this local subnet.
          </p>
          <div class="text-[11px] text-slate-400 bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-left space-y-1 max-w-md mx-auto">
            <div>• Make sure your smart hardware (Xiaomi, Tapo, Samsung/LG TV) is powered on.</div>
            <div>• Verify that your device and computer are on the same Wi-Fi subnet.</div>
            <div>• Router "AP Client Isolation" must be disabled for local IoT discovery.</div>
          </div>
          <div class="pt-2 flex justify-center items-center gap-2">
            <button onclick="startNetworkScan()" class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5">
              <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
              Retry Physical Scan
            </button>
            <button onclick="setScanMode('simulation', true)" class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5">
              <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
              Switch to Demo Mode
            </button>
          </div>
        </div>
      `;
    } else {
      container.innerHTML = `<div class="py-6 text-center text-slate-400 text-sm">No devices found.</div>`;
    }
    lucide.createIcons();
    return;
  }

  container.innerHTML = state.discoveredDevices.map((dev, idx) => {
    const isVirtual = dev.device_uid && dev.device_uid.startsWith("SIM_");
    const sourceTag = isVirtual 
      ? `<span class="px-1.5 py-0.2 rounded text-[10px] uppercase font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Virtual</span>`
      : `<span class="px-1.5 py-0.2 rounded text-[10px] uppercase font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Physical</span>`;

    return `
      <div class="p-3 bg-slate-900/70 border border-slate-800 rounded-xl flex items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
            <i data-lucide="${getDeviceIcon(dev.device_type)}" class="w-5 h-5"></i>
          </div>
          <div>
            <div class="font-semibold text-white text-sm flex items-center gap-2">
              <span>${escapeHtml(dev.name)}</span>
              ${sourceTag}
            </div>
            <div class="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
              <span class="badge-${dev.brand} px-1.5 py-0.2 rounded text-[10px] uppercase font-bold">${dev.brand}</span>
              <span>${dev.ip_address}</span>
              <span class="text-slate-500 font-mono text-[11px]">${dev.protocol || dev.mac_address}</span>
            </div>
          </div>
        </div>

        <div>
          ${dev.is_registered ? `
            <span class="text-xs px-3 py-1.5 bg-slate-800 text-slate-400 rounded-lg font-medium">Already Added</span>
          ` : `
            <button 
              onclick="addDiscoveredDevice(${idx})"
              id="addBtn-${idx}"
              class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
            >
              <i data-lucide="plus" class="w-3.5 h-3.5"></i>
              Add
            </button>
          `}
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

async function addDiscoveredDevice(index) {
  const dev = state.discoveredDevices[index];
  if (!dev) return;

  const btn = document.getElementById(`addBtn-${index}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin text-xs">↻</span> Adding...`;
  }

  try {
    await window.api.addDevice(dev);
    dev.is_registered = true;
    window.showToast(`Added "${dev.name}" to dashboard!`, "success");
    renderDiscoveredDevices();
    await refreshDashboard();
  } catch (err) {
    window.showToast("Failed to add device: " + err.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `Add`;
    }
  }
}

// --- Group Management Modals ---
function openCreateGroupModal() {
  const modal = document.getElementById("groupModal");
  document.getElementById("groupModalTitle").textContent = "Create New Device Group";
  document.getElementById("groupNameInput").value = "";
  document.getElementById("groupDescInput").value = "";
  
  renderGroupDeviceCheckboxes([]);
  modal.classList.remove("hidden");
}

function openEditGroupDevicesModal(groupId) {
  const group = state.groups.find(g => g.id === groupId);
  if (!group) return;

  const modal = document.getElementById("groupModal");
  document.getElementById("groupModalTitle").textContent = `Edit Devices: ${group.name}`;
  document.getElementById("groupNameInput").value = group.name;
  document.getElementById("groupDescInput").value = group.description || "";
  
  const assignedIds = (group.devices || []).map(d => d.id);
  renderGroupDeviceCheckboxes(assignedIds);
  
  modal.dataset.editingGroupId = groupId;
  modal.classList.remove("hidden");
}

function renderGroupDeviceCheckboxes(selectedDeviceIds) {
  const container = document.getElementById("groupDevicesList");
  if (!container) return;

  if (state.devices.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-400">No devices available. Add devices first.</div>`;
    return;
  }

  container.innerHTML = state.devices.map(d => {
    const isChecked = selectedDeviceIds.includes(d.id);
    return `
      <label class="flex items-center gap-2.5 p-2 rounded-lg bg-slate-900/50 hover:bg-slate-900 cursor-pointer border border-slate-800 text-xs">
        <input type="checkbox" value="${d.id}" class="rounded text-indigo-600 focus:ring-0" ${isChecked ? 'checked' : ''} />
        <span class="font-medium text-slate-200">${escapeHtml(d.name)}</span>
        <span class="text-[10px] text-slate-400 ml-auto uppercase">${d.brand}</span>
      </label>
    `;
  }).join("");
}

function closeGroupModal() {
  const modal = document.getElementById("groupModal");
  modal.classList.add("hidden");
  delete modal.dataset.editingGroupId;
}

async function saveGroupForm() {
  const modal = document.getElementById("groupModal");
  const groupId = modal.dataset.editingGroupId;
  const name = document.getElementById("groupNameInput").value.trim();
  const desc = document.getElementById("groupDescInput").value.trim();
  
  const checkedBoxes = document.querySelectorAll("#groupDevicesList input[type='checkbox']:checked");
  const deviceIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value, 10));

  if (!name) {
    window.showToast("Please enter a group name", "warning");
    return;
  }

  try {
    if (groupId) {
      await window.api.updateGroup(groupId, name, desc);
      await window.api.assignGroupDevices(groupId, deviceIds);
      window.showToast("Group updated successfully", "success");
    } else {
      await window.api.createGroup(name, desc, deviceIds);
      window.showToast("Group created successfully", "success");
    }
    closeGroupModal();
    await refreshDashboard();
  } catch (err) {
    window.showToast("Failed to save group: " + err.message, "error");
  }
}

// --- Profile & Account Management ---
function openProfileModal() {
  if (!state.currentUser) return;
  const modal = document.getElementById("profileModal");
  
  document.getElementById("profileFullName").value = state.currentUser.full_name || "";
  document.getElementById("profileEmail").value = state.currentUser.email || "";
  document.getElementById("profileBio").value = state.currentUser.bio || "";
  document.getElementById("modalAvatarPreview").src = state.currentUser.avatar_url || "/static/images/default_avatar.svg";

  modal.classList.remove("hidden");
}

function closeProfileModal() {
  document.getElementById("profileModal").classList.add("hidden");
}

async function handleSaveProfile() {
  const full_name = document.getElementById("profileFullName").value.trim();
  const email = document.getElementById("profileEmail").value.trim();
  const bio = document.getElementById("profileBio").value.trim();

  try {
    const res = await window.api.updateProfile({ full_name, email, bio });
    state.currentUser = res.user;
    updateNavbarProfile(res.user);
    window.showToast("Profile details updated", "success");
    closeProfileModal();
  } catch (err) {
    window.showToast("Update failed: " + err.message, "error");
  }
}

async function handleAvatarUpload(file) {
  if (!file) return;
  
  // Client MIME-type check
  const allowed = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
  if (!allowed.includes(file.type)) {
    window.showToast("Please upload a PNG, JPG, or WebP image", "error");
    return;
  }

  try {
    window.showToast("Uploading avatar...", "info");
    const res = await window.api.uploadAvatar(file);
    state.currentUser = res.user;
    updateNavbarProfile(res.user);
    document.getElementById("modalAvatarPreview").src = res.avatar_url;
    window.showToast("Avatar updated successfully!", "success");
  } catch (err) {
    window.showToast("Avatar upload failed: " + err.message, "error");
  }
}

async function handleDeleteAccount() {
  const confirmed = confirm("WARNING: Deleting your account will permanently wipe all connected devices, groups, and avatar files. Proceed?");
  if (!confirmed) return;

  try {
    await window.api.deleteAccount();
    window.showToast("Account deleted successfully", "info");
    closeProfileModal();
    setUnauthenticated();
  } catch (err) {
    window.showToast("Failed to delete account: " + err.message, "error");
  }
}

// --- Event Listeners Setup ---
function initEventListeners() {
  // Brand Filter Pills
  document.querySelectorAll(".brand-filter-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".brand-filter-btn").forEach(b => {
        b.classList.remove("bg-indigo-600", "text-white");
        b.classList.add("bg-slate-800", "text-slate-300");
      });
      btn.classList.remove("bg-slate-800", "text-slate-300");
      btn.classList.add("bg-indigo-600", "text-white");
      state.filterBrand = btn.dataset.brand;
      renderDevices();
    });
  });

  // Search input
  const searchInput = document.getElementById("deviceSearchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value.trim();
      renderDevices();
    });
  }

  // Auth toggle (login vs register)
  const authToggleBtn = document.getElementById("authToggleMode");
  const authSubmitBtn = document.getElementById("authSubmitBtn");
  const authFormTitle = document.getElementById("authFormTitle");
  const registerFields = document.getElementById("registerExtraFields");

  let isRegisterMode = false;

  if (authToggleBtn) {
    authToggleBtn.addEventListener("click", () => {
      isRegisterMode = !isRegisterMode;
      if (isRegisterMode) {
        authFormTitle.textContent = "Create an OmniLink Account";
        authSubmitBtn.textContent = "Sign Up";
        authToggleBtn.textContent = "Already have an account? Sign In";
        registerFields.classList.remove("hidden");
      } else {
        authFormTitle.textContent = "Sign In to OmniLink";
        authSubmitBtn.textContent = "Sign In";
        authToggleBtn.textContent = "Need an account? Create one";
        registerFields.classList.add("hidden");
      }
    });
  }

  // Auth form submit
  const authForm = document.getElementById("authForm");
  if (authForm) {
    authForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("authUsername").value.trim();
      const password = document.getElementById("authPassword").value;
      const email = document.getElementById("authEmail") ? document.getElementById("authEmail").value.trim() : "";
      const fullName = document.getElementById("authFullName") ? document.getElementById("authFullName").value.trim() : "";

      try {
        if (isRegisterMode) {
          if (!email) {
            window.showToast("Email is required for registration", "warning");
            return;
          }
          const res = await window.api.register(username, email, password, fullName);
          window.showToast("Welcome to OmniLink!", "success");
          setAuthenticatedUser(res.user);
        } else {
          const res = await window.api.login(username, password);
          window.showToast("Logged in successfully", "success");
          setAuthenticatedUser(res.user);
        }
      } catch (err) {
        window.showToast(err.message, "error");
      }
    });
  }

  // Logout button
  const logoutBtn = document.getElementById("navLogoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      window.api.setToken(null);
      setUnauthenticated();
      window.showToast("Logged out", "info");
    });
  }

  // Avatar file upload input change
  const avatarInput = document.getElementById("avatarFileInput");
  if (avatarInput) {
    avatarInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleAvatarUpload(e.target.files[0]);
      }
    });
  }

  // Global unauthorized event
  window.addEventListener("omnilink:unauthorized", () => {
    setUnauthenticated();
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
