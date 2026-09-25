"""Тесты общей части сайта: базовый шаблон templates/base/base.html и общие статики.

Здесь проверяется кнопка «наверх» (стрелочка возврата к началу страницы):
её разметка на страницах, правила в static/css/style.css и логика в static/js/main.js.
JS-раннера в проекте нет, поэтому поведение скрипта проверяем по его исходнику через
регулярные выражения — если логику уберут или сломают, тест упадёт (проверка подстроки
такого не ловит).
"""
import re

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

# Страницы, которые наследуют base/base.html и должны отдавать кнопку «наверх».
# Берём только статические страницы и списки: они отвечают 200 даже на пустой базе.
PAGES_WITH_BASE_TEMPLATE = (
    'home',
    'catalog:product_list',
    'cart:cart_detail',
    'blog:blog_list',
    'nursery',
    'search',
    'account',
    'legal_info',
)

# id и класс кнопки из templates/base/base.html
BUTTON_ID = 'backToTop'
BUTTON_CLASS = 'back-to-top'

# Порог прокрутки (px) из static/js/main.js, после которого кнопка появляется
SHOW_AFTER_PX = 300


def read_static_file(relative_path):
    """Возвращает текст статического файла по пути относительно static/ (например, 'js/main.js').

    Ищем через finders.find — тогда тест работает с тем же файлом, что отдаёт collectstatic,
    и не зависит от того, где именно лежит папка static.
    """
    absolute_path = finders.find(relative_path)
    if absolute_path is None:
        # Без этой проверки open(None) падал бы с непонятным TypeError
        raise AssertionError(
            f'Статический файл static/{relative_path} не найден. '
            'Проверьте, что файл существует и папка static есть в STATICFILES_DIRS.'
        )
    with open(absolute_path, encoding='utf-8') as static_file:
        return static_file.read()


def read_css_rule(style_css, selector):
    """Возвращает тело первого правила `selector { ... }` из CSS (то, что в фигурных скобках).

    Так проверяются конкретные объявления, а не просто наличие слова в файле.
    """
    match = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', style_css)
    if match is None:
        raise AssertionError(f'В style.css нет правила для селектора {selector!r}.')
    return match.group(1)


def read_css_rules(style_css, selector):
    """Возвращает тела ВСЕХ правил с этим селектором.

    Правил с одним селектором может быть несколько: например `:focus-visible`
    встречается и в общей группе с `:hover`, и отдельным блоком с контуром.
    В CSS такие правила складываются, поэтому достаточно найти объявление
    хотя бы в одном из тел.
    """
    bodies = [
        match.group(1)
        for match in re.finditer(re.escape(selector) + r'\s*\{([^}]*)\}', style_css)
    ]
    if not bodies:
        raise AssertionError(f'В style.css нет правила для селектора {selector!r}.')
    return bodies


def read_media_block(style_css, at_rule, contains):
    """Возвращает тело блока `@media ... { ... }`, внутри которого есть подстрока `contains`.

    Один и тот же @media может встречаться в файле несколько раз, поэтому выбираем тот блок,
    где реально лежат правила нужного селектора.
    """
    # Пробелы внутри @media не важны: сравниваем только слова правила
    pattern = r'\s*'.join(re.escape(token) for token in at_rule.split())
    for match in re.finditer(pattern + r'\s*\{([\s\S]*?)\n\}', style_css):
        if contains in match.group(1):
            return match.group(1)
    raise AssertionError(f'В style.css нет блока {at_rule!r} с правилами для {contains!r}.')


def has_declaration(css_text, declaration, value):
    """Есть ли в тексте CSS объявление вида `declaration: value` (пробелы и регистр не важны)."""
    pattern = re.escape(declaration) + r'\s*:\s*' + re.escape(value)
    return re.search(pattern, css_text, flags=re.IGNORECASE) is not None


class BackToTopMarkupTests(TestCase):
    """Разметка кнопки «наверх»: она лежит в base/base.html, значит есть на всех страницах."""

    def get_button_markup(self, url_name='home'):
        """Возвращает HTML-фрагмент кнопки со страницы (или падает, если кнопки нет)."""
        content = self.client.get(reverse(url_name)).content.decode('utf-8')
        match = re.search(rf'<button[^>]*id="{BUTTON_ID}".*?</button>', content, flags=re.DOTALL)
        self.assertIsNotNone(match, f'Кнопка «наверх» не найдена на странице {url_name}.')
        return match.group(0)

    def test_button_is_on_every_page_with_base_template(self):
        """Кнопка есть на всех страницах, которые наследуют base/base.html."""
        for url_name in PAGES_WITH_BASE_TEMPLATE:
            with self.subTest(page=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'id="{BUTTON_ID}"')
                self.assertContains(response, f'class="{BUTTON_CLASS}"')

    def test_only_one_button_on_page(self):
        """На странице ровно одна кнопка «наверх» (не дублируется)."""
        content = self.client.get(reverse('home')).content.decode('utf-8')
        self.assertEqual(content.count(f'id="{BUTTON_ID}"'), 1)

    def test_button_markup_is_complete(self):
        """У кнопки правильный тип, подписи для скринридеров и иконка стрелки."""
        markup = self.get_button_markup()
        self.assertIn('type="button"', markup)           # клик не отправляет форму
        self.assertIn('aria-label="Наверх"', markup)     # подпись для скринридеров
        self.assertIn('title="Наверх"', markup)          # подсказка при наведении мышью
        self.assertIn('class="bi bi-arrow-up"', markup)  # иконка Bootstrap Icons
        self.assertIn('aria-hidden="true"', markup)      # иконка не озвучивается дважды

    def test_button_is_not_disabled_or_hidden_by_attribute(self):
        """Кнопка активна: нет атрибутов disabled/hidden (скрытие делает CSS-класс)."""
        markup = self.get_button_markup()
        self.assertNotIn('disabled', markup)
        # именно атрибут hidden (без значения), а не aria-hidden у иконки внутри
        self.assertIsNone(re.search(r'\shidden(?=[\s>])', markup))


class BackToTopStyleTests(SimpleTestCase):
    """Внешний вид кнопки «наверх» в static/css/style.css.

    SimpleTestCase — база данных для этих проверок не нужна, читаем только файлы статики.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.style_css = read_static_file('css/style.css')
        cls.button_rule = read_css_rule(cls.style_css, f'.{BUTTON_CLASS}')

    def test_button_is_fixed_in_bottom_corner(self):
        """Кнопка закреплена в правом нижнем углу и не уезжает при прокрутке страницы."""
        self.assertTrue(has_declaration(self.button_rule, 'position', 'fixed'))
        self.assertTrue(has_declaration(self.button_rule, 'right', '20px'))
        self.assertTrue(has_declaration(self.button_rule, 'bottom', '20px'))

    def test_button_is_hidden_until_scroll(self):
        """До прокрутки кнопка не видна и её нельзя нажать (мышью, тапом или Tab)."""
        self.assertTrue(has_declaration(self.button_rule, 'opacity', '0'))
        self.assertTrue(has_declaration(self.button_rule, 'visibility', 'hidden'))
        self.assertTrue(has_declaration(self.button_rule, 'pointer-events', 'none'))

    def test_button_background_is_semitransparent(self):
        """Фон кнопки — полупрозрачный цвет шапки/подвала сайта (#9dab8a)."""
        match = re.search(r'background-color\s*:\s*rgba\(([^)]*)\)', self.button_rule)
        self.assertIsNotNone(match, 'У кнопки нет полупрозрачного rgba-фона.')
        parts = [part.strip() for part in match.group(1).split(',')]
        self.assertEqual(parts[:3], ['157', '171', '138'])  # #9dab8a
        self.assertLess(float(parts[3]), 1)                 # alpha < 1 — полупрозрачность

    def test_icon_color_is_dark_not_white(self):
        """Стрелка тёмная: белая на светлом полупрозрачном фоне давала контраст ≈1.6:1."""
        self.assertTrue(has_declaration(self.button_rule, 'color', '#2f3d22'))

    def test_show_class_makes_button_visible(self):
        """Класс .show (его ставит скрипт при прокрутке) включает кнопку."""
        show_rule = read_css_rule(self.style_css, f'.{BUTTON_CLASS}.show')
        self.assertTrue(has_declaration(show_rule, 'opacity', '1'))
        self.assertTrue(has_declaration(show_rule, 'visibility', 'visible'))
        self.assertTrue(has_declaration(show_rule, 'pointer-events', 'auto'))

    def test_button_stays_visible_while_focused(self):
        """Пока на кнопке фокус, она не исчезает (иначе фокус уезжает в body)."""
        focus_rules = read_css_rules(self.style_css, f'.{BUTTON_CLASS}:focus-visible')
        self.assertTrue(any(has_declaration(rule, 'opacity', '1') for rule in focus_rules))
        self.assertTrue(any(has_declaration(rule, 'visibility', 'visible') for rule in focus_rules))
        self.assertTrue(any(has_declaration(rule, 'pointer-events', 'auto') for rule in focus_rules))
        # видимый контур для тех, кто ходит сайтом с клавиатуры
        self.assertTrue(any(has_declaration(rule, 'outline', '2px solid') for rule in focus_rules))

    def test_mobile_media_query_makes_button_compact(self):
        """На телефоне (<768px) кнопка меньше (44px) — удобно нажимать пальцем."""
        mobile_block = read_media_block(
            self.style_css, '@media (max-width: 768px)', f'.{BUTTON_CLASS}'
        )
        self.assertTrue(has_declaration(mobile_block, 'width', '44px'))
        self.assertTrue(has_declaration(mobile_block, 'height', '44px'))

    def test_reduced_motion_disables_transition(self):
        """При системном «уменьшить движение» анимация кнопки отключается."""
        reduced_block = read_media_block(
            self.style_css, '@media (prefers-reduced-motion: reduce)', f'.{BUTTON_CLASS}'
        )
        self.assertTrue(has_declaration(reduced_block, 'transition', 'none'))


class BackToTopScriptTests(SimpleTestCase):
    """Логика кнопки в static/js/main.js.

    JS-раннера в проекте нет, поэтому проверяем исходник регулярными выражениями:
    если логику уберут или сломают, тест упадёт. Поведение в браузере проверяется
    вручную (см. README: «Кнопка наверх»).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_js = read_static_file('js/main.js')

    def test_script_finds_button_and_handles_its_absence(self):
        """Скрипт ищет кнопку по id, а на страницах без неё просто выходит."""
        self.assertRegex(self.main_js, rf"getElementById\('{BUTTON_ID}'\)")
        self.assertRegex(self.main_js, r'if\s*\(\s*!\s*backToTopButton\s*\)')

    def test_button_appears_after_scroll_threshold(self):
        """Кнопка появляется, когда страница прокручена больше SHOW_AFTER_PX пикселей."""
        self.assertRegex(self.main_js, rf'SHOW_AFTER_PX\s*=\s*{SHOW_AFTER_PX}\b')
        self.assertRegex(self.main_js, r'window\.scrollY\s*>\s*SHOW_AFTER_PX')

    def test_show_class_is_added_and_removed(self):
        """Класс .show ставится при прокрутке вниз и снимается при возврате наверх."""
        self.assertRegex(self.main_js, r"classList\.add\('show'\)")
        self.assertRegex(self.main_js, r"classList\.remove\('show'\)")

    def test_click_scrolls_page_to_top(self):
        """По клику (и по Enter/Space с клавиатуры) страница возвращается в начало."""
        self.assertRegex(self.main_js, r'window\.scrollTo\(\{[\s\S]*?top:\s*0')
        # обработчик висит на самой кнопке: срабатывает и от клика, и от Enter/Space
        self.assertRegex(self.main_js, r'backToTopButton\.addEventListener\(\s*\'click\'')

    def test_reduced_motion_disables_smooth_scrolling(self):
        """При системном «уменьшить движение» прокрутка идёт без анимации."""
        self.assertRegex(self.main_js, r'prefers-reduced-motion:\s*reduce')
        self.assertRegex(self.main_js, r"reduceMotion\s*\?\s*'auto'\s*:\s*'smooth'")

    def test_scroll_listener_is_passive_and_throttled(self):
        """Слушатель прокрутки passive (не тормозит скролл) и сглажен через requestAnimationFrame."""
        self.assertRegex(self.main_js, r'\{\s*passive:\s*true\s*\}')
        self.assertRegex(self.main_js, r'requestAnimationFrame\(\s*updateBackToTop\s*\)')

    def test_state_is_set_on_page_load(self):
        """Состояние кнопки расставляется сразу: страница может открыться уже прокрученной."""
        self.assertRegex(self.main_js, r'\n\s*updateBackToTop\(\);')
