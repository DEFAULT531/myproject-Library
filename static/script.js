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