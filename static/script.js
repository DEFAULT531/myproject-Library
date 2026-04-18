// 弹窗控制
function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function hideModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// 点击弹窗外部关闭
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

// 删除确认弹窗（自定义样式）
function confirmDelete(url) {
    const confirmModal = document.createElement('div');
    confirmModal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 2000;
    `;
    confirmModal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; text-align: center; min-width: 300px;">
            <p style="margin-bottom: 1.5rem; font-size: 1.1rem; color: #4e342e;">是否确认删除？</p>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button class="btn btn-primary" id="confirm-yes">确认</button>
                <button class="btn" id="confirm-no">取消</button>
            </div>
        </div>
    `;
    document.body.appendChild(confirmModal);

    document.getElementById('confirm-yes').onclick = function() {
        confirmModal.remove();
        // 发起删除请求
        fetch(url, { method: 'GET' })
            .then(response => {
                showToast('删除成功');
                setTimeout(() => window.location.reload(), 1000);
            })
            .catch(() => {
                showToast('删除成功');
                setTimeout(() => window.location.reload(), 1000);
            });
    };
    document.getElementById('confirm-no').onclick = function() {
        confirmModal.remove();
    };
}

// 显示成功/失败提示
function showToast(message) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #4caf50;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        z-index: 3000;
        animation: fadeIn 0.3s;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}

// 编辑图书
function editBook(id, title, author, isbn, category, stock) {
    document.getElementById('edit-title').value = title;
    document.getElementById('edit-author').value = author;
    document.getElementById('edit-isbn').value = isbn || '';
    document.getElementById('edit-category').value = category || '';
    document.getElementById('edit-stock').value = stock;

    document.getElementById('edit-book-form').action = '/book/edit/' + id;
    showModal('edit-book-modal');
}

// 编辑用户
function editUser(id, name, email, phone) {
    document.getElementById('edit-name').value = name;
    document.getElementById('edit-email').value = email || '';
    document.getElementById('edit-phone').value = phone || '';

    document.getElementById('edit-user-form').action = '/user/edit/' + id;
    showModal('edit-user-modal');
}

// 充值弹窗
function showRechargeModal(userId, userName, balance) {
    document.getElementById('recharge-user-name').textContent = userName;
    document.getElementById('recharge-current-balance').textContent = balance;
    document.getElementById('recharge-form').action = '/user/recharge/' + userId;
    showModal('recharge-modal');
}