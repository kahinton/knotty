"""
This module should hold the registries responsible for managing different metric groups
"""
import asyncio
from threading import Thread
from logging import getLogger


class RegistryCollisionException(Exception):
    pass


class MeterRegistry:
    push_interval: int = None
    _meters = dict()
    _loop = asyncio.new_event_loop()
    _thread: Thread = None

    @classmethod
    def add_meter(cls, meter: "knotty.meters.BaseMeter") -> None:
        """
        Adds a new meter to the registry dictionary.
        :param meter: knotty.meters.BaseMeter
        :return:
        """
        logger = getLogger(f"{cls.__name__}.add_meter")
        meter_key = tuple([meter.__class__, meter.name])
        logger.debug(f"Adding meter {meter_key}")
        cls._meters[meter_key] = meter

    @classmethod
    def get_meter(cls, name: str, meter_class: "knotty.meters.BaseMeter") -> "knotty.meters.BaseMeter":
        """
        Either returns the requested meter from the registry if it has already been created, or creates the requested
        meter (which will automatically register itself). This is the suggested way of getting a reference to
        any desired meter.

        :param name: str: The name of the meter
        :param meter_class: The desired subclass of knotty.meters.BaseMeter that should be created or returned
        :return: knotty.meters.BaseMeter
        """
        return cls._meters.get(tuple([meter_class, name])) or meter_class(name)

    @classmethod
    def is_meter_registered(cls, meter: "knotty.meters.BaseMeter") -> bool:
        """
        Verifies whether the input meter has been added to the registry previously and returns the corresponding bool.
        :param meter: Any meter that inherits from the knotty.meters.BaseMeter class
        :return: bool: Whether or not the given meter has already been added to the registry
        """
        return tuple([meter.__class__, meter.name]) in cls._meters.keys()

    @classmethod
    def _start_background_loop(cls) -> None:
        """
        Starts a new abstract event loop. This is used to start the new loop that will be used to gather the metrics
        from the different meters in a concurrent manner.
        :return:
        """
        logger = getLogger(f"{cls.__name__}._start_background_loop")
        logger.debug("Starting Knotty background collection loop.")
        asyncio.set_event_loop(cls._loop)
        cls._loop.run_forever()

    @classmethod
    async def _async_gather_metrics(cls) -> "[knotty.meters.Metric]":
        """
        Creates a list of synchronous tasks and applies them to the class async event loop.
        :return: [knotty.meters.Metric]: A list of metrics returned from the registered meters
        """
        tasks = [cls._loop.create_task(meter.get_metrics()) for key, meter in cls._meters.items()]
        results = await asyncio.gather(*tasks)
        return results

    @classmethod
    def get_all_metrics(cls) -> "[knotty.meters.Metric]":
        """
        Ensures that the classes execution thread is up and running before managing the collection and return of all
        metrics from all registered meters.
        :return: [knotty.meters.Metric]: A flattened list of all metrics from all registered meters
        """
        logger = getLogger(f"{cls.__name__}.get_all_metrics")
        logger.debug("Collecting all metrics.")
        if cls._thread is None:
            logger.debug("Knotty collection thread not initiated, starting now.")
            cls._thread = Thread(target=cls._start_background_loop, daemon=True)
            cls._thread.start()
        task = asyncio.run_coroutine_threadsafe(cls._async_gather_metrics(), cls._loop)
        return [metric for metric_list in task.result() for metric in metric_list]
