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
    """Фото товара: на десктопе — главное фото + сетка по 2 в ряд,
    на телефоне (<768px) — лента больших фото со свайпом, без миниатюр.

    Проверяем, что:
    * главное фото идёт ДО сетки фото (по 2 в ряд), а старого «столбика справа»
      (из-за него фото на странице товара выстраивались буквой «Г») больше нет;
    * каждое фото отдаётся через <picture>: телефону — крупная версия 600px
      (для свайп-ленты), десктопу — лёгкая миниатюра 150px;
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

    def test_gallery_desktop_grid_and_mobile_swipe_strip(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # берём только блок галереи: дальше на странице есть другие картинки
        html = response.content.decode()
        gallery = html[html.index('<div class="product-gallery'):
                       html.index('<!-- описание товара -->')]

        # маркер для мобильного CSS: фото есть → на телефоне лента вместо главного фото
        self.assertIn('class="product-gallery has-thumbs"', gallery)

        # десктоп: главное фото идёт ДО сетки фото, сетка — по 2 в ряд
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


        """В style.css есть мобильные правила: главное фото спрятано, лента без миниатюр."""
        css = (settings.BASE_DIR / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')

        self.assertIn('@media (max-width: 767.98px)', css)
        self.assertIn('.product-gallery.has-thumbs .main-image', css)   # прячем главное фото
        self.assertIn('overflow-x: auto', css)                          # прокрутка вбок
        self.assertIn('scroll-snap-type: x mandatory', css)             # остановка на фото
        self.assertIn('flex: 0 0 100%', css)                            # фото на всю ширину
        self.assertIn('border: none !important', css)                   # без рамки миниатюры

