from django import template
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError

register = template.Library()


@register.simple_tag
def safe_thumbnail(image, alias):
    """Генерирует миниатюру с обработкой ошибок"""
    if not image:
        return ''
    try:
        thumbnailer = get_thumbnailer(image)
        thumbnail = thumbnailer[alias]
        return thumbnail.url
    except (InvalidImageFormatError, Exception):
        return ''
