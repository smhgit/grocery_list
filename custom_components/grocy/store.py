'''Online grocery store'''

import logging

from .store_api_client import RamiLevyStoreApiClient, ShufersalStoreApiClient

_LOGGER = logging.getLogger(__name__)


class Store:
    """Online store"""
    
    def __init__(self):
      self._client = RamiLevyStoreApiClient()

    @property
    def name(self):
        return self._client.name

    def get_product_by_barcode(self, barcode: str):
      return self._client.get_product_by_barcode(barcode)


# def test():
#     store = Store(RamiLevyStoreApiClient())
#     p = store.get_product_by_barcode('100')
#     print('Pass: Found: ' + p.name) if p else print('Failure')
#     p = store.get_product_by_barcode('7290016096590')
#     print('Pass: Found: ' + p.name) if p else print('Failure')
#     p = store.get_product_by_barcode('7290102398065')
#     print('Pass: Found: ' + p.name) if p else print('Failure')
#     p = store.get_product_by_barcode('000')
#     print('Failure') if p else print('Pass: Product not exists')

#     store = Store(ShufersalStoreApiClient())
#     p = store.get_product_by_barcode('7290102395224')
#     print('Pass: Found: ' + p.name) if p else print('Failure')

# test()