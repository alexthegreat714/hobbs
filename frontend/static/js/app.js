/**
 * Hobbs Frontend Application
 *
 * Handles:
 * - Chat with Gemma 3 + DeepCoder reasoning
 * - Camera grid management
 * - Farm data dashboard
 */

// =============================================================================
// State
// =============================================================================

const state = {
    cameras: [],
    zones: [],
    currentZone: null,
    cameraSlots: { 1: null, 2: null, 3: null, 4: null },
    isProcessing: false
};

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
    // Check services
    await checkModelStatus();
    await checkHobbsStatus();

    // Load data
    await loadCameras();
    await loadZones();
    await loadWeather();
    await loadAlerts();

    // Start polling
    setInterval(updateStats, 30000);
    setInterval(checkModelStatus, 60000);
}

// =============================================================================
// Status Checks
// =============================================================================

async function checkModelStatus() {
    const indicator = document.getElementById('ollama-status');
    try {
        const response = await fetch('/api/models/status');
        const data = await response.json();

        if (data.ollama_available) {
            indicator.textContent = `AI: ${data.gemma_ready ? 'Gemma ' : ''}${data.deepcoder_ready ? '+ DeepCoder' : ''}`;
            indicator.className = 'status-indicator connected';
        } else {
            indicator.textContent = 'AI: Offline';
            indicator.className = 'status-indicator disconnected';
        }
    } catch (e) {
        indicator.textContent = 'AI: Error';
        indicator.className = 'status-indicator disconnected';
    }
}

async function checkHobbsStatus() {
    const indicator = document.getElementById('hobbs-status');
    try {
        const response = await fetch('/api/hobbs/status');
        const data = await response.json();

        if (data.status === 'ok') {
            indicator.textContent = `Hobbs v${data.version}`;
            indicator.className = 'status-indicator connected';
            updateStatsFromData(data);
        } else {
            indicator.textContent = 'Hobbs: Error';
            indicator.className = 'status-indicator disconnected';
        }
    } catch (e) {
        indicator.textContent = 'Hobbs: Offline';
        indicator.className = 'status-indicator disconnected';
    }
}

async function updateStats() {
    try {
        const response = await fetch('/api/hobbs/status');
        const data = await response.json();
        updateStatsFromData(data);
    } catch (e) {
        console.error('Stats update failed:', e);
    }
}

function updateStatsFromData(data) {
    document.getElementById('stat-sensors').textContent = data.sensors_today || 0;
    document.getElementById('stat-cameras').textContent = data.camera_events_today || 0;
    document.getElementById('stat-valves').textContent = data.valves_known || 0;
    document.getElementById('stat-suspicious').textContent = data.suspicious_events_today || 0;
}

// =============================================================================
// Chat Functions
// =============================================================================

function handleChatKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();

    if (!message || state.isProcessing) return;

    state.isProcessing = true;
    sendBtn.disabled = true;
    input.value = '';

    // Add user message
    addChatMessage(message, 'user');

    // Add loading indicator
    const loadingMsg = addChatMessage('Thinking', 'assistant loading');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        // Remove loading message
        loadingMsg.remove();

        if (data.ok) {
            // Add response with reasoning badge if used
            addChatMessage(data.response, 'assistant', data.reasoning_used);

            // Update reasoning panel
            if (data.reasoning_used && data.reasoning_trace) {
                updateReasoningPanel(data.reasoning_trace);
            }
        } else {
            addChatMessage(`Error: ${data.error || 'Unknown error'}`, 'assistant');
        }

    } catch (e) {
        loadingMsg.remove();
        addChatMessage(`Error: ${e.message}`, 'assistant');
    }

    state.isProcessing = false;
    sendBtn.disabled = false;
}

function addChatMessage(content, type, hadReasoning = false) {
    const container = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = `message ${type}`;

    let html = '';
    if (hadReasoning) {
        html += '<span class="reasoning-badge">Used Reasoning</span><br>';
    }
    html += `<div class="message-content">${escapeHtml(content)}</div>`;

    msg.innerHTML = html;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;

    return msg;
}

function updateReasoningPanel(trace) {
    const content = document.getElementById('reasoning-text');
    content.textContent = trace;

    // Auto-expand if new reasoning
    const panel = document.getElementById('reasoning-content');
    panel.classList.add('expanded');
    document.getElementById('reasoning-toggle').textContent = '-';
}

function toggleReasoning() {
    const content = document.getElementById('reasoning-content');
    const toggle = document.getElementById('reasoning-toggle');

    content.classList.toggle('expanded');
    toggle.textContent = content.classList.contains('expanded') ? '-' : '+';
}

// =============================================================================
// Tab Functions
// =============================================================================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tabs .tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

function switchCameraView(view) {
    document.querySelectorAll('.camera-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === view);
    });

    const grid = document.getElementById('camera-grid');
    if (view === 'single') {
        grid.style.gridTemplateColumns = '1fr';
    } else {
        grid.style.gridTemplateColumns = 'repeat(2, 1fr)';
    }
}

// =============================================================================
// Camera Functions
// =============================================================================

async function loadCameras() {
    try {
        const response = await fetch('/api/cameras');
        const data = await response.json();
        state.cameras = data.cameras || [];
        renderCameraList();
    } catch (e) {
        console.error('Failed to load cameras:', e);
    }
}

function renderCameraList() {
    const container = document.getElementById('camera-list');
    container.innerHTML = '';

    state.cameras.forEach(cam => {
        const item = document.createElement('div');
        item.className = `camera-item ${cam.enabled ? '' : 'disabled'}`;
        item.textContent = cam.name;
        item.draggable = cam.enabled;
        item.dataset.cameraId = cam.id;

        if (cam.enabled) {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('cameraId', cam.id);
            });
        }

        container.appendChild(item);
    });
}

function allowDrop(event) {
    event.preventDefault();
}

function dropCamera(event, slotNum) {
    event.preventDefault();
    const cameraId = event.dataTransfer.getData('cameraId');

    if (!cameraId) return;

    const camera = state.cameras.find(c => c.id === cameraId);
    if (!camera) return;

    // Update state
    state.cameraSlots[slotNum] = cameraId;

    // Update slot
    const slot = event.target.closest('.camera-slot');
    slot.classList.add('has-camera');
    slot.innerHTML = `
        <img src="/api/cameras/${cameraId}/snapshot" alt="${camera.name}"
             onerror="this.style.display='none'">
        <div class="camera-label">${camera.name}</div>
    `;
}

// =============================================================================
// Zone/Dashboard Functions
// =============================================================================

async function loadZones() {
    try {
        const response = await fetch('/api/farm/zones');
        const data = await response.json();
        state.zones = data.zones || [];
        renderZoneTabs();
        if (state.zones.length > 0) {
            selectZone(state.zones[0].id);
        }
    } catch (e) {
        console.error('Failed to load zones:', e);
    }
}

function renderZoneTabs() {
    const container = document.getElementById('zone-tabs');
    container.innerHTML = '';

    state.zones.forEach(zone => {
        const tab = document.createElement('button');
        tab.className = 'zone-tab';
        tab.textContent = zone.name;
        tab.dataset.zoneId = zone.id;
        tab.onclick = () => selectZone(zone.id);
        container.appendChild(tab);
    });
}

function selectZone(zoneId) {
    state.currentZone = zoneId;

    // Update tabs
    document.querySelectorAll('.zone-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.zoneId === zoneId);
    });

    // Render zone data
    const zone = state.zones.find(z => z.id === zoneId);
    if (zone) {
        renderZoneData(zone);
    }
}

function renderZoneData(zone) {
    const container = document.getElementById('zone-data');

    const moistureClass = zone.sensors.moisture < 0.2 ? 'warning' :
                          zone.sensors.moisture < 0.15 ? 'critical' : 'good';

    container.innerHTML = `
        <h3>${zone.name}</h3>
        <div class="sensor-grid">
            <div class="sensor-card">
                <div class="label">Moisture</div>
                <div class="value ${moistureClass}">${(zone.sensors.moisture * 100).toFixed(0)}%</div>
            </div>
            <div class="sensor-card">
                <div class="label">Temperature</div>
                <div class="value good">${zone.sensors.temperature}°F</div>
            </div>
            <div class="sensor-card">
                <div class="label">pH Level</div>
                <div class="value good">${zone.sensors.ph}</div>
            </div>
            <div class="sensor-card">
                <div class="label">Valve Status</div>
                <div class="value ${zone.valve_status === 'open' ? 'good' : ''}">${zone.valve_status.toUpperCase()}</div>
            </div>
        </div>
    `;
}

// =============================================================================
// Weather Functions
// =============================================================================

async function loadWeather() {
    try {
        const response = await fetch('/api/farm/weather');
        const data = await response.json();
        renderWeather(data);
    } catch (e) {
        console.error('Failed to load weather:', e);
    }
}

function renderWeather(data) {
    const container = document.getElementById('weather-data');

    if (data.current) {
        container.innerHTML = `
            <div><strong>${data.current.temperature}°F</strong> - ${data.current.condition}</div>
            <div>Humidity: ${data.current.humidity}%</div>
        `;
    } else {
        container.textContent = 'Weather data unavailable';
    }
}

// =============================================================================
// Alerts Functions
// =============================================================================

async function loadAlerts() {
    try {
        const response = await fetch('/api/farm/alerts');
        const data = await response.json();
        renderAlerts(data.alerts || []);
    } catch (e) {
        console.error('Failed to load alerts:', e);
    }
}

function renderAlerts(alerts) {
    const container = document.getElementById('alerts-list');

    if (alerts.length === 0) {
        container.innerHTML = '<div class="alert-item"><div class="alert-message">No active alerts</div></div>';
        return;
    }

    container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.severity === 'critical' ? 'critical' : ''}">
            <div class="alert-header">
                <span class="alert-type">${alert.type}</span>
                <span class="alert-time">${formatTime(alert.timestamp)}</span>
            </div>
            <div class="alert-message">${alert.message}</div>
        </div>
    `).join('');
}

// =============================================================================
// Utility Functions
// =============================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}
