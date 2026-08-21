// ==============================================================================
// DASHGROW TECHNOLOGIES - CLIENT DATA PORTAL & MULTI-TENANT LOGIC (WITH PAGINATION)
// ==============================================================================

const API_BASE = '/api/v1';

let appState = {
    token: localStorage.getItem('dg_token') || null,
    currentUser: null,
    clientDashboards: [],
    activeDashboardIndex: 0,
    
    // Pagination States
    pagination: {
        users: { currentPage: 1, pageSize: 5, data: [] },
        audit: { currentPage: 1, pageSize: 5, data: [] },
        scd:   { currentPage: 1, pageSize: 5, data: [] }
    }
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
    lucide.createIcons();
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
    const btn = document.getElementById('btnLoginSubmit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span><span>Đang đăng nhập...</span>';
    }
    await loginUser(email, password);
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>Đăng Nhập Vào Hệ Thống</span><i data-lucide="arrow-right" class="w-4 h-4"></i>';
        lucide.createIcons();
    }
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

    const isAdmin = user.role === 'platform_admin';

    if (isAdmin) {
        document.getElementById('headerUserRole').textContent = 'Platform Super Admin';
        document.getElementById('navAdminTabs').classList.remove('hidden');
        document.getElementById('navAdminTabs').classList.add('flex');
        document.getElementById('navClientTabs').classList.add('hidden');
        document.getElementById('navClientTabs').classList.remove('flex');
        switchAdminTab('admin-users');
    } else {
        document.getElementById('headerUserRole').textContent = 'Khách Hàng Doanh Nghiệp';
        document.getElementById('navClientTabs').classList.remove('hidden');
        document.getElementById('navClientTabs').classList.add('flex');
        document.getElementById('navAdminTabs').classList.add('hidden');
        document.getElementById('navAdminTabs').classList.remove('flex');
        switchClientTab('client-looker');
    }
    lucide.createIcons();
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
    lucide.createIcons();
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
    lucide.createIcons();
}

async function fetchWithAuth(endpoint) {
    return fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${appState.token}`,
            'Content-Type': 'application/json'
        }
    });
}

// ==================== PAGINATION HELPER FUNCTIONS ====================
function renderPaginationControls(type, totalItems, currentPage, pageSize, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (totalItems === 0) {
        container.innerHTML = `<div>Chưa có dữ liệu nào.</div>`;
        return;
    }

    const totalPages = Math.ceil(totalItems / pageSize) || 1;
    const startItem = (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, totalItems);

    let pageButtons = '';
    for (let p = 1; p <= totalPages; p++) {
        if (p === currentPage) {
            pageButtons += `<button class="w-7 h-7 rounded-lg bg-[#0284c7] text-white font-bold text-xs shadow-sm">${p}</button>`;
        } else {
            pageButtons += `<button onclick="goToPage('${type}', ${p})" class="w-7 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold">${p}</button>`;
        }
    }

    container.innerHTML = `
        <div>
            Hiển thị <strong>${startItem}</strong> - <strong>${endItem}</strong> trong tổng số <strong>${totalItems}</strong> bản ghi
        </div>
        <div class="flex items-center gap-1.5">
            <button 
                onclick="goToPage('${type}', ${currentPage - 1})" 
                ${currentPage === 1 ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-200 text-xs text-slate-300 cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-200 text-xs text-slate-600 hover:bg-slate-100 font-semibold"'}
            >
                ← Trước
            </button>
            <div class="flex items-center gap-1">
                ${pageButtons}
            </div>
            <button 
                onclick="goToPage('${type}', ${currentPage + 1})" 
                ${currentPage === totalPages ? 'disabled class="px-2.5 py-1 rounded-lg border border-slate-200 text-xs text-slate-300 cursor-not-allowed"' : 'class="px-2.5 py-1 rounded-lg border border-slate-200 text-xs text-slate-600 hover:bg-slate-100 font-semibold"'}
            >
                Sau →
            </button>
        </div>
    `;
}

function goToPage(type, pageNumber) {
    const p = appState.pagination[type];
    const totalPages = Math.ceil(p.data.length / p.pageSize) || 1;
    if (pageNumber < 1 || pageNumber > totalPages) return;
    p.currentPage = pageNumber;

    if (type === 'users') renderUsersTablePage();
    if (type === 'audit') renderAuditTablePage();
    if (type === 'scd') renderScdTablePage();
}

function changePageSize(type, newSize) {
    const p = appState.pagination[type];
    p.pageSize = parseInt(newSize, 10) || 5;
    p.currentPage = 1;

    if (type === 'users') renderUsersTablePage();
    if (type === 'audit') renderAuditTablePage();
    if (type === 'scd') renderScdTablePage();
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
            lucide.createIcons();
            return;
        }

        fallback.classList.add('hidden');
        selectorBar.innerHTML = dashboards.map((d, idx) => `
            <button onclick="selectLookerDashboard(${idx})" id="btnLookerDash${idx}" class="px-4 py-2 rounded-xl text-xs font-bold transition-all ${idx === 0 ? 'bg-[#0284c7] text-white shadow-md' : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50'}">
                ${d.title} (${d.category})
            </button>
        `).join('');

        selectLookerDashboard(0);
    } catch (e) {
        console.error('Failed to load Looker dashboards:', e);
    }
}

function normalizeLookerUrl(url) {
    if (!url) return '';
    let clean = url.trim();
    if (clean.includes('lookerstudio.google.com/reporting/') && !clean.includes('/embed/')) {
        clean = clean.replace('lookerstudio.google.com/reporting/', 'lookerstudio.google.com/embed/reporting/');
    } else if (clean.includes('datastudio.google.com/reporting/') && !clean.includes('/embed/')) {
        clean = clean.replace('datastudio.google.com/reporting/', 'datastudio.google.com/embed/reporting/');
    }
    return clean;
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
                btn.className = 'px-4 py-2 rounded-xl text-xs font-bold transition-all bg-[#0284c7] text-white shadow-md';
            } else {
                btn.className = 'px-4 py-2 rounded-xl text-xs font-bold transition-all bg-white text-slate-700 border border-slate-200 hover:bg-slate-50';
            }
        }
    });

    const iframe = document.getElementById('lookerEmbedIframe');
    iframe.src = normalizeLookerUrl(dash.embed_url);
}

function reloadLookerIframe() {
    const iframe = document.getElementById('lookerEmbedIframe');
    if (iframe.src && iframe.src !== 'about:blank') {
        const currentSrc = iframe.src;
        iframe.src = 'about:blank';
        setTimeout(() => { iframe.src = currentSrc; }, 100);
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

// ==================== CLIENT: SCD TYPE 2 EXPLORER (WITH PAGINATION) ====================
async function fetchScdData() {
    const q = document.getElementById('inputScdSearch')?.value || '';
    try {
        const endpoint = q ? `/explorer/scd2/orders?query=${encodeURIComponent(q)}` : '/explorer/scd2/orders';
        const res = await fetchWithAuth(endpoint);
        if (!res.ok) return;
        const rows = await res.json();

        appState.pagination.scd.data = rows;
        appState.pagination.scd.currentPage = 1;
        renderScdTablePage();
    } catch (e) {
        console.error(e);
    }
}

function renderScdTablePage() {
    const p = appState.pagination.scd;
    const startIndex = (p.currentPage - 1) * p.pageSize;
    const currentSlice = p.data.slice(startIndex, startIndex + p.pageSize);

    const tbody = document.getElementById('tbodyScd2');
    if (!tbody) return;

    if (currentSlice.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-slate-400 text-xs">Không tìm thấy bản ghi nào.</td></tr>`;
        renderPaginationControls('scd', p.data.length, p.currentPage, p.pageSize, 'paginationScd');
        return;
    }

    tbody.innerHTML = currentSlice.map(r => {
        let statusBadge = r.is_current 
            ? '<span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 font-bold text-xs">🟢 Đang Áp Dụng (Active)</span>' 
            : '<span class="px-2.5 py-1 rounded-md bg-sky-50 text-sky-700 font-bold text-xs">🟡 Lịch Sử Cũ (Updated)</span>';
        
        if (r.order_id === 'ORD_DEMO_222' && !r.is_current) {
            statusBadge = '<span class="px-2.5 py-1 rounded-md bg-rose-50 text-rose-700 font-bold text-xs">🔴 Đã Bị Xóa (Hard-Deleted)</span>';
        }

        return `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="py-3.5 px-4 font-mono text-xs text-[#0284c7] font-semibold">${r.dbt_scd_id}</td>
                <td class="py-3.5 px-4 font-bold text-dg-dark">${r.order_id}</td>
                <td class="py-3.5 px-4 text-slate-600">${r.customer_id}</td>
                <td class="py-3.5 px-4"><span class="px-2.5 py-0.5 rounded bg-slate-100 text-slate-700 text-xs font-semibold">${r.order_status}</span></td>
                <td class="py-3.5 px-4 font-mono text-xs text-slate-500">${r.dbt_valid_from}</td>
                <td class="py-3.5 px-4 font-mono text-xs text-slate-500">${r.dbt_valid_to || 'NULL (Current)'}</td>
                <td class="py-3.5 px-4">${statusBadge}</td>
            </tr>
        `;
    }).join('');

    renderPaginationControls('scd', p.data.length, p.currentPage, p.pageSize, 'paginationScd');
    lucide.createIcons();
}

// ==================== ADMIN: USER & TENANT MANAGER (WITH PAGINATION) ====================
async function fetchUsersList() {
    try {
        const res = await fetchWithAuth('/users');
        if (!res.ok) return;
        const users = await res.json();

        // Update total tenant count
        const tenantSet = new Set(users.map(u => u.tenant_slug));
        document.getElementById('valTotalTenants').textContent = `${tenantSet.size} Doanh Nghiệp`;

        appState.pagination.users.data = users;
        appState.pagination.users.currentPage = 1;
        renderUsersTablePage();
    } catch (e) {
        console.error(e);
    }
}

function renderUsersTablePage() {
    const p = appState.pagination.users;
    const startIndex = (p.currentPage - 1) * p.pageSize;
    const currentSlice = p.data.slice(startIndex, startIndex + p.pageSize);

    const tbody = document.getElementById('tbodyUsersList');
    if (!tbody) return;

    if (currentSlice.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-slate-400 text-xs">Chưa có khách hàng nào.</td></tr>`;
        renderPaginationControls('users', p.data.length, p.currentPage, p.pageSize, 'paginationUsers');
        return;
    }

    tbody.innerHTML = currentSlice.map(u => {
        let planBadge = '<span class="px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-bold uppercase">Starter (1.99tr)</span>';
        if (u.tenant_plan === 'growth_pro' || u.tenant_plan === 'growth') {
            planBadge = '<span class="px-2.5 py-1 rounded-md bg-sky-50 text-sky-800 border border-sky-200/60 text-xs font-bold uppercase">Growth Pro (4.49tr)</span>';
        } else if (u.tenant_plan === 'enterprise') {
            planBadge = '<span class="px-2.5 py-1 rounded-md bg-purple-50 text-purple-800 border border-purple-200/60 text-xs font-bold uppercase">Enterprise (8.99tr)</span>';
        }

        return `
            <tr class="hover:bg-slate-50 transition-colors">
                <td class="py-3.5 px-4 font-bold text-dg-dark">${u.full_name}</td>
                <td class="py-3.5 px-4 font-mono text-xs text-slate-600">${u.email}</td>
                <td class="py-3.5 px-4">
                    <div class="font-bold text-dg-dark">${u.tenant_name}</div>
                    <div class="text-[11px] text-slate-400 font-mono">${u.tenant_slug}</div>
                </td>
                <td class="py-3.5 px-4">
                    ${planBadge}
                </td>
                <td class="py-3.5 px-4">
                    ${u.is_active 
                        ? '<span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold">● Hoạt Động</span>' 
                        : '<span class="px-2.5 py-1 rounded-md bg-rose-50 text-rose-700 text-xs font-bold">● Bị Khóa</span>'}
                </td>
                <td class="py-3.5 px-4">
                    ${u.tenant_id ? `
                        <button onclick="openAssignLookerModal('${u.tenant_id}', '${u.tenant_name}')" class="px-3 py-1.5 rounded-lg border border-sky-200 bg-sky-50 text-sky-800 text-xs font-bold hover:bg-sky-100 flex items-center gap-1 transition-all">
                            <i data-lucide="layout-dashboard" class="w-3.5 h-3.5 text-[#0284c7]"></i>
                            <span>Quản Lý Looker URL</span>
                        </button>
                    ` : '<span class="text-xs text-slate-400">DashGrow HQ</span>'}
                </td>
                <td class="py-3.5 px-4">
                    <div class="flex items-center gap-2">
                        <button onclick="toggleUserStatus('${u.id}', ${u.is_active})" class="px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-all">
                            ${u.is_active ? 'Khóa' : 'Mở Khóa'}
                        </button>
                        <button onclick="deleteUserAccount('${u.id}')" class="px-2.5 py-1 rounded-lg border border-rose-200 text-xs font-semibold text-rose-600 hover:bg-rose-50 transition-all">
                            Xóa
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    renderPaginationControls('users', p.data.length, p.currentPage, p.pageSize, 'paginationUsers');
    lucide.createIcons();
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
        showToast(`Đã tạo khách hàng mới thành công: ${payload.company_name}`, 'success');
        await fetchUsersList();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== ADMIN: ASSIGN & DELETE LOOKER DASHBOARDS ====================
async function openAssignLookerModal(tenantId, tenantName) {
    document.getElementById('assignLookerTenantId').value = tenantId;
    document.getElementById('assignLookerTenantSub').textContent = `Doanh nghiệp: ${tenantName}`;
    document.getElementById('assignLookerTitle').value = `Báo Cáo Doanh Thu P&L - ${tenantName}`;
    document.getElementById('modalAssignLooker').classList.add('active');
    
    // Load list of existing dashboards for this tenant with Delete buttons
    await loadTenantDashboardsInModal(tenantId);
}

async function loadTenantDashboardsInModal(tenantId) {
    const listContainer = document.getElementById('listTenantDashboards');
    const countEl = document.getElementById('countTenantDashboards');
    listContainer.innerHTML = '<div class="text-xs text-slate-400 py-2">Đang tải danh sách báo cáo...</div>';

    try {
        const res = await fetchWithAuth(`/looker/tenants/${tenantId}`);
        if (!res.ok) {
            listContainer.innerHTML = '<div class="text-xs text-slate-400 py-2">Chưa có báo cáo nào được gán.</div>';
            countEl.textContent = '(0 báo cáo)';
            return;
        }

        const dashboards = await res.json();
        countEl.textContent = `(${dashboards.length} báo cáo)`;

        if (dashboards.length === 0) {
            listContainer.innerHTML = '<div class="text-xs text-slate-400 py-2 italic">Chưa có báo cáo nào. Hãy điền form bên dưới để thêm!</div>';
            return;
        }

        listContainer.innerHTML = dashboards.map(d => `
            <div class="p-2.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between gap-3 text-xs">
                <div class="min-w-0 flex-1">
                    <div class="font-bold text-dg-dark truncate">${d.title}</div>
                    <div class="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                        <span class="px-1.5 py-0.5 rounded bg-sky-100 text-sky-800 font-semibold text-[10px]">${d.category}</span>
                        ${d.is_default ? '<span class="text-emerald-600 font-bold text-[10px]">★ Mặc định</span>' : ''}
                    </div>
                </div>
                <button 
                    onclick="deleteTenantDashboard('${d.id}', '${tenantId}', '${d.title}')"
                    class="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 border border-rose-200 text-xs font-bold transition-colors flex items-center gap-1 shrink-0"
                    title="Xóa dashboard này"
                >
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    <span>Xóa</span>
                </button>
            </div>
        `).join('');

        lucide.createIcons();
    } catch (e) {
        console.error(e);
        listContainer.innerHTML = '<div class="text-xs text-rose-500 py-2">Lỗi tải danh sách báo cáo.</div>';
    }
}

async function deleteTenantDashboard(dashboardId, tenantId, title) {
    if (!confirm(`Bạn có chắc chắn muốn XÓA báo cáo "${title}" không?`)) return;

    try {
        const res = await fetch(`${API_BASE}/looker/${dashboardId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${appState.token}` }
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Lỗi khi xóa dashboard.');
        }

        showToast(`Đã xóa dashboard: ${title}`, 'success');
        await loadTenantDashboardsInModal(tenantId);
    } catch (err) {
        showToast(err.message, 'error');
    }
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

        showToast('Đã thêm dashboard Looker Studio thành công!', 'success');
        document.getElementById('assignLookerUrl').value = '';
        await loadTenantDashboardsInModal(tenantId);
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
    if (!confirm('Bạn có chắc chắn muốn xóa vĩnh viễn tài khoản này không?')) return;
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

// ==================== ADMIN: AUDIT LOGS (WITH PAGINATION) ====================
async function fetchAuditLogs() {
    try {
        const res = await fetchWithAuth('/explorer/audit-logs');
        if (!res.ok) return;
        const rows = await res.json();

        appState.pagination.audit.data = rows;
        appState.pagination.audit.currentPage = 1;
        renderAuditTablePage();
    } catch (e) {
        console.error(e);
    }
}

function renderAuditTablePage() {
    const p = appState.pagination.audit;
    const startIndex = (p.currentPage - 1) * p.pageSize;
    const currentSlice = p.data.slice(startIndex, startIndex + p.pageSize);

    const tbody = document.getElementById('tbodyAuditLogs');
    if (!tbody) return;

    if (currentSlice.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-slate-400 text-xs">Chưa có nhật ký vận hành nào.</td></tr>`;
        renderPaginationControls('audit', p.data.length, p.currentPage, p.pageSize, 'paginationAudit');
        return;
    }

    tbody.innerHTML = currentSlice.map(r => `
        <tr class="hover:bg-slate-50 transition-colors">
            <td class="py-3.5 px-4 font-mono text-xs text-[#0284c7] font-semibold">${r.run_id}</td>
            <td class="py-3.5 px-4 font-bold text-dg-dark">${r.connector_name}</td>
            <td class="py-3.5 px-4"><span class="px-2.5 py-0.5 rounded-md bg-sky-50 text-sky-800 border border-sky-200/60 text-xs font-semibold">${r.run_mode}</span></td>
            <td class="py-3.5 px-4"><span class="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-bold">✓ ${r.status}</span></td>
            <td class="py-3.5 px-4 font-semibold text-slate-700">${r.records_extracted.toLocaleString()} dòng</td>
            <td class="py-3.5 px-4 text-slate-500">${r.duration_sec}s</td>
            <td class="py-3.5 px-4 font-mono text-xs text-slate-500">${r.executed_at}</td>
        </tr>
    `).join('');

    renderPaginationControls('audit', p.data.length, p.currentPage, p.pageSize, 'paginationAudit');
    lucide.createIcons();
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
        showToast(`Đã kích hoạt pipeline cho ${connector}!`, 'success');
        await fetchAuditLogs();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==================== LIGHTWEIGHT TOAST NOTIFICATION ====================
function showToast(msg, type = 'info') {
    const wrap = document.getElementById('toastWrap');
    if (!wrap) return;
    const t = document.createElement('div');
    t.className = 'toast-msg';
    t.innerHTML = `<span>${type === 'success' ? '✓' : type === 'error' ? '⚠' : 'ℹ'}</span><span>${msg}</span>`;
    wrap.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0';
        setTimeout(() => t.remove(), 200);
    }, 1200);
}
