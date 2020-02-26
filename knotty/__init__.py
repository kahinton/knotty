"""
The __init__ file for Knotty defines the Knotty object and automatically starts up all of our pre-defined
meters.
"""

from knotty import meters, registry
import psutil
from logging import Logger
import sys


__all__ = ["exporters", "meters", "registry"]


def timer(name) -> meters.Timer:
    return registry.MeterRegistry.get_meter(name, meters.Timer)


def counter(name) -> meters.Counter:
    return registry.MeterRegistry.get_meter(name, meters.Counter)


def gauge(name) -> meters.Gauge:
    return registry.MeterRegistry.get_meter(name, meters.Gauge)


def histogram(name) -> meters.Histogram:
    return registry.MeterRegistry.get_meter(name, meters.Histogram)


class Knotty:
    @classmethod
    def _start_system_monitors(cls) -> None:
        """
        This function starts a number of monitors for system level metrics. Most of these are gathered using the psutil
        package. The metrics gathered here are still subject to changes as the package is developed.
        :return:
        """
        process = psutil.Process()
        process_cpu_gauge = gauge("process_cpu_percentage")
        process_cpu_gauge.add_tags({"pid": process.pid.real})
        process_cpu_gauge.set_gauge_function(process.cpu_percent)

        system_cpu_gauge = gauge("system_cpu_percentage")
        system_cpu_gauge.set_gauge_function(psutil.cpu_percent)

        process_memory_gauge = gauge("process_memory_percentage")
        process_memory_gauge.add_tags({"pid": process.pid.real})
        process_memory_gauge.set_gauge_function(process.memory_percent)

        process_thread_gauge = gauge("process_thread_count")
        process_thread_gauge.add_tags({"pid": process.pid.real})
        process_thread_gauge.set_gauge_function(process.num_threads)

        process_files_gauge = gauge("process_open_file_count")
        process_files_gauge.add_tags({"pid": process.pid.real})
        process_files_gauge.set_gauge_function(lambda: len(process.open_files()))

        process_mem_info_gauge = gauge("process_memory_info")
        process_mem_info_gauge.add_tags({"pid": process.pid.real})
        process_mem_info_gauge.set_gauge_function(lambda: process.memory_full_info()._asdict(), key_tag="memory_type")

        disk_total_gauge = gauge("disk_space_total")
        disk_total_gauge.set_gauge_function(lambda: {part.mountpoint: psutil.disk_usage(part.mountpoint).total
                                                     for part in psutil.disk_partitions()}, key_tag="mount_point")

        disk_used_gauge = gauge("disk_space_used")
        disk_used_gauge.set_gauge_function(lambda: {part.mountpoint: psutil.disk_usage(part.mountpoint).used
                                                    for part in psutil.disk_partitions()}, key_tag="mount_point")

        disk_io_gauge = gauge("disk_io_stats")
        disk_io_gauge.set_gauge_function(lambda: psutil.disk_io_counters()._asdict(), key_tag="stat")

        system_memory_gauge = gauge("system_memory_stats")
        system_memory_gauge.set_gauge_function(lambda: psutil.virtual_memory()._asdict(), key_tag="stat")

        system_network_gauge = gauge("system_network_io_stats")
        system_network_gauge.set_gauge_function(lambda: psutil.net_io_counters()._asdict(), key_tag="stat")

    @classmethod
    def _start_std_lib_monitoring(cls) -> None:
        """
        The function will be responsible for setting up monitors for any functionality in the standard library. This
        will continue to grow as development continues.
        :return:
        """
        logging_counter = counter("logback_events_count")

        logging_counter.augmentor = lambda self, method, results, *args, **kwargs: self.set_tags({"level": method.__name__})
        Logger.info = logging_counter.auto_count_method(Logger.info)
        Logger.warning = logging_counter.auto_count_method(Logger.warning)
        Logger.error = logging_counter.auto_count_method(Logger.error)
        Logger.debug = logging_counter.auto_count_method(Logger.debug)

    @classmethod
    def _start_third_party_lib_monitors(cls) -> None:
        """
        This function will maintain a list of monitors for third party packages. It will check for the presence of the
        libraries in the registered system modules, and if found we will wrap the functionality the appropriate meter
        and provide a useful augmentor.
        :return:
        """
        if "requests" in sys.modules.keys():
            import requests
            request_timer = timer("requests_http")
            request_timer.augmentor = lambda self, method, results, *args, **kwargs: self.set_tags({"url": args[1],
                                                                                                    "method": args[0],
                                                                                                    "status_code": results.status_code})
            requests.api.request = request_timer.timer(requests.api.request)

        if "flask" in sys.modules.keys() or "Flask" in sys.modules.keys():
            from flask import Flask
            from flask.wrappers import Response
            flask_timer = timer("flask_http_request")
            flask_timer.augmentor = lambda self, method, results, *args, **kwargs: self.set_tags({"path": args[1]["PATH_INFO"],
                                                                                                  "method": args[1]["REQUEST_METHOD"],
                                                                                                  "status_code": [response.__self__._status_code
                                                                                                                  for response in results._callbacks
                                                                                                                  if isinstance(response.__self__, Response)][0]})
            Flask.wsgi_app = flask_timer.timer(Flask.wsgi_app)

    @classmethod
    def initiate_monitors(cls) -> None:
        """
        Simple function to make sure that all automatically registered meters have been created. This function should be
        called through the __init__ file of the package, however it is also left publicly accessible in the event that
        you cannot start your code with a guarantee that Knotty will be the last package loaded.
        :return:
        """
        cls._start_system_monitors()
        cls._start_std_lib_monitoring()
        cls._start_third_party_lib_monitors()


Knotty.initiate_monitors()
