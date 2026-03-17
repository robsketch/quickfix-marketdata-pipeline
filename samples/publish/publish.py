from rtpy import Publisher, RTParams
from datetime import datetime, timedelta
import os
import sys
import random
import pykx as kx
import pandas as pd


VENDORS = ['Platinum Transport', 'Airport Taxi', 'Midtown', 'Precision Chauffeur',
           'Pocono Daytrips']
PAYMENT_TYPES = ['Cash', 'Debit', 'VISA', 'MasterCard', 'AMEX']


rt_cfg = os.environ.get('RT_CONFIG')
rt_dir = os.environ.get('RT_LOG_PATH')
pubs = int(os.environ.get('PUBLISHES', '10'))

if rt_cfg is None:
    print("Missing configuration for $RT_CONFIG")
    sys.exit(1)

if rt_dir is None:
    print("Missing configuration for $RT_DIR")
    sys.exit(1)

print('Connecting to RT with details:')
print(f'  config_url={rt_cfg}')
print(f'  rt_dir={rt_dir}')
print(f'  publishes={pubs}')

table_name = os.environ.get('PUB_TABLE')
if table_name is None:
    table_name = 'taxi'

print(f'Publishing to {table_name} table')

params = RTParams(config_url=rt_cfg, rt_dir=rt_dir)
with Publisher(params) as pub:
    print(f'Generating {pubs} publish events')
    for _ in range(pubs):
        table = []
        for _ in range(random.randint(1, 20)):
            vendor = VENDORS[random.randrange(len(VENDORS))]
            payment = PAYMENT_TYPES[random.randrange(len(PAYMENT_TYPES))]
            start = datetime.now()
            duration = random.randint(0, 300)
            end = start + timedelta(minutes=duration)
            fare = random.random() * 10
            trip = {
                'vendor': vendor,
                'pickup': datetime.now(),
                'dropoff': end,
                'passengers': kx.ShortAtom(random.randint(1, 7)),
                'distance': kx.RealAtom(random.random() * 100),
                'fare': kx.RealAtom(fare),
                'extra': kx.RealAtom(fare * .08),
                'tax': kx.RealAtom(fare * .13),
                'tip': kx.RealAtom(fare * .18),
                'tolls': kx.RealAtom(fare * .1),
                'fees': kx.RealAtom(fare * .05),
                'total': kx.RealAtom(fare * .54),
                'payment_type': payment
            }
            table.append(trip)

        df = pd.DataFrame.from_records(table)
        print(f'Publishing {len(table)} rows')
        pub(table_name, df)

print('Publishes complete')
