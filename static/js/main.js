// Активация всплывающих подсказок
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
});

// Плавная прокрутка для якорей
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Функции для работы с cookie
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// Управление модальным окном согласия
document.addEventListener('DOMContentLoaded', function() {
    const modal = new bootstrap.Modal(document.getElementById('personalDataModal'));
    const acceptBtn = document.getElementById('acceptBtn');
    
    // Проверяем, дали ли уже согласие
    if (!getCookie('consent')) {
        modal.show();
    }
    
    // Обработчик кнопки "Принять"
    acceptBtn.addEventListener('click', function() {
        setCookie('consent', 'accepted', 365); // Сохраняем на 1 год
        modal.hide();
    });
});
