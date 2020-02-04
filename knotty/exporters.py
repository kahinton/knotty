from knotty import registry
import requests
import time
from datetime import datetime
from threading import Thread
from uuid import uuid4
from base64 import urlsafe_b64encode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging import getLogger
import pickle
import socket
import struct


class Exporter:
    """
    Base class for all exporters.
    """
    def _metrics_translator(self):
        raise NotImplementedError()

    def _export(self):
        raise NotImplementedError()


class OpenTSDBExporter(Exporter):
    """
    Translates application metrics and sends them to an OpenTSDB instance.
    """
    _logger = getLogger(__name__)

    def __init__(self, push_interval: int, endpoint: str) -> None:
        self._push_interval = push_interval
        self._endpoint = endpoint
        self._logger.debug("Starting OpenTSDBExporter thread, pushing to {0} every {1} seconds.".format(endpoint,
                                                                                                        push_interval))
        self._thread = Thread(target=self._export, daemon=True)
        self._thread.start()

    def _metrics_translator(self) -> [dict]:
        """
        Gathers all metrics from the Registry and translates them into a list of dictionaries that will be sent as json
        data to the OpenTSDB instance.
        :return:
        """
        metrics = registry.MeterRegistry.get_all_metrics()
        unix_time = int(time.time())
        return [{"metric": metric.name.replace("_", "."),
                 "timestamp": unix_time,
                 "value": metric.value,
                 "tags": dict(metric.tags)
                 } for metric in metrics]

    def _export(self) -> None:
        """
        This function is the target of the exporters thread, and will run continuously until application shutdown,
        sending metrics to the OpenTSDB instance at the requested push interval.
        :return:
        """
        while True:
            try:
                metric_data = self._metrics_translator()
                self._logger.debug("Push metrics to OpenTSDB...")
                res = requests.post(url=self._endpoint, data=metric_data)
                self._logger.debug("Response from OpenTSDB; Status: {0}, Content: {1}".format(res.status_code,
                                                                                              res.content))

            except Exception as e:
                self._logger.error(e)

            finally:
                time.sleep(self._push_interval)


class _PrometheusStarter(Exporter):
    """
    The PrometheusStarter is used to encapsulate the shared behaviors between creating a metrics endpoint for scraping
    and creating a set of data to send to a PushGateway.
    """
    def _tag_translator(self, tag_dict: dict) -> str:
        """
        This takes a dictionary of tags and translates them into the string format that Prometheus and Pushgateway
        expect.
        :param tag_dict: The dictionary containing the list of tags for a given metric
        :return: str: The tags formatted as the string that Prometheus/PushGateway expect
        """
        return "{"+", ".join(['{0}="{1}"'.format(key, value) for key, value in tag_dict.items()])+"}"

    def _metrics_translator(self) -> str:
        """
        This gets all of the metrics from the registry and creates a document in the format expected by Prometheus or
        PushGateway. This includes the grouping of metrics by their name, and the addition of the expected type names
        that Prometheus defines.
        :return: str: Formatted string containing all metrics to export.
        """
        metrics = registry.MeterRegistry.get_all_metrics()
        metric_builder = dict()
        for metric in metrics:
            name = metric.name
            if metric.prometheus_type in ["histogram", "summary"]:
                name = "_".join(name.split("_")[0:-1])
            key = "#TYPE {0} {1}\n".format(name, metric.prometheus_type)
            value = "{0}{1} {2}\n".format(metric.name, self._tag_translator(dict(metric.tags)), metric.value)
            metric_builder[key] = (metric_builder.get(key) or []) + [value]

        return "".join([key+"".join(value) for key, value in metric_builder.items()])

    def _export(self):
        return NotImplementedError()


class PushgatewayExporter(_PrometheusStarter):
    """
    The PushGateway Exporter manages collecting and sending metrics to the given PushGateway endpoint at the desired
    push interval.
    """
    _logger = getLogger(__name__)

    def __init__(self, push_interval: int, endpoint: str, job_name: str = None, instance: str = "default"):
        self._push_interval = push_interval
        self._endpoint = endpoint
        self._job_name = job_name or str(uuid4())
        self._instance = instance
        self._logger.debug("Starting PushgatewayExporter thread, pushing to {0} every {1} seconds."
                           .format(endpoint, push_interval))
        self._thread = Thread(target=self._export, daemon=True)
        self._thread.start()

    def _export(self) -> None:
        """
        This function is the target of the exporters thread, and will run continuously until application shutdown,
        sending metrics to the PushGateway instance at the requested push interval.
        :return:
        """
        while True:
            try:
                metric_data = self._metrics_translator()
                b64_instance = urlsafe_b64encode(self._instance.encode('ascii')).decode("ascii")
                req = requests.post(url="{0}/metrics/job/{1}/instance@base64/{2}".format(self._endpoint, self._job_name,
                                                                                         b64_instance),
                                    data=metric_data)
                self._logger.debug("Response from Pushgateway; Status: {0}, Content: {1}".format(req.status_code,
                                                                                                 req.content))
            except Exception as e:
                self._logger.error(e)

            finally:
                time.sleep(self._push_interval)


class PrometheusExporter(_PrometheusStarter):
    """
    The Prometheus Exporter manages a metrics endpoint for Prometheus to scrape. This can be handled through its own
    built in http server, or through providing a Flask app which which will have an endpoint added to it. Note that the
    built in http server only aims to provide minimal functionality, and if you need any sort of security, please
    implement that through Flask.
    """
    _logger = getLogger(__name__)

    def __init__(self, flask_app=None, server_name: str = "0.0.0.0", port: int = 2091, path: str = "/metrics"):
        self._flask_app = flask_app
        self._server_name = server_name
        self._port = port
        self._path = path
        self._logger.debug("Starting PrometheusExporter thread")
        self._thread = Thread(target=self._export, daemon=True)
        self._thread.start()

    class _PrometheusHandler(BaseHTTPRequestHandler, _PrometheusStarter):
        """
        The Prometheus Handler is a custom HTTP handler that will return the metrics for Prometheus in the correct
        format.
        """
        metrics_path: str = None
        logger = getLogger(__name__)

        def do_GET(self):
            if self.path == self.metrics_path:
                self.logger.debug("Serving request for metrics at {0}".format(self.path))
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(self._metrics_translator().encode("ascii"))
                self.server.path = self.path
            else:
                self.logger.debug("Request was made to the metrics server for an unknown path {0}".format(self.path))
                self.send_response(404)
                self.end_headers()
                self.server.path = self.path

    def __start_http_server(self) -> None:
        """
        Starts the http server to handle incoming metrics requests from Prometheus if no other WSGI application (eg
        Flask) has been provided.
        :return:
        """
        server = ThreadingHTTPServer((self._server_name, self._port), type("handler", (self._PrometheusHandler,),
                                                                           {"metrics_path": self._path}))
        self._logger.debug("Starting http server, binding to {0}:{1}/{2}"
                           .format(self._server_name, self._port, self._path))
        server.serve_forever()

    def _export(self) -> None:
        """
        For Prometheus the export function is run once to ensure that the proper metrics endpoint is added to the
        application.
        :return:
        """
        if self._flask_app:
            self._logger.debug("Adding metrics endpoint {0} to provided Flask Application.".format(self._path))
            self._flask_app.route(self._path)(lambda: (self._metrics_translator(), 200, {"Content-Type": "text/plain"}))
        else:
            self.__start_http_server()


class InfluxDBExporter(Exporter):
    """
    Translates application metrics and sends them to an InfluxDB instance.
    """
    _logger = getLogger(__name__)

    def __init__(self, push_interval: int, influxdb_client: "influxdb.InfluxDBClient") -> None:
        self._push_interval = push_interval
        self._client = influxdb_client
        self._logger.debug("Starting InfluxDBExporter thread, pushing to {0} every {1} seconds."
                           .format(influxdb_client.host, push_interval))
        self._thread = Thread(target=self._export, daemon=True)
        self._thread.start()

    def _metrics_translator(self) -> [dict]:
        """
        Gathers all metrics from the Registry and translates them into a list of dictionaries that will be sent as json
        data to the InfluxDB instance.
        :return:
        """
        metrics = registry.MeterRegistry.get_all_metrics()
        timestamp = datetime.utcnow().isoformat()+"Z"
        return [{"measurement": metric.name,
                 "time": timestamp,
                 "fields": {"value": metric.value},
                 "tags": dict(metric.tags)
                 } for metric in metrics]

    def _export(self) -> None:
        """
        This function is the target of the exporters thread, and will run continuously until application shutdown,
        sending metrics to the InfluxDB instance at the requested push interval.
        :return:
        """
        while True:
            try:
                metric_data = self._metrics_translator()
                self._logger.debug("Push metrics to InfluxDB...")
                self._client.write_points(metric_data)
                self._logger.debug("Metrics pushed successfully.")

            except Exception as e:
                self._logger.error(e)

            finally:
                time.sleep(self._push_interval)


class GraphiteExporter(Exporter):
    """
    Translates application metrics and sends them to a Graphite instance.
    """
    _logger = getLogger(__name__)

    def __init__(self, push_interval: int, graphite_endpoint: str,
                 graphite_port: int = 2004, pickle_protocol: int = 2, socket_family: int = socket.AF_INET) -> None:
        self._push_interval = push_interval
        self._graphite_endpoint = graphite_endpoint
        self._graphite_port = graphite_port
        self._pickle_protocol = pickle_protocol
        self._socket_family = socket_family
        self._logger.debug("Starting GraphiteExporter thread, pushing to {0}:{1} every {2} seconds."
                           .format(graphite_endpoint, graphite_port, push_interval))
        self._thread = Thread(target=self._export, daemon=True)
        self._thread.start()

    def _join_tags(self, tags: dict):
        return ".".join(["{0}.{1}".format(key, value) for key, value in tags])

    def _metrics_translator(self) -> [tuple]:
        """
        Gathers all metrics from the Registry and translates them into tuples to be pickled and sent to Graphite
        :return:
        """
        metrics = registry.MeterRegistry.get_all_metrics()
        timestamp = int(time.time())
        return [((metric.name.replace("_", ".")+"."+self._join_tags(metric.tags))
                 .replace(" ", "_")
                 .replace("/", ".")
                 .replace("..", "."),
                (timestamp, metric.value)) for metric in metrics]

    def _export(self) -> None:
        """
        This function is the target of the exporters thread, and will run continuously until application shutdown,
        sending metrics to the Graphite instance at the requested push interval.
        :return:
        """
        while True:
            try:
                metric_data = self._metrics_translator()
                self._logger.debug("Pickling metrics to push to Graphite...")
                payload = pickle.dumps(metric_data, protocol=self._pickle_protocol)
                header = struct.pack("!L", len(payload))
                message = header + payload
                sock = socket.socket(family=self._socket_family)
                sock.connect((self._graphite_endpoint, self._graphite_port))
                sock.sendall(message)
                sock.close()
                self._logger.debug("Metrics pushed successfully.")

            except Exception as e:
                self._logger.error(e)

            finally:
                time.sleep(self._push_interval)
