from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from catalog import views
from catalog.models import Category, Product, Subcategory


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

