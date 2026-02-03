from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class NamespaceProxy(Generic[T]):
    """
    Generic proxy for transparently delegating calls to SDK namespace objects.

    This proxy allows decorators to intercept specific method calls on SDK namespaces
    while transparently delegating all other attribute accesses to the wrapped object.

    Usage:
        Wrap an SDK namespace and provide an interceptor function that gets called
        for every attribute access. The interceptor can choose to return a modified
        version (e.g., wrapped method) or pass through the original attribute.

    Example:
        ```python
        def my_interceptor(name: str, attr: Any) -> Any:
            if name == "generate_content":
                # Wrap this specific method to track usage
                return wrap_with_tracking(attr)
            # Pass through all other attributes unchanged
            return attr

        proxy = NamespaceProxy(client.models, my_interceptor)
        # proxy.generate_content() -> intercepted and wrapped
        # proxy.list_models() -> passed through to original client.models
        ```

    This is used in Google AI and Replicate decorators to intercept specific SDK calls
    (like `generate_content` or `create`) while maintaining full SDK compatibility.
    """

    __wrapped: T
    __interceptor: Callable[[str, Any], Any]

    def __init__(self, wrapped: T, interceptor: Callable[[str, Any], Any]):
        self.__wrapped = wrapped
        self.__interceptor = interceptor

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self.__wrapped, name)
        return self.__interceptor(name, attr)
