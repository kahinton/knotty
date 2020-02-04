"""
This module is responsible for holding the base definitions of the different types of metric meters.
"""
from logging import getLogger
from time import time
from functools import wraps
from numpy import percentile, histogram
from knotty import registry
from dataclasses import dataclass
from collections import deque, OrderedDict


def _add_tags(tag_dict: dict, new_tags: dict) -> dict:
    """
    Adds new tags to a previously existing set of tags.

    :param tag_dict: The previously existing tag dictionary that should be added to
    :param new_tags: The new dictionary of tags to be added
    :return: dict: The combined dictionary of old and new tags
    """
    for value in new_tags.values():
        try:
            str(value)
        except Exception as e:
            raise ValueError("All metrics tags must be castable to str: {0}".format(e))
    return {**tag_dict, **new_tags}


def _remove_tags(tag_dict: dict, tag_key_list: [str]) -> dict:
    """
    Removes the requested tags from the tag dictionary.

    :param tag_dict: The tag dictionary to remove tags from
    :param tag_key_list: A list of the tag keys to be removed
    :return: Returns the tag dictionary with the requested keys removed
    """
    new_dict = tag_dict
    for tag in tag_key_list:
        del (new_dict[tag])
    return new_dict


@dataclass()
class Metric:
    """
    Dataclass for storing metric data.
    """
    name: str
    tags: tuple
    value: float
    prometheus_type: str


class GlobalTags:
    """
    Class for storing global level tags. These will be applied to all metrics generated by all meters.
    """
    tags = dict()

    @classmethod
    def add_global_tags(cls, tags: dict) -> None:
        """
        Adds global level tags.

        :param tags: a {str, str} dict of tags to be added at the global level.
        :return:
        """
        cls.tags = _add_tags(cls.tags, tags)

    @classmethod
    def remove_global_tags(cls, tags: [str]) -> None:
        """
        Removes global level tags

        :param tags: A list of strings representing the keys of the global tag that you would like removed.
        :return:
        """
        cls.tags = _remove_tags(cls.tags, tags)


class BaseMeter:
    """
    The BaseMeter class provides some common functionality that should be shared across any fully fleshed out meter
    classes.
    """
    _name = None
    _tags = dict()
    _metric_keys = set()
    _context_tags = dict()

    @property
    def name(self) -> str:
        """
        Provide read only unprotected access to the classes name.

        :return: str
        """
        return self._name

    def _ensure_registered_with_registry(self) -> None:
        """
        Ensures that when a meter is created directly it is properly registered. If an identical meter has already been
        created, a RegistryCollisionException will be thrown. This is why you should manage the creation of all meters
        through the use of registry.MeterRegistry.get_meter.

        :return:
        """
        if registry.MeterRegistry.is_meter_registered(self):
            raise registry.RegistryCollisionException("{0} with the name {1} already exists.".
                                                      format(self.__class__.__name__, self._name))
        registry.MeterRegistry.add_meter(self)

    def get_tags(self) -> {str, str}:
        """
        Gets the combination of the global tags and the local tags of the meter.

        :return:
        """
        copy_globals = GlobalTags.tags
        return {**copy_globals, **self._tags, **self._context_tags}

    def set_context_tags(self, tags: dict) -> None:
        """
        Sets the context tag dictionary of the meter to the input dictionary. These should always be reset between
        measurements

        :param tags: {str, str} dictionary of tags to apply to the current meter context.
        :return:
        """
        self._context_tags = tags

    def reset_context_tags(self) -> None:
        """
        Resets the context tags back to an empty dict

        :return:
        """
        self._context_tags = dict()

    def set_tags(self, tags: dict) -> None:
        """
        Sets the tag dictionary of the meter to the input dictionary. THIS WILL OVERWRITE ALL PREVIOUSLY DEFINED TAGS.

        :param tags: {str, str} dictionary of tags to apply to the meter.
        :return:
        """
        self._tags = tags

    def add_tags(self, tags: dict) -> None:
        """
        Combines the input tags dictionary with the current tag dictionary of the meter.

        :param tags:
        :return:
        """
        self._tags = _add_tags(self._tags, tags)

    def remove_tags(self, tags: [str]) -> None:
        """
        Removes tags from the meter.

        :param tags: [str] List of keys for tags to be removed.
        :return:
        """
        self._tags = _remove_tags(self._tags, tags)

    def augmentor(self, method, method_results, *args, **kwargs) -> None:
        """
        Meters have the option to be able to use augmentor functions when they are using decorators to monitor a method.
        These can act as a powerful way to modify the state of the meter to produce unique metric keys to monitor many
        different states under a single meter. In general the augmentor function should be a method defined outside the
        scope of the meter that is applied to handle data specific to what the meter is monitoring.

        :param self: any methods used as augmentors need to provide a self parameter for the meter to passed into
        :param method: the method that is being wrapped by the meter's decorator
        :param method_results: the return value of the wrapped method
        :param args: the args that were passed into the wrapped method
        :param kwargs: the keyword args that were passed into the wrapped method.
        :return:
        """
        pass

    async def get_metrics(self) -> [Metric]:
        """
        All meters need to expose and async method to return a list of metrics to the registry.

        :return: [Metric]
        """
        raise NotImplementedError("Class {0} has not implemented the get_metrics functions. "
                                  "All meters must implement this function".format(self.__class__))


class Timer(BaseMeter):
    """
    The Timer Meter is designed to measure the total execution time of a given callable as well as keeping track of how
    many times it has been called. This provides a good sense of the average execution time of a function. If more
    detail is need, try using the Histogram instead.
    """
    def __init__(self, name: str):
        self._name = name
        # Current times can probably get blasted out of here.
        self.current_time = dict()
        self.total_time = dict()
        self.counter = Counter(name + "_time_count")
        self.counter.modify_prometheus_type("summary")
        self._ensure_registered_with_registry()

    def timer(self, method: callable) -> callable:
        """
        Wraps the given method and measures how long it takes to run at every invocation. The augmentor can be
        utilized to provide any additionally needed functionality around the method call. The times are summed as the
        process continues to run, and a Counter is incremented at each execution to provide a full summary metric.

        :param method: callable
        :return:
        """
        @wraps(method)
        def measure_execution(*args, callback_timer: Timer = self, **kwargs):
            start = time()
            method_result = method(*args, **kwargs)
            execution_time = time() - start
            callback_timer.augmentor(callback_timer, method, method_result, *args, **kwargs)
            metric_key = tuple(callback_timer.get_tags().items())
            callback_timer._metric_keys.add(metric_key)
            callback_timer.current_time[metric_key] = execution_time
            callback_timer.total_time[metric_key] = (callback_timer.total_time.get(metric_key) or 0) + execution_time
            callback_timer.counter.increment(metric_key=metric_key)
            callback_timer.reset_context_tags()
            return method_result

        return measure_execution

    async def get_metrics(self) -> [Metric]:
        """
        Returns a list of metrics for the Timer instance. This will only return the sum of the time spent, however a
        complimentary Counter will generate the partner metric for the summary to be complete.

        :return: [Metric]
        """
        total_metrics = [Metric(self.name+"_time_sum", key, value, "summary")
                         for key, value in self.total_time.items()]
        return total_metrics


class Counter(BaseMeter):
    """
    The Counter Meter does exactly what it sounds like. Counters are only designed to increase values, such as measuring
    the number of times that a function has been invoked. If you have a value that can go up or down, consider using a
    Gauge instead.
    """

    def __init__(self, name: str):
        self._name = name
        self._count = dict()
        self._ensure_registered_with_registry()
        self._prometheus_type = "counter"

    def auto_count_method(self, method: callable) -> callable:
        """
        Wraps the given method and increments the counter by 1 every time the function is called. The augmentor can be
        utilized to provide any additionally needed functionality around the method call.

        :param method: callable
        :return:
        """
        @wraps(method)
        def count_execution(*args, callback_counter: Counter = self, **kwargs):
            method_result = method(*args, **kwargs)
            callback_counter.augmentor(callback_counter, method, method_result, *args, **kwargs)
            metric_key = tuple(callback_counter.get_tags().items())
            callback_counter._metric_keys.add(metric_key)
            callback_counter.increment(metric_key=metric_key)
            callback_counter.reset_context_tags()
            return method_result

        return count_execution

    def modify_prometheus_type(self, prometheus_type: str) -> None:
        """
        This function can be used to change the Prometheus type on the outgoing metrics. This is mainly used in
        conjunction with a Timer to create a full Prometheus summary object. It is NOT recommended to use this function
        for anything else.

        :param prometheus_type: str
        :return:
        """
        self._prometheus_type = prometheus_type

    def increment(self, amount: int = 1, metric_key: tuple = None) -> None:
        """
        Increments the value of the Counter corresponding to the given metric_key.

        :param amount:
        :param metric_key:
        :return:
        """
        key = metric_key or tuple(self.get_tags().items())
        self._metric_keys.add(key)
        self._count[key] = (self._count.get(key) or 0) + amount
        self.reset_context_tags()

    async def get_metrics(self) -> [Metric]:
        """
        Returns a list of metrics for the Counter instance.

        :return: [Metric]
        """
        return [Metric(self.name, key, value, self._prometheus_type) for key, value in self._count.items()]


class Gauge(BaseMeter):
    """
    The Gauge type meter stores a measurement function which will be called whenever a request for metrics is made. This
    value can go up or down.
    """

    logger = getLogger(__name__)

    def __init__(self, name: str):
        self._name = name
        self.value_function = None
        self.key_tag = None
        self._ensure_registered_with_registry()
        self._integer_return = True

    def set_gauge_function(self, value_function: callable, key_tag: str = None) -> None:
        """
        Set the function that the gauge will call when measuring a value. The function either needs to return a number
        or a dictionary whose keys are strings and values are numbers. If your function returns a dictionary, you must
        provide a key_tag. The key_tag will be used to create unique metric tags from the keys of the dictionary. eg:
        If you provide the key_tag "value_name" and your function produces the following dictionary:

        {
        "value1": 1
        "value2": 2
        }

        the following metrics will be returned:
        [
        Metric("gauge_name", (("value_name", "value1"), 1, "gauge")
        Metric("gauge_name", (("value_name", "value2"), 2, "gauge")
        ]

        :param value_function: Function the gauge will use to take a measure. Should return number or {str, number}.
        :param key_tag: str: An identifier to produce unique tags from the keys of a returned dictionary.
        :return:
        """
        self.value_function = value_function
        self.key_tag = key_tag
        self._integer_return = not bool(key_tag)

    async def get_metrics(self) -> [Metric]:
        """
        Returns a list of metrics for the Gauge instance.

        :return: [Metric]
        """
        try:
            measurement = self.value_function()
            self.augmentor(self.value_function, measurement, [], {})
            base_key = tuple(self.get_tags().items())
            self.reset_context_tags()

            if self._integer_return:
                if isinstance(measurement, int) or isinstance(measurement, float):
                    return [Metric(self.name, base_key, measurement, "gauge")]
                else:
                    raise ValueError("Gauge {0} is expecting function to return number, received {1} instead"
                                     .format(self.name, type(measurement)))
            else:
                if isinstance(measurement, dict) or isinstance(measurement, OrderedDict):
                    if all([isinstance(value, int) or isinstance(value, float) for _, value in measurement.items()]):
                        return [Metric(self.name, base_key + tuple({self.key_tag: key}.items()), value, "gauge")
                                for key, value in measurement.items()]
                    else:
                        raise ValueError("Gauge {0} received a dictionary response with non-number values"
                                         .format(self.name))
                else:
                    raise ValueError("Gauge {0} received a value that is neither a number or dict. Received {1}"
                                     .format(self.name, type(measurement)))

        except Exception as e:
            self.logger.error(e)


class Histogram(BaseMeter):
    """
    The Histogram meter is used to keep track of a set of data and provide statistical analysis regarding their
    distribution.
    """

    # Todo: Add method to summarize function call time.
    logger = getLogger(__name__)

    def __init__(self, name: str):
        self._name = name
        self._current_values = dict()
        self._bin_count = 10
        self._percentiles = [50, 75, 90, 95, 99]
        self._max_data_values = 1000
        self._ensure_registered_with_registry()

    def add_new_value(self, value: float, metric_key: tuple = None) -> None:
        """
        Stores a new value for the given metric key. If no metric key is provided the current tags of the histogram will
        be used.

        :param value: float (or int)
        :param metric_key: tuple
        :return:
        """
        key = metric_key or tuple(self.get_tags().items())
        self._metric_keys.add(key)
        if self._current_values.get(key):
            self._current_values[key].append(value)
        else:
            self._current_values[key] = deque([value], maxlen=self._max_data_values)

    def set_max_data_values(self, max_data_values: int) -> None:
        """
        Sets the maximum number of data points that the histogram will keep. Storing more data will result in more
        memory being used, as well as an increase in cpu usage for calculating metrics. 
        :param max_data_values: int
        :return: 
        """
        self._max_data_values = max_data_values

    def set_percentiles(self, percentiles: [int]) -> None:
        """
        Sets the list of percentiles that will be calculated when metrics are exported.
        :param percentiles: [int]
        :return:
        """
        self._percentiles = percentiles

    def set_number_of_bins(self, bin_count: int) -> None:
        """
        Sets the number of bins that should be created when exporting the histogram metrics
        :param bin_count: int
        :return:
        """
        self._bin_count = bin_count

    def summarize_method(self, method: callable) -> callable:
        """
        Wraps the given method and adds it's return value to the current set of stored metrics. The augmentor can be
        utilized to provide any additionally needed functionality around the method call.

        :param method: A callable method that should return either an int or a float (or something castable to either)
        :return:
        """
        @wraps(method)
        def track_execution(*args, callback_summary: Histogram = self, **kwargs):
            method_result = method(*args, **kwargs)
            if not (isinstance(method_result, int) or isinstance(method_result, float)):
                try:
                    method_result = float(method_result)
                except (ValueError, TypeError) as e:
                    callback_summary.logger.error("Can not cast type {0} to float in histogram {1}: {2}"
                                                  .format(type(method_result), callback_summary.name, e))
                except Exception as e:
                    callback_summary.logger.error(e)
            callback_summary.augmentor(callback_summary, method, method_result, *args, **kwargs)
            metric_key = tuple(callback_summary.get_tags().items())
            callback_summary._metric_keys.add(metric_key)
            callback_summary.add_new_value(method_result, metric_key=metric_key)
            return method_result

        return track_execution

    def _get_percentile(self, percentile_value: int) -> {tuple: tuple}:
        """
        Creates a dictionary giving the value of the requested percentile.

        :param percentile_value: The percentile to calculate, eg 95 will return the 95th percentile
        :return: {tuple: tuple(int, int)} Key tuple corresponds to metric key, value tuple is value and percentile
        """
        return {key: percentile(value, percentile_value) for key, value in self._current_values.items()}

    def _get_histogram(self, number_of_bins: int = 10) -> {tuple: tuple}:
        """
        Creates a dictionary of histograms corresponding to each different available metric key.

        :param number_of_bins: The requested number of bins to be automatically generated by numpy
        :return: {tuple: tuple([],[]} Key tuple corresponds to metric key, value tuple represents numpy histogram
        """
        return {key: histogram(value, bins=number_of_bins) for key, value in self._current_values.items()}

    async def get_metrics(self) -> [Metric]:
        """
        Returns a list of metrics for the Histogram instance. These metrics include the sum of all measured points, the
        count of all measured points, the number of values in each bucket, and metrics displaying the different
        percentiles that the instance is instantiated to track.

        :return: [Metric]
        """
        metrics = []
        metrics += [Metric(self.name + "_sum", key, sum(value), "histogram")
                    for key, value in self._current_values.items()]
        metrics += [Metric(self.name + "_count", key, len(value), "histogram")
                    for key, value in self._current_values.items()]

        for key, value in self._get_histogram(self._bin_count).items():
            for bin_value in range(self._bin_count):
                full_key = key + tuple({"le": str(value[1][bin_value+1])}.items())
                metrics += [Metric(self.name + "_bucket", full_key, int(value[0][bin_value]), "histogram")]

        for p in self._percentiles:
            metrics += [Metric(self.name + "_percentile", key +
                               tuple({"percentile": str(p)}.items()), float(value), "gauge")
                        for key, value in self._get_percentile(p).items()]
        return metrics