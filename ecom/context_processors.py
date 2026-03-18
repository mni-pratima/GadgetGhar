from .models import Category

def categories_processor(request):
    categories = Category.objects.exclude(name__iexact='default category')
    return {'categories': categories}
