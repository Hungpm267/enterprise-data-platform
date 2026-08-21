// ==============================================================================
// DASHGROW CLIENT PORTAL - FULL AUTHENTICATION & MULTI-TENANT LOGIC
// ==============================================================================

const API_BASE = '/api/v1';

let appState = {
    token: localStorage.getItem('dg_token') || null,
    currentUser: null,
    clientDashboards: [],
    activeDashboardIndex: 0
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
        switchClientTab('client-looker');
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

    const btnId = tabId === 'client-looker' ? 'btnClientTabLooker' : tabId === 'client-scd2' ? 'btnClientTabScd2' : 'btnClientTabHealth';
    const activeBtn = document.getElementById(btnId);
    if (activeBtn) {
        activeBtn.classList.add('bg-white', 'text-dg-dark', 'shadow-sm');
        activeBtn.classList.remove('text-slate-600');
    }

    if (tabId === 'client-looker') loadClientLookerDashboards();
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

// ==================== CLIENT: LOOKER STUDIO EMBED ====================
async function loadClientLookerDashboards() {
    try {
        const res = await fetchWithAuth('/looker/my-dashboards');
        if (!res.ok) return;
        const dashboards = await res.json();
        appState.clientDashboards = dashboards;

        const selectorBar = document.getElementById('lookerDashboardSelectorBar');
        const iframe = document.getElementById('lookerEmbedIframe');
        const fallback = document.getElementById('lookerFallbackNotice');

        if (!dashboards || dashboards.length === 0) {
            fallback.classList.remove('hidden');
            iframe.src = 'about:blank';
            selectorBar.innerHTML = '';
            return;
        }

        fallback.classList.add('hidden');
        selectorBar.innerHTML = dashboards.map((d, idx) => `
            <button onclick="selectLookerDashboard(${idx})" id="btnLookerDash${idx}" class="px-4 py-2 rounded-xl text-xs font-bold transition-all ${idx === 0 ? 'bg-teal-600 text-white shadow-md' : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'}">
                📊 ${d.title} (${d.category})
            </button>
        `).join('');

        selectLookerDashboard(0);
    } catch (e) {
        console.error('Failed to load Looker dashboards:', e);
    }
}

function selectLookerDashboard(index) {
    if (!appState.clientDashboards || !appState.clientDashboards[index]) return;
    appState.activeDashboardIndex = index;
    const dash = appState.clientDashboards[index];

    // Toggle button active classes
    appState.clientDashboards.forEach((_, idx) => {
        const btn = document.getElementById(`btnLookerDash${idx}`);
        if (btn) {
            if (idx === index) {
                btn.className = 'px-4 py-2 rounded-xl text-xs font-bold transition-all bg-teal-600 text-white shadow-md';
            } else {
                btn.className = 'px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white text-slate-700 border border-slate-200 hover:bg-slate-50';
            }
        }
    });

    const iframe = document.getElementById('lookerEmbedIframe');
    iframe.src = dash.embed_url;
}

function reloadLookerIframe() {
    const iframe = document.getElementById('lookerEmbedIframe');
    if (iframe.src && iframe.src !== 'about:blank') {
        const currentSrc = iframe.src;
        iframe.src = 'about:blank';
        setTimeout(() => { iframe.src = currentSrc; }, 200);
        showToast('Đang làm mới báo cáo Looker Studio...');
    }
}

function toggleFullscreenLooker() {
    const container = document.getElementById('lookerIframeContainer');
    if (!document.fullscreenElement) {
        container.requestFullscreen().catch(err => {
            alert(`Lỗi mở toàn màn hình: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
}

function applyCustomLookerUrl() {
    const url = document.getElementById('customLookerInput').value.trim();
    if (!url) return;
    document.getElementById('lookerFallbackNotice').classList.add('hidden');
    document.getElementById('lookerEmbedIframe').src = url;
    showToast('Đã tải báo cáo Looker Studio!', 'success');
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

// ==================== ADMIN: USER & TENANT MANAGER (AIVEN DB) ====================
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
                <td class="py-3.5 px-4">
                    ${u.is_active 
                        ? '<span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold">● Hoạt Động</span>' 
                        : '<span class="px-2.5 py-1 rounded-md bg-rose-50 text-rose-700 text-xs font-bold">● Bị Khóa</span>'}
                </td>
                <td class="py-3.5 px-4">
                    ${u.tenant_id ? `
                        <button onclick="openAssignLookerModal('${u.tenant_id}', '${u.tenant_name}')" class="px-3 py-1.5 rounded-lg border border-teal-200 bg-teal-50 text-teal-800 text-xs font-bold hover:bg-teal-100 flex items-center gap-1">
                            🔗 Gán Looker URL
                        </button>
                    ` : '<span class="text-xs text-slate-400">DashGrow HQ</span>'}
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
        showToast(`Đã lưu khách hàng mới lên Aiven.io: ${payload.company_name}`, 'success');
        await fetchUsersList();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== ADMIN: ASSIGN LOOKER URL ====================
function openAssignLookerModal(tenantId, tenantName) {
    document.getElementById('assignLookerTenantId').value = tenantId;
    document.getElementById('assignLookerTitle').value = `Báo Cáo Doanh Thu P&L - ${tenantName}`;
    document.getElementById('modalAssignLooker').classList.add('active');
}

function closeAssignLookerModal() {
    document.getElementById('modalAssignLooker').classList.remove('active');
}

async function handleAssignLookerSubmit(e) {
    e.preventDefault();
    const tenantId = document.getElementById('assignLookerTenantId').value;
    const payload = {
        title: document.getElementById('assignLookerTitle').value,
        category: document.getElementById('assignLookerCategory').value,
        embed_url: document.getElementById('assignLookerUrl').value,
        is_default: document.getElementById('assignLookerDefault').checked,
        sort_order: 1
    };

    try {
        const res = await fetch(`${API_BASE}/looker/tenants/${tenantId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${appState.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Không thể gán Looker URL.');
        }

        closeAssignLookerModal();
        showToast('Đã lưu cấu hình Looker Studio lên Aiven PostgreSQL!', 'success');
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

        showToast('Đã cập nhật trạng thái người dùng trên Aiven.', 'success');
        await fetchUsersList();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteUserAccount(userId) {
    if (!confirm('Bạn có chắc chắn muốn xóa vĩnh viễn tài khoản này khỏi Aiven?')) return;
    try {
        const res = await fetch(`${API_BASE}/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${appState.token}` }
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Lỗi xóa tài khoản');
        }

        showToast('Đã xóa tài khoản thành công trên Aiven.', 'success');
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
