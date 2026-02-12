from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ReviewForm

def add_review(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Спасибо за ваш отзыв! Он будет опубликован после модерации.')
            return redirect('nursery')
    else:
        form = ReviewForm()
    return render(request, 'reviews/add_review.html', {'form': form})
