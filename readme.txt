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


создать пароль к яндекс аккаунту :

### Создание пароля приложения Yandex:

1. Войдите в аккаунт Yandex (yabloni-grushi@yandex.ru)
2. Перейдите: Настройки → Пароли и безопасность → Пароли приложений
3. Нажмите "Создать пароль"
4. Введите название: "Django Shop"
5. Скопируйте сгенерированный пароль (показывается только один раз!)
6. Вставьте пароль в `.env` файл в переменную `EMAIL_HOST_PASSWORD`


++++ команды ++++++
активация Вирт окружения:
source venv/bin/activate

запуск сервера:
python manage.py runserver

Жесткий откат : 
git reset --hard « …»

пароль приложения для почты :
saeftncoarafjaci

создание папки:
mkdir -p templates/cart

создание файла:
touch templates/cart/detail.html

миграции:
python manage.py makemigrations
python manage.py migrate

тоннель : 
во втором терминале после запуска сервера в первом : 
lt --port 8000


