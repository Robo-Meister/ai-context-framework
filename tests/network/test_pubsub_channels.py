import json
import os
from unittest import mock

os.environ.setdefault("CAIENGINE_LIGHT_IMPORT", "1")

from caiengine.network.redis_pubsub_channel import RedisPubSubChannel
from caiengine.network.kafka_pubsub_channel import KafkaPubSubChannel


def test_redis_pubsub_channel_publish_subscribe():
    mock_pubsub = mock.Mock()
    mock_thread = mock.Mock()
    mock_pubsub.run_in_thread.return_value = mock_thread
    mock_redis = mock.Mock()
    mock_redis.pubsub.return_value = mock_pubsub
    with mock.patch("caiengine.network.redis_pubsub_channel.Redis", return_value=mock_redis):
        channel = RedisPubSubChannel()
        channel.publish("topic", {"foo": "bar"})
        mock_redis.publish.assert_called_once_with("topic", json.dumps({"foo": "bar"}))

        callback = mock.Mock()
        channel.subscribe("topic", callback)
        mock_pubsub.subscribe.assert_called_once()
        mock_pubsub.run_in_thread.assert_called_once()


def test_kafka_pubsub_channel_publish_subscribe():
    mock_producer = mock.Mock()
    mock_consumer = mock.Mock()
    with (
        mock.patch("caiengine.network.kafka_pubsub_channel.KafkaProducer", return_value=mock_producer),
        mock.patch("caiengine.network.kafka_pubsub_channel.KafkaConsumer", return_value=mock_consumer) as consumer_cls,
        mock.patch("threading.Thread") as thread_cls,
    ):
        dummy_thread = mock.Mock()
        thread_cls.return_value = dummy_thread

        channel = KafkaPubSubChannel()
        channel.publish("topic", {"foo": "bar"})
        mock_producer.send.assert_called_once_with("topic", {"foo": "bar"})
        mock_producer.flush.assert_called_once()

        callback = mock.Mock()
        channel.subscribe("topic", callback)
        consumer_cls.assert_called_once()
        dummy_thread.start.assert_called_once()
