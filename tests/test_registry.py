import unittest
import os
import sys
lib_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'knotty')
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

import knotty.registry as registry
import knotty.meters as meters


class TestRegistry(unittest.TestCase):
    def test_add_meter_enters_new_meter_into_meters_dictionary(self):
        registry.MeterRegistry._meters = dict()
        test_counter = meters.Counter("test_counter")
        registry.MeterRegistry._meters = dict()
        registry.MeterRegistry.add_meter(test_counter)
        self.assertEqual(registry.MeterRegistry._meters, {(meters.Counter, "test_counter"): test_counter})

    def test_is_meter_registered_returning_true_for_meter_that_exists(self):
        registry.MeterRegistry._meters = dict()
        test_counter = meters.Counter("test_counter")
        registry.MeterRegistry._meters = dict()
        registry.MeterRegistry.add_meter(test_counter)
        self.assertTrue(registry.MeterRegistry.is_meter_registered(test_counter))

    def test_that_meters_are_auto_registering_themselves(self):
        registry.MeterRegistry._meters = dict()
        test_counter = meters.Counter("test_counter")
        self.assertTrue(registry.MeterRegistry.is_meter_registered(test_counter))

    def test_get_all_metrics_is_return_expected_values(self):
        registry.MeterRegistry._meters = dict()
        test_gauge = meters.Gauge("test_gauge")
        test_gauge.set_gauge_function(lambda: 1)
        self.assertEqual(registry.MeterRegistry.get_all_metrics(), [meters.Metric(name='test_gauge', tags=(), value=1,
                                                                                  prometheus_type='gauge')])



if __name__ == '__main__':
    unittest.main()
