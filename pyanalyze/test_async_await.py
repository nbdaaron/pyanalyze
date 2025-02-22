# static analysis: ignore
from .value import (
    GenericValue,
    KnownValue,
    TypedValue,
    make_weak,
    AnyValue,
    AnySource,
    SequenceIncompleteValue,
)
from .implementation import assert_is_value
from .test_node_visitor import assert_passes
from .test_name_check_visitor import TestNameCheckVisitorBase


class TestAsyncDef(TestNameCheckVisitorBase):
    @assert_passes()
    def test_missing_return(self):
        async def capybara() -> int:  # E: missing_return
            pass

        async def acouchy(cond: bool) -> int:  # E: missing_return
            if cond:
                return 4


class TestAsyncAwait(TestNameCheckVisitorBase):
    @assert_passes()
    def test_type_inference(self):
        from collections.abc import Awaitable

        async def capybara(x):
            assert_is_value(x, AnyValue(AnySource.unannotated))
            return "hydrochoerus"

        async def kerodon(x):
            task = capybara(x)
            assert_is_value(task, GenericValue(Awaitable, [KnownValue("hydrochoerus")]))
            val = await task
            assert_is_value(val, KnownValue("hydrochoerus"))

    @assert_passes()
    def test_type_error(self):
        async def capybara():
            await None  # E: unsupported_operation

    @assert_passes()
    def test_exotic_awaitable(self):
        from typing import TypeVar, Awaitable, Iterable

        T = TypeVar("T")
        U = TypeVar("U")

        class Aww(Iterable[T], Awaitable[U]):
            pass

        async def capybara(aw: Aww[int, str]) -> None:
            assert_is_value(await aw, TypedValue(str))

    @assert_passes()
    def test_async_comprehension(self):
        class ANext:
            async def __anext__(self) -> int:
                return 42

        class AIter:
            def __aiter__(self) -> ANext:
                return ANext()

        async def f():
            x = [y async for y in AIter()]
            assert_is_value(x, make_weak(GenericValue(list, [TypedValue(int)])))

    @assert_passes()
    def test_async_generator(self):
        import collections.abc
        from typing import AsyncIterator

        async def f() -> AsyncIterator[int]:
            yield 1
            yield 2

        async def capybara():
            x = f()
            assert_is_value(
                x, GenericValue(collections.abc.AsyncIterator, [TypedValue(int)])
            )
            ints = [i async for i in x]
            # TODO should be list[int] but we lose the type argument somewhere
            assert_is_value(
                ints,
                make_weak(GenericValue(list, [AnyValue(AnySource.generic_argument)])),
            )

    @assert_passes()
    def test_bad_async_comprehension(self):
        async def f():
            return [x async for x in []]  # E: unsupported_operation


class TestMissingAwait(TestNameCheckVisitorBase):
    @assert_passes()
    def test_asyncio_coroutine_internal(self):
        import asyncio

        @asyncio.coroutine
        def f():
            yield from asyncio.sleep(3)

        @asyncio.coroutine
        def g():
            f()  # E: missing_await

    @assert_passes()
    def test_yield_from(self):
        import asyncio

        @asyncio.coroutine
        def f():
            yield from asyncio.sleep(3)

        @asyncio.coroutine
        def g():
            yield from f()

    @assert_passes()
    def test_asyncio_coroutine_external(self):
        import asyncio

        @asyncio.coroutine
        def f():
            asyncio.sleep(3)  # E: missing_await

    def test_add_yield_from(self):
        self.assert_is_changed(
            """
            import asyncio

            @asyncio.coroutine
            def f():
                asyncio.sleep(3)
            """,
            """
            import asyncio

            @asyncio.coroutine
            def f():
                yield from asyncio.sleep(3)
            """,
        )

    @assert_passes()
    def test_has_yield_from_external(self):
        import asyncio

        @asyncio.coroutine
        def f():
            yield from asyncio.sleep(3)

    @assert_passes()
    def test_async_def_internal(self):
        async def f():
            return 42

        async def g():
            f()  # E: missing_await

    @assert_passes()
    def test_async_def_internal_has_await(self):
        async def f():
            return 42

        async def g():
            await f()

    @assert_passes()
    def test_async_def_external(self):
        import asyncio

        async def f():
            asyncio.sleep(1)  # E: missing_await

    def test_async_def_external_add_await(self):
        self.assert_is_changed(
            """
            import asyncio

            async def f():
                asyncio.sleep(1)
            """,
            """
            import asyncio

            async def f():
                await asyncio.sleep(1)
            """,
        )

    @assert_passes()
    def test_async_def_external_has_await(self):
        import asyncio

        async def f():
            await asyncio.sleep(1)


class TestArgSpec(TestNameCheckVisitorBase):
    @assert_passes()
    def test_asyncio_coroutine(self):
        import asyncio
        from collections.abc import Awaitable

        @asyncio.coroutine
        def f():
            yield from asyncio.sleep(3)
            return 42

        @asyncio.coroutine
        def g():
            assert_is_value(f(), GenericValue(Awaitable, [KnownValue(42)]))

    @assert_passes()
    def test_coroutine_from_typeshed(self):
        import asyncio
        import collections.abc

        async def capybara():
            assert_is_value(
                asyncio.sleep(3),
                GenericValue(
                    collections.abc.Awaitable, [AnyValue(AnySource.unannotated)]
                ),
            )
            return 42

    @assert_passes()
    def test_async_def_from_typeshed(self):
        from asyncio.streams import open_connection, StreamReader, StreamWriter
        from collections.abc import Awaitable

        async def capybara():
            # annotated as async def in typeshed
            assert_is_value(
                open_connection(),
                GenericValue(
                    Awaitable,
                    [
                        SequenceIncompleteValue(
                            tuple, [TypedValue(StreamReader), TypedValue(StreamWriter)]
                        )
                    ],
                ),
            )
            return 42

    @assert_passes()
    def test_async_def(self):
        from collections.abc import Awaitable

        async def f():
            return 42

        async def g():
            assert_is_value(f(), GenericValue(Awaitable, [KnownValue(42)]))


class TestNoReturn(TestNameCheckVisitorBase):
    @assert_passes()
    def test(self):
        from typing import NoReturn

        async def noret() -> NoReturn:
            raise NotImplementedError

        async def capybara(cond) -> int:
            if cond:
                return 3
            else:
                await noret()

        async def pacarana(cond) -> int:  # E: missing_return
            if cond:
                return 3
            else:
                x = noret()
                print(x)

        async def hutia(cond) -> int:  # E: missing_return
            if cond:
                return 3


class TestAsyncGenerator(TestNameCheckVisitorBase):
    @assert_passes()
    def test_async_gen(self):
        import collections.abc
        from typing import AsyncIterator

        async def gen() -> AsyncIterator[int]:
            yield 3

        async def capybara() -> None:
            assert_is_value(
                gen(), GenericValue(collections.abc.AsyncIterator, [TypedValue(int)])
            )
            async for i in gen():
                # TODO should be int
                assert_is_value(i, AnyValue(AnySource.generic_argument))
