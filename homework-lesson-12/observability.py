from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from config import settings, sync_langfuse_environment


@dataclass
class LangfuseRun:
    enabled: bool
    handler: Any = None
    client: Any = None
    trace_id: str | None = None
    output: dict[str, Any] = field(default_factory=dict)

    def with_callbacks(self, config: dict) -> dict:
        runtime_config = dict(config)
        metadata = dict(runtime_config.get("metadata") or {})
        metadata.update(
            {
                "homework": "lesson-12",
                "session_id": settings.langfuse_session_id,
                "user_id": settings.langfuse_user_id,
                "langfuse_tags": ",".join(settings.langfuse_tag_list),
                "model_name": settings.model_name,
            }
        )
        runtime_config["metadata"] = metadata

        if self.handler is not None:
            callbacks = list(runtime_config.get("callbacks") or [])
            callbacks.append(self.handler)
            runtime_config["callbacks"] = callbacks

        return runtime_config

    def flush(self) -> None:
        if self.client is not None:
            self.client.flush()


@contextmanager
def langfuse_observed_run(user_request: str, thread_id: str) -> Iterator[LangfuseRun]:
    sync_langfuse_environment()

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        yield LangfuseRun(enabled=False)
        return

    from langfuse import get_client, propagate_attributes
    from langfuse.langchain import CallbackHandler

    client = get_client()
    handler = CallbackHandler()
    run = LangfuseRun(enabled=True, handler=handler, client=client)

    metadata = {
        "homework": "lesson-12",
        "thread_id": thread_id,
        "model_name": settings.model_name,
        "rag_collection": settings.qdrant_collection,
    }

    with client.start_as_current_observation(
        as_type="span",
        name=settings.langfuse_trace_name,
        input={"request": user_request},
    ) as root_span:
        with propagate_attributes(
            trace_name=settings.langfuse_trace_name,
            session_id=settings.langfuse_session_id,
            user_id=settings.langfuse_user_id,
            tags=settings.langfuse_tag_list,
            metadata=metadata,
        ):
            run.trace_id = client.get_current_trace_id()
            try:
                yield run
                root_span.update(output=run.output)
                if hasattr(client, "set_current_trace_io"):
                    client.set_current_trace_io(
                        input={"request": user_request},
                        output=run.output,
                    )
            finally:
                run.flush()
