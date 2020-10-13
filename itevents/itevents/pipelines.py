import json
import os

import dateparser
from scrapy.exceptions import DropItem
from geopy.geocoders import Nominatim


def is_duplicated(id, filename):
    if os.path.exists(filename) is False:
        return False

    with open(filename, 'r', encoding='utf8') as f:
        for line in f.readlines():
            row = json.loads(line)
            if id == row.get('id'):
                return True

    return False


def retrieve_location(raw_locations_set):
    for raw_loc in raw_locations_set:
        if raw_loc is None:
            continue

        nom = Nominatim(user_agent="iteventscraper")
        loc = nom.geocode(cleanup_text(raw_loc), language='en')

        if loc is None:
            continue

        loc_details = nom.reverse((loc.raw.get('lat'), loc.raw.get('lon')), language='en')
        if loc_details is None:
            continue

        return {
            'city': loc_details.raw['address'].get('city', None),
            'region': loc_details.raw['address'].get('state', None),
            'country': loc_details.raw['address'].get('country', None),
            'latitude': loc_details.raw.get('lat', None),
            'longitude': loc_details.raw.get('lon', None)
        }

    return {
        'city': None,
        'region': None,
        'country': None,
        'latitude': None,
        'longitude': None
    }


def cleanup_text(text):
    text = text.strip('\n\r')
    text = text.replace('\t', ' ')
    while '  ' in text:
        text = text.replace('  ', ' ')
    return text


def cleanup_tag(tag):
    return cleanup_text(tag) \
        .replace(' ', '_') \
        .replace(',', '_') \
        .lower()


def convert(input):
    if isinstance(input, dict):
        return {convert(key): convert(value) for key, value in input.items()}
    elif isinstance(input, list):
        return [convert(element) for element in input]
    elif isinstance(input, str):
        return input.encode('utf-8').decode('ascii', 'ignore')
    else:
        return input


def retrieve_date(date):
    if date is None:
        return None
    if '-' in date:
        date = date.split('-')[0]

    date = dateparser.parse(date)
    if date:
        return date.isoformat()
    else:
        return None



class IteventsPipeline:
    def process_item(self, item, spider):
        if is_duplicated(
                id=item.get('id'),
                filename=spider.settings.get('FEED_URI')):
            raise DropItem("Repeated items found: %s" % item.get('id'))

        if item.get('title', None):
            item['title'] = cleanup_text(item['title'])
        if item.get('summary', None):
            item['summary'] = '\n'.join(cleanup_text(x) for x in item['summary'] if x)
        if item.get('date', None):
            item['date'] = retrieve_date(item['date'])

        item['tags'] = [cleanup_tag(tag) for tag in item.get('tags', [])]

        item.update(retrieve_location(item.get('raw_locations_set', [])))
        del item['raw_locations_set']

        return convert(item)
