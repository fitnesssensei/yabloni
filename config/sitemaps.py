from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Category, Product, Subcategory
from blog.models import BlogPost


class StaticSitemap(Sitemap):
    """Статические страницы: главная, питомник, правовая информация."""
    priority = 1.0
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['home', 'nursery', 'legal_info']

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()


class ProductSitemap(Sitemap):
    priority = 0.7
    changefreq = 'daily'
    protocol = 'https'

    def items(self):
        return Product.objects.filter(available=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated


class SubcategorySitemap(Sitemap):
    """Страницы-фильтры «категория/подкатегория». Низкий приоритет:
    контент почти дублирует страницу категории."""
    priority = 0.3
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return Subcategory.objects.all()

    def location(self, obj):
        category = Category.objects.filter(products__subcategories=obj).first()
        if not category:
            return None
        return reverse('catalog:product_list_by_category_subcategory',
                       args=[category.slug, obj.slug])

    def lastmod(self, obj):
        latest = obj.products.order_by('-updated').first()
        return latest.updated if latest else None


class BlogPostSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        return BlogPost.objects.filter(is_published=True)

    def location(self, obj):
        return reverse('blog:blog_detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


