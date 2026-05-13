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
function confirmDelete(url, message, successMessage) {
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
    const msg = message || '是否确认删除？';
    confirmModal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; text-align: center; min-width: 300px;">
            <p style="margin-bottom: 1.5rem; font-size: 1.1rem; color: #4e342e;">${msg}</p>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button class="btn btn-primary" id="confirm-yes">确认</button>
                <button class="btn" id="confirm-no">取消</button>
            </div>
        </div>
    `;
    document.body.appendChild(confirmModal);

    document.getElementById('confirm-yes').onclick = function() {
        confirmModal.remove();
        // 发起请求
        fetch(url, { method: 'GET' })
            .then(response => {
                showToast(successMessage || '操作成功');
                setTimeout(() => window.location.reload(), 1000);
            })
            .catch(() => {
                showToast(successMessage || '操作成功');
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
function editUser(id, name, email, phone, reader_type, max_borrow) {
    document.getElementById('edit-name').value = name;
    document.getElementById('edit-email').value = email || '';
    document.getElementById('edit-phone').value = phone || '';
    document.getElementById('edit-reader_type').value = reader_type || '普通会员';
    document.getElementById('edit-max_borrow').value = max_borrow || 5;

    document.getElementById('edit-user-form').action = '/user/edit/' + id;
    showModal('edit-user-modal');
}

// 充值弹窗
function showRechargeModal(userId, userName, balance) {
    document.getElementById('recharge-user-name').textContent = userName;
    document.getElementById('recharge-current-balance').textContent = balance;
    document.getElementById('recharge-message').style.display = 'none';
    window.rechargeUserId = userId;
    showModal('recharge-modal');
}

// 提交充值
async function submitRecharge() {
    const userId = window.rechargeUserId;
    const amount = document.getElementById('recharge-amount').value;
    const messageEl = document.getElementById('recharge-message');

    if (!amount || amount <= 0) {
        messageEl.textContent = '请输入有效的充值金额';
        messageEl.style.display = 'block';
        messageEl.style.backgroundColor = '#f8d7da';
        messageEl.style.color = '#721c24';
        return;
    }

    try {
        const response = await fetch('/user/recharge/' + userId, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'amount=' + encodeURIComponent(amount)
        });
        const result = await response.json();

        if (result.success) {
            messageEl.textContent = result.message + '，三秒后关闭';
            messageEl.style.backgroundColor = '#d4edda';
            messageEl.style.color = '#155724';
            setTimeout(() => hideModal('recharge-modal'), 3000);
        } else {
            messageEl.textContent = result.message + '，三秒后关闭';
            messageEl.style.backgroundColor = '#f8d7da';
            messageEl.style.color = '#721c24';
            setTimeout(() => hideModal('recharge-modal'), 3000);
        }
        messageEl.style.display = 'block';
    } catch (e) {
        messageEl.textContent = '充值失败，请重试，三秒后关闭';
        messageEl.style.display = 'block';
        messageEl.style.backgroundColor = '#f8d7da';
        messageEl.style.color = '#721c24';
        setTimeout(() => hideModal('recharge-modal'), 3000);
    }
}