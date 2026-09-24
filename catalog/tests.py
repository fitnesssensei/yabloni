import io
import re
import shutil
import tempfile
from unittest.mock import patch

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
    """Галерея товара: главное фото сверху, под ним сетка миниатюр по 2 в ряд.

    Проверяем, что старый «столбик миниатюр справа» (из-за него фото на странице
    товара выстраивались буквой «Г») больше не используется, а все миниатюры
    рендерятся не пустыми ссылками (иначе браузер показывает значок «битая картинка»).
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

    def test_gallery_shows_main_image_above_thumbnail_grid(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # берём только блок галереи: дальше на странице есть другие картинки
        html = response.content.decode()
        gallery = html[html.index('<div class="product-gallery"'):
                       html.index('<!-- описание товара -->')]

        # главное фото идёт ДО сетки миниатюр, миниатюры — по 2 в ряд
        self.assertIn('id="mainImage"', gallery)
        self.assertIn('class="thumbnails row row-cols-2 g-2"', gallery)
        self.assertLess(gallery.index('id="mainImage"'),
                        gallery.index('thumbnails row row-cols-2'))
        # старого «столбика справа» (буква Г) больше нет
        self.assertNotIn('d-flex flex-column gap-2', gallery)

        # 3 миниатюры отрисованы, у каждой есть data-src, основное фото подсвечено
        self.assertEqual(len(re.findall(
            r'<img[^>]+class="thumbnail[^"]*"[^>]+data-src="/media/', gallery)), 3)
        self.assertEqual(len(re.findall(r'class="thumbnail active"', gallery)), 1)

        # картинки отдаёт easy-thumbnails: 1 главное фото + 3 миниатюры, пустых src нет
        self.assertNotIn('src=""', gallery)
        self.assertEqual(len(re.findall(r'(?<!data-)src="/media/', gallery)), 4)

