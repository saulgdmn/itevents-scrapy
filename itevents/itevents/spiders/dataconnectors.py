import hashlib

import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class DataconnectorsSpider(scrapy.Spider):
    name = 'dataconnectors'
    website_url = 'https://www.dataconnectors.com/attend/'

    def start_requests(self):
        yield SeleniumRequest(url='https://www.dataconnectors.com/attend/', callback=self.parse_events_page)
        yield SeleniumRequest(url='https://www.dataconnectors.com/past-events/', callback=self.parse_events_page)

    def parse_events_page(self, response: Response):
        for item in response.xpath('//div[@class="dc-event-tile-cont"]/ul/a'):
            if item.xpath('li/div[@class="ribbon"]/span[contains(text(), "VIRTUAL")]'):
                yield SeleniumRequest(
                    url=item.xpath('@href').get(),
                    callback=self.parse_virtual_event,
                    meta={
                        'city': item.xpath('li/div[@class="dc-event-tile-city"]/text()').get()
                    }
                )
            else:
                yield SeleniumRequest(
                    url=item.xpath('@href').get(),
                    callback=self.parse_live_event
                )

    def parse_virtual_event(self, response: Response):
        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'series': 'futurecon',
            'direct_url': response.url,
            'event_website': response.url
        }

        item['event_id'] = hashlib.sha256(bytes(response.url, 'utf8')).hexdigest()
        item['title'] = response.xpath('//title/text()').get(default=None)
        item['summary'] = None
        item['date'] = response.xpath('//div[@class="dc-event-date-mobile"]/text()').get(default=None)
        item['virtual'] = True
        item['live'] = False
        item['tags'] = []

        item['raw_locations_set'] = [response.meta.get('city')]

        item['sponsors'] = list()
        for sponsor in response.xpath('//li[@id="dc-right-column-cont"]//div[@class="dc-home-sponsor-tile-cont dc-event"]//img'):
            item['sponsors'].append({
                'level': None,
                'logo': sponsor.xpath('@src').get(),
                'website': None,
                'description': None,
                'name': sponsor.xpath('@title').get(),
            })

        return item

    def parse_live_event(self, response: Response):
        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'series': 'futurecon',
            'direct_url': response.url,
            'event_website': response.url
        }

        item['event_id'] = hashlib.sha256(bytes(response.url, 'utf8')).hexdigest()
        item['title'] = response.xpath('//title/text()').get(default=None)
        item['summary'] = ''
        item['date'] = response.xpath('//div[@class="dc-event-date-mobile"]/text()').get(default=None)
        item['virtual'] = False
        item['live'] = True
        item['tags'] = []

        raw_locations_set = response.xpath('//li[@id="dc-right-column-cont"]//div[@class="event-venue-address"]/text()').getall()
        item['raw_locations_set'] = [' '.join(raw_locations_set), raw_locations_set[-1]]

        item['sponsors'] = list()
        for sponsor in response.xpath('//li[@id="dc-right-column-cont"]//div[@class="dc-home-sponsor-tile-cont dc-event"]//img'):
            item['sponsors'].append({
                'level': 'vendor_partner',
                'logo': sponsor.xpath('@src').get(),
                'website': None,
                'description': None,
                'name': sponsor.xpath('@title').get(),
            })

        return item
