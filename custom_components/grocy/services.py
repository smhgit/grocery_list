'''Custom component services'''

import logging

from homeassistant.core import callback

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, CONF_ENTITY_ID

from .store import Store

from .sensor import ProductSensor, ShoppingListSensor
from .utils import contains

from .const import (DOMAIN, DOMAIN_DATA, DOMAIN_EVENT,
                    DATA_GROCY, DATA_DATA, DATA_ENTITIES, 
                    CONF_APIKEY, CONF_AMOUNT, CONF_SHOPPING_LIST_ID,
                    CONF_BARCODE, CONF_STORE, CONF_PRODUCT_GROUP_ID, CONF_UNIT_OF_MEASUREMENT,
                    CONF_PRODUCT_LOCATION_ID, CONF_PRODUCT_DESCRIPTION,
                    SYNC_GROCY_SERVICE, ADD_TO_LIST_SERVICE, SUBTRACT_FROM_LIST_SERVICE,
                    ADD_PRODUCT_SERVICE, UPDATE_PRODUCT_SERVICE, REMOVE_PRODUCT_SERVICE,
                    PRODUCTS_NAME, SHOPPING_LIST_NAME,
                    EVENT_ADDED_TO_LIST, EVENT_SUBTRACT_FROM_LIST, EVENT_PRODUCT_ADDED,
                    EVENT_PRODUCT_REMOVED)
from .schema import (CONFIG_SCHEMA,
                    ADD_TO_LIST_SERVICE_SCHEMA, SUBTRACT_FROM_LIST_SERVICE_SCHEMA,
                    ADD_PRODUCT_SERVICE_SCHEMA, UPDATE_PRODUCT_SERVICE_SCHEMA,
                    REMOVE_PRODUCT_SERVICE_SCHEMA)

_LOGGER = logging.getLogger(__name__)


def setup_services(hass):

    @callback
    def handle_add_to_list_service(call):
        hass.async_add_job(async_add_to_list(hass, call.data))
    hass.services.async_register(
        DOMAIN, ADD_TO_LIST_SERVICE, handle_add_to_list_service, schema=ADD_TO_LIST_SERVICE_SCHEMA
        )

    @callback
    def handle_subtract_from_list_service(call):
        hass.async_add_job(async_subtract_from_list(hass, call.data))
    hass.services.async_register(
        DOMAIN, SUBTRACT_FROM_LIST_SERVICE, handle_subtract_from_list_service, schema=SUBTRACT_FROM_LIST_SERVICE_SCHEMA
        )

    @callback
    def handle_add_product_service(call):
        hass.async_add_job(async_add_product(hass, call.data))
    hass.services.async_register(
        DOMAIN, ADD_PRODUCT_SERVICE, handle_add_product_service, schema=ADD_PRODUCT_SERVICE_SCHEMA
        )

    @callback
    def handle_remove_product_service(call):
        hass.async_add_job(async_remove_product(hass, call.data))
    hass.services.async_register(
        DOMAIN, REMOVE_PRODUCT_SERVICE, handle_remove_product_service, schema=REMOVE_PRODUCT_SERVICE_SCHEMA
        )

    @callback
    def handle_update_product_service(call):
        hass.async_add_job(async_update_product(hass, call.data))
    hass.services.async_register(
        DOMAIN, UPDATE_PRODUCT_SERVICE, handle_update_product_service, schema=UPDATE_PRODUCT_SERVICE_SCHEMA
        )

    @callback
    def handle_sync_grocy_service(call):
        hass.async_add_job(async_sync_grocy(hass, call.data))
    hass.services.async_register(
        DOMAIN, SYNC_GROCY_SERVICE, handle_sync_grocy_service
        )


async def async_subtract_from_list(hass, data):
    domain_data = hass.data[DOMAIN_DATA]
    # Can be product or barcode sensor
    entity_id = data[CONF_ENTITY_ID][0]
    entity = domain_data[DATA_ENTITIES].async_get(entity_id)
    if entity:
        resp = domain_data[DATA_GROCY].remove_product_in_shopping_list(
            entity.device_state_attributes['_id'], data[CONF_SHOPPING_LIST_ID], data[CONF_AMOUNT]
            )
        if resp.status_code == 204:
            _LOGGER.debug("Product was subtarcted from list {}".format(entity_id))
            await domain_data[DATA_DATA].async_update_data([SHOPPING_LIST_NAME], True)
            entity.async_schedule_update_ha_state(True)
            shopping_list_entity_id = domain_data[DATA_ENTITIES].async_get(ShoppingListSensor.to_entity_id(data[CONF_SHOPPING_LIST_ID]))
            shopping_list_entity_id.async_schedule_update_ha_state(True)
            hass.bus.fire(DOMAIN_EVENT, {
                "event": EVENT_SUBTRACT_FROM_LIST,
                "entity_id": entity_id
            })
        else:
            _LOGGER.debug("Failed to subtarct product from list {}".format(entity_id))

async def async_add_to_list(hass, data):
    domain_data = hass.data[DOMAIN_DATA]
    # Can be product or barcode sensor
    entity_id = data[CONF_ENTITY_ID][0]
    entity = domain_data[DATA_ENTITIES].async_get(entity_id)
    if not entity:
        barcode = hass.states.get(entity_id)
        if barcode:
            product = domain_data[DATA_GROCY].get_product_by_barcode(barcode.state)
            if product:
                entity_id = 'sensor.product' + str(product.id)
                entity = domain_data[DATA_ENTITIES].async_get(entity_id)
    if entity:
        # Product was found, add it to shopping list
        domain_data[DATA_GROCY].add_product_to_shopping_list(entity.device_state_attributes['_id'], data[CONF_SHOPPING_LIST_ID], data[CONF_AMOUNT])
        await domain_data[DATA_DATA].async_update_data([SHOPPING_LIST_NAME], True)
        entity.async_schedule_update_ha_state(True)
        shopping_list_entity_id = domain_data[DATA_ENTITIES].async_get(ShoppingListSensor.to_entity_id(data[CONF_SHOPPING_LIST_ID]))
        shopping_list_entity_id.async_schedule_update_ha_state(True)    
        hass.bus.fire(DOMAIN_EVENT, {
            "event": EVENT_ADDED_TO_LIST,
            "entity_id": entity_id,
        })

async def async_add_product(hass, data):
    store = Store()
    # Add all products to grocy (products can be ',' seperated)
    for barcode in data[CONF_BARCODE].split(","):
        product = store.get_product_by_barcode(barcode)
        if product:
            _LOGGER.debug('Found product: ' + product.name)
            resp = hass.data[DOMAIN_DATA][DATA_GROCY].add_product(
                product.id,
                product.name,
                product.barcode,
                data[CONF_PRODUCT_DESCRIPTION],
                data[CONF_PRODUCT_GROUP_ID],
                product.qu_id_purchase,
                data[CONF_PRODUCT_LOCATION_ID],
                product.picture
            )
            if resp.status_code == 200:
                _LOGGER.debug("Product {} was added".format(product.name))
            else:
                _LOGGER.debug("Failed to add product {} (already exists?)".format(product.name))
        else:
            _LOGGER.debug('Product was not found: ' + str(barcode))
            hass.bus.fire(DOMAIN_EVENT, {
                "event": EVENT_GROCY_ERROR,
                "message": "{} wasn't found at {} store".format(barcode, store.name)
            })
    # Sync with grocy§
    await hass.data[DOMAIN_DATA][DATA_DATA].async_update_data([PRODUCTS_NAME], True)
    # Add all non existing products
    for product in hass.data[DOMAIN_DATA].get(PRODUCTS_NAME):
        entity_id = ProductSensor.to_entity_id(product.id)
        if not hass.data[DOMAIN_DATA][DATA_ENTITIES].is_exists(entity_id):
            hass.add_job(ProductSensor(hass, product).async_add())
            hass.bus.fire(DOMAIN_EVENT, {
                "event": EVENT_PRODUCT_ADDED,
                "entity_id": entity_id
            })

async def async_remove_product(hass, data):
    # Can be product or barcode sensor
    entity_id = data[CONF_ENTITY_ID][0]
    # Search for product by entity id
    entity = hass.data[DOMAIN_DATA][DATA_ENTITIES].async_get(entity_id)
    if not entity:
        # Search for product by barcode (sensor state)
        barcode = hass.states.get(entity_id)
        if barcode:
            product = hass.data[DOMAIN_DATA][DATA_GROCY].get_product_by_barcode(barcode.state)
            if product:
                entity_id = 'sensor.product' + str(product.id)
                entity = hass.data[DOMAIN_DATA][DATA_ENTITIES].async_get(entity_id)
    if entity:
        _LOGGER.debug('Remove product {}'.format(entity.entity_id))
        # Remove from grocy ERP
        product_id = entity.device_state_attributes['_id']
        resp = hass.data[DOMAIN_DATA][DATA_GROCY].remove_product(product_id)
        if resp.status_code == 204:
            # Remove entity from home assisatnt
            hass.add_job(entity.async_remove)
            # Remove from local entity registry
            hass.data[DOMAIN_DATA][DATA_ENTITIES].async_remove(entity.entity_id)
            # Sync products with grocy
            await hass.data[DOMAIN_DATA][DATA_DATA].async_update_data([PRODUCTS_NAME], True)
            # Send event
            hass.bus.fire(DOMAIN_EVENT, {
                "event": EVENT_PRODUCT_REMOVED,
                "entity_id": entity_id
            })
        else:
            _LOGGER.debug('Failed to remove product from grocy {}'.format(product_id))
    else:
        _LOGGER.debug('Product {} doesn\'t exist'.format(entity.entity_id))
    return True

async def async_update_product(hass, data):
    return True

async def async_sync_grocy(hass, data):
    domain_data = hass.data[DOMAIN_DATA]
    # Force update from grocy
    await domain_data[DATA_DATA].async_update_data(force=True)
    # Add missing products
    for product in domain_data.get(PRODUCTS_NAME):
        entity_id = ProductSensor.to_entity_id(product.id)
        if not domain_data[DATA_ENTITIES].is_exists(entity_id):
            hass.add_job(ProductSensor(hass, product).async_add())
            _LOGGER.debug('Sync add product: {}'.format(entity_id))
    # Remove floating products
    for entity in domain_data[DATA_ENTITIES].async_get_all_by_class_name('ProductSensor'):
        if not contains(domain_data.get(PRODUCTS_NAME), lambda p: p.id == entity.device_state_attributes['_id']):
            hass.add_job(entity.async_remove)
            _LOGGER.debug('Remove product: {}'.format(entity.entity_id))
    _LOGGER.debug('Sync done')
    # Update all products
    for entity in domain_data[DATA_ENTITIES].async_get_all():
        entity.async_schedule_update_ha_state(True)
    return True