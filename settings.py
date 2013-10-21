#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_PATH = os.path.join(ROOT_PATH, "tests")

ENV = os.environ.get('ENV', 'DEV')
if ENV == '':
    ENV = 'DEV'

envs = {
    'DEV': {
        'QUEUE_URI': 'redis://localhost:6379/11',
        'CACHE_URI': 'redis://localhost:6379/12',
        'DB_HOSTS': ['localhost:9160'],
        'MONGO_HOST': 'localhost:27017',
    },
    'TEST': {
        'QUEUE_URI': 'redis://ec2-107-22-142-71.compute-1.amazonaws.com:6379/11',
        'CACHE_URI': 'redis://ec2-107-22-142-71.compute-1.amazonaws.com:6379/12',
        'DB_HOSTS': [
            'ec2-54-224-101-163.compute-1.amazonaws.com:9160',
            'ec2-23-20-136-42.compute-1.amazonaws.com:9160',
            'ec2-54-242-132-111.compute-1.amazonaws.com:9160',
            'ec2-72-44-53-84.compute-1.amazonaws.com:9160',
            'ec2-184-73-45-244.compute-1.amazonaws.com:9160',
        ],
        'MONGO_HOST': 'ec2-54-227-0-188.compute-1.amazonaws.com:27017',
    },
}

for key, value in envs.get(ENV, envs['DEV']).iteritems():
    globals()[key] = value
