//版权所有©ExcuseBox 禁止复制修改或商用 侵权必究
const STORAGE_KEY = 'admin_login_data';

window.addEventListener('DOMContentLoaded', function() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        try {
            const data = JSON.parse(saved);
            document.getElementById('username').value = data.username || '';
            document.getElementById('password').value = data.password || '';
            document.getElementById('remember').checked = true;
        } catch (e) {
            localStorage.removeItem(STORAGE_KEY);
        }
    }
});

document.getElementById('remember').addEventListener('change', function() {
    if (!this.checked) {
        localStorage.removeItem(STORAGE_KEY);
    }
});

function handleLogin() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const remember = document.getElementById('remember').checked;
    const errorMsg = document.getElementById('errorMsg');

    if (remember) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            username: username,
            password: password
        }));
    } else {
        localStorage.removeItem(STORAGE_KEY);
    }

    if (username === 'admin' && password === '123456') {
        window.location.href = 'https://eclik.cn/zyj/pic.html?id=18513d1fd19f4b119f42c3ad9b24d80c';
    } else {
        errorMsg.classList.add('show');
        setTimeout(() => {
            errorMsg.classList.remove('show');
        }, 3000);
    }
}

document.getElementById('password').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        handleLogin();
    }
});

document.getElementById('username').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        document.getElementById('password').focus();
    }
});