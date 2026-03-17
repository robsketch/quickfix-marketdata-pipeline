import os
from pprint import pprint
from kxi.query import Query
from datetime import datetime, timedelta
from rtpy import Publisher, RTParams
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




os.environ['INSIGHTS_URL'] = 'http://kxi-gw:8080'
query = Query(data_format='application/json', usage='MICROSERVICES')

# First check how many rows are in the 'taxi' table
start = datetime.now() - timedelta(hours=24)
end = datetime.now() + timedelta(hours=24)
res = query.get_data('taxi', start_time=start, end_time=end)
table_len = len(res)


# Get the meta data for the kdb Insights instance and select the API meta data
api_meta_data = query.get_meta()['api']

# Filter for just meta data related to custom APIs
custom_api_meta_data = [d['metadata'] for d in api_meta_data if d['custom']]

# Display the meta data for the custom API(s)
pprint(custom_api_meta_data)
print()

query.fetch_custom_apis()

# Call the custom API
params = {
    "table": "taxi",
    "column":"fare",
    "multiplier":10
}
result = query.example_daAPI(json=params)
pprint(result['payload'])
custom_api_result_len = len(result['payload'])

if table_len == custom_api_result_len:
    exit(0)
else:
    exit(1)
