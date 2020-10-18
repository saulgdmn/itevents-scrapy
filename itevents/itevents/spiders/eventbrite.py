import re
import hashlib

import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class EventbriteSpider(scrapy.Spider):
    name = 'eventbrite'
    website_url = 'https://www.allevents.in'

    countries = [
        'united-states',
        'online',
        'canada',
        'australia',

    ]

    def response_is_ban(self, request, response: Response):
        return b'Too many requests' in response.body

    def start_requests(self):

        for country in self.countries:
            yield Request(
                url='https://www.eventbrite.com/d/{}/all-events/?page={}'.format(country, 1),
                callback=self.parse_event_page,
                meta={
                    'country': country,
                    'page': 1
                }
            )

    def parse_event_page(self, response: Response):
        for li in response.xpath('//ul[@class="search-main-content__events-list"]/li'):
            yield Request(
                url=li.xpath('div/div/div/div/div/div/article/aside/a/@href').get().split('?')[0],
                callback=self.parse_event,
                meta={
                    'date': li.xpath('div/div/div/div/div/div/article/div/div/div/div/div/text()').get(default=None)
                }
            )

        no_events = response.xpath('//div[contains(text(), "No events match your search")]')
        if not no_events:
            yield Request(
                url='https://www.eventbrite.com/d/{}/all-events/?page={}'.format(
                    response.meta.get('country'), response.meta.get('page') + 1
                ),
                callback=self.parse_event_page,
                meta={
                    'country': response.meta.get('country'),
                    'page': response.meta.get('page') + 1
                }
            )

    def parse_event(self, response: Response):
        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'direct_url': response.url,
            'event_website': response.xpath('(//span[contains(text(), "Web")]/../text())[2]').get(default=None) or response.url
        }

        item['event_id'] = hashlib.sha256(bytes(item['meta']['direct_url'], 'utf8')).hexdigest()
        item['title'] = response.xpath('//h1[@class="listing-hero-title"]/text()').get(default=None)
        item['summary'] = response.xpath('//div[@class="structured-content-rich-text structured-content__module l-align-left l-mar-vert-6 l-sm-mar-vert-4 text-body-medium"]/*/text()').getall()
        item['date'] = response.meta.get('date')
        item['virtual'] = True if response.xpath('//div[@class="event-details__data"]/p[contains(text(), "Online Event")]') else False
        item['live'] = not item['virtual']
        item['tags'] = response.xpath('//section/span/a/span/text()').getall()

        item['raw_locations_set'] = list()
        if item['virtual']:
            item['address'] = None
        else:
            '''
            raw_address = response.xpath('//div[@class="event-details__data"]/p/text()').getall()
            item['address'] = ' '.join(raw_address)
            item['raw_locations_set'] = [
                ' '.join(raw_address[-4:]),
                ' '.join(raw_address[-3:]),
                ' '.join(raw_address[-2:]),
            ]
            '''

            raw_address = response.xpath('//p[@class="listing-map-card-street-address text-default"]/text()').get(default=None)
            item['address'] = raw_address
            item['raw_locations_set'] = [
                raw_address,
                ' '.join(raw_address.split(',')[-3:]),
                ' '.join(raw_address.split(',')[-2:]),
            ]

        return item