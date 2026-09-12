/**
 * OmniLink Unified API Client
 */
const API_BASE = "";

class OmniLinkAPI {
  constructor() {
    this.token = localStorage.getItem("omnilink_token") || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem("omnilink_token", token);
    } else {
      localStorage.removeItem("omnilink_token");
    }
  }

  getHeaders(isJson = true) {
    const headers = {};
    if (isJson) {
      headers["Content-Type"] = "application/json";
    }
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const isFormData = options.body instanceof FormData;
    const headers = this.getHeaders(!isFormData);
    
    const config = {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, config);
      
      if (response.status === 401) {
        // Token expired or invalid
        this.setToken(null);
        window.dispatchEvent(new CustomEvent("omnilink:unauthorized"));
        throw new Error("Session expired. Please log in again.");
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.message || "An error occurred");
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  }

  // --- Auth & Users ---
  async login(username, password) {
    const data = await this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
    this.setToken(data.access_token);
    return data;
  }

  async register(username, email, password, full_name = "") {
    const data = await this.request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password, full_name })
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe() {
    return this.request("/api/auth/me");
  }

  async updateProfile(updates) {
    return this.request("/api/users/profile", {
      method: "PUT",
      body: JSON.stringify(updates)
    });
  }

  async uploadAvatar(file) {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("/api/users/avatar", {
      method: "POST",
      body: formData
    });
  }

  async deleteAccount() {
    const res = await this.request("/api/users/account", { method: "DELETE" });
    this.setToken(null);
    return res;
  }

  // --- IoT Devices & Scanner ---
  async scanDevices(options = {}) {
    let url = "/api/iot/scan";
    if (typeof options === "boolean") {
      url += `?force_simulation=${options}`;
    } else if (typeof options === "object") {
      const params = new URLSearchParams();
      if (options.disableSimulation) {
        params.append("disable_simulation", "true");
      } else if (options.forceSimulation !== undefined) {
        params.append("force_simulation", String(options.forceSimulation));
      }
      const qs = params.toString();
      if (qs) url += `?${qs}`;
    }
    return this.request(url);
  }

  async getSimulationMode() {
    return this.request("/api/iot/simulation");
  }

  async setSimulationMode(simulationMode) {
    return this.request("/api/iot/simulation", {
      method: "POST",
      body: JSON.stringify({ simulation_mode: simulationMode })
    });
  }

  async getDevices() {
    return this.request("/api/iot/devices");
  }

  async addDevice(devicePayload) {
    return this.request("/api/iot/devices", {
      method: "POST",
      body: JSON.stringify(devicePayload)
    });
  }

  async updateDevice(id, data) {
    return this.request(`/api/iot/devices/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  }

  async deleteDevice(id) {
    return this.request(`/api/iot/devices/${id}`, {
      method: "DELETE"
    });
  }

  async controlDevice(id, action, parameter = "level", value = null) {
    return this.request(`/api/iot/devices/${id}/control`, {
      method: "POST",
      body: JSON.stringify({ action, parameter, value })
    });
  }

  async syncDevice(id) {
    return this.request(`/api/iot/devices/${id}/sync`, {
      method: "POST"
    });
  }

  // --- Groups & Orchestration ---
  async getGroups() {
    return this.request("/api/groups");
  }

  async createGroup(name, description = "", deviceIds = []) {
    return this.request("/api/groups", {
      method: "POST",
      body: JSON.stringify({ name, description, device_ids: deviceIds })
    });
  }

  async updateGroup(id, name, description) {
    return this.request(`/api/groups/${id}`, {
      method: "PUT",
      body: JSON.stringify({ name, description })
    });
  }

  async deleteGroup(id) {
    return this.request(`/api/groups/${id}`, {
      method: "DELETE"
    });
  }

  async assignGroupDevices(groupId, deviceIds) {
    return this.request(`/api/groups/${groupId}/devices`, {
      method: "PUT",
      body: JSON.stringify({ device_ids: deviceIds })
    });
  }

  async batchControlGroup(groupId, action, parameter = "level", value = 50) {
    return this.request(`/api/groups/${groupId}/batch-control`, {
      method: "POST",
      body: JSON.stringify({ action, parameter, value })
    });
  }
}

window.api = new OmniLinkAPI();

// Toast helper function
window.showToast = function(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  const colors = {
    success: "border-emerald-500/50 bg-emerald-950/80 text-emerald-200",
    error: "border-rose-500/50 bg-rose-950/80 text-rose-200",
    info: "border-indigo-500/50 bg-indigo-950/80 text-indigo-200",
    warning: "border-amber-500/50 bg-amber-950/80 text-amber-200"
  };

  toast.className = `flex items-center gap-3 p-4 rounded-xl border backdrop-blur-md shadow-2xl toast-slide-in text-sm font-medium ${colors[type] || colors.info}`;
  toast.innerHTML = `
    <span class="flex-1">${message}</span>
    <button class="text-xs opacity-70 hover:opacity-100 transition-opacity" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};
