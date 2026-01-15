from time import time
from typing import Any

from replicate.client import Client

from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.tool_choice_resolver import ConfiguredTool


class UsageTrackingPrediction:
    """Wraps a Replicate prediction to track usage metadata when wait() completes."""

    def __init__(
        self,
        wrapped_prediction: Any,
        configured_tool: ConfiguredTool,
        tracking_service: UsageTrackingService,
        image_size: str | None = None,
    ):
        self._wrapped_prediction = wrapped_prediction
        self._configured_tool = configured_tool
        self._tracking_service = tracking_service
        self._image_size = image_size
        self._tracked = False

    def wait(self) -> Any:
        start_time = time()
        result = self._wrapped_prediction.wait()
        runtime_seconds = int(time() - start_time)

        if not self._tracked:
            self._track_usage(runtime_seconds)
            self._tracked = True

        return result

    def _track_usage(self, runtime_seconds: int) -> None:
        tool, _, _ = self._configured_tool

        metrics = getattr(self._wrapped_prediction, "metrics", None)
        if metrics:
            runtime_from_metrics = getattr(metrics, "predict_time", None)
            if runtime_from_metrics is not None:
                runtime_seconds = int(runtime_from_metrics)

        self._tracking_service.track_image(
            tool = tool,
            runtime_seconds = runtime_seconds,
            image_size = self._image_size,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped_prediction, name)


class UsageTrackingReplicateClient(Client):
    """Wraps a Replicate client to automatically track usage for predictions."""

    def __init__(
        self,
        wrapped_client: Client,
        configured_tool: ConfiguredTool,
        tracking_service: UsageTrackingService,
        image_size: str | None = None,
    ):
        # Initialize parent Client - we'll delegate all calls to wrapped_client via __getattr__
        # We need to extract api_token and timeout from wrapped_client's internal state
        # Since Client doesn't expose these, we'll use the wrapped client directly
        # and only override the predictions property
        # Try to get timeout from wrapped client, fallback to default
        timeout = getattr(wrapped_client, "_timeout", None) or getattr(wrapped_client, "timeout", None)
        api_token = getattr(wrapped_client, "_api_token", None) or getattr(wrapped_client, "api_token", None)
        super().__init__(api_token = api_token, timeout = timeout)
        self._wrapped_client = wrapped_client
        self._configured_tool = configured_tool
        self._tracking_service = tracking_service
        self._image_size = image_size

    @property
    def predictions(self) -> Any:
        return UsageTrackingPredictions(
            self._wrapped_client.predictions,
            self._configured_tool,
            self._tracking_service,
            self._image_size,
        )

    def __getattr__(self, name: str) -> Any:
        # Delegate all other attributes to wrapped client
        return getattr(self._wrapped_client, name)


class UsageTrackingPredictions:
    """Wraps Replicate predictions collection to return tracked predictions."""

    def __init__(
        self,
        wrapped_predictions: Any,
        configured_tool: ConfiguredTool,
        tracking_service: UsageTrackingService,
        image_size: str | None = None,
    ):
        self._wrapped_predictions = wrapped_predictions
        self._configured_tool = configured_tool
        self._tracking_service = tracking_service
        self._image_size = image_size

    def create(self, **kwargs: Any) -> UsageTrackingPrediction:
        prediction = self._wrapped_predictions.create(**kwargs)
        return UsageTrackingPrediction(
            prediction,
            self._configured_tool,
            self._tracking_service,
            self._image_size,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped_predictions, name)
