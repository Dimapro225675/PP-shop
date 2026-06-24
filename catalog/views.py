import re
from decimal import Decimal, InvalidOperation
from random import SystemRandom

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from users.services import RECOMMENDATION_LIMIT, initialize_user_recommendations

from .models import Product


FILTER_FIELDS = ('manufacturer', 'color', 'material', 'shape', 'installation_type')
CATEGORY_TITLES = dict(Product.Category.choices)
CATEGORY_ALIASES = {
    Product.Category.FAUCET: ('кран', 'краны', 'смеситель', 'смесители'),
    Product.Category.SINK: ('раковина', 'раковины', 'умывальник', 'умывальники'),
    Product.Category.BATHTUB: ('ванна', 'ванны'),
    Product.Category.SHOWER: ('душ', 'душевая', 'душевые', 'душевая программа'),
    Product.Category.PIPE: ('труба', 'трубы', 'трубопровод', 'трубопроводные системы'),
    Product.Category.TOILET: ('унитаз', 'унитазы', 'unitaz', 'unitazy'),
    Product.Category.OTHER: ('другое', 'инструменты', 'оборудование'),
}
SORT_OPTIONS = {
    'name': ('name', 'По названию'),
    'price_asc': ('price', 'Сначала дешевле'),
    'price_desc': ('-price', 'Сначала дороже'),
}


def _normalize_query(value):
    return ' '.join(value.lower().replace('ё', 'е').split())


def _matched_category(query):
    normalized_query = _normalize_query(query)
    for category, aliases in CATEGORY_ALIASES.items():
        if normalized_query in aliases:
            return category
    return None


def _direct_product_match(query):
    product = Product.objects.filter(name__iexact=query).first()
    if product:
        return product

    code_match = re.fullmatch(r'(?:VD[-\s]?)?0*(\d+)', query, flags=re.IGNORECASE)
    if not code_match:
        return None
    return Product.objects.filter(pk=int(code_match.group(1))).first()


def _decimal_label(value):
    return format(value.normalize(), 'f')


def _size_filter_query(raw_sizes):
    query = Q()
    valid_sizes = []

    for raw_size in raw_sizes:
        values = raw_size.split(':')
        try:
            if len(values) == 3 and values[0] == 'pipe':
                length, diameter = (Decimal(value) for value in values[1:])
                query |= Q(
                    category=Product.Category.PIPE,
                    length_cm=length,
                    diameter_cm=diameter,
                )
            elif len(values) == 4 and values[0] == 'box':
                length, width, height = (Decimal(value) for value in values[1:])
                query |= Q(
                    length_cm=length,
                    width_cm=width,
                    height_cm=height,
                ) & ~Q(category__in=(Product.Category.PIPE, Product.Category.OTHER))
            else:
                continue
        except InvalidOperation:
            continue
        valid_sizes.append(raw_size)

    return query, valid_sizes


def _size_facets(products):
    options = {}
    rows = products.values(
        'category',
        'length_cm',
        'width_cm',
        'height_cm',
        'diameter_cm',
    ).distinct()

    for row in rows:
        category = row['category']
        length = row['length_cm']
        if category == Product.Category.PIPE:
            diameter = row['diameter_cm']
            if length is None or diameter is None:
                continue
            value = f'pipe:{length}:{diameter}'
            label = f'{_decimal_label(length)} см × Ø {_decimal_label(diameter)} см'
        elif category == Product.Category.OTHER:
            continue
        else:
            width = row['width_cm']
            height = row['height_cm']
            if None in (length, width, height):
                continue
            value = f'box:{length}:{width}:{height}'
            label = (
                f'{_decimal_label(length)} × {_decimal_label(width)} × '
                f'{_decimal_label(height)} см'
            )
        options[value] = label

    return [
        {'value': value, 'label': label}
        for value, label in sorted(options.items(), key=lambda item: item[1])
    ]


def _search_products(products, query):
    tokens = _normalize_query(query).split()
    if not tokens:
        return products.none()

    token_query = Q()
    for token in tokens:
        token_query &= (
            Q(name__icontains=token)
            | Q(manufacturer__icontains=token)
            | Q(material__icontains=token)
            | Q(color__icontains=token)
            | Q(shape__icontains=token)
        )

    matches = products.filter(token_query)
    seed = matches.first()
    if not seed:
        return matches

    similar = products.filter(
        manufacturer__iexact=seed.manufacturer,
        category=seed.category,
    )
    return (matches | similar).distinct()


def _category_navigation():
    counts = {
        item['category']: item['count']
        for item in Product.objects.values('category').annotate(count=Count('id'))
    }
    return [
        {
            'value': value,
            'label': label,
            'count': counts.get(value, 0),
            'url': reverse('catalog:product_type', args=[value]),
        }
        for value, label in Product.Category.choices
    ]


def _guest_recommendations(request):
    stored_ids = request.session.get('recommended_product_ids', [])
    if stored_ids:
        products_by_id = Product.objects.in_bulk(stored_ids)
        return [
            products_by_id[product_id]
            for product_id in stored_ids
            if product_id in products_by_id
        ]

    product_ids = list(Product.objects.values_list('pk', flat=True))
    selected_ids = (
        SystemRandom().sample(product_ids, min(RECOMMENDATION_LIMIT, len(product_ids)))
        if product_ids
        else []
    )
    request.session['recommended_product_ids'] = selected_ids
    products_by_id = Product.objects.in_bulk(selected_ids)
    return [products_by_id[product_id] for product_id in selected_ids]


def home(request):
    if request.user.is_authenticated:
        recommendations = initialize_user_recommendations(request.user)
        recommended_products = [item.product for item in recommendations]
        favorite_product_ids = set(
            request.user.favorites.filter(
                product_id__in=[product.pk for product in recommended_products]
            ).values_list('product_id', flat=True)
        )
    else:
        recommended_products = _guest_recommendations(request)
        favorite_product_ids = set()

    return render(
        request,
        'catalog/home.html',
        {
            'recommended_products': recommended_products,
            'favorite_product_ids': favorite_product_ids,
        },
    )


def about(request):
    return render(request, 'catalog/about.html')


def contacts(request):
    return render(request, 'catalog/contacts.html')


def product_list(request, product_type=None):
    categories = dict(Product.Category.choices)
    if product_type is not None and product_type not in categories:
        raise Http404('Категория товара не найдена')

    raw_search_query = request.GET.get('q', '').strip()
    if raw_search_query and product_type is None:
        matched_category = _matched_category(raw_search_query)
        if matched_category:
            return redirect('catalog:product_type', product_type=matched_category)
        direct_product = _direct_product_match(raw_search_query)
        if direct_product:
            return redirect('catalog:product_detail', product_id=direct_product.pk)

    products = Product.objects.all()
    if product_type:
        products = products.filter(category=product_type)

    if raw_search_query:
        products = _search_products(products, raw_search_query)

    facet_source = products
    selected_filters = {
        field: request.GET.getlist(field)
        for field in FILTER_FIELDS
    }

    for field, selected_values in selected_filters.items():
        if selected_values:
            products = products.filter(**{f'{field}__in': selected_values})

    size_query, selected_sizes = _size_filter_query(request.GET.getlist('size'))
    selected_filters['size'] = selected_sizes
    if selected_sizes:
        products = products.filter(size_query)

    sort = request.GET.get('sort', 'name')
    if sort not in SORT_OPTIONS:
        sort = 'name'
    products = products.order_by(SORT_OPTIONS[sort][0], 'pk')

    installation_labels = dict(Product.InstallationType.choices)
    facets = {
        'manufacturer': facet_source.values_list('manufacturer', flat=True).distinct().order_by('manufacturer'),
        'color': facet_source.values_list('color', flat=True).distinct().order_by('color'),
        'material': facet_source.values_list('material', flat=True).distinct().order_by('material'),
        'shape': facet_source.values_list('shape', flat=True).distinct().order_by('shape'),
        'installation_type': [
            {'value': value, 'label': installation_labels.get(value, value)}
            for value in facet_source.values_list('installation_type', flat=True).distinct()
        ],
        'size': _size_facets(facet_source),
    }

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    favorite_product_ids = set()
    if request.user.is_authenticated:
        favorite_product_ids = set(
            request.user.favorites.filter(
                product_id__in=[product.pk for product in page_obj]
            ).values_list('product_id', flat=True)
        )

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'page_obj': page_obj,
        'product_type': product_type,
        'product_type_label': CATEGORY_TITLES.get(product_type),
        'type_navigation': _category_navigation(),
        'facets': facets,
        'selected_filters': selected_filters,
        'active_filter_count': sum(len(values) for values in selected_filters.values()),
        'sort': sort,
        'sort_options': [(value, label) for value, (_, label) in SORT_OPTIONS.items()],
        'query_string': query_params.urlencode(),
        'favorite_product_ids': favorite_product_ids,
        'search_query': raw_search_query,
        'catalog_overview': not raw_search_query and product_type is None,
        'type_catalog': not raw_search_query and product_type is not None,
    }
    return render(request, 'catalog/product_list.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    is_favorite = (
        request.user.is_authenticated
        and request.user.favorites.filter(product=product).exists()
    )
    return render(
        request,
        'catalog/product_detail.html',
        {
            'product': product,
            'is_favorite': is_favorite,
        },
    )
