import io
import re
import shutil
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog import views
from catalog.models import Category, Product, ProductImage, Subcategory


# Временная папка для картинок в тестах галереи (чтобы не мусорить в media/)
GALLERY_TEST_MEDIA = tempfile.mkdtemp()


def make_png_bytes():
    """Возвращает байты настоящей PNG-картинки 600x600 (для ProductImage в тестах)."""
    buffer = io.BytesIO()
    Image.new('RGB', (600, 600), (120, 170, 90)).save(buffer, format='PNG')
    return buffer.getvalue()


class LegacySlugRedirectTests(TestCase):
    """301-редиректы со старых слагов (CATEGORY_SLUG_REDIRECTS / SUBREDIRECTS)."""

    def setUp(self):
        self.category = Category.objects.create(name='Черешни', slug='chereshnya')
        Subcategory.objects.create(name='Летние', slug='letnie')

    def test_old_category_slug_redirects_permanently(self):
        response = self.client.get('/catalog/chereshni/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/catalog/chereshnya/')

    def test_old_category_slug_with_subcategory_redirects(self):
        response = self.client.get('/catalog/chereshni/letnie/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/catalog/chereshnya/letnie/')

    def test_old_category_slug_with_unknown_subcategory_leads_to_category(self):
        response = self.client.get('/catalog/chereshni/nonexistent/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/catalog/chereshnya/')

    def test_actual_category_slug_is_not_redirected(self):
        response = self.client.get('/catalog/chereshnya/')
        self.assertEqual(response.status_code, 200)

    def test_unknown_slug_still_returns_404(self):
        response = self.client.get('/catalog/nonexistent/')
        self.assertEqual(response.status_code, 404)

    def test_old_slug_returns_404_when_actual_category_missing(self):
        """Если категория удалена (а не переименована) — редиректа быть не должно."""
        self.category.delete()
        response = self.client.get('/catalog/chereshni/')
        self.assertEqual(response.status_code, 404)

    def test_renamed_subcategory_redirects(self):
        with patch.dict(views.SUBCATEGORY_SLUG_REDIRECTS, {'letnih': 'letnie'}):
            response = self.client.get('/catalog/chereshnya/letnih/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/catalog/chereshnya/letnie/')


class ProductDetailNavTests(TestCase):
    """Ссылки на категории на странице товара берутся из БД, а не захардкожены."""

    def test_nav_links_use_category_slugs_from_db(self):
        category = Category.objects.create(name='Черешни', slug='chereshnya')
        product = Product.objects.create(
            name='Саженец черешни', slug='sazhenec-chereshni', category=category, price=1000,
        )
        response = self.client.get(product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse('catalog:product_list_by_category', args=['chereshnya']))


@override_settings(MEDIA_ROOT=GALLERY_TEST_MEDIA)
class ProductGalleryLayoutTests(TestCase):
    """Фото товара: главное фото + сетка фото по 2 в ряд.

    На телефоне (<768px) главное фото скрыто, а фото идут той же сеткой по 2 в ряд
    (свайп-ленту убрали: на телефоне было видно только первое фото).

    Проверяем, что:
    * главное фото идёт ДО сетки фото (по 2 в ряд), а старого «столбика справа»
      (из-за него фото на странице товара выстраивались буквой «Г») больше нет;
    * каждое фото отдаётся через <picture>: телефону — крупная версия 600px,
      десктопу — лёгкая миниатюра 150px;
    * у галереи есть маркер has-thumbs — по нему мобильный CSS прячет главное фото;
    * все ссылки не пустые (иначе браузер рисует значок «битая картинка»).
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(GALLERY_TEST_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        # категория и товар, как на реальной странице /catalog/<id>/<slug>/
        self.category = Category.objects.create(name='Яблони', slug='yabloni')
        self.product = Product.objects.create(
            name='Северный синап', slug='severnyj-sinap',
            category=self.category, price=1000, stock=5,
        )
        # загружаем 3 настоящие картинки (первая — основная)
        for index in range(3):
            ProductImage.objects.create(
                product=self.product,
                image=SimpleUploadedFile(
                    f'foto{index}.png', make_png_bytes(), content_type='image/png'),
                is_main=(index == 0),
            )

    def test_gallery_grid_is_two_columns_on_desktop_and_mobile(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # берём только блок галереи: дальше на странице есть другие картинки
        html = response.content.decode()
        gallery = html[html.index('<div class="product-gallery'):
                       html.index('<!-- описание товара -->')]

        # маркер для мобильного CSS: фото есть → главное фото на телефоне прячем (сетка 2 в ряд)
        self.assertIn('class="product-gallery has-thumbs"', gallery)

        # главное фото идёт ДО сетки, а сетка — по 2 в ряд и на десктопе, и на телефоне
        self.assertIn('id="mainImage"', gallery)
        self.assertIn('class="gallery-photos row row-cols-2 g-2"', gallery)
        self.assertLess(gallery.index('id="mainImage"'),
                        gallery.index('gallery-photos row row-cols-2'))
        # старого «столбика справа» (буква Г) больше нет
        self.assertNotIn('d-flex flex-column gap-2', gallery)

        # каждое фото отдаётся через <picture>: телефону 600px, десктопу 150px
        self.assertEqual(gallery.count('<picture>'), 3)
        self.assertEqual(gallery.count('media="(max-width: 767.98px)"'), 3)
        self.assertEqual(len(re.findall(r'srcset="/media/[^"]*600x600', gallery)), 3)
        self.assertEqual(len(re.findall(r'(?<!data-)src="/media/[^"]*150x150', gallery)), 3)

        # 3 фото с data-src (для клика на десктопе), одно помечено как основное
        self.assertEqual(len(re.findall(r'data-src="/media/', gallery)), 3)
        self.assertEqual(len(re.findall(r'class="thumbnail active"', gallery)), 1)

        # пустых ссылок нет (иначе браузер покажет «битую картинку»)
        self.assertNotIn('src=""', gallery)
        self.assertNotIn('srcset=""', gallery)

    def test_broken_image_is_not_rendered_in_gallery(self):
        broken = ProductImage.objects.create(
            product=self.product,
            image=SimpleUploadedFile(
                'broken.png', b'not an image', content_type='image/png'),
        )
        broken.image.delete(save=False)

        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        gallery = html[html.index('<div class="product-gallery'):
                       html.index('<!-- описание товара -->')]
        self.assertNotIn('broken.png', gallery)
        self.assertNotIn('src=""', gallery)
        self.assertNotIn('srcset=""', gallery)
        self.assertIn('class="product-gallery has-thumbs"', gallery)


    def test_style_css_mobile_gallery_is_two_column_grid(self):
        """Мобильный CSS: главное фото скрыто, а фото идут сеткой по 2 в ряд.

        Свайп-ленту убрали (на телефоне было видно только первое фото),
        поэтому в мобильном блоке не должно остаться правил прокрутки вбок.
        """
        css = (settings.BASE_DIR / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
        self.assertIn('@media (max-width: 767.98px)', css)

        # берём только мобильный блок (он последний в файле)
        mobile_css = css[css.index('@media (max-width: 767.98px)'):]

        self.assertIn('.product-gallery.has-thumbs .main-image', mobile_css)  # прячем главное фото
        self.assertIn('max-width: 100%', mobile_css)  # галерея на всю ширину → 2 фото крупные

        # свайп-ленты больше нет
        self.assertNotIn('overflow-x', mobile_css)
        self.assertNotIn('scroll-snap', mobile_css)
        self.assertNotIn('flex: 0 0 100%', mobile_css)


class CatalogCardLayoutTests(TestCase):
    """Карточки товара в каталоге: кнопка «Подробнее» не должна выходить за карточку.

    Раньше кнопка вылезала за границы карточки, и тест следит, чтобы причины не вернулись:
    * у карточки был жёсткий `height: 300px`, а длинное название товара
      («Купить саженец яблони Кандиль орловский») в него не влезало — контент уезжал вниз;
    * у кнопки была фиксированная ширина 150px, а на ширине экрана 768–991px
      колонка `col-md-3` уже 150px — кнопка вылезала вправо за карточку;
    * лишний `<br>` после цены добавлял пустую строку и выталкивал кнопку вниз.

    Тест проверяет разметку и правила CSS из шаблона (сам вёрстку браузер считает
    только визуально, поэтому вручную страницу дополнительно смотрят в браузере).
    """

    def setUp(self):
        self.category = Category.objects.create(name='Яблони', slug='yabloni')
        # длинное название, как у реальных товаров на странице /catalog/
        self.product = Product.objects.create(
            name='Купить саженец яблони Кандиль орловский',
            slug='kandil-orlovskij', category=self.category, price=1000,
        )

    def _catalog_html(self):
        """Возвращает HTML страницы каталога и проверяет, что она открывается."""
        response = self.client.get(reverse('catalog:product_list'))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    @staticmethod
    def _rule(html, selector):
        """Вырезает из HTML тело правила CSS по его селектору (до закрывающей скобки)."""
        start = html.index(f'{selector} {{')
        return html[start:html.index('}', start)]

    def test_card_height_is_min_not_fixed(self):
        """У карточки минимальная высота, а не жёсткие 300px (иначе кнопка вылезает вниз)."""
        html = self._catalog_html()
        card_css = self._rule(html, '.product-card')
        self.assertIn('min-height: 300px', card_css)
        # жёсткого height нет (минус-вариант min-height не считаем)
        self.assertIsNone(re.search(r'(?<!min-)height:\s*300px', card_css))

    def test_button_width_is_limited_by_card(self):
        """Ширина кнопки — 100% карточки, но не больше 150px (иначе вылезает вправо)."""
        html = self._catalog_html()
        # правило должно быть привязано к карточке каталога, а не к кнопке вообще
        button_css = self._rule(html, '.product-card .btn-success')
        self.assertIn('width: 100% !important', button_css)
        self.assertIn('max-width: 150px', button_css)

    def test_card_markup_keeps_button_inside_card(self):
        """Разметка карточки: длинное название, цена и кнопка — внутри одной карточки."""
        html = self._catalog_html()
        # карточка — ссылка на всю высоту колонки: все карточки в строке одной высоты
        self.assertIn('text-decoration-none text-dark d-block h-100', html)
        self.assertIn('class="card product-card"', html)
        # длинное название товара отображается
        self.assertIn(self.product.name, html)
        # цена выводится отдельной строкой, а не через лишний <br>
        self.assertIn('class="h5 mb-1 d-block"', html)
        self.assertNotIn('₽</span><br>', html)
        # кнопка «Подробнее» внутри карточки
        self.assertIn('<button class="btn btn-success mt-2">Подробнее</button>', html)

