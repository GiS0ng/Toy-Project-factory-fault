import queue
import threading
from dataclasses import dataclass

from network.message import MessageType, TelemetryMessage
from persistence.event_store import EventStore


@dataclass(frozen=True)
class IngestedEvent:
    """수신 스레드가 검증을 마치고 writer 큐로 넘기는 이벤트."""

    message: TelemetryMessage
    received_at: str

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

    Zone D 연속 카운트는 이 스레드 안에서만 계산하므로 락이 필요 없고, 저장 순서와
    카운트가 항상 일치한다(C++ MachineMonitor.consecutiveZoneDCount_와 같은 규칙).
    """

    def __init__(
        self,
        event_store: EventStore,
        *,
        max_queue_size: int = 1000,
        owns_store: bool = False,
    ) -> None:
        if max_queue_size <= 0:
            raise ValueError("max_queue_size는 양수여야 합니다")
        self._event_store = event_store
        # owns_store=True면 stop()에서 연결을 닫는다. 조립부(create_bridge)가 연 연결만
        # 여기서 책임진다. 테스트처럼 밖에서 관리하는 연결은 건드리지 않는다.
        self._owns_store = owns_store
        self._queue: "queue.Queue[object]" = queue.Queue(maxsize=max_queue_size)
        self._thread: threading.Thread | None = None
        self._zone_d_streak: dict[int, int] = {}
        self._lock = threading.Lock()
        self.dropped_count = 0
        self.write_error_count = 0

    def submit(self, event: IngestedEvent) -> bool:
        """이벤트를 큐에 넣는다. 가득 차 있으면 버리고 False를 돌려준다."""
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            with self._lock:
                self.dropped_count += 1
                dropped = self.dropped_count
            print(
                "  ➔ 🟠 [백프레셔] 저장 큐가 가득 차 이벤트를 버립니다 "
                f"(누적 유실 {dropped}건)"
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
        """큐에 남은 이벤트를 모두 처리한 뒤 writer 스레드를 정지하고 연결을 닫는다."""
        if self._thread is None:
            return
        try:
            # writer가 살아 있으면 큐를 비우며 자리를 낸다. 이미 죽었으면 Full로 넘어간다.
            self._queue.put(_SHUTDOWN, timeout=timeout)
        except queue.Full:
            pass
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            print("  ➔ 🔴 [종료] writer 스레드가 제한 시간 내에 멈추지 않았습니다")
            return
        self._thread = None
        if self._owns_store:
            self._event_store.close()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if isinstance(item, IngestedEvent):
                    self._write(item)
                elif item is _SHUTDOWN:
                    return
            except Exception as error:  # writer 스레드는 어떤 예외에도 살아남아야 한다
                self.write_error_count += 1
                print(f"  ➔ 🔴 [저장 실패] 이벤트를 기록하지 못했습니다: {error!r}")
            finally:
                self._queue.task_done()

    def _write(self, event: IngestedEvent) -> None:
        streak = self._advance_zone_d_streak(event.message)
        self._event_store.record_event(
            event.message,
            observed_at=event.observed_at,
            received_at=event.received_at,
            zone_d_consecutive_count=streak,
        )

    def _advance_zone_d_streak(self, message: TelemetryMessage) -> int:
        """CRITICAL(Zone D)이면 +1, 아니면 0으로 리셋한다. writer 스레드 전용."""
        if message.message_type == MessageType.CRITICAL:
            self._zone_d_streak[message.machine_id] = (
                self._zone_d_streak.get(message.machine_id, 0) + 1
            )
        else:
            self._zone_d_streak[message.machine_id] = 0
        return self._zone_d_streak[message.machine_id]
