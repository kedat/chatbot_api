
# datastore_service.py

from google.cloud import datastore
from google.cloud.datastore.query import PropertyFilter

# Initialize the Datastore client
datastore_client = datastore.Client()

def fetch_entities(kind, bot_id):
    query = datastore_client.query(kind=kind)
    query.add_filter(filter=PropertyFilter("bot_id", "=", bot_id))
    results = list(query.fetch())
    return results

def add_entity(kind, data):
    key = datastore_client.key(kind)
    entity = datastore.Entity(key=key)
    entity.update(data)
    datastore_client.put(entity)
    return entity

def update_entity(bot_id, data):
    query = datastore_client.query(kind='chatbotdata')
    query.add_filter(filter=PropertyFilter("bot_id", "=", bot_id))
    results = list(query.fetch())
    results[0]['data']=data
    datastore_client.put(results[0])
    return None

def delete_entity(kind, entity_id):
    key = datastore_client.key(kind, entity_id)
    datastore_client.delete(key)

def create_user(data):
    key = datastore_client.key('user')
    entity = datastore.Entity(key=key)
    entity.update(data)
    datastore_client.put(entity)
    return entity

def fetch_user(data):
    query = datastore_client.query(kind='user')
    query.add_filter(filter=PropertyFilter("email", "=", data['email']))
    query.add_filter(filter=PropertyFilter("password", "=", data['password']))
    results = list(query.fetch())
    return results

def check_user(data):
    query = datastore_client.query(kind='user')
    query.add_filter(filter=PropertyFilter("email", "=", data['email']))
    results = list(query.fetch())
    return results

