import queue
import sqlite3
import threading
from dataclasses import dataclass

from network.message import TelemetryMessage
from persistence.event_store import EventStore


@dataclass(frozen=True)
class IngestedEvent:
    """수신 스레드가 검증을 마치고 writer 큐로 넘기는 이벤트."""

    message: TelemetryMessage
    received_at: str
    zone_d_consecutive_count: int

    @property
    def observed_at(self) -> str:
        # JSON v1은 원본 timestamp를, CSV v1(timestamp 없음)은 수신 시각을 이벤트 시각으로 쓴다.
        return self.message.timestamp or self.received_at


# 큐에 넣는 종료 신호. 앞선 이벤트가 모두 처리된 뒤에 소비된다.
_SHUTDOWN = object()


class EventWriter:
    """bounded 큐를 소비하는 단일 writer 스레드. DB에 쓰는 유일한 지점이다.

    수신 스레드는 submit()으로 큐에 넣기만 하고 DB를 직접 건드리지 않는다. 큐가
    가득 차면 새 이벤트를 버린다(reject-newest, 누적 수를 센다). 종료 시에는 큐에
    남은 이벤트를 모두 처리한 뒤 스레드를 멈춘다.
    """

    def __init__(self, event_store: EventStore, *, max_queue_size: int = 1000) -> None:
        if max_queue_size <= 0:
            raise ValueError("max_queue_size는 양수여야 합니다")
        self._event_store = event_store
        self._queue: "queue.Queue[object]" = queue.Queue(maxsize=max_queue_size)
        self._thread: threading.Thread | None = None
        self.dropped_count = 0

    def submit(self, event: IngestedEvent) -> bool:
        """이벤트를 큐에 넣는다. 가득 차 있으면 버리고 False를 돌려준다."""
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            self.dropped_count += 1
            print(
                "  ➔ 🟠 [백프레셔] 저장 큐가 가득 차 이벤트를 버립니다 "
                f"(누적 유실 {self.dropped_count}건)"
            )
            return False

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("이미 시작된 writer입니다")
        self._thread = threading.Thread(
            target=self._run, name="event-writer", daemon=True
        )
        self._thread.start()

    def wait_idle(self) -> None:
        """큐에 쌓인 이벤트가 모두 처리될 때까지 기다린다."""
        self._queue.join()

    def stop(self, *, timeout: float = 5.0) -> None:
        """큐에 남은 이벤트를 모두 처리한 뒤 writer 스레드를 정지한다."""
        if self._thread is None:
            return
        self._queue.put(_SHUTDOWN)
        self._thread.join(timeout=timeout)
        self._thread = None

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if isinstance(item, IngestedEvent):
                    self._event_store.record_event(
                        item.message,
                        observed_at=item.observed_at,
                        received_at=item.received_at,
                        zone_d_consecutive_count=item.zone_d_consecutive_count,
                    )
                elif item is _SHUTDOWN:
                    return
            except sqlite3.Error as error:
                print(f"  ➔ 🔴 [저장 실패] 이벤트를 기록하지 못했습니다: {error}")
            finally:
                self._queue.task_done()
