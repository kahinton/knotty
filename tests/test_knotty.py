import unittest
from knotty import Knotty
import knotty.registry as registry
import knotty.meters as meters
import logging
import flask
import requests


class TestKnotty(unittest.TestCase):
    def test_registy_is_populated_with_expected_metrics_via_start_system_monitors(self):
        registry.MeterRegistry._meters = dict()
        Knotty._start_system_monitors()
        self.assertEqual({metric.name for metric in registry.MeterRegistry.get_all_metrics()},
                         {'process_memory_percentage', 'process_open_file_count', 'disk_space_used',
                          'process_thread_count', 'process_memory_info', 'disk_space_total', 'system_cpu_percentage',
                          'disk_io_stats', 'system_network_io_stats', 'process_cpu_percentage', 'system_memory_stats'}
                         )

    def test_registy_is_populated_with_expected_metrics_via_start_std_lib_monitoring(self):
        registry.MeterRegistry._meters = dict()
        Knotty._start_std_lib_monitoring()
        self.assertEqual(list(registry.MeterRegistry._meters.keys()), [(meters.Counter, "logback_events_count")])

    def test_registy_is_populated_with_expected_metrics_via_start_third_party_lib_monitors(self):
        registry.MeterRegistry._meters = dict()
        Knotty._start_third_party_lib_monitors()
        self.assertEqual(list(registry.MeterRegistry._meters.keys()),
                         [(meters.Counter, "requests_http_time_count"),
                          (meters.Timer, "requests_http"),
                          (meters.Counter, "flask_http_request_time_count"),
                          (meters.Timer, "flask_http_request")])


if __name__ == '__main__':
    unittest.main()
