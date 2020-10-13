import hashlib

import scrapy
from scrapy.http import Request, Response

class InfosecConferencesSpider(scrapy.Spider):
    name = 'infosecconferences'
    website_url = 'https://infosec-conferences.com'

    def start_requests(self):
        for year in range(2020, 2022 + 1):
            for month in range(1, 12 + 1):
                for day in range(1, 31 + 1):
                    date = '%d-%02d-%02d' % (year, month, day)

                    yield scrapy.Request(
                        url=self.website_url + '/filter/?fwp_date=' + date + '%2C' + date,
                        callback=self.parse_search)

    def parse_search(self, response: Response):
        for href in response.xpath('//div[@class="fwpl-item el-vhkit"]//a/@href'):
            yield response.follow(url=href, callback=self.parse_event)

    def parse_event(self, response: Response):
        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'series': None,
            'direct_url': response.url,
            'event_website': response.xpath('//a[contains(text(), "Event Website")]/@href').get(default=None)
        }

        item['event_id'] = hashlib.sha256(bytes(response.url, 'utf8')).hexdigest()
        item['title'] = response.xpath('//div[@class="inside-page-hero grid-container grid-parent"]/h1/text()').get(default=None)
        item['summary'] = response.xpath('//div[@class="entry-content"]/p[not(@style)]/text()').getall()
        item['date'] = response.xpath('//div[@class="inside-page-hero grid-container grid-parent"]/div/text()[2]').get(default=None)
        item['virtual'] = True if response.xpath('//div[contains(text(), "online event")]') else False
        item['live'] = not item['virtual']
        item['tags'] = response.xpath('//ul[@class="post-categories"]/li/a/text()').getall()
        item['address'] = None
        item['country'] = response.xpath('//a[contains(@href, "country")]/text()').get(default=None)
        item['region'] = response.xpath('//a[contains(@href, "us-state")]/text()').get(default=None)
        item['city'] = response.xpath('//a[@rel="tag"]/text()').get(default=None)

        item['raw_locations_set'] = []

        if item['address'] is not None:
            item['raw_locations_set'].append(item['address'])

        item['raw_locations_set'].append(
            ' '.join(x for x in [item['city'], item['region'], item['country']] if x)
        )

        if item['city']:
            item['raw_locations_set'].append(item['city'])

        if item['region']:
            item['raw_locations_set'].append(item['region'])

        if item['country']:
            item['raw_locations_set'].append(item['country'])

        return item
