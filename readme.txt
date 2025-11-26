# Устройство : macBook Pro c процессором M4 Pro 2024 года
# Операционная система : macOS Tahoe 26.1
# Браузер FireFox

зачем файл : context_processors.py
проверь синтаксис и отступы !
проверь файл : templates/base/header.html
посмотри файлы catalog/views.py и catalog/urls.py

# Библиотеки : 
Bootstrap Icons - библиотека иконок
Font Awesome - библиотека иконок
Bootstrap 5 - CSS-фреймворк для создания адаптивного дизайна
jQuery - JavaScript-библиотека для упрощения работы с DOM и AJAX


# основной веб-фреймворк
Django (5.2.7)

# стилизации форм
django-crispy-forms с шаблоном crispy-bootstrap5

# драйвер PostgreSQL для Django
psycopg2-binary

# для работы с переменными окружения
python-dotenv

# для работы с изображениями (используется в моделях для загрузки изображений)
Pillow

# Основные встроенные приложения Django:
django.contrib.admin
django.contrib.auth
django.contrib.contenttypes
django.contrib.sessions
django.contrib.messages
django.contrib.staticfiles

# Кастомные приложения проекта:
catalog
cart
orders



++++ команды ++++++
активация Вирт окружения:
source venv/bin/activate

запуск сервера:
python manage.py runserver

создание папки:
mkdir -p templates/cart

создание файла:
touch templates/cart/detail.html

миграции:
python manage.py makemigrations
python manage.py migrate