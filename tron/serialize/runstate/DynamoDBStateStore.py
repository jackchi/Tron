import math
import pickle
from threading import Thread

import boto3

from tron.serialize.runstate.shelvestore import ShelveKey
from tron.serialize.runstate.shelvestore import ShelveStateStore
# from collections import namedtuple

# DynamoDBStateKey = namedtuple('DynamoDBStateKey', ['type', 'id'])
OBJECT_SIZE = 400000
REGION_NAME = 'us-west-1'


class DynamoDBStateStore(object):
    def __init__(self, name):
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
        self.client = boto3.client('dynamodb', region_name=REGION_NAME)
        self.name = name
        self.shelve = ShelveStateStore(name)
        self.table = self.dynamodb.Table(name.replace('/', '-'))

    def build_key(self, type, iden):
        """
        It builds a unique partition key. The key could be objects with __str__ method.
        """
        # TODO: build shorter keys?
        return ShelveKey(type, iden)

    def restore(self, keys) -> dict:
        """
        Fetch all under the same parition key(keys).
        ret: <dict of key to states>
        """
        def join(d1, d2):
            for k, v in d1.items():
                d2[k] = v

        def shelve_restore(keys, res):
            join(self.shelve.restore(keys), res)

        def dynamodb_restore(keys, res):
            items = zip(
                keys,
                (self[key] for key in keys),
            )
            join(dict(filter(lambda x: x[1], items)), res)

        res1, res2 = {}, {}
        thread1 = Thread(target = dynamodb_restore, args=(keys, res1,))
        thread2 = Thread(target = shelve_restore, args=(keys, res2,))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # merge
        for i, j in res1.items():
            if i not in res2.keys():
                res2[i] = j
        return res2

    def __getitem__(self, key):
        """
        It returns an object which is deserialized from binary
        """
        val = bytearray()
        for index in range(self._get_num_of_partitions(key)):
            val += bytes(self.table.get_item(
                Key={
                    'key': str(key),
                    'index': index
                },
                ProjectionExpression='val',
                ConsistentRead=True
            )['Item']['val'].value)
        return pickle.loads(val) if val else None

    def save(self, key_value_pairs):
        """
        Remove all previous data with the same partition key, examine the size of state_data,
        and splice it into different parts under 400KB with different sort keys,
        and save them under the same partition key built.
        """
        def dynamodb_save(key_value_pairs):
            for key, val in key_value_pairs:
                self._delete_item(key)
                self[key] = pickle.dumps(val)

        thread1 = Thread(target = dynamodb_save, args=(key_value_pairs,))
        thread2 = Thread(target = self.shelve.save, args=(key_value_pairs,))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

    def __setitem__(self, key, val):
        size = math.ceil(len(val) / OBJECT_SIZE)
        for index in range(size):
            self.table.put_item(
                Item={
                    'key': str(key),
                    'index': index,
                    'val': val[index * OBJECT_SIZE:min(index * OBJECT_SIZE + OBJECT_SIZE, len(val))],
                    'size': size,
                }
            )

    def _delete_item(self, key):
        for index in range(self._get_num_of_partitions(key)):
            self.table.delete_item(
                Key={
                    'key': str(key),
                    'index': index,
                }
            )

    def _get_num_of_partitions(self, key) -> int:
        """
        Return how many parts is the item partitioned into
        """
        try:
            partition = self.table.get_item(
                Key={
                    'key': str(key),
                    'index': 0,
                },
                ConsistentRead=True
            )
            return int(partition.get('Item', {}).get('size', 0))
        except self.client.exceptions.ResourceNotFoundException:
            return 0

    def cleanup(self):
        self.shelve.cleanup()
