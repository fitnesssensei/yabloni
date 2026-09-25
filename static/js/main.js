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

// Управление баннером согласия на cookies
document.addEventListener('DOMContentLoaded', function() {
    const cookieBanner = document.getElementById('cookieBanner');
    const acceptBtn = document.getElementById('acceptBtn');
    const declineBtn = document.getElementById('declineBtn');
    
    // Проверяем, дали ли уже согласие
    if (!getCookie('consent')) {
        cookieBanner.style.display = 'block';
    }
    
    // Обработчик кнопки "Принять"
    acceptBtn.addEventListener('click', function() {
        setCookie('consent', 'accepted', 365); // Сохраняем на 1 год
        cookieBanner.style.display = 'none';
    });
    
    // Обработчик кнопки "Отклонить"
    declineBtn.addEventListener('click', function() {
        cookieBanner.style.display = 'none';
        // Можно добавить логику для повторного показа через время
    });
});

// ===== Кнопка «наверх» (стрелочка перемотки страницы вверх) =====
// Разметка кнопки лежит в общем шаблоне templates/base/base.html (id="backToTop"),
// внешний вид — класс .back-to-top в static/css/style.css.
// Логика: когда страница прокручена вниз больше чем на 300px — кнопка видна,
// по клику (или Enter/Space с клавиатуры) страница плавно возвращается в начало.
document.addEventListener('DOMContentLoaded', function() {
    const backToTopButton = document.getElementById('backToTop');

    // На страницах без base.html кнопки нет — тогда просто выходим
    if (!backToTopButton) {
        return;
    }

    const SHOW_AFTER_PX = 300; // после скольких пикселей прокрутки показывать кнопку
    // Если в системе включено «уменьшить движение» — прокручиваем без анимации
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let ticking = false; // защита от лишних пересчётов: не чаще одного раза за кадр

    // Пересчитываем видимость кнопки по текущему положению прокрутки
    function updateBackToTop() {
        if (window.scrollY > SHOW_AFTER_PX) {
            backToTopButton.classList.add('show');
        } else {
            backToTopButton.classList.remove('show');
        }
        ticking = false;
    }

    // Слушатель прокрутки: passive — чтобы не тормозить скролл, rAF — чтобы сгладить частоту вызовов
    window.addEventListener('scroll', function() {
        if (!ticking) {
            ticking = true;
            window.requestAnimationFrame(updateBackToTop);
        }
    }, { passive: true });

    // Возврат в начало страницы по клику по кнопке
    backToTopButton.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: reduceMotion ? 'auto' : 'smooth'
        });
    });

    // Сразу расставляем состояние: страница может открыться уже прокрученной вниз
    updateBackToTop();
});
