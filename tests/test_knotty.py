import unittest
import os
import sys
lib_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

from knotty import Knotty, timer, counter, gauge, histogram
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

    def test_timer_returns_timer_as_expected(self):
        test_timer = timer("test_timer")
        self.assertTrue(isinstance(test_timer, meters.Timer))

    def test_counter_returns_timer_as_expected(self):
        test_counter = counter("test_counter")
        self.assertTrue(isinstance(test_counter, meters.Counter))

    def test_gauge_returns_timer_as_expected(self):
        test_gauge = gauge("test_gauge")
        self.assertTrue(isinstance(test_gauge, meters.Gauge))

    def test_histogram_returns_timer_as_expected(self):
        test_histogram = histogram("test_histogram")
        self.assertTrue(isinstance(test_histogram, meters.Histogram))


if __name__ == '__main__':
    unittest.main()
