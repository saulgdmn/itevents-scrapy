import hashlib

import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class AlleventsSpider(scrapy.Spider):
    name = 'allevents'
    website_url = 'https://www.allevents.in'

    def response_is_ban(self, request, response: Response):
        return b'Too many requests' in response.body

    def start_requests(self):
        yield SeleniumRequest(url='https://allevents.in/location.php', callback=self.parse_countries_page)

    def parse_countries_page(self, response: Response):
        for a in response.xpath('//a[@class="h4-count skyload"]'):
            yield SeleniumRequest(
                url=a.xpath('@href').get(),
                callback=self.parse_cities_page,
                meta={
                    'country': a.xpath('text()').get(default=None)
                }
            )

    def parse_cities_page(self, response: Response):
        for a in response.xpath('//a[@class="skyload"]'):
            yield Request(
                url=a.xpath('@href').get() + '/all',
                callback=self.parse_events_page,
                meta={
                    'country': response.meta.get('country'),
                    'city': a.xpath('text()').get(default=None)
                }
            )

    def parse_events_page(self, response: Response):
        for href in response.xpath('//div[@class="title"]/a/@href'):
            yield Request(
                url=href.get(),
                callback=self.parse_event,
                meta={
                    'country': response.meta.get('country'),
                    'city': response.meta.get('city'),
                }
            )

        next_page = response.xpath('//a[contains(text(), "Show more events")]/@href')
        if next_page:
            yield response.follow(
                url=next_page.get(),
                callback=self.parse_events_page,
                meta={
                    'country': response.meta.get('country'),
                    'city': response.meta.get('city'),
                })

    def parse_event(self, response: Response):

        # skip
        if response.xpath('//label[@class="badge badge-important evnt-ended-label"]'):
            return

        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'direct_url': response.url,
            'event_website': response.xpath('(//span[contains(text(), "Web")]/../text())[2]').get(default=None) or response.url
        }

        item['event_id'] = hashlib.sha256(bytes(item['meta']['direct_url'], 'utf8')).hexdigest()
        item['title'] = response.xpath('//h1/text()').get(default=None)
        item['summary'] = [response.xpath('//div[@class="event-description-html"]/text()').get(default='')] + response.xpath('//div[@class="event-description-html"]//*/text()').getall()
        item['date'] = response.xpath('//span[@class="event-date" or contains(@class,"display_start_time")]/text()').get(default=None)
        item['virtual'] = True if response.xpath('//span[@class="full-venue" and contains(text(), "Online")]') else False
        item['live'] = not item['virtual']
        item['tags'] = []

        item['raw_locations_set'] = list()
        if item['virtual']:
            item['address'] = None
        else:
            raw_address = response.xpath('//span[@class="full-venue"]/text()').getall()
            item['address'] = ' '.join(raw_address)
            item['raw_locations_set'] = [
                ' '.join(raw_address[-4:]),
                ' '.join(raw_address[-3:]),
                ' '.join(raw_address[-2:]),
            ]

        item['raw_locations_set'].append(response.meta.get('country') + ' ' + response.meta.get('city'))
        return item