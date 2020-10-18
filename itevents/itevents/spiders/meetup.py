import re
import csv
import datetime
import hashlib

import requests
import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class MeetupSpider(scrapy.Spider):
    name = 'meetup'
    website_url = 'https://www.meetup.com'

    def response_is_ban(self, request, response: Response):
        return b'Too many requests' in response.body

    def start_requests(self):

        worldcities = list()
        with open('worldcities.csv', 'r', encoding='ascii', errors='ignore') as f:
            data = csv.reader(f, delimiter=',')
            for row in data:
                worldcities.append(
                    {
                        'lat': row[2],
                        'lon': row[3]
                    }
                )
        #print(worldcities)

        for city in worldcities[1:]:
            response = requests.post(
                url="https://api.meetup.com/gql",
                headers={
                    "accept": "*/*",
                    "accept-language": "ru,en;q=0.9,uk;q=0.8",
                    "apollographql-client-name": "build-meetup web",
                    "content-type": "application/json",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site",
                    "x-meetup-view-id": "40a73604-469a-4027-8f52-6908122d5d58"
                },
                data=
                (
                    "{\"operationName\":\"categoryEvents\",\"variables\":"
                    "{\"startDateRange\":\"" + datetime.datetime.now().isoformat() + "\",\"lat\":" + str(city['lat']) + ",\"lon\":" + str(city['lon']) + ",\"first\":10000},"
                    "\"query\":\"query categoryEvents($lat: Float!, $lon: Float!, $topicId: Int, $startDateRange: DateTime, $endDateRange: DateTime, $first: Int, $after: String) "
                    "{\\n  searchEvents: upcomingEvents(search: {lat: $lat, lon: $lon, categoryId: $topicId, startDateRange: $startDateRange, endDateRange: $endDateRange}, input: {first: $first, after: $after}) "
                    "{\\n    pageInfo {\\n      hasNextPage\\n      endCursor\\n      __typename\\n    }"
                    "\\n    count\\n    recommendationSource\\n    recommendationId\\n    edges {"
                    "\\n      node {\\n        id\\n        group {\\n          id\\n          name\\n          urlname\\n          "
                    "timezone\\n          link\\n          groupPhoto {\\n            id\\n            baseUrl\\n            __typename\\n          }"
                    "\\n          __typename\\n        }\\n        description\\n        fee\\n        feeCurrency\\n        id\\n        title\\n        "
                    "dateTime\\n        eventPhoto {\\n          id\\n          baseUrl\\n          __typename\\n        }\\n        "
                    "venue {\\n          id\\n          name\\n          address1\\n          address2\\n          address3\\n          "
                    "city\\n          state\\n          country\\n          zip\\n          phone\\n          venueType\\n          __typename\\n        }"
                    "\\n        going {\\n          totalCount\\n          edges {\\n            metadata {\\n              memberGroupPhoto "
                    "{\\n                thumbUrl\\n                __typename\\n              }\\n              __typename\\n            }"
                    "\\n            __typename\\n          }\\n          __typename\\n        }\\n        link\\n        isSaved\\n        __typename\\n      }"
                    "\\n      __typename\\n    }\\n    __typename\\n  }\\n}\\n\"}"
                ),
            )

            if response.status_code != 200:
                continue

            data = response.json().get('data', None)
            if data is None:
                continue

            edges = data.get('searchEvents').get('edges', None)
            if edges is None:
                continue

            for edge in edges:
                node = edge.get('node', None)
                if node is None:
                    continue

                meta = {
                        'title': node.get('title', None),
                        'direct_url': node.get('link', None),
                    }

                venue = node.get('venue', None)
                if venue:
                    venue.update({
                        'virtual': True if venue.get('venueType', None) else False,
                        'address': venue.get('address1', None),
                        'city': venue.get('city', None),
                        'state': venue.get('state', None),
                        'country': venue.get('country', None),
                    })

                yield Request(
                    url=node.get('link'),
                    callback=self.parse_event,
                    meta=meta
                )

        return []


    def parse_event(self, response: Response):
        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'direct_url': response.meta.get('direct_url', None),
            'event_website': response.meta.get('direct_url', None)
        }

        item['event_id'] = hashlib.sha256(bytes(item['meta']['direct_url'], 'utf8')).hexdigest()
        item['title'] = response.meta.get('title', None)
        item['summary'] = response.xpath('//div[@class="event-description runningText"]/*/text()').getall()
        item['date'] = response.xpath('//time[@class="eventStatusLabel"]/span/text()', default=None).get()
        item['virtual'] = response.meta.get('virtual', None)
        item['live'] = not item['virtual']
        item['tags'] = []

        raw_locations = []
        if response.meta.get('city', None):
            raw_locations.append(response.meta['city'])
        if response.meta.get('state', None):
            raw_locations.append(response.meta['state'])
        if response.meta.get('country', None):
            raw_locations.append(response.meta['country'])

        item['raw_locations_set'] = list()
        if response.meta.get('address', None):
            item['raw_locations_set'].append(response.meta['address'])

        item['raw_locations_set'].append(','.join(raw_locations))
        item['raw_locations_set'] += raw_locations

        return item