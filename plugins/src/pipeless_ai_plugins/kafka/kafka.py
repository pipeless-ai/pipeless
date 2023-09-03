import os
import sys
from confluent_kafka import Producer

class KafkaProducer:
    """
    This class allows to send the data extracted from the stream to a Kafka topic.
    """
    def __init__(self):
        """
        Creates and configures the Kafka producer

        Config env vars:
        - KAFKA_BOOTSTRAP_SERVERS: a comma separated list of host and port. Ex: 'host1:9092,host2:9092'
        - KAFKA_CLIENT_ID (optional): the client ID for the connection
        - KAFKA_USERNAME (optional): username when using SASL or SCRAM authentication
        - KAFKA_PASSWORD (optional): password when using SASL or SCRAM authentication
        """
        bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', None)
        if bootstrap_servers is None:
            print('ERROR: missing KAFKA_BOOTSTRAP_SERVERS env var')
            sys.exit(1)
        conf = { 'bootstrap.servers': bootstrap_servers }
        client_id = os.environ.get('KAFKA_CLIENT_ID', None)
        if client_id is not None:
            conf["client.id"] = client_id

        self.__producer = Producer(conf)

        username = os.environ.get('KAFKA_USERNAME', None)
        password = os.environ.get('KAFKA_PASSWORD', None)
        if username is not None and password is not None:
            self.__producer.set_sasl_credentials(username, password)
        elif username is not None:
            print('ERROR: KAFKA_USERNAME was provided but KAFKA_PASSWORD WAS NOT')
        elif password is not None:
            print('ERROR: KAFKA_PASSWORD was provided but KAFKA_USERNAME WAS NOT')

    def produce(self, topic : str, value : str | bytes, key : str | bytes = None,
        partition : int = None, on_delivery : callable = None):
        """
        Send data to a topic

        Params:
        - topic (str): name of the topic to produce the message to
        - value (str|bytes): Message payload.
        - key (srt|bytes): optional. Message key
        - partition (int): optional. Partition to produce to
        - on_delivery(err,msg)(function): optional. Callback to call after success or failed delivery
        """
        named_params = {}
        if key is not None: named_params['key'] = key
        if partition is not None: named_params['partition'] = partition
        if on_delivery is not None: named_params['on_delivery'] = on_delivery
        self.__producer.produce(topic, value, **named_params)
        self.__producer.poll(1) # TODO: check the implications of this timeout
