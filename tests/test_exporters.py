import unittest
import os
import sys
lib_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

import knotty.registry as registry
import knotty.exporters as exporters
import knotty.meters as meters
from time import sleep


class DependableTimer(meters.Timer):
    """
    This is a nice fake timer for our tests that always returns the same time.
    """
    async def get_metrics(self) -> [meters.Metric]:
        total_metrics = [meters.Metric(self.name + "_time_sum", key, 1, "summary")
                         for key, _ in self.total_time.items()]
        return total_metrics


class TestExporters(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        registry.MeterRegistry._meters = dict()
        test_histogram = registry.MeterRegistry.get_meter("test_histogram", meters.Histogram)
        test_histogram.set_percentiles([50])
        test_histogram.set_number_of_bins(2)

        @test_histogram.summarize_method
        def x(f):
            return f

        for q in range(100):
            x(q)

        test_timer = registry.MeterRegistry.get_meter("test_timer", DependableTimer)

        @test_timer.timer
        def bogus_function():
            sleep(.001)

        bogus_function()

        test_gauge = registry.MeterRegistry.get_meter("test_gauge", meters.Gauge)
        test_gauge.set_gauge_function(lambda: 1)

    def test_OpenTSDB_metrics_are_formatted_correctly(self):
        open_tsdb = exporters.OpenTSDBExporter(30, "http://localhost")
        expected = ['metric', 'timestamp', 'value', 'tags']

        matching_results = [list(metric.keys()) == expected for metric in open_tsdb._metrics_translator()]
        self.assertTrue(all(matching_results) and len(matching_results) == 8)

    def test__PrometheusStarter_metrics_are_formatted_correctly(self):
        any_prometheus = exporters._PrometheusStarter()
        expected = "#TYPE test_histogram histogram test_histogram_sum{} 4950 test_histogram_count{} 100 test_histogram_bucket{le=\"49.5\"} 50 test_histogram_bucket{le=\"99.0\"} 50 #TYPE test_histogram_percentile gauge test_histogram_percentile{percentile=\"50\"} 49.5 #TYPE test_timer_time summary test_timer_time_count{} 1 test_timer_time_sum{} 1 #TYPE test_gauge gauge test_gauge{} 1 "
        self.assertEqual(any_prometheus._metrics_translator().replace("\n", " "), expected)

    def test__InfluxDB_metrics_are_formatted_correctly(self):
        class FakeInflux:
            host = "http://localhost"

            def write_points(self, points):
                pass

        influx_db = exporters.InfluxDBExporter(30, FakeInflux())
        expected = ['measurement', 'time', 'fields', 'tags']
        matching_results = [list(metric.keys()) == expected for metric in influx_db._metrics_translator()]
        self.assertTrue(all(matching_results) and len(matching_results) == 8)

    def test_Graphite_metrics_are_formatted_correctly(self):
        graphite = exporters.GraphiteExporter(30, "http://localhost")
        expected = ['test.histogram.sum.', 'test.histogram.count.', 'test.histogram.bucket.le.49.5',
                    'test.histogram.bucket.le.99.0', 'test.histogram.percentile.percentile.50',
                    'test.timer.time.count.', 'test.timer.time.sum.', 'test.gauge.']

        self.assertEqual([metric[0] for metric in graphite._metrics_translator()], expected)



if __name__ == '__main__':
    unittest.main()
