import json
from datetime import datetime, timedelta

import requests
import rethinkdb as r
from flask import request, make_response, jsonify

from utils.db import get_db

config = json.load(open('config.json'))


class RatelimitCache(object):
    def __init__(self, expire_time=timedelta(0, 1, 0)):
        self.expire_time = expire_time
        self.cache = {}

    def __getitem__(self, item):
        c = self.cache[item]

        now = datetime.now()
        if now - c['timestamp'] < c['expire_time']:
            return c['data']

        self.cache.pop(item)
        return 0

    def get(self, item):
        return self.__getitem__(item)

    def __contains__(self, item):
        return item in self.cache

    def __setitem__(self, key, value):
        self.cache[key] = {
            'data': value,
            'timestamp': datetime.now(),
            'expire_time': self.expire_time
        }

    def expires_on(self, item):
        c = self.cache[item]

        return c['timestamp'] + c['expire_time']

    def set(self, key, value):
        return self.__setitem__(key, value)


cache = RatelimitCache()


def ratelimit(func, max_usage=5):
    def wrapper(*args, **kwargs):
        auth = request.headers.get('authorization', None)
        key = r.table('keys').get(auth).run(get_db())
        if key['unlimited']:
            return make_response(
                (*func(*args, **kwargs), {'X-RateLimit-Limit': 'Unlimited',
                                          'X-RateLimit-Remaining': 'Unlimited',
                                          'X-RateLimit-Reset': 2147483647}))
        if key['id'] in cache:
            usage = cache.get(key['id'])
            if usage < max_usage:
                cache.set(key['id'], usage + 1)
                return make_response((*func(*args, **kwargs),
                                      {'X-RateLimit-Limit': max_usage,
                                       'X-RateLimit-Remaining': max_usage - usage - 1,
                                       'X-RateLimit-Reset': cache.expires_on(key['id'])}))
            else:
                ratelimit_reached = key.get('ratelimit_reached', 0) + 1
                r.table('keys').get(auth).update({"ratelimit_reached": ratelimit_reached}).run(get_db())
                if ratelimit_reached % 5 == 0 and 'webhook_url' in config:
                    requests.post(config['webhook_url'],
                                  json={"embeds": [{
                                      "title": f"Application '{key['name']}' ratelimited 5 times!",
                                      "description": f"Owner: {key['owner']}\n"
                                      f"Total: {ratelimit_reached}"}]})
                return make_response((jsonify({'status': 429, 'error': 'You are being ratelimited'}), 429,
                                      {'X-RateLimit-Limit': max_usage,
                                       'X-RateLimit-Remaining': 0,
                                       'X-RateLimit-Reset': cache.expires_on(key['id'])}))
        else:
            cache.set(key['id'], 1)
            return make_response((*func(*args, **kwargs), {'X-RateLimit-Limit': max_usage,
                                                           'X-RateLimit-Remaining': max_usage - 1,
                                                           'X-RateLimit-Reset': cache.expires_on(key['id'])}))

    return wrapper
