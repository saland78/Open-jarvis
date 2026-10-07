"""Buffer a single secured engine stream; never expose partial JSON."""
from __future__ import annotations
import asyncio
import inspect
import time

from synthesis_contract import validate_contract, render_contract


async def collect(stream, messages, sources, measurement, *, validate=validate_contract, render=render_contract):
    parts = []
    size = 0
    completed = False
    terminal = False
    chunks = 0
    start = time.perf_counter()
    iterator = stream(messages)
    try:
        async for chunk in iterator:
            chunks += 1
            if chunks > 4096 or terminal:
                completed = False
                break
            if getattr(chunk, 'tool_calls', None):
                break  # no tool execution in this profile
            content = getattr(chunk, 'content', '')
            if content is None:
                content = ''  # StreamChunk terminal frames have no text.
            if not isinstance(content, str):
                break
            if content:
                if measurement.record.get('structuredFirstJsonMs') is None:
                    measurement.record['structuredFirstJsonMs'] = round((time.perf_counter()-start)*1000, 2)
                size += len(content)
                if size > 32000:
                    break
                parts.append(content)
            reason = getattr(chunk, 'finish_reason', None)
            if reason:
                completed = reason == 'stop'
                terminal = True
    finally:
        await iterator.aclose()
        measurement.record['structuredGenerationMs'] = round((time.perf_counter()-start)*1000, 2)
    validation_started = time.perf_counter()
    result = validate(''.join(parts), sources, completed=completed)
    if inspect.isawaitable(result):
        result = await result
    measurement.record['structuredValidationMs'] = round((time.perf_counter()-validation_started)*1000, 2)
    measurement.record['structuredOutcome'] = ('accepted' if result['status'] == 'valid_structure_pending_semantic_review' else result['status'])
    return result, render(result)


async def until_disconnect(operation, receive):
    """Cancel the producer on disconnect; always release both tasks."""
    async def disconnected():
        while True:
            event = await receive()
            if event['type'] == 'http.disconnect':
                return
    producer = asyncio.create_task(operation)
    watcher = asyncio.create_task(disconnected())
    try:
        done, _ = await asyncio.wait((producer, watcher), return_when=asyncio.FIRST_COMPLETED)
        if watcher in done:
            raise asyncio.CancelledError()
        return await producer
    finally:
        for task in (producer, watcher):
            if not task.done():
                task.cancel()
        await asyncio.gather(producer, watcher, return_exceptions=True)
