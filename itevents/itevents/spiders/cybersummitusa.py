import hashlib

import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class CybersummitusaSpider(scrapy.Spider):
    name = 'cybersummitusa'
    website_url = 'https://cybersummitusa.com'

    def start_requests(self):
        yield SeleniumRequest(url='https://cybersummitusa.com/summits/', callback=self.parse_events_page)

    def parse_events_page(self, response: Response):

        for div in response.xpath('//div[@class="summit-half"]'):
            yield SeleniumRequest(
                url=div.xpath('div/center/a[contains(text(), "Details")]/@href').get(),
                callback=self.parse_event,
                meta={
                    'city': div.xpath('div/h4/text()').get(default=None),
                    'virtual': True if div.xpath('div/p[contains(text(), "Virtual Event")]') else False
                }
            )

    def parse_event(self, response: Response):
        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'direct_url': response.url,
            'event_website': response.url
        }

        item['event_id'] = hashlib.sha256(bytes(response.url, 'utf8')).hexdigest()
        item['title'] = '{} {}'.format(
            response.xpath('//div[@class="summit-wrapper"]//h1/text()').get(default=''),
            response.xpath('//div[@class="summit-wrapper"]//h3/text()').get(default='')
        )
        item['summary'] = [response.xpath('(//p[@class="heading"])[1]/text()').get(default=None)]
        item['virtual'] = response.meta.get('virtual')
        item['live'] = not item['virtual']
        item['tags'] = []

        if item['virtual']:
            item['date'] = response.xpath('(//div[@class="virtual-event-date-block"]//span)[1]/text()').get(default=None)
        else:
            item['date'] = response.xpath('//i[@class="fa fa-calendar fa- calendar-icon "]/../p/span/text()').get(default=None)

        item['raw_locations_set'] = list()

        if item['live']:
            item['raw_locations_set'] = response.xpath('//div[@class="venue-box-2019"]//p/text()').getall()
            item['address'] = ' '.join(item['raw_locations_set'])
        else:
            item['address'] = None

        item['raw_locations_set'].append(response.meta.get('city'))

        item['sponsors'] = list()
        for key, sponsor_level_div in enumerate(response.xpath('//center/h4')):
            level = sponsor_level_div.xpath('text()').get().split()[0].lower()

            for sponsor_div in sponsor_level_div.xpath('(//div[@class="lshowcase-logos"])[{}]/div/div'.format(key + 1)):
                item['sponsors'].append({
                    'level': level,
                    'website': sponsor_div.xpath('div/div/a/@href').get(default=None),
                    'description': None,
                    'logo': sponsor_div.xpath('div/div/a/img/@src').get(default=None),
                    'name': sponsor_div.xpath('div/div/a/img/@alt').get(default=None),
                })

        return item
