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
    document.getElementById('authScreen').classList.remove('hidden');
    document.getElementById('portalScreen').classList.add('hidden');
}

function showPortalScreen() {
    document.getElementById('authScreen').classList.add('hidden');
    document.getElementById('portalScreen').classList.remove('hidden');
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
        showToast(`Đăng nhập thành công: ${data.full_name}`, 'success');
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

    if (isAdmin) {
        document.getElementById('navAdminTabs').classList.remove('hidden');
        document.getElementById('navAdminTabs').classList.add('flex');
        document.getElementById('navClientTabs').classList.add('hidden');
        document.getElementById('navClientTabs').classList.remove('flex');
        switchAdminTab('admin-users');
    } else {
        document.getElementById('navClientTabs').classList.remove('hidden');
        document.getElementById('navClientTabs').classList.add('flex');
        document.getElementById('navAdminTabs').classList.add('hidden');
        document.getElementById('navAdminTabs').classList.remove('flex');
        
        document.getElementById('clientDashboardTitle').textContent = `📊 Báo Cáo Doanh Số & P&L - ${user.tenant_name}`;
        switchClientTab('client-analytics');
    }
}

// ==================== ADMIN TAB SWITCHER ====================
function switchAdminTab(tabId) {
    document.querySelectorAll('.admin-view').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.client-view').forEach(el => el.classList.add('hidden'));

    document.querySelectorAll('.tab-btn-admin').forEach(btn => {
        btn.classList.remove('bg-white', 'text-dg-dark', 'shadow-sm');
        btn.classList.add('text-slate-600');
    });

    const targetView = document.getElementById(`view-${tabId}`);
    if (targetView) targetView.classList.remove('hidden');

    const btnId = tabId === 'admin-users' ? 'btnAdminTabUsers' : tabId === 'admin-pipelines' ? 'btnAdminTabPipelines' : 'btnAdminTabQuality';
    const activeBtn = document.getElementById(btnId);
    if (activeBtn) {
        activeBtn.classList.add('bg-white', 'text-dg-dark', 'shadow-sm');
        activeBtn.classList.remove('text-slate-600');
    }

    if (tabId === 'admin-users') fetchUsersList();
    if (tabId === 'admin-pipelines') fetchAuditLogs();
}

// ==================== CLIENT TAB SWITCHER ====================
function switchClientTab(tabId) {
    document.querySelectorAll('.admin-view').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.client-view').forEach(el => el.classList.add('hidden'));

    document.querySelectorAll('.tab-btn-client').forEach(btn => {
        btn.classList.remove('bg-white', 'text-dg-dark', 'shadow-sm');
        btn.classList.add('text-slate-600');
    });

    const targetView = document.getElementById(`view-${tabId}`);
    if (targetView) targetView.classList.remove('hidden');

    const btnId = tabId === 'client-analytics' ? 'btnClientTabAnalytics' : tabId === 'client-scd2' ? 'btnClientTabScd2' : 'btnClientTabHealth';
    const activeBtn = document.getElementById(btnId);
    if (activeBtn) {
        activeBtn.classList.add('bg-white', 'text-dg-dark', 'shadow-sm');
        activeBtn.classList.remove('text-slate-600');
    }

    if (tabId === 'client-analytics') {
        loadKpis();
        loadRevenueChart();
        loadOrderStatusChart();
    }
    if (tabId === 'client-scd2') fetchScdData();
}

async function fetchWithAuth(endpoint) {
    return fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${appState.token}`,
            'Content-Type': 'application/json'
        }
    });
}

// ==================== CLIENT: ANALYTICS (P&L) ====================
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
                        backgroundColor: 'rgba(2, 132, 199, 0.08)',
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
                    legend: { labels: { color: '#0e3a40', font: { family: 'Plus Jakarta Sans', weight: '600' } } }
                },
                scales: {
                    x: { grid: { color: 'rgba(14, 58, 64, 0.05)' }, ticks: { color: '#64748b' } },
                    y: {
                        position: 'left',
                        grid: { color: 'rgba(14, 58, 64, 0.05)' },
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
                    legend: { position: 'bottom', labels: { color: '#0e3a40', boxWidth: 12, font: { family: 'Plus Jakarta Sans', weight: '600' } } }
                },
                cutout: '70%'
            }
        });
    } catch (e) {
        console.error(e);
    }
}

// ==================== CLIENT: SCD TYPE 2 EXPLORER ====================
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
                ? '<span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 font-bold text-xs">🟢 Đang Áp Dụng (Active)</span>' 
                : '<span class="px-2.5 py-1 rounded-md bg-sky-50 text-sky-700 font-bold text-xs">🟡 Lịch Sử Cũ (Updated)</span>';
            
            if (r.order_id === 'ORD_DEMO_222' && !r.is_current) {
                statusBadge = '<span class="px-2.5 py-1 rounded-md bg-rose-50 text-rose-700 font-bold text-xs">🔴 Đã Bị Xóa (Hard-Deleted)</span>';
            }

            return `
                <tr class="hover:bg-slate-50 transition-colors">
                    <td class="py-3.5 px-4 font-mono text-xs text-teal-700">${r.dbt_scd_id}</td>
                    <td class="py-3.5 px-4 font-bold text-dg-dark">${r.order_id}</td>
                    <td class="py-3.5 px-4 text-slate-600">${r.customer_id}</td>
                    <td class="py-3.5 px-4"><span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs font-semibold">${r.order_status}</span></td>
                    <td class="py-3.5 px-4 font-mono text-xs text-slate-500">${r.dbt_valid_from}</td>
                    <td class="py-3.5 px-4 font-mono text-xs text-slate-500">${r.dbt_valid_to || 'NULL (Current)'}</td>
                    <td class="py-3.5 px-4">${statusBadge}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error(e);
    }
}

// ==================== ADMIN: USER & TENANT MANAGER ====================
async function fetchUsersList() {
    try {
        const res = await fetchWithAuth('/users');
        if (!res.ok) return;
        const users = await res.json();

        // Update counts
        const tenantSet = new Set(users.map(u => u.tenant_slug));
        document.getElementById('valTotalTenants').textContent = `${tenantSet.size} Doanh Nghiệp`;

        const tbody = document.getElementById('tbodyUsersList');
        tbody.innerHTML = users.map(u => `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="py-3.5 px-4 font-bold text-dg-dark">${u.full_name}</td>
                <td class="py-3.5 px-4 font-mono text-xs text-slate-600">${u.email}</td>
                <td class="py-3.5 px-4">
                    <div class="font-bold text-dg-dark">${u.tenant_name}</div>
                    <div class="text-[11px] text-slate-400 font-mono">${u.tenant_slug}</div>
                </td>
                <td class="py-3.5 px-4">
                    <span class="px-2.5 py-1 rounded-md bg-teal-50 text-teal-800 text-xs font-bold uppercase">${u.tenant_plan}</span>
                </td>
                <td class="py-3.5 px-4 text-xs font-semibold text-slate-700">
                    ${u.role === 'platform_admin' ? '👑 Platform Admin' : '🏢 Client Owner'}
                </td>
                <td class="py-3.5 px-4">
                    ${u.is_active 
                        ? '<span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold">● Hoạt Động</span>' 
                        : '<span class="px-2.5 py-1 rounded-md bg-rose-50 text-rose-700 text-xs font-bold">● Bị Khóa</span>'}
                </td>
                <td class="py-3.5 px-4">
                    <div class="flex items-center gap-2">
                        <button onclick="toggleUserStatus('${u.id}', ${u.is_active})" class="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-100">
                            ${u.is_active ? 'Khóa' : 'Mở Khóa'}
                        </button>
                        <button onclick="deleteUserAccount('${u.id}')" class="px-2.5 py-1 rounded-lg border border-rose-200 text-xs font-semibold text-rose-600 hover:bg-rose-50">
                            Xóa
                        </button>
                    </div>
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

// ==================== ADMIN: AUDIT LOGS ====================
async function fetchAuditLogs() {
    try {
        const res = await fetchWithAuth('/explorer/audit-logs');
        if (!res.ok) return;
        const rows = await res.json();

        const tbody = document.getElementById('tbodyAuditLogs');
        tbody.innerHTML = rows.map(r => `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="py-3.5 px-4 font-mono text-xs text-teal-700">${r.run_id}</td>
                <td class="py-3.5 px-4 font-bold text-dg-dark">${r.connector_name}</td>
                <td class="py-3.5 px-4"><span class="px-2 py-0.5 rounded bg-teal-50 text-teal-800 text-xs font-semibold">${r.run_mode}</span></td>
                <td class="py-3.5 px-4"><span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold">✓ ${r.status}</span></td>
                <td class="py-3.5 px-4 font-semibold text-slate-700">${r.records_extracted.toLocaleString()} dòng</td>
                <td class="py-3.5 px-4 text-slate-500">${r.duration_sec}s</td>
                <td class="py-3.5 px-4 font-mono text-xs text-slate-500">${r.executed_at}</td>
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
        await fetchAuditLogs();
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
