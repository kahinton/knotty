import unittest
import os
import sys
lib_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

import knotty.meters as meters
import knotty.registry as registry
from time import sleep
import asyncio


class TestMeters(unittest.TestCase):
    def tearDown(self):
        registry.MeterRegistry._meters = dict()
        meters.GlobalTags.tags = dict()

    def test_adding_global_tags(self):
        tags = {"test1": "t1", "test2": "t2"}
        meters.GlobalTags.add_global_tags(tags)
        self.assertEqual(meters.GlobalTags.tags, tags)

    def test_removing_global_tags(self):
        tags = {"test1": "t1", "test2": "t2"}
        meters.GlobalTags.add_global_tags(tags)
        meters.GlobalTags.remove_global_tags(["test2"])
        self.assertEqual(meters.GlobalTags.tags, {"test1": "t1"})

    def test_add_tags_properly_merges_dictionaries(self):
        self.assertEqual(meters._add_tags({"test1": "t1", "test2": "t2"}, {"test2": "r2", "test3": "r3"}),
                         {"test1": "t1", "test2": "r2", "test3": "r3"})

    def test_remove_tags_gets_rid_of_expected_entries(self):
        self.assertEqual(meters._remove_tags({"test1": "t1", "test2": "t2", "test3": "t3", "test4": "t4"},
                                             ["test1", "test3"]), {"test2": "t2", "test4": "t4"})

    def test_timers_wrap_functions_as_expected(self):
        test_timer = meters.Timer("test_timer")

        @test_timer.timer
        def bogus_function():
            sleep(.001)

        bogus_function()
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_timer.get_metrics()))
        expected = [meters.Metric(name='test_timer_time_sum', tags=(), value=0.001, prometheus_type='summary')]

        self.assertAlmostEqual(actual[0].value, expected[0].value, 3)
        self.assertEqual(actual[0].name, expected[0].name)
        self.assertEqual(actual[0].tags, expected[0].tags)
        self.assertEqual(actual[0].prometheus_type, expected[0].prometheus_type)

    def test_counters_wrap_functions_as_expected(self):
        test_counter = meters.Counter("test_counter")

        @test_counter.auto_count_method
        def bogus_function():
            pass

        bogus_function()
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_counter.get_metrics()))
        expected = [meters.Metric(name='test_counter', tags=(), value=1, prometheus_type='counter')]
        self.assertEqual(actual, expected)

    def test_counters_increment_as_expected(self):
        test_counter = meters.Counter("test_counter")
        test_counter.increment()
        test_counter.increment()
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_counter.get_metrics()))
        expected = [meters.Metric(name='test_counter', tags=(), value=2, prometheus_type='counter')]
        self.assertEqual(actual, expected)

    def test_gauge_when_gauge_function_returns_number(self):
        test_gauge = meters.Gauge("Test Gauge")
        test_gauge.set_gauge_function(lambda: 1)
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_gauge.get_metrics()))
        expected = [meters.Metric(name='Test Gauge', tags=(), value=1, prometheus_type='gauge')]
        self.assertEqual(actual, expected)

    def test_gauge_when_gauge_function_returns_dictionary(self):
        test_gauge = meters.Gauge("Test Gauge")
        test_gauge.set_gauge_function(lambda: {"value1": 2, "value2": 3}, "key")
        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_gauge.get_metrics()))
        expected = [meters.Metric(name='Test Gauge', tags=(('key', 'value1'),), value=2, prometheus_type='gauge'),
                    meters.Metric(name='Test Gauge', tags=(('key', 'value2'),), value=3, prometheus_type='gauge')]
        self.assertEqual(actual, expected)

    def test_histograms_return_all_values_as_expected_with_defaults(self):
        test_histogram = meters.Histogram("test_histogram")

        @test_histogram.summarize_method
        def x(f):
            return f

        for q in range(100):
            x(q)

        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_histogram.get_metrics()))
        expected = [meters.Metric(name='test_histogram_sum', tags=(), value=4950, prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_count', tags=(), value=100, prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '9.9'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '19.8'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '29.700000000000003'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '39.6'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '49.5'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '59.400000000000006'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '69.3'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '79.2'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '89.10000000000001'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_bucket', tags=(('le', '99.0'),), value=10,
                                  prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_percentile', tags=(('percentile', '50'),), value=49.5,
                                  prometheus_type='gauge'),
                    meters.Metric(name='test_histogram_percentile', tags=(('percentile', '75'),), value=74.25,
                                  prometheus_type='gauge'),
                    meters.Metric(name='test_histogram_percentile', tags=(('percentile', '90'),),
                                  value=89.10000000000001, prometheus_type='gauge'),
                    meters.Metric(name='test_histogram_percentile', tags=(('percentile', '95'),), value=94.05,
                                  prometheus_type='gauge'),
                    meters.Metric(name='test_histogram_percentile', tags=(('percentile', '99'),), value=98.01,
                                  prometheus_type='gauge')]

        self.assertEqual(actual, expected)

    def test_histograms_keep_correct_number_of_data_when_set_max_data_values_called(self):
        test_histogram = meters.Histogram("test_histogram")
        test_histogram.set_max_data_values(25)

        @test_histogram.summarize_method
        def x(f):
            return f

        for q in range(100):
            x(q)

        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_histogram.get_metrics()))
        useful = [metric for metric in actual if metric.name in ["test_histogram_sum", "test_histogram_count"] ]
        expected = [meters.Metric(name='test_histogram_sum', tags=(), value=2175, prometheus_type='histogram'),
                    meters.Metric(name='test_histogram_count', tags=(), value=25, prometheus_type='histogram')]

        self.assertEqual(useful, expected)

    def test_histograms_create_correct_number_of_bins_when_set_number_of_bins_called(self):
        test_histogram = meters.Histogram("test_histogram")
        number_of_buckets = 5
        test_histogram.set_number_of_bins(number_of_buckets)

        @test_histogram.summarize_method
        def x(f):
            return f

        for q in range(100):
            x(q)

        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_histogram.get_metrics()))
        actual_number_of_buckets = len([metric for metric in actual if metric.name == "test_histogram_bucket"])
        self.assertEqual(actual_number_of_buckets, number_of_buckets)

    def test_histograms_create_correct_percentiles_when_set_percentiles_called(self):
        test_histogram = meters.Histogram("test_histogram")
        percentiles = [10, 50, 75]
        test_histogram.set_percentiles(percentiles)

        @test_histogram.summarize_method
        def x(f):
            return f

        for q in range(100):
            x(q)

        loop = asyncio.get_event_loop()
        actual = loop.run_until_complete(loop.create_task(test_histogram.get_metrics()))
        acutal_percentiles = [int(metric.tags[0][1]) for metric in actual if metric.name == "test_histogram_percentile"]
        self.assertEqual(acutal_percentiles, percentiles)


if __name__ == '__main__':
    unittest.main()
