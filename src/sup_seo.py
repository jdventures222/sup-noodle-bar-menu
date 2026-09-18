"""SUP's crawl surface, from its own menu data: one Restaurant per location with the menu nested
as JSON-LD, and the web app manifest. The two locations are the ones the page's footer prints;
release.py checks they still agree."""
import json
from decimal import Decimal, ROUND_HALF_UP

HOST = 'https://menu.fyt.life/sup/'
LOCATIONS = [
    {'street': '5141 Beach Blvd Unit B', 'city': 'Buena Park', 'zip': '90621', 'phone': '714-521-2444'},
    {'street': '14370 Culver Dr Unit 2H', 'city': 'Irvine', 'zip': '92604', 'phone': '657-300-8420'},
]


def amount(n):
    value = Decimal(str(n)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return str(int(value)) if value == int(value) else format(value, '.2f')


def menu(structure, s):
    sections = []
    for sec in structure['sections']:
        items = []
        for it in sec['items']:
            key = 'item.' + it['id']
            item = {'@type': 'MenuItem', 'name': s[key + '.name']}
            text = ' '.join(s[key + '.' + suffix] for suffix in ('tagline', 'desc') if key + '.' + suffix in s)
            if text:
                item['description'] = text
            rows = []
            for p in it['prices']:
                if p.get('plus'):
                    continue  # an add-on delta is not the dish's price
                offer = {'@type': 'Offer', 'price': amount(p['p']), 'priceCurrency': 'USD'}
                if 'k' in p:
                    offer['name'] = s[key + '.price.' + p['k']]
                rows.append(offer)
            if rows:
                item['offers'] = rows[0] if len(rows) == 1 else rows
            items.append(item)
        sections.append({'@type': 'MenuSection', 'name': s['sec.' + sec['id'] + '.title'], 'hasMenuItem': items})
    return {'@type': 'Menu', 'name': s['ui.title'], 'hasMenuSection': sections}


def jsonld(structure, s):
    prices = [p['p'] for sec in structure['sections'] for it in sec['items'] for p in it['prices'] if not p.get('plus')]
    places = [{'@context': 'https://schema.org', '@type': 'Restaurant', 'name': s['ui.brand'], 'url': HOST,
               'image': HOST + 'img/social-logo.png',
               'address': {'@type': 'PostalAddress', 'streetAddress': loc['street'], 'addressLocality': loc['city'],
                           'addressRegion': 'CA', 'postalCode': loc['zip'], 'addressCountry': 'US'},
               'telephone': loc['phone'], 'servesCuisine': ['Vietnamese'],
               'priceRange': f'${amount(min(prices))} to ${amount(max(prices))}', 'hasMenu': menu(structure, s)}
              for loc in LOCATIONS]
    return json.dumps(places, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def manifest(s):
    return json.dumps({'name': s['ui.title'], 'short_name': 'SUP', 'description': s['ui.tagline'], 'start_url': './',
                       'display': 'minimal-ui', 'lang': 'en', 'background_color': '#F6F2ED', 'theme_color': '#FFFFFF',
                       'icons': [{'src': 'img/logo.png', 'sizes': '320x320', 'type': 'image/png'}]},
                      ensure_ascii=False, indent=1) + '\n'
