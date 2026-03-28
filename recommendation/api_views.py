from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import get_recommendations_for_user


@api_view(['GET'])
def api_recommendations(request):
    try:
        limit = int(request.query_params.get('limit', 8))
    except (TypeError, ValueError):
        limit = 8
    limit = max(1, min(limit, 20))

    products, source, personalized_ids = get_recommendations_for_user(request.user, limit=limit)

    items = []
    for product in products:
        if source == 'itemcf' or (source == 'mixed' and product.id in personalized_ids):
            reason = '基于您的兴趣推荐'
        else:
            reason = '热门商品'
        items.append({
            'id': product.id,
            'name': product.name,
            'price': str(product.price),
            'image': product.image.url if product.image else '',
            'reason': reason,
        })

    return Response({'source': source, 'items': items})
