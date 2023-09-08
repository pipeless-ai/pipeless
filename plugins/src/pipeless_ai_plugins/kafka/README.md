# Kafka plugin for Pipeless

> IMPORTANT: THIS MODULE IS DEPRECATED IN FAVOR OF THE NEW PLUGIN SYSTEM
> Check the [plugins docs](https://www.pipeless.ai/docs/v0/plugins) for more information about the new plugin system.

This plugin makes easy to connect to a Kafka cluster using Pipeless.
It works as a Kafka producer to send information to Kafka topics that can later be used to take actions on events.

## Simple usage

Initialize the producer within the `before` stage:

```python
...
def before(self):
    self.producer = KafkaProducer()
...
```

Send information to a Kafka topic at any stage:

```python
self.producer.produce('pipeless', 'hello!')
```

## Configuration

This plugin supports the following environment variables:

- `KAFKA_BOOTSTRAP_SERVERS`: A comma separated list of host and port. Example: `host1:9092,host2:9092`
- `KAFKA_CLIENT_ID` (optional): The client ID for the connection
- `KAFKA_USERNAME` (optional): Username when using SASL or SCRAM authentication
- `KAFKA_PASSWORD` (optional): Password when using SASL or SCRAM authentication

## Methods

#### `produce(topic, value, key, partition, on_delivery)`:

Sends information to a Kafka topic. Supports the following parameters:

- `topic` (str): name of the topic to produce the message to
- `value` (str|bytes): Message payload.
- `key` (srt|bytes): optional. Message key
- `partition` (int): optional. Partition to produce to
- `on_delivery` (err,msg)(function): optional. Callback to call after success or failed delivery
