// ==============================================================================
// DASHGROW CLIENT PORTAL - FRONTEND JAVASCRIPT LOGIC
// ==============================================================================

const API_BASE = '/api/v1';

// Global App State
let appState = {
    token: null,
    user: null,
    currentRole: 'client_owner', // 'platform_admin' or 'client_owner'
    revenueChartInstance: null,
    statusChartInstance: null
};

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize Demo Authentication (Default to SMB Client)
    await switchDemoAccount('client');
});

// ==================== AUTHENTICATION & SWITCHER ====================
async function switchDemoAccount(roleType) {
    const creds = roleType === 'admin' 
        ? { email: 'admin@dashgrow.io', password: 'admin123' }
        : { email: 'owner@olist-store.vn', password: 'client123' };

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(creds)
        });

        if (!res.ok) throw new Error('Login failed');

        const data = await res.json();
        appState.token = data.access_token;
        appState.user = data;
        appState.currentRole = data.role;

        // Update UI
        updateUserHeaderUI(data);
        updateRoleViewRestrictions(data.role);

        // Fetch Data for Active View
        await loadAllDashboardData();

        showToast(`Đã chuyển chế độ: ${data.role === 'platform_admin' ? '👑 DashGrow Admin (Bên Bán)' : '🏢 Doanh Nghiệp SMB (Bên Mua)'}`);
    } catch (err) {
        console.error('Error switching demo account:', err);
        showToast('Không thể đăng nhập tài khoản demo.', 'error');
    }
}

function updateUserHeaderUI(user) {
    document.getElementById('userNameDisplay').textContent = user.full_name;
    document.getElementById('tenantNameDisplay').textContent = user.tenant_name;
    document.getElementById('userRoleBadge').textContent = user.role === 'platform_admin' ? 'Platform Super Admin' : 'Chủ Doanh Nghiệp (Owner)';
    document.getElementById('userAvatar').textContent = user.full_name.split(' ').map(n => n[0]).slice(0, 2).join('');

    // Toggle button active classes
    if (user.role === 'platform_admin') {
        document.getElementById('btnSwitchAdmin').classList.add('active');
        document.getElementById('btnSwitchClient').classList.remove('active');
    } else {
        document.getElementById('btnSwitchClient').classList.add('active');
        document.getElementById('btnSwitchAdmin').classList.remove('active');
    }
}

function updateRoleViewRestrictions(role) {
    const adminTab = document.getElementById('tabBtnPipelines');
    if (role === 'platform_admin') {
        adminTab.style.display = 'flex';
    } else {
        adminTab.style.display = 'none';
        // If currently on pipeline tab, switch to analytics
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab && activeTab.id === 'tab-pipelines') {
            switchTab('analytics');
        }
    }
}

// ==================== TAB SWITCHING ====================
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

    const targetContent = document.getElementById(`tab-${tabId}`);
    if (targetContent) targetContent.classList.add('active');

    // Find tab button
    const btns = document.querySelectorAll('.tab-btn');
    btns.forEach(btn => {
        if (btn.getAttribute('onclick').includes(tabId)) {
            btn.classList.add('active');
        }
    });

    if (tabId === 'scd2') loadScd2Data();
    if (tabId === 'pipelines') loadAuditLogs();
}

// ==================== DATA FETCHING ====================
async function loadAllDashboardData() {
    await Promise.all([
        loadKpis(),
        loadRevenueChart(),
        loadOrderStatusChart(),
        loadCryptoMarket(),
        loadScd2Data()
    ]);
}

async function fetchWithAuth(endpoint) {
    return fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${appState.token}`,
            'Content-Type': 'application/json'
        }
    });
}

// 1. KPIs
async function loadKpis() {
    try {
        const res = await fetchWithAuth('/analytics/kpis');
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('kpiRevenue').textContent = `$${Number(data.total_revenue).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
        document.getElementById('kpiOrders').textContent = Number(data.total_orders).toLocaleString('en-US');
        document.getElementById('kpiAOV').textContent = `$${Number(data.aov).toFixed(2)}`;
        document.getElementById('kpiDeliveryRate').textContent = `${data.delivery_success_rate}%`;
    } catch (e) {
        console.error('Failed to load KPIs:', e);
    }
}

// 2. Revenue Trend Chart (Chart.js)
async function loadRevenueChart() {
    try {
        const res = await fetchWithAuth('/analytics/revenue-trend');
        if (!res.ok) return;
        const data = await res.json();

        const ctx = document.getElementById('revenueTrendChart').getContext('2d');
        if (appState.revenueChartInstance) {
            appState.revenueChartInstance.destroy();
        }

        appState.revenueChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Doanh Thu ($)',
                        data: data.revenue,
                        borderColor: '#0284c7',
                        backgroundColor: 'rgba(2, 132, 199, 0.15)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.35,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Số Lượng Đơn',
                        data: data.orders,
                        borderColor: '#0d9488',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.35,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } }
                },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#64748b', callback: v => `$${v.toLocaleString()}` }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#0d9488' }
                    }
                }
            }
        });
    } catch (e) {
        console.error('Failed to render revenue chart:', e);
    }
}

// 3. Order Status Donut Chart
async function loadOrderStatusChart() {
    try {
        const res = await fetchWithAuth('/analytics/order-status');
        if (!res.ok) return;
        const data = await res.json();

        const ctx = document.getElementById('orderStatusChart').getContext('2d');
        if (appState.statusChartInstance) {
            appState.statusChartInstance.destroy();
        }

        appState.statusChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: ['#10b981', '#0284c7', '#f59e0b', '#8b5cf6', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12 } }
                },
                cutout: '70%'
            }
        });
    } catch (e) {
        console.error('Failed to render status chart:', e);
    }
}

// 4. Crypto Market List
async function loadCryptoMarket() {
    try {
        const res = await fetchWithAuth('/analytics/crypto-market');
        if (!res.ok) return;
        const items = await res.json();

        const container = document.getElementById('cryptoListContainer');
        container.innerHTML = items.map(c => `
            <div class="crypto-item">
                <div class="crypto-name-col">
                    <span class="crypto-symbol-badge">${c.symbol}</span>
                    <span style="font-weight: 500;">${c.name}</span>
                </div>
                <div style="text-align: right;">
                    <div class="crypto-price">$${Number(c.price).toLocaleString()}</div>
                    <div class="${c.change_24h >= 0 ? 'crypto-change-pos' : 'crypto-change-neg'}">
                        ${c.change_24h >= 0 ? '▲ +' : '▼ '}${c.change_24h}%
                    </div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load crypto data:', e);
    }
}

// ==================== SCD TYPE 2 EXPLORER ====================
async function loadScd2Data() {
    const q = document.getElementById('scd2SearchInput')?.value || '';
    try {
        const endpoint = q ? `/explorer/scd2/orders?query=${encodeURIComponent(q)}` : '/explorer/scd2/orders';
        const res = await fetchWithAuth(endpoint);
        if (!res.ok) return;
        const rows = await res.json();

        const tbody = document.getElementById('scd2TableBody');
        tbody.innerHTML = rows.map(r => {
            let statusTag = r.is_current 
                ? '<span class="tag-success">🟢 Đang Áp Dụng (Active)</span>' 
                : '<span class="tag-primary">🟡 Lịch Sử Cũ (Updated)</span>';
            
            if (r.order_id === 'ORD_DEMO_222' && !r.is_current) {
                statusTag = '<span class="tag-deleted">🔴 Đã Bị Xóa (Hard-Deleted)</span>';
            }

            return `
                <tr>
                    <td><code>${r.dbt_scd_id}</code></td>
                    <td><strong>${r.order_id}</strong></td>
                    <td>${r.customer_id}</td>
                    <td><span class="tag-primary">${r.order_status}</span></td>
                    <td><code>${r.dbt_valid_from}</code></td>
                    <td><code>${r.dbt_valid_to || 'NULL (Current)'}</code></td>
                    <td>${statusTag}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error('Failed to load SCD 2 data:', e);
    }
}

function handleScdSearch(e) {
    if (e.key === 'Enter') loadScd2Data();
}

// ==================== AUDIT LOGS ====================
async function loadAuditLogs() {
    try {
        const res = await fetchWithAuth('/explorer/audit-logs');
        if (!res.ok) return;
        const rows = await res.json();

        const tbody = document.getElementById('auditLogsBody');
        tbody.innerHTML = rows.map(r => `
            <tr>
                <td><code>${r.run_id}</code></td>
                <td><strong>${r.connector_name}</strong></td>
                <td><span class="badge-conn">${r.run_mode}</span></td>
                <td><span class="tag-success">✓ ${r.status}</span></td>
                <td>${r.records_extracted.toLocaleString()} dòng</td>
                <td>${r.duration_sec}s</td>
                <td><code>${r.executed_at}</code></td>
            </tr>
        `).join('');
    } catch (e) {
        console.error('Failed to load audit logs:', e);
    }
}

// ==================== TRIGGER PIPELINE MODAL ====================
function openTriggerModal() {
    document.getElementById('triggerModal').classList.add('active');
}

function closeTriggerModal() {
    document.getElementById('triggerModal').classList.remove('active');
}

async function executeTriggerPipeline() {
    const connector = document.getElementById('modalConnectorSelect').value;
    const fullRefresh = document.getElementById('modalFullRefreshCheckbox').checked;

    const logBox = document.getElementById('modalLogBox');
    const logContent = document.getElementById('modalLogContent');
    const btn = document.getElementById('btnExecuteTrigger');

    logBox.style.display = 'block';
    logContent.textContent = `[Init] Requesting trigger for connector: ${connector} (Full Refresh: ${fullRefresh})...\n`;
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/pipelines/trigger`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${appState.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ connector, full_refresh: fullRefresh })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Trigger failed');
        }

        showToast('Pipeline đã được kích hoạt chạy ngầm!', 'success');
        
        // Poll status for 10 seconds
        let polls = 0;
        const interval = setInterval(async () => {
            polls++;
            const statusRes = await fetchWithAuth('/pipelines/status');
            if (statusRes.ok) {
                const s = await statusRes.json();
                if (s.logs && s.logs.length > 0) {
                    logContent.textContent = s.logs.join('\n');
                    logBox.scrollTop = logBox.scrollHeight;
                }
                if (!s.is_running || polls > 20) {
                    clearInterval(interval);
                    btn.disabled = false;
                    loadAuditLogs();
                }
            }
        }, 1500);

    } catch (e) {
        logContent.textContent += `\n[ERROR] ${e.message}`;
        btn.disabled = false;
        showToast(e.message, 'error');
    }
}

// ==================== TOAST HELPER ====================
function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
