// ==============================================================================
// DASHGROW CLIENT PORTAL - FULL AUTHENTICATION & MULTI-TENANT LOGIC
// ==============================================================================

const API_BASE = '/api/v1';

let appState = {
    token: localStorage.getItem('dg_token') || null,
    currentUser: null,
    chartRevenueInstance: null,
    chartStatusInstance: null
};

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async () => {
    if (appState.token) {
        await verifyAndLoadUserSession();
    } else {
        showAuthScreen();
    }
});

function showAuthScreen() {
    document.getElementById('authScreen').style.display = 'flex';
    document.getElementById('portalScreen').classList.remove('active');
}

function showPortalScreen() {
    document.getElementById('authScreen').style.display = 'none';
    document.getElementById('portalScreen').classList.add('active');
    lucide.createIcons();
}

// ==================== AUTHENTICATION FLOW ====================
async function handleLoginSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    await loginUser(email, password);
}

function quickFillLogin(email, pass) {
    document.getElementById('loginEmail').value = email;
    document.getElementById('loginPassword').value = pass;
    loginUser(email, pass);
}

async function loginUser(email, password) {
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Email hoặc mật khẩu không chính xác.');
        }

        const data = await res.json();
        appState.token = data.access_token;
        appState.currentUser = data;
        localStorage.setItem('dg_token', data.access_token);

        setupPortalForUser(data);
        showPortalScreen();
        await loadActiveTabContent();
        showToast(`Đăng nhập thành công: ${data.full_name} (${data.tenant_name})`, 'success');
    } catch (err) {
        console.error('Login error:', err);
        showToast(err.message, 'error');
    }
}

async function verifyAndLoadUserSession() {
    try {
        const res = await fetch(`${API_BASE}/auth/me`, {
            headers: { 'Authorization': `Bearer ${appState.token}` }
        });

        if (!res.ok) throw new Error('Session expired');

        const user = await res.json();
        appState.currentUser = user;
        setupPortalForUser(user);
        showPortalScreen();
        await loadActiveTabContent();
    } catch (e) {
        handleLogout();
    }
}

function handleLogout() {
    appState.token = null;
    appState.currentUser = null;
    localStorage.removeItem('dg_token');
    showAuthScreen();
    showToast('Đã đăng xuất khỏi tài khoản.');
}

function setupPortalForUser(user) {
    document.getElementById('headerUserName').textContent = user.full_name;
    document.getElementById('headerTenantName').textContent = user.tenant_name;
    document.getElementById('headerUserAvatar').textContent = user.full_name.split(' ').map(n => n[0]).slice(0, 2).join('');

    const isAdmin = user.role === 'platform_admin';
    document.getElementById('headerUserRole').textContent = isAdmin ? '👑 Platform Super Admin' : '🏢 Khách Hàng (Client Owner)';

    // Role-based Tab Visibility
    document.querySelectorAll('.admin-view-only').forEach(el => {
        el.style.display = isAdmin ? 'flex' : 'none';
    });

    // Custom Header titles
    if (isAdmin) {
        document.getElementById('analyticsHeaderTitle').textContent = '📊 Bảng Điều Hành Toàn Sàn (DashGrow Super Admin)';
        document.getElementById('analyticsHeaderSubtitle').textContent = 'Tổng hợp số liệu toàn bộ các doanh nghiệp khách hàng trên Data Marts';
    } else {
        document.getElementById('analyticsHeaderTitle').textContent = `📊 Báo Cáo Doanh Số & P&L - ${user.tenant_name}`;
        document.getElementById('analyticsHeaderSubtitle').textContent = 'Dữ liệu kinh doanh thời gian thực dành riêng cho doanh nghiệp của bạn';
    }
}

// ==================== TAB NAVIGATION ====================
function switchPortalTab(tabId) {
    document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

    const targetView = document.getElementById(`view-${tabId}`);
    if (targetView) targetView.classList.add('active');

    const targetBtn = document.getElementById(`tabNav${tabId.charAt(0).toUpperCase() + tabId.slice(1)}`);
    if (targetBtn) targetBtn.classList.add('active');

    loadActiveTabContent(tabId);
}

async function loadActiveTabContent(specificTab = null) {
    const activeTab = specificTab || document.querySelector('.tab-view.active')?.id.replace('view-', '') || 'analytics';

    if (activeTab === 'analytics') {
        await Promise.all([loadKpis(), loadRevenueChart(), loadOrderStatusChart()]);
    } else if (activeTab === 'scd2') {
        await fetchScdData();
    } else if (activeTab === 'users') {
        await fetchUsersList();
    } else if (activeTab === 'pipelines') {
        await fetchAuditLogs();
    }
}

async function fetchWithAuth(endpoint) {
    return fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${appState.token}`,
            'Content-Type': 'application/json'
        }
    });
}

// ==================== TAB 1: ANALYTICS ====================
async function loadKpis() {
    try {
        const res = await fetchWithAuth('/analytics/kpis');
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('valRevenue').textContent = `$${Number(data.total_revenue).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
        document.getElementById('valOrders').textContent = Number(data.total_orders).toLocaleString('en-US');
        document.getElementById('valAOV').textContent = `$${Number(data.aov).toFixed(2)}`;
        document.getElementById('valDelivery').textContent = `${data.delivery_success_rate}%`;
    } catch (e) {
        console.error(e);
    }
}

async function loadRevenueChart() {
    try {
        const res = await fetchWithAuth('/analytics/revenue-trend');
        if (!res.ok) return;
        const data = await res.json();

        const ctx = document.getElementById('canvasRevenueTrend').getContext('2d');
        if (appState.chartRevenueInstance) appState.chartRevenueInstance.destroy();

        appState.chartRevenueInstance = new Chart(ctx, {
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
                    legend: { labels: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans', weight: '600' } } }
                },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                    y: {
                        position: 'left',
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#64748b', callback: v => `$${v.toLocaleString()}` }
                    },
                    y1: {
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#0d9488' }
                    }
                }
            }
        });
    } catch (e) {
        console.error(e);
    }
}

async function loadOrderStatusChart() {
    try {
        const res = await fetchWithAuth('/analytics/order-status');
        if (!res.ok) return;
        const data = await res.json();

        const ctx = document.getElementById('canvasOrderStatus').getContext('2d');
        if (appState.chartStatusInstance) appState.chartStatusInstance.destroy();

        appState.chartStatusInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: ['#10b981', '#0284c7', '#f59e0b', '#6366f1', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12, font: { family: 'Plus Jakarta Sans' } } }
                },
                cutout: '68%'
            }
        });
    } catch (e) {
        console.error(e);
    }
}

// ==================== TAB 2: SCD TYPE 2 EXPLORER ====================
async function fetchScdData() {
    const q = document.getElementById('inputScdSearch')?.value || '';
    try {
        const endpoint = q ? `/explorer/scd2/orders?query=${encodeURIComponent(q)}` : '/explorer/scd2/orders';
        const res = await fetchWithAuth(endpoint);
        if (!res.ok) return;
        const rows = await res.json();

        const tbody = document.getElementById('tbodyScd2');
        tbody.innerHTML = rows.map(r => {
            let statusBadge = r.is_current 
                ? '<span class="badge-active">🟢 Đang Áp Dụng (Active)</span>' 
                : '<span class="badge-plan">🟡 Lịch Sử Cũ (Updated)</span>';
            
            if (r.order_id === 'ORD_DEMO_222' && !r.is_current) {
                statusBadge = '<span class="badge-locked">🔴 Đã Bị Xóa (Hard-Deleted)</span>';
            }

            return `
                <tr>
                    <td><code>${r.dbt_scd_id}</code></td>
                    <td><strong>${r.order_id}</strong></td>
                    <td>${r.customer_id}</td>
                    <td><span class="badge-plan">${r.order_status}</span></td>
                    <td><code>${r.dbt_valid_from}</code></td>
                    <td><code>${r.dbt_valid_to || 'NULL (Current)'}</code></td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error(e);
    }
}

// ==================== TAB 3: ADMIN USER & TENANT MANAGER ====================
async function fetchUsersList() {
    try {
        const res = await fetchWithAuth('/users');
        if (!res.ok) return;
        const users = await res.json();

        const tbody = document.getElementById('tbodyUsersList');
        tbody.innerHTML = users.map(u => `
            <tr>
                <td><strong>${u.full_name}</strong></td>
                <td><code>${u.email}</code></td>
                <td><span style="color: #fff; font-weight: 600;">${u.tenant_name}</span> <br><small style="color: var(--text-dim);">${u.tenant_slug}</small></td>
                <td><span class="badge-plan">${u.tenant_plan}</span></td>
                <td>${u.role === 'platform_admin' ? '👑 Platform Admin' : '🏢 Client Owner'}</td>
                <td>${u.is_active ? '<span class="badge-active">● Hoạt Động</span>' : '<span class="badge-locked">● Bị Khóa</span>'}</td>
                <td>
                    <button class="btn-action-small" onclick="toggleUserStatus('${u.id}', ${u.is_active})">
                        ${u.is_active ? 'Khóa' : 'Mở Khóa'}
                    </button>
                    <button class="btn-action-small btn-action-danger" onclick="deleteUserAccount('${u.id}')">
                        Xóa
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

function openCreateUserModal() {
    document.getElementById('modalCreateUser').classList.add('active');
}

function closeCreateUserModal() {
    document.getElementById('modalCreateUser').classList.remove('active');
}

async function handleCreateUserSubmit(e) {
    e.preventDefault();
    const payload = {
        company_name: document.getElementById('newCompanyName').value,
        company_slug: document.getElementById('newCompanySlug').value,
        plan: document.getElementById('newCompanyPlan').value,
        full_name: document.getElementById('newUserFullName').value,
        email: document.getElementById('newUserEmail').value,
        password: document.getElementById('newUserPassword').value,
        role: 'client_owner'
    };

    try {
        const res = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${appState.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Không thể tạo khách hàng.');
        }

        closeCreateUserModal();
        showToast(`Đã tạo thành công khách hàng: ${payload.company_name}`, 'success');
        await fetchUsersList();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function toggleUserStatus(userId, currentStatus) {
    try {
        const res = await fetch(`${API_BASE}/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${appState.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: !currentStatus })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Lỗi cập nhật');
        }

        showToast('Đã cập nhật trạng thái người dùng.', 'success');
        await fetchUsersList();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteUserAccount(userId) {
    if (!confirm('Bạn có chắc chắn muốn xóa vĩnh viễn tài khoản này?')) return;
    try {
        const res = await fetch(`${API_BASE}/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${appState.token}` }
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Lỗi xóa tài khoản');
        }

        showToast('Đã xóa tài khoản thành công.', 'success');
        await fetchUsersList();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== TAB 4: AUDIT LOGS & PIPELINE ====================
async function fetchAuditLogs() {
    try {
        const res = await fetchWithAuth('/explorer/audit-logs');
        if (!res.ok) return;
        const rows = await res.json();

        const tbody = document.getElementById('tbodyAuditLogs');
        tbody.innerHTML = rows.map(r => `
            <tr>
                <td><code>${r.run_id}</code></td>
                <td><strong>${r.connector_name}</strong></td>
                <td><span class="badge-plan">${r.run_mode}</span></td>
                <td><span class="badge-active">✓ ${r.status}</span></td>
                <td>${r.records_extracted.toLocaleString()} dòng</td>
                <td>${r.duration_sec}s</td>
                <td><code>${r.executed_at}</code></td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

function openPipelineModal() {
    document.getElementById('modalPipeline').classList.add('active');
}

function closePipelineModal() {
    document.getElementById('modalPipeline').classList.remove('active');
}

async function executePipelineTrigger() {
    const connector = document.getElementById('selectPipelineConn').value;
    const fullRefresh = document.getElementById('checkFullRefresh').checked;

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
            throw new Error(err.detail || 'Không thể trigger');
        }

        closePipelineModal();
        showToast(`Đã kích hoạt chạy pipeline cho ${connector} ngầm!`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== TOAST HELPER ====================
function showToast(msg, type = 'info') {
    const wrap = document.getElementById('toastWrap');
    const t = document.createElement('div');
    t.className = 'toast-msg';
    t.textContent = msg;
    wrap.appendChild(t);
    setTimeout(() => t.remove(), 4000);
}
