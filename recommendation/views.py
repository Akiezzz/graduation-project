from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import get_recommendations_for_user


@login_required
def recommendations(request):
    products, _, _ = get_recommendations_for_user(request.user, limit=12)
    return render(request, 'recommendation/list.html', {'products': products})
