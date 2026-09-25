from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


def read_static_file(relative_path):
    """Возвращает текст статического файла по пути относительно static/ (например, 'js/main.js').

    Ищем через finders.find — тогда тест работает с тем же файлом, что отдаёт collectstatic,
    и не зависит от того, где именно лежит папка static.
    """
    absolute_path = finders.find(relative_path)
    with open(absolute_path, encoding='utf-8') as static_file:
        return static_file.read()


class BackToTopButtonTests(TestCase):
    """Кнопка «наверх» (стрелочка перемотки страницы вверх).

    Кнопка лежит в общем шаблоне templates/base/base.html, поэтому должна быть
    на всех страницах сайта. Проверяем разметку, доступность и наличие
    стилей/скрипта, которые её показывают и прокручивают страницу.
    """

    def test_button_is_present_on_home_page(self):
        """На главной странице есть кнопка «наверх»."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="backToTop"')

    def test_button_is_present_on_catalog_page(self):
        """Кнопка «наверх» есть и на других страницах (общий шаблон base.html)."""
        response = self.client.get(reverse('catalog:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="back-to-top"')

    def test_button_is_accessible(self):
        """У кнопки есть подпись для скринридеров и подсказка при наведении."""
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'aria-label="Наверх"')
        self.assertContains(response, 'title="Наверх"')

    def test_style_file_has_button_rules(self):
        """В style.css описаны сама кнопка и класс .show, который её включает."""
        style_css = read_static_file('css/style.css')
        self.assertIn('.back-to-top', style_css)
        self.assertIn('.back-to-top.show', style_css)

    def test_script_file_has_button_logic(self):
        """В main.js есть показ кнопки по прокрутке и плавный возврат в начало."""
        main_js = read_static_file('js/main.js')
        self.assertIn("getElementById('backToTop')", main_js)
        self.assertIn("classList.add('show')", main_js)
        self.assertIn('window.scrollTo', main_js)
