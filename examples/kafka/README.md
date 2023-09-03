# Sending data to Kafka and reacting to events on real time

This example uses Pipeless and Kafka and demonstrates how to send data to a Kafka topic to which you can subscribe to perform actions by receiving events on real time.

In this case, we are not interested on the output video since we just want to analyze the input and create events based on the elements that appear on it, so **we will disable the video output**.

We will do the same detections that we did on the [cats](../cats/) example, but instead of drawing the bounding box around the cat face, we will send a message to a Kafka topic to get notified that there is a cat on the video.

To connect to Kafka we will use the **Pipeless Kafka Plugin** from `pipeless_ai_plugins`. This plugin is just a wrapper around the `confluent_kafka` package for a more convenient usage, but you modify the example to use any Kafka client or even replace Kafka by any event streaming platform or messaging broker. Check the whole documentation of the [Pipeless Kafka Plugin](../../plugins/src/pipeless_ai_plugins/kafka/).

For simplicity we have included a Kafka `docker-compose.yaml` on this same directory so you can easily start a local Kafka cluster for testing.

## Requirements

* Pipeless: `pip install pipeless_ai_cli`

* Pipeless plugins: `pip install pipeless_ai_plugins`

* OpenCV: `pip install opencv-python`

## Run the example

1. Clone the repository

1. Update the video paths at `config.yaml` to match the paths on your system. ** They must be absolute paths**

1. Move to the `examples/kafka` directory

1. Start the Kafka instance by running:

    ```console
    docker compose up
    ```

    You can verify it is started by running `docker compose logs kafka`. You should see something like the following indicating the Kafka server has started properly:

    ```
    kafka-kafka-1  | [2023-09-02 14:38:36,823] INFO [KafkaRaftServer nodeId=0] Kafka Server started (kafka.server.KafkaRaftServer)
    ```

1. Configure the Pipeless Kafka plugin by running:

    ```console
    export KAFKA_BOOTSTRAP_SERVERS="localhost:9094"
    ```

1. Finally, run the example with:

    ```console
    pipeless run
    ```

## Consume the data that was sent to the Kafka topic

The commands on this section must be executed within the Kafka container. Exec into the container by running:

```console
docker compose exec kafka bash
```

The `docker-compose.yaml` included on configured Kafka to automatically create topics. You can verify the `pipeless` topic was created when writing to it:

```console
kafka-topics.sh  --list --bootstrap-server localhost:9094
```

The code of the example only sends information to Kafka, it does not consume from the topic, thus the topic still contains all the information we have sent to it. It is your task to listen for messages on the Kafka topics and take actions based on those messages. Let's run a consumer to verify the information is arriving to the topic:

```console
kafka-console-consumer.sh --bootstrap-server localhost:9094 --topic pipeless --from-beginning
```

> Use `Ctrl + C` to stop the consumer.

And that's all. Now, it is your time to complete your application by listening and consuming messages from the Kafka topic, process that information and take any required actions. A simple example could be to send us a notification when a cat appears on the image. In this case that will correspond to identify a bounding box on a frame since the model we loaded only identifies cats, so we have no labels.

## Walkthrough

We describe here only the new lines, to understand how the recognition model is used please check the [cats example walkthrough](../cats/).

### Before stage

In the before state we initiate the producer connection to our Kafka cluster and store on the context so we can use the producer later to send messages to the topic. Initiating the connection is realy simple thanks to the Pipeless Kafka Plugin:

```python
ctx['producer'] = KafkaProducer()
```

### Processing stage

In this case, instead of editing the frame to draw a bounding box and return the modified video frame like we did on the original cats example, we simply identify the bounding box and, if there is a bounding box, we send a message to the `pipeless` kafka topic:

```python
producer = ctx['producer']

...

if len(bounding_boxes) > 0:
    producer.produce('pipeless', 'There is a cat!')
```

> NOTE: the bounding box detection is exactly the same than on the cats example.
