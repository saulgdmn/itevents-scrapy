import os
import json
import argparse
import logging
import subprocess

from pprint import pprint

import boto3
import boto3.exceptions

client = boto3.client('firehose')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

log = logging.getLogger(__name__)

DELIVERY_STREAM_NAME = 'hm-scraping-data'
DATA_PATH = './data/'
FIREHOSE_RECORDS = './data/firehose_records.json'
SPIDER_NAMES = [
    'cybersummitusa',
    'dataconnectors',
    'f2fevents',
    'futureconevents',
    'infosecconferences',
    'secureworldexpo',
    'allevents'
]


def is_record_pushed(record):
    if os.path.exists(FIREHOSE_RECORDS) is False:
        return False

    with open(FIREHOSE_RECORDS, 'r') as f:
        for r in json.load(f):
            if r.get('id') == record.get('id'):
                return True
    return False


def update_pushed_records(record):

    if os.path.exists(FIREHOSE_RECORDS):
        with open(FIREHOSE_RECORDS, 'r') as f:
            data = json.load(f)
    else:
        data = []

    data.append(record)

    with open(FIREHOSE_RECORDS, 'w') as f:
        json.dump(data, f)


def load_local_records(filename):
    if os.path.exists(filename) is False:
        return []

    with open(filename) as f:
        return [json.loads(line) for line in f.readlines() if line]


def push_record_to_firehose(record):
    try:
        response = client.put_record(
            DeliveryStreamName=DELIVERY_STREAM_NAME,
            Record={
                'Data': (json.dumps(record) + '\n').encode('utf8')
            }
        )
    except boto3.exceptions.Boto3Error as e:
        log.warning('Failed to push: %s', str(e))
        return None

    return response.get('RecordId', None)


def run_crawl(spider_name, force=False):
    log.info('Starting crawling for %s..', spider_name)

    if force:
        filename = os.path.join(DATA_PATH, spider_name + '.jsonlines')
        os.remove(filename)

    subprocess.run(
        args='scrapy crawl {} -s FEED_URI="{}{}.jsonlines"'.format(
            spider_name, DATA_PATH, spider_name),
        shell=True,
        encoding='utf-8')

    log.info('Finished!')


def run_push(spiders_name, force=False):
    for file in [os.path.join(DATA_PATH, spider + '.jsonlines') for spider in spiders_name]:
        log.info('Pushing %s to firehose..', file)
        records = load_local_records(file)
        log.info('%d records was founded locally.', len(records))

        records_to_push = [r for r in records if force or is_record_pushed(r) is False]
        log.info('%d records can be pushed.', len(records_to_push))

        for key, record in enumerate(records_to_push):
            log.info('Pushing %s (%d/%d)', record.get('id'), key + 1, len(records_to_push))

            if record.get('sponsors', None):
                log.info('Pushing sponsors..')
                for key_sponsor, sponsor in enumerate(record.get('sponsors')):
                    log.info('Pushing (%d/%d)', key_sponsor + 1, len(record.get('sponsors')))
                    push_record_to_firehose({
                        'id': record.get('id', None),
                        'meta': record.get('meta', None),
                        'event': {
                            'event_id': record.get('event_id', None),
                            'title': record.get('title', None),
                            'date': record.get('date', None),
                            'virtual': record.get('virtual', None),
                            'country': record.get('country', None),
                            'region': record.get('region', None),
                            'city': record.get('city', None),
                            'latitude': record.get('latitude', None),
                            'longitude': record.get('longitude', None),
                        },
                        'name': sponsor.get('name', None),
                        'level': sponsor.get('level', None),
                        'website': sponsor.get('website', None),
                        'description': sponsor.get('description', None),
                        'logo': sponsor.get('logo', None)
                    })

                del record['sponsors']

            record_id = push_record_to_firehose(record)
            if not record_id:
                log.warning('Failed.')
                continue

            update_pushed_records({
                'id': record.get('id'),
                'record_id': record_id
            })

    log.info('Finished!')


def run():
    parser = argparse.ArgumentParser()

    parser.add_argument('command', action='store', choices=['crawl', 'backup', 'push'])
    parser.add_argument('--spider_name', action='store', default='all', choices=['all'] + SPIDER_NAMES)
    parser.add_argument('--force', action='store_true', default=False)

    args = parser.parse_args()

    if args.command == 'crawl':
        if args.spider_name == 'all':
            for name in SPIDER_NAMES:
                run_crawl(spider_name=name, force=args.force)
        else:
            run_crawl(spider_name=args.spider_name, force=args.force)

    if args.command == 'backup':
        pass

    if args.command == 'push':
        if args.spider_name == 'all':
            run_push(spiders_name=SPIDER_NAMES, force=args.force)
        else:
            run_push(spiders_name=[args.spider_name], force=args.force)


if __name__ == '__main__':

    run()


