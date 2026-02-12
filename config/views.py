from django.views.generic import TemplateView
from reviews.models import Review

class NurseryView(TemplateView):
    template_name = 'header/nursery.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = Review.objects.filter(is_approved=True).order_by('-created_at')[:6]  # Показываем последние 6 одобренных отзывов
        return context