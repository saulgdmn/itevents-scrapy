import hashlib

import scrapy
from scrapy.http import Request, Response
from scrapy_selenium import SeleniumRequest


class SecureworldexpoSpider(scrapy.Spider):
    name = 'secureworldexpo'
    website_url = 'https://www.secureworldexpo.com'

    def start_requests(self):
        yield SeleniumRequest(url='https://www.secureworldexpo.com/events', callback=self.parse_events_page)
        yield SeleniumRequest(url='https://www.secureworldexpo.com/past-events', callback=self.parse_past_events_page)

    def parse_events_page(self, response: Response):
        for div in response.xpath('//div[@class="event upcoming"]'):
            yield SeleniumRequest(
                url='https:' + div.xpath('a/@href').get(),
                callback=self.parse_event,
                meta={
                    'city': div.xpath('div[@class="event-header"]//h2/text()').get()
                })

    def parse_past_events_page(self, response: Response):
        for li in response.xpath('//li[@class="event past"]'):
            yield SeleniumRequest(
                url='https:' + li.xpath('a/@href').get(),
                callback=self.parse_event,
                meta={
                    'city': li.xpath('div[@class="event-header"]//h2/text()').get()
                })


    def parse_event(self, response: Response):
        item = dict()

        item['id'] = hashlib.sha256(bytes(self.name + ':' + response.url, 'utf8')).hexdigest()
        item['meta'] = {
            'scraper_id': self.name,
            'site': self.website_url,
            'direct_url': response.url,
            'event_website': response.xpath('//div[@class="venue-website"]/a/@href').get(default=None)
        }

        item['event_id'] = hashlib.sha256(bytes(response.url, 'utf8')).hexdigest()
        item['title'] = response.xpath('//h1[@class="big-title"]/text()').get(default=None)
        item['summary'] = response.xpath('//div[@class="entry-content"]/p[not(@style)]/text()').getall()
        item['date'] = response.xpath('//span[@class="event-date"]/text()').get(default=None)
        item['virtual'] = True if response.xpath('//div[contains(text(), "online platform")]') else False
        item['live'] = not item['virtual']
        item['tags'] = response.xpath('//ul[@class="post-categories"]/li/a/text()').getall()

        item['raw_locations_set'] = [response.meta.get('city')]

        item['sponsors'] = []
        for div in response.xpath('//div[@class="sponsors"]//li[contains(@class, "sponsors")]'):
            level = div.xpath('@class').get().split()[0].split('-')[0]
            for logo in div.xpath('div/div[@class="logo"]'):
                item['sponsors'].append({
                    'level': level,
                    'name': None,
                    'description': None,
                    'website': logo.xpath('a/@href').get(default=None),
                    'logo': logo.xpath('a/img/@src').get(default=None)
                })

        yield SeleniumRequest(
            url='https://events.secureworldexpo.com/{}/?show=exhibitors-info'.format(
                response.xpath('//a[contains(text(), "View Agenda")]/@href').get()
            ),
            callback=self.parse_exhibitors,
            meta={
                'item': item
            }
        )

    def parse_exhibitors(self, response):
        item = response.meta.get('item')

        sponsors = []
        for sponsor in item.get('sponsors'):
            sponsors.append({
                'level': sponsor['level'],
                'name': response.xpath(
                    '//li[@class="exhibitor-block"]//a[contains(@href, "{}")]/../..//div[@class="title"]/text()'.format(
                        sponsor['website']
                    )
                ).get(default=None),
                'description': ' '.join(
                    response.xpath(
                        '//li[@class="exhibitor-block"]//a[contains(@href, "{}")]/../..//div[@class="description"]//*/text()'.format(
                            sponsor['website']
                    )).getall()
                ),
                'website': sponsor['website'],
                'logo': sponsor['logo'],
            })

        item['sponsors'] = sponsors
        yield item
