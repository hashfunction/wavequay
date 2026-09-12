# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""One exact repository/source/run/attempt contract for original release records."""
import argparse
import json
import os
import re
from source_catalog import require


def _shape(record):
    require(isinstance(record,dict) and set(record)=={'repository','sourceCommit','runId','runAttempt'}
            and record['repository']=='hashfunction/wavequay'
            and isinstance(record['sourceCommit'],str) and re.fullmatch('[0-9a-f]{40}',record['sourceCommit'])
            and isinstance(record['runId'],str) and re.fullmatch('[1-9][0-9]{0,19}',record['runId'])
            and type(record['runAttempt']) is int and 0<record['runAttempt']<10**10,
            'Exact typed repository/source/run/attempt required')


def current(source_commit,environment=None):
    env=os.environ if environment is None else environment
    require(env.get('CI')=='true' and env.get('GITHUB_SHA')==source_commit
            and isinstance(env.get('GITHUB_RUN_ATTEMPT'),str)
            and re.fullmatch('[1-9][0-9]{0,9}',env['GITHUB_RUN_ATTEMPT']),
            'Current exact-source GitHub run/attempt environment required')
    record=dict(repository=env.get('GITHUB_REPOSITORY'),sourceCommit=source_commit,runId=env.get('GITHUB_RUN_ID'),
                runAttempt=int(env['GITHUB_RUN_ATTEMPT']))
    _shape(record)
    return record


def validate(record,expected):
    _shape(record);_shape(expected)
    require(record==expected,'Original evidence belongs to a different source/run/attempt')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-commit',required=True)
    print(json.dumps(current(parser.parse_args().source_commit),sort_keys=True))
