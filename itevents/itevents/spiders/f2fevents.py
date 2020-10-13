import re
import hashlib

import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class F2feventsSpider(scrapy.Spider):
    name = 'f2fevents'
    website_url = 'https://f2fevents.com'

    def start_requests(self):
        yield SeleniumRequest(url='https://f2fevents.com/events/upcoming/', callback=self.parse_events_page)
        yield SeleniumRequest(url='https://f2fevents.com/events/past/', callback=self.parse_events_page)

    def parse_events_page(self, response: Response):
        for item in response.xpath('//div[@class="row"]//div[@class="caption"]'):
            yield SeleniumRequest(
                url=item.xpath('h3[@class="caption-title"]/a/@href').get(),
                callback=self.parse_event,
                meta={
                    'title': item.xpath('h3[@class="caption-title"]/a/text()').get(),
                    'date': item.xpath('p[@class="caption-category"]/text()').get()
                })

        next_page = response.xpath('//a[@class="next page-numbers"]/@href')
        if next_page:
            yield SeleniumRequest(url=next_page.get(), callback=self.parse_events_page)

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
        item['title'] = response.meta.get('title')
        item['summary'] = response.xpath('//div[@style="padding: 0 40px 40px 0;"]/p/text()').getall()
        item['date'] = response.meta.get('date')
        item['virtual'] = True if response.xpath('//div[@class="three-fifth last"]/p[contains(text(), "virtual")]') else False
        item['live'] = not item['virtual']
        item['tags'] = []

        item['raw_locations_set'] = list()
        raw_locations_set = response.xpath('//div[@class="on-gmap color"]/p/text()').getall()
        if not raw_locations_set:
            item['raw_locations_set'].append(' '.join(raw_locations_set[1:]))

            for x in raw_locations_set:
                item['raw_locations_set'].append(x)

        item['raw_locations_set'].append(
            re.search('INTERFACE-([\sa-zA-Z]+) [\d]{4}', response.meta.get('title')).group(1))

        item['sponsors'] = list()
        for h4 in response.xpath('//h4[contains(text(), "SPONSORS")]'):
            level = h4.xpath('text()').get().split()[0].lower()

            sponsor = dict()
            for div in h4.xpath('../..//div[@class="modal-content"]'):
                sponsor['level'] = level
                sponsor['name'] = div.xpath('div[@class="modal-header"]/h4[@class="modal-title"]/text()').get(
                    default=None)
                sponsor['website'] = div.xpath('div[@class="modal-footer"]/a/@href').get(default=None)
                sponsor['logo'] = div.xpath('div[@class="modal-body"]//img/@src').get(default=None)
                sponsor['description'] = div.xpath('div[@class="modal-body"]//div[@style="display: table-cell; vertical-align: middle;"]/text()').get(default=None)

            item['sponsors'].append(sponsor)

        return item
