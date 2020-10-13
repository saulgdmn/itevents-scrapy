import hashlib

import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class FutureconeventsSpider(scrapy.Spider):
    name = 'futureconevents'
    website_url = 'https://futureconevents.com'

    def start_requests(self):
        yield SeleniumRequest(url='https://futureconevents.com/events/', callback=self.parse_events_page)

    def parse_events_page(self, response: Response):
        for item in response.xpath('//li[@class="fc-event fc-card"]'):
            button = item.xpath('ul/li[1]/a[contains(text(), "View Event")]')
            if button:
                yield SeleniumRequest(
                    url=self.website_url + button.xpath('@href').get(),
                    callback=self.parse_event,
                    meta={
                        'virtual': True if item.xpath('h3[contains(text(), "Virtual")]') else False,
                        'live': True if item.xpath('h3[contains(text(), "Live")]') else False,
                        'date': item.xpath('p[@class="date-time"]/text()').get()
                    })

    def parse_event(self, response: Response):
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
        item['title'] = response.xpath('//header[@class="fc-event-header"]/h1/span/text()').get(default=None)
        item['summary'] = response.xpath('//div[@class="et_pb_module et_pb_text et_pb_text_1  et_pb_text_align_left et_pb_bg_layout_light"]/div/*/text()').getall()
        item['date'] = response.meta.get('date')
        item['virtual'] = response.meta.get('virtual')
        item['live'] = response.meta.get('live')
        item['tags'] = []

        raw_locations_set = [
            response.xpath('//section[@class="block footer-widget-2"]//p[1]/text()[2]').get(default=None),
            response.xpath('//section[@class="block footer-widget-2"]//p[1]/text()[4]').get(default=None),
        ]

        item['raw_locations_set'] = [
            ' '.join(raw_locations_set),
            raw_locations_set[0],
            raw_locations_set[1]
        ]

        item['sponsors'] = list()
        for key, div in enumerate(response.xpath('//div[@class="fc-sponsor-items"]//div[@data-visual-label]')):
            item['sponsors'].append({
                'level': div.xpath('@data-visual-label').get().lower(),
                'logo': div.xpath('div/img/@src').get(default=None),
                'description': response.xpath('(//div[@class="fc-sponsor-info"])[{}]/p/text()'.format(key + 1)).get(default=None),
                'website': response.xpath('(//div[@class="fc-sponsor-info"])[{}]//a[@title="website"]/@href'.format(key + 1)).get(default=None),
                'name': None
            })

        return item
