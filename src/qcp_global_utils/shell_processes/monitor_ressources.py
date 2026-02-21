import time
from dataclasses import dataclass, field
from threading import Thread, Event, Lock
from typing import Optional, Dict, Any, Tuple

import psutil
from subprocess import Popen


@dataclass
class MonitorSnapshot:
    timestamp: float
    rss_GB: float
    cpu_percent: float


@dataclass
class timer:
    idle: float = 0.0
    parallel: float = 0.0
    serial: float = 0.0


@dataclass
class timer_agg(timer):
    total: float = 0.0


@dataclass
class load:
    idle: float = 0.0
    parallel: float = 0.0
    serial: float = 0.0


@dataclass
class counter:
    idle: int = 0
    parallel: int = 0
    serial: int = 0


def record_snap(
    ps_proc: psutil.Process,
    include_children: bool = True,
) -> Optional[MonitorSnapshot]:
    """
    Take one instantaneous sample.
    NOTE: psutil cpu_percent(interval=None) is stateful per Process instance.
    We only use this helper for a quick snapshot, not for the main monitoring loop.
    """
    try:
        procs = ([ps_proc] + ps_proc.children(recursive=True)) if include_children else [ps_proc]
        rss_GB = sum(p.memory_info().rss for p in procs) / (1024 ** 3)
        cpu_percent = sum(p.cpu_percent(interval=None) for p in procs)
        return MonitorSnapshot(timestamp=time.time(), rss_GB=rss_GB, cpu_percent=cpu_percent)
    except psutil.Error:
        return None


class BackgroundProcessMonitor:
    """
    Monitors a subprocess.Popen in a background thread.

    Each *time step* (sample interval) is assigned to exactly one category:
      - idle:     cpu_percent < idle_cpu_threshold_percent
      - serial:   idle_thr <= cpu_percent <= serial_cpu_threshold_percent
      - parallel: cpu_percent > serial_cpu_threshold_percent

    Invariants (up to rounding / first-sample gap):
      idle + serial + parallel ~= runtime
    """

    def __init__(
        self,
        proc: Popen,
        *,
        refresh: float = 1.0,
        include_children: bool = True,
        idle_cpu_threshold_percent: float = 0.25,
        serial_cpu_threshold_percent: float = 125.0,
    ) -> None:
        self._idle_threshold_prc = float(idle_cpu_threshold_percent)
        self._serial_threshold_prc = float(serial_cpu_threshold_percent)
        self._refresh_interval_s = float(refresh)
        self._include_children = bool(include_children)
        self._proc = proc

        self._stop = Event()
        self._lock = Lock()
        self._thread: Optional[Thread] = None

        self._ps_proc = psutil.Process(proc.pid)

        # timers + counters
        self._timer_user: timer_agg = timer_agg()
        self._timer_system: timer_agg = timer_agg()
        self._timer_total: timer_agg = timer_agg()   # wall-time per class
        self._counter: counter = counter()

        # per-class load accumulators (sum of cpu% per interval; divide by counter for average)
        self._load_user: load = load()
        self._load_system: load = load()
        self._load_total: load = load()

        # peak cpu% per component
        self._cpu_user_max: float = 0.0
        self._cpu_system_max: float = 0.0
        self._cpu_total_max: float = 0.0

        # memory
        self._mem_sum_GB: float = 0.0   # accumulate here; divide by _n for average
        self._mem_max_GB: float = 0.0

        # sample count
        self._n: int = 0

        # time bounds
        self._t_first: Optional[float] = None
        self._t_last: Optional[float] = None
        self._t_prev: Optional[float] = None

        # last cumulative CPU times (for delta computation)
        self._cpu_user_prev_s: float = 0.0
        self._cpu_system_prev_s: float = 0.0

        # diagnostics
        self._mem_read_errors: int = 0
        self._cpu_times_read_errors: int = 0

        # snapshot
        self._last: Optional[MonitorSnapshot] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> "BackgroundProcessMonitor":
        self._t_first = time.time()
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = Thread(target=self._run, name=f"proc-monitor-{self._proc.pid}", daemon=True)
        self._thread.start()
        return self

    def stop(self, *, join: bool = True, timeout: Optional[float] = 5.0) -> None:
        self._t_last= time.time()
        self._stop.set()
        if join and self._thread is not None:
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def last(self) -> Optional[MonitorSnapshot]:
        with self._lock:
            return self._last

    @property
    def mem_avr_GB(self) -> float:
        with self._lock:
            if self._n == 0:
                return 0.0
            return self._mem_sum_GB / self._n

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_psutil_procs(self):
        yield self._ps_proc
        if self._include_children:
            try:
                yield from self._ps_proc.children(recursive=True)
            except psutil.Error:
                pass

    def _collect(self) -> Tuple[float, float, float]:
        """
        Returns (rss_GB, cpu_user_s, cpu_system_s) — cumulative CPU times at this moment.
        Errors are counted but do not raise.
        """
        procs = list(self._iter_psutil_procs())
        mem_bytes = 0
        cpu_user_s = 0.0
        cpu_system_s = 0.0

        if not procs:
            with self._lock:
                self._mem_read_errors += 1
                self._cpu_times_read_errors += 1
            return 0.0, 0.0, 0.0

        for p in procs:
            try:
                mem_bytes += p.memory_info().rss
            except psutil.Error:
                with self._lock:
                    self._mem_read_errors += 1

            try:
                ct = p.cpu_times()          # <-- was incorrectly calling children() again
                cpu_user_s += float(getattr(ct, "user", 0.0))
                cpu_system_s += float(getattr(ct, "system", 0.0))
            except psutil.Error:
                with self._lock:
                    self._cpu_times_read_errors += 1

        return mem_bytes / (1024 ** 3), cpu_user_s, cpu_system_s

    def _classify_and_accumulate(self, *, dt: float) -> None:
        """
        Take one sample, classify by CPU%, and accumulate all O(1) aggregates.
        Caller must NOT hold self._lock (we acquire it internally).
        """
        if dt <= 0:
            return

        mem_GB, cpu_user_s, cpu_system_s = self._collect()

        with self._lock:
            # ---- delta CPU times (guard against negative due to disappearing children) ----
            d_user = max(0.0, cpu_user_s - self._cpu_user_prev_s)
            d_system = max(0.0, cpu_system_s - self._cpu_system_prev_s)
            self._cpu_user_prev_s = cpu_user_s
            self._cpu_system_prev_s = cpu_system_s

            load_user_pct = 100.0 * d_user / dt
            load_system_pct = 100.0 * d_system / dt
            cpu_pct = load_user_pct + load_system_pct

            # ---- classify ----
            if cpu_pct < self._idle_threshold_prc:
                field = "idle"
            elif cpu_pct <= self._serial_threshold_prc:
                field = "serial"
            else:
                field = "parallel"

            # ---- accumulate wall-time timers ----
            setattr(self._timer_user,   field, getattr(self._timer_user,   field) + d_user)
            setattr(self._timer_system, field, getattr(self._timer_system, field) + d_system)
            setattr(self._timer_total,  field, getattr(self._timer_total,  field) + dt)
            self._timer_total.total += dt

            # ---- accumulate loads (sum of cpu% per interval; divide by counter later) ----
            setattr(self._load_user,   field, getattr(self._load_user,   field) + load_user_pct)
            setattr(self._load_system, field, getattr(self._load_system, field) + load_system_pct)
            setattr(self._load_total,  field, getattr(self._load_total,  field) + cpu_pct)

            # ---- counters ----
            setattr(self._counter, field, getattr(self._counter, field) + 1)
            self._n += 1

            # ---- peaks ----
            if load_user_pct > self._cpu_user_max:
                self._cpu_user_max = load_user_pct
            if load_system_pct > self._cpu_system_max:
                self._cpu_system_max = load_system_pct
            if cpu_pct > self._cpu_total_max:
                self._cpu_total_max = cpu_pct

            # ---- memory ----
            self._mem_sum_GB += mem_GB
            if mem_GB > self._mem_max_GB:
                self._mem_max_GB = mem_GB

            # ---- snapshot ----
            now = time.time()
            self._t_last = now
            self._last = MonitorSnapshot(timestamp=now, rss_GB=mem_GB, cpu_percent=cpu_pct)

    def record(self) -> None:
        now = time.time()
        with self._lock:
            t_prev = self._t_prev
            self._t_prev = now
        dt = now - t_prev if t_prev is not None else 0.0
        self._classify_and_accumulate(dt=dt)

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                if self._proc.poll() is not None:
                    break
                self.record()
                time.sleep(self._refresh_interval_s)
        finally:
            try:
                self.record()
            except Exception:
                pass

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            n = self._n

            # wall-time per category
            times = {
                cat: {
                    "user":   getattr(self._timer_user,   cat),
                    "system": getattr(self._timer_system, cat),
                    "total":  getattr(self._timer_total,  cat),
                }
                for cat in ("idle", "serial", "parallel")
            }

            # average loads per category (sum / count)
            avr_loads = {
                cat: {
                    "user":   getattr(self._load_user,   cat) / max(1, getattr(self._counter, cat)),
                    "system": getattr(self._load_system, cat) / max(1, getattr(self._counter, cat)),
                    "total":  getattr(self._load_total,  cat) / max(1, getattr(self._counter, cat)),
                }
                for cat in ("idle", "serial", "parallel")
            }

            max_loads = {
                "cpu_user":   self._cpu_user_max,
                "cpu_system": self._cpu_system_max,
                "cpu_total":  self._cpu_total_max,
            }

            mem_avr = (self._mem_sum_GB / n) if n else 0.0
            mem_max = self._mem_max_GB

            clocked_time = self._timer_total.total

        real_time = (self._t_last - self._t_first) if (self._t_first is not None and self._t_last is not None) else 0.0

        if real_time > 0 and clocked_time > 0:
            if abs(real_time / clocked_time - 1) > 0.01:
                print(
                    f"Real time ({real_time:.2f}s) and clocked time ({clocked_time:.2f}s) "
                    f"differ by more than 1% (check your timers?)"
                )

        time_ratios = {
            cat: times[cat]["total"] / real_time if real_time > 0 else 0.0
            for cat in ("idle", "serial", "parallel")
        }

        return dict(
            times=times,
            time_ratios=time_ratios,
            avr_loads=avr_loads,
            max_loads=max_loads,
            avr_memory=mem_avr,
            peak_memory=mem_max,
            real_time=real_time,
            clocked_time=clocked_time,
        )


def monitor_process_in_background(
    proc: Popen,
    *,
    refresh: float = 1.0,
    include_children: bool = True,
    idle_cpu_threshold_percent: float = 0.25,
    serial_cpu_threshold_percent: float = 125.0,
) -> BackgroundProcessMonitor:
    mon = BackgroundProcessMonitor(
        proc,
        refresh=refresh,
        include_children=include_children,
        idle_cpu_threshold_percent=idle_cpu_threshold_percent,
        serial_cpu_threshold_percent=serial_cpu_threshold_percent,
    )
    return mon.start()