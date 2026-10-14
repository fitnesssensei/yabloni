"""Тесты общей части сайта: базовый шаблон templates/base/base.html и общие статики.

Здесь проверяется кнопка «наверх» (стрелочка возврата к началу страницы):
её разметка на страницах, правила в static/css/style.css и логика в static/js/main.js.
JS-раннера в проекте нет, поэтому поведение скрипта проверяем по его исходнику через
регулярные выражения — если логику уберут или сломают, тест упадёт (проверка подстроки
такого не ловит).
"""
import re
from html.parser import HTMLParser
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.models import EmailSettings
from core.signals import send_test_email

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

# Постоянный фон кнопки «наверх»: акцентный оранжевый сайта #ff8b00 и его прозрачность.
# Прозрачность меньше 1, поэтому кнопка не перекрывает контент страницы.
BUTTON_BACKGROUND_RGB = ('255', '139', '0')
BUTTON_BACKGROUND_ALPHA = '0.85'

# id баннера согласия на cookies (тоже из templates/base/base.html): он обязан лежать
# прямо в <body>, иначе из-за незакрытого тега уедет в подвал
COOKIE_BANNER_ID = 'cookieBanner'

# Шаблоны макета сайта: их незаметно ломает закрытие HTML-комментария раньше времени
LAYOUT_TEMPLATES = ('base/base.html', 'base/header.html', 'base/footer.html')

# Теги макета, которые обязаны открываться и закрываться одинаковое число раз
PAIRED_LAYOUT_TAGS = ('div', 'footer')

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


def read_template_file(relative_path):
    """Возвращает текст шаблона по пути относительно папки templates/ (например, 'base/footer.html')."""
    with open(settings.BASE_DIR / 'templates' / relative_path, encoding='utf-8') as template_file:
        return template_file.read()


def strip_html_comments(html_text):
    """Убирает HTML-комментарии так же, как это делает браузер.

    Возвращает кортеж (текст без комментариев, все_ли_комментарии_закрыты).
    Важно: комментарий закрывается ПЕРВОЙ последовательностью «-->», а вложенный «<!--»
    внутри комментария — обычный текст. Поэтому «-->», поставленный раньше конца
    выключенного блока, выкидывает следующие за ним реальные теги (</div>, </footer>)
    внутрь комментария — и макет ломается незаметно.
    """
    parts = []
    position = 0
    while True:
        comment_start = html_text.find('<!--', position)
        if comment_start == -1:
            parts.append(html_text[position:])
            return ''.join(parts), True
        parts.append(html_text[position:comment_start])
        comment_end = html_text.find('-->', comment_start + 4)
        if comment_end == -1:
            # Комментарий не закрыт: по правилам HTML браузер считает комментарием остаток файла
            return ''.join(parts), False
        position = comment_end + 3


class AncestorChainParser(HTMLParser):
    """Разбирает HTML и запоминает цепочку предков элемента с нужным id.

    Разбор идёт стандартным html.parser: он обрабатывает комментарии и вложенность так же,
    как браузер, поэтому теги, «съеденные» комментарием, в цепочке не появятся.
    """

    # Теги без закрывающей пары: в стек их класть нельзя
    VOID_TAGS = frozenset({
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'link', 'meta', 'param', 'source', 'track', 'wbr',
    })

    def __init__(self, element_id):
        super().__init__(convert_charrefs=True)
        self.element_id = element_id
        self.stack = []        # открытые теги: пары (имя тега, описание для сообщения)
        self.ancestors = None  # цепочка предков найденного элемента

    @staticmethod
    def describe(tag, attrs):
        """Описание тега для сообщения об ошибке: 'div.row', 'footer.custom-footer'."""
        attributes = dict(attrs)
        description = tag
        if attributes.get('id'):
            description += f"#{attributes['id']}"
        if attributes.get('class'):
            description += '.' + '.'.join(attributes['class'].split())
        return description

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID_TAGS:
            return
        if dict(attrs).get('id') == self.element_id and self.ancestors is None:
            self.ancestors = [description for _, description in self.stack]
        self.stack.append((tag, self.describe(tag, attrs)))

    def handle_endtag(self, tag):
        # Закрываем ближайший открытый тег с таким именем — так же поступает браузер
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def get_ancestor_chain(html_text, element_id):
    """Возвращает цепочку предков элемента (от внешнего к внутреннему), например ['html', 'body'].

    Если элемента на странице нет, возвращает None.
    """
    parser = AncestorChainParser(element_id)
    parser.feed(html_text)
    return parser.ancestors


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

    def test_button_background_is_accent_orange(self):
        """Фон кнопки — акцентный оранжевый сайта #ff8b00 (тот же цвет, что был при наведении)."""
        match = re.search(r'background-color\s*:\s*rgba\(([^)]*)\)', self.button_rule)
        self.assertIsNotNone(match, 'У кнопки нет полупрозрачного rgba-фона.')
        parts = [part.strip() for part in match.group(1).split(',')]
        self.assertEqual(parts[:3], list(BUTTON_BACKGROUND_RGB))  # #ff8b00
        self.assertLess(float(parts[3]), 1)                       # alpha < 1 — полупрозрачность
        self.assertEqual(parts[3], BUTTON_BACKGROUND_ALPHA)

    def test_hover_does_not_change_button_color(self):
        """Кнопка всегда одного цвета: правило :hover не задаёт другой фон (или его нет вовсе)."""
        hover_blocks = re.findall(r'\.back-to-top:hover[^{]*\{([^}]*)\}', self.style_css)
        for block in hover_blocks:
            match = re.search(r'background-color\s*:\s*rgba\(([^)]*)\)', block)
            if match is None:
                continue
            parts = [part.strip() for part in match.group(1).split(',')]
            self.assertEqual(
                parts,
                list(BUTTON_BACKGROUND_RGB) + [BUTTON_BACKGROUND_ALPHA],
                'Фон кнопки при наведении отличается от постоянного оранжевого.',
            )

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


class BaseTemplateStructureTests(TestCase):
    """Структура страницы: подвал закрыт, а кнопка «наверх» и баннер cookie — прямые потомки <body>.

    Регрессия: в templates/base/footer.html закрывающая последовательность комментария
    стояла раньше конца выключенного блока, поэтому </div>, </div> и </footer> попадали
    внутрь комментария. Подвал оставался незакрытым, и вся разметка после него (баннер
    cookie и кнопка «наверх») оказывалась внутри .row подвала. Bootstrap по правилу
    `.row > *` давал таким элементам width: 100%, и кнопка превращалась в прямоугольник
    во всю ширину экрана в самом низу страницы.
    """

    def setUp(self):
        # Главная страница отвечает 200 даже на пустой базе — БД для проверки не нужна
        self.content = self.client.get(reverse('home')).content.decode('utf-8')

    def test_back_to_top_button_is_direct_child_of_body(self):
        """Кнопка «наверх» лежит прямо в <body>: предки — только html и body."""
        self.assertEqual(
            get_ancestor_chain(self.content, BUTTON_ID), ['html', 'body'],
            'Кнопка «наверх» вложена не в <body>. Проверьте закрывающие теги в шаблонах '
            'макета: незакрытый тег утаскивает разметку внутрь .row подвала, а Bootstrap '
            'по правилу `.row > *` растягивает такие элементы на всю ширину экрана.',
        )

    def test_cookie_banner_is_direct_child_of_body(self):
        """Баннер согласия на cookies тоже лежит прямо в <body>."""
        self.assertEqual(
            get_ancestor_chain(self.content, COOKIE_BANNER_ID), ['html', 'body'],
            'Баннер cookie оказался внутри другой разметки — значит подвал или другой '
            'контейнер в шаблоне не закрыт.',
        )

    def test_footer_is_closed_before_button_markup(self):
        """Тег </footer> есть на странице и стоит раньше кнопки «наверх»."""
        footer_end = self.content.find('</footer>')
        self.assertGreater(footer_end, -1, 'На странице нет закрывающего тега </footer>.')
        self.assertLess(
            footer_end, self.content.find(f'id="{BUTTON_ID}"'),
            'Кнопка «наверх» идёт в разметке раньше </footer>: подвал не закрыт.',
        )


class HtmlCommentsGuardTests(SimpleTestCase):
    """Сторож битых HTML-комментариев в шаблонах макета.

    Комментарий в HTML закрывается первой последовательностью «-->». Если поставить её
    раньше конца выключенного блока, следующие за ней реальные теги попадают внутрь
    комментария и макет ломается незаметно (именно так сломалась кнопка «наверх»).
    Поэтому теги считаем в шаблонах БЕЗ комментариев.
    """

    def test_html_comments_are_closed(self):
        """В шаблонах макета нет незакрытых HTML-комментариев."""
        for template_name in LAYOUT_TEMPLATES:
            with self.subTest(template=template_name):
                _, comments_closed = strip_html_comments(read_template_file(template_name))
                self.assertTrue(
                    comments_closed,
                    f'В {template_name} HTML-комментарий не закрыт до конца файла: '
                    'всё, что ниже, браузер считает текстом комментария.',
                )

    def test_paired_tags_are_balanced(self):
        """Теги div и footer в шаблонах макета открыты и закрыты одинаковое число раз."""
        for template_name in LAYOUT_TEMPLATES:
            template_without_comments, _ = strip_html_comments(read_template_file(template_name))
            for tag in PAIRED_LAYOUT_TAGS:
                with self.subTest(template=template_name, tag=tag):
                    opens = len(re.findall(rf'<{tag}[\s>]', template_without_comments))
                    closes = len(re.findall(rf'</{tag}>', template_without_comments))
                    self.assertEqual(
                        opens, closes,
                        f'В {template_name} тег <{tag}> открыт {opens} раз, а закрыт {closes}. '
                        'Скорее всего HTML-комментарий закрывается раньше выключенного блока '
                        'и «съедает» закрывающие теги.',
                    )

# ---------------------------------------------------------------------------
# Настройки email из админки (модель core.EmailSettings)
# ---------------------------------------------------------------------------

# Состояние EMAIL_* «как на сервере, где в .env нет переменных EMAIL_*»: логин и
# пароль пустые. Этот же словарь используется как override_settings — тогда
# post_save-сигнал update_email_settings, срабатывающий при создании записи в
# тесте, не «протечёт» изменёнными значениями в остальные тесты процесса.
EMPTY_EMAIL_SETTINGS = {
    'EMAIL_HOST': 'smtp.yandex.ru',
    'EMAIL_PORT': 465,
    'EMAIL_USE_SSL': True,
    'EMAIL_USE_TLS': False,
    'EMAIL_HOST_USER': '',
    'EMAIL_HOST_PASSWORD': '',
    'DEFAULT_FROM_EMAIL': '',
    'SERVER_EMAIL': '',
}


class SendTestEmailTests(TestCase):
    """Тестовое письмо из админки обязано брать настройки из БД, а не из settings.

    На сервере переменных EMAIL_* в .env нет (settings.EMAIL_HOST_USER пустой), а
    сигнал update_email_settings обновляет settings только в том процессе, который
    обработал сохранение в админке. Поэтому тест-письмо обязано работать через
    get_connection с параметрами из EmailSettings — иначе падает с ошибкой
    аутентификации SMTP (или работает лишь иногда, сразу после сохранения).
    """

    def create_email_settings(self, **overrides):
        """Создаёт единственную запись настроек email (сохраняется под pk=1)."""
        values = {
            'email_host_user': 'shop@yandex.ru',
            'email_host_password': 'app-password',
            'default_from_email': 'shop@yandex.ru',
        }
        values.update(overrides)
        return EmailSettings.objects.create(**values)

    def send_test_email_with_empty_settings(self, to_email=None, **email_settings_values):
        """Создаёт настройки в БД и шлёт тест-письмо, пока EMAIL_* в settings пустые.

        override_settings подключён контекстным менеджером внутри теста, а не
        декоратором класса: запись в БД вызывает post_save-сигнал
        update_email_settings, который меняет settings, и это обязано откатиться в
        конце блока — при декораторе класса мутация «течёт» в следующие тесты.

        Патчим и get_connection, и send_mail: в тестовом окружении Django подменяет
        EMAIL_BACKEND на locmem, поэтому реальное SMTP-соединение не собирается —
        параметры подключения проверяем по аргументам вызова.
        """
        with override_settings(**EMPTY_EMAIL_SETTINGS):
            self.assertEqual(settings.EMAIL_HOST_USER, '')
            self.assertEqual(settings.EMAIL_HOST_PASSWORD, '')
            self.create_email_settings(**email_settings_values)
            with patch('core.signals.get_connection') as get_connection_mock:
                with patch('core.signals.send_mail') as send_mail_mock:
                    success, message = send_test_email(to_email)
        return success, message, send_mail_mock, get_connection_mock

    def test_credentials_are_taken_from_database(self):
        """Логин/пароль/сервер берутся из БД, хотя в settings они пустые."""
        success, message, _, get_connection_mock = self.send_test_email_with_empty_settings()
        self.assertTrue(success, message)
        kwargs = get_connection_mock.call_args.kwargs
        self.assertEqual(kwargs['host'], 'smtp.yandex.ru')
        self.assertEqual(kwargs['port'], 465)
        self.assertEqual(kwargs['username'], 'shop@yandex.ru')
        self.assertEqual(kwargs['password'], 'app-password')
        self.assertTrue(kwargs['use_ssl'])
        self.assertFalse(kwargs['use_tls'])

    def test_default_recipient_is_sender_email(self):
        """Без аргумента письмо уходит на адрес отправителя."""
        success, _, send_mail_mock, _ = self.send_test_email_with_empty_settings()
        self.assertTrue(success)
        kwargs = send_mail_mock.call_args.kwargs
        self.assertEqual(kwargs['recipient_list'], ['shop@yandex.ru'])
        self.assertEqual(kwargs['from_email'], 'shop@yandex.ru')

    def test_explicit_recipient_is_used(self):
        """Переданный адрес получателя попадает в recipient_list и в сообщение."""
        success, message, send_mail_mock, _ = self.send_test_email_with_empty_settings(
            to_email='client@example.com'
        )
        self.assertTrue(success, message)
        self.assertEqual(
            send_mail_mock.call_args.kwargs['recipient_list'], ['client@example.com']
        )
        self.assertIn('client@example.com', message)

    def test_disabled_sending_returns_error_and_does_not_send(self):
        """При выключенной отправке письмо не уходит, возвращается причина."""
        success, message, send_mail_mock, _ = self.send_test_email_with_empty_settings(
            email_enabled=False
        )
        self.assertFalse(success)
        self.assertIn('отключена', message)
        send_mail_mock.assert_not_called()

    def test_missing_settings_row_returns_error(self):
        """Без записи в БД возвращается понятная ошибка, а не исключение."""
        with patch('core.signals.send_mail') as send_mail_mock:
            success, message = send_test_email()
        self.assertFalse(success)
        self.assertIn('Настройки email не найдены', message)
        send_mail_mock.assert_not_called()

    def test_missing_sender_email_returns_error(self):
        """Пустой email отправителя — явная ошибка, без попытки отправки."""
        success, message, send_mail_mock, _ = self.send_test_email_with_empty_settings(
            email_host_user=''
        )
        self.assertFalse(success)
        self.assertIn('Не указан email отправителя', message)
        send_mail_mock.assert_not_called()

    def test_missing_password_returns_error(self):
        """Пустой пароль приложения — явная ошибка, без попытки отправки."""
        success, message, send_mail_mock, _ = self.send_test_email_with_empty_settings(
            email_host_password=''
        )
        self.assertFalse(success)
        self.assertIn('Не указан пароль приложения', message)
        send_mail_mock.assert_not_called()

    def test_ssl_and_tls_together_return_error_not_exception(self):
        """Одновременно включённые SSL и TLS: возвращаем причину, а не падаем.

        Настоящий SMTP-бэкенд Django в такой комбинации бросает ValueError
        («EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive»). В тестах
        EMAIL_BACKEND подменён на locmem и эту проверку не выполняет, поэтому
        поведение SMTP-бэкенда воспроизводим через side_effect.
        """
        with override_settings(**EMPTY_EMAIL_SETTINGS):
            self.create_email_settings(email_use_ssl=True, email_use_tls=True)
            with patch(
                'core.signals.get_connection',
                side_effect=ValueError('EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive'),
            ):
                with patch('core.signals.send_mail') as send_mail_mock:
                    success, message = send_test_email()
        self.assertFalse(success)
        self.assertIn('Не удалось создать SMTP-соединение', message)
        send_mail_mock.assert_not_called()

    def test_explicit_settings_object_is_used(self):
        """Переданная запись настроек используется вместо записи из БД."""
        with override_settings(**EMPTY_EMAIL_SETTINGS):
            email_settings = self.create_email_settings()
            # Меняем объект только в памяти: функция обязана взять именно его
            email_settings.email_host = 'smtp.example.org'
            email_settings.email_host_user = 'other@example.org'
            with patch('core.signals.get_email_settings') as get_email_settings_mock:
                with patch('core.signals.get_connection') as get_connection_mock:
                    with patch('core.signals.send_mail') as send_mail_mock:
                        success, message = send_test_email(email_settings=email_settings)
        self.assertTrue(success, message)
        # Запись из БД не запрашиваем, раз объект настроек передали явно
        get_email_settings_mock.assert_not_called()
        kwargs = get_connection_mock.call_args.kwargs
        self.assertEqual(kwargs['host'], 'smtp.example.org')
        self.assertEqual(kwargs['username'], 'other@example.org')
        self.assertEqual(
            send_mail_mock.call_args.kwargs['recipient_list'], ['other@example.org']
        )


class EmailSettingsAdminActionTests(TestCase):
    """Экшн «Отправить тестовое письмо» в админке настроек email.

    Экшн обязан использовать выбранную запись настроек (а не настройки процесса) и
    показывать результат отправки сообщением в админке.
    """

    def setUp(self):
        # Без прав суперпользователя админка не отдаст changelist и экшены
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username='root', email='root@example.org', password='secret-password'
        )
        self.client.force_login(self.user)
        # override_settings нужен, чтобы post_save-сигнал update_email_settings
        # не изменил настоящие settings процесса и не «протёк» в другие тесты
        with override_settings(**EMPTY_EMAIL_SETTINGS):
            self.email_settings = EmailSettings.objects.create(
                email_host_user='shop@yandex.ru',
                email_host_password='app-password',
                default_from_email='shop@yandex.ru',
            )
        self.changelist_url = reverse('admin:core_emailsettings_changelist')

    def test_changelist_page_opens_without_error(self):
        """Список настроек email открывается без ошибки (раньше отдавал 500).

        Причина была в email_status: format_html без аргументов бросает TypeError.
        """
        response = self.client.get(self.changelist_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Включено')

    def post_action(self, **extra_data):
        """Отправляет POST на changelist с выбранным экшеном и выбранной записью."""
        data = {
            'action': 'send_test_email_action',
            'index': '0',
            'select_across': '0',
            '_selected_action': [str(self.email_settings.pk)],
        }
        data.update(extra_data)
        return self.client.post(self.changelist_url, data, follow=True)

    def test_action_uses_selected_settings_object(self):
        """Тест-письмо отправляется с настройками выбранной записи."""
        with patch(
            'core.admin.send_test_email',
            return_value=(True, 'Тестовое письмо успешно отправлено на shop@yandex.ru'),
        ) as send_test_email_mock:
            response = self.post_action()
        called_settings = send_test_email_mock.call_args.kwargs['email_settings']
        self.assertEqual(called_settings.pk, self.email_settings.pk)
        self.assertEqual(called_settings.email_host_user, 'shop@yandex.ru')
        self.assertContains(response, 'успешно отправлено')

    def test_action_shows_error_message_when_sending_fails(self):
        """При ошибке отправки в админке показывается сообщение об ошибке."""
        with patch(
            'core.admin.send_test_email',
            return_value=(False, 'Ошибка отправки: 535 Authentication failed'),
        ):
            response = self.post_action()
        self.assertContains(response, 'Ошибка отправки: 535 Authentication failed')

    def test_action_does_not_send_without_selection(self):
        """Без выбранной записи экшн не пытается ничего отправлять."""
        with patch('core.admin.send_test_email') as send_test_email_mock:
            response = self.client.post(
                self.changelist_url,
                {'action': 'send_test_email_action', 'index': '0', 'select_across': '0'},
                follow=True,
            )
        self.assertEqual(response.status_code, 200)
        send_test_email_mock.assert_not_called()


