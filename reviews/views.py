from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ReviewForm
from orders.models import Order

def add_review(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if Order.objects.filter(email=email).exists():
                form.save()
                messages.success(request, 'Спасибо за ваш отзыв! Он будет опубликован после модерации.')
                return redirect('nursery')
            else:
                messages.error(request, 'Отзыв могут оставить только те, кто уже сделал заказ. Проверьте email.')
                return render(request, 'reviews/add_review.html', {'form': form})
    else:
        form = ReviewForm()
    return render(request, 'reviews/add_review.html', {'form': form})
