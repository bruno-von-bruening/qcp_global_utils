import time
from dataclasses import dataclass
from threading import Thread, Event, Lock
from typing import Optional, Dict, Any, Tuple

import psutil
from subprocess import Popen


@dataclass
class MonitorSnapshot:
    timestamp: float
    rss_GB: float
    cpu_percent: float


def mapper():

@dataclass
class timer:
    idle: float
    parallel: float
    serial: float



class BackgroundProcessMonitor:
    """
    Monitors a subprocess.Popen in a background thread.

    Keeps only O(1) state:
      - avg/peak RSS (MB)
      - avg/peak CPU% (computed from delta CPU seconds / delta wall time)
      - wall-time CPU seconds (user/system/total) (proc (+ children optionally))
      - runtime (wall time)
      - last snapshot

      - idle wall time (based on a CPU% threshold)
      - serial wall time (based on a CPU% threshold; "one-core-ish")
      - parallel wall time (everything else)

    Classification is per *sample interval* [t_prev, t_now):
      - idle:     cpu_percent < idle_cpu_threshold_percent
      - serial:   idle_thr <= cpu_percent <= serial_cpu_threshold_percent
      - parallel: cpu_percent > serial_cpu_threshold_percent

    Invariants (up to rounding / first-sample gap):
      idle_wall_s + serial_wall_s + parallel_wall_s ~= runtime_s
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
        self._proc = proc
        self._refresh = float(refresh)
        self._include_children = bool(include_children)
        self._idle_cpu_threshold_percent = float(idle_cpu_threshold_percent)
        self._serial_cpu_threshold_percent = float(serial_cpu_threshold_percent)

        self._stop = Event()
        self._lock = Lock()
        self._thread: Optional[Thread] = None

        self._ps_proc = psutil.Process(proc.pid)

        # Running aggregates (whole runtime) for sampled rss/cpu%
        self._n: int = 0
        self._rss_sum_GB: float = 0.0
        self._cpu_sum_percent: float = 0.0
        self._rss_peak_GB: float = 0.0
        self._cpu_peak_percent: float = 0.0

        # Running aggregates within classes (for means over intervals)
        self._idle_n: int = 0
        self._idle_cpu_sum_percent: float = 0.0
        self._serial_n: int = 0
        self._serial_cpu_sum_percent: float = 0.0
        self._parallel_n: int = 0
        self._parallel_cpu_sum_percent: float = 0.0

        # CPU time tracking (seconds, cumulative at each sample)
        self._cpu_user_last_s: Optional[float] = None
        self._cpu_system_last_s: Optional[float] = None
        self._cpu_total_last_s: Optional[float] = None

        # last totals for dt/dcpu computation
        self._cpu_total_prev_s: Optional[float] = None
        self._t_prev: Optional[float] = None

        # wall-time class accumulators
        self._idle_wall_s: float = 0.0
        self._serial_wall_s: float = 0.0
        self._parallel_wall_s: float = 0.0

        self._last: Optional[MonitorSnapshot] = None
        self._t_first: Optional[float] = None
        self._t_last: Optional[float] = None

        # diagnostics
        self._cpu_times_read_errors: int = 0
        self._cpu_times_read_ok: int = 0

    def start(self) -> "BackgroundProcessMonitor":
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = Thread(target=self._run, name=f"proc-monitor-{self._proc.pid}", daemon=True)
        self._thread.start()
        return self

    def stop(self, *, join: bool = True, timeout: Optional[float] = 5.0) -> None:
        self._stop.set()
        if join and self._thread is not None:
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def last(self) -> Optional[MonitorSnapshot]:
        with self._lock:
            return self._last

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            n = self._n
            rss_sum_GB = self._rss_sum_GB
            cpu_sum_percent = self._cpu_sum_percent
            rss_peak_GB = self._rss_peak_GB
            cpu_peak_percent = self._cpu_peak_percent
            t_first = self._t_first
            t_last = self._t_last

            cpu_user_s = self._cpu_user_last_s
            cpu_system_s = self._cpu_system_last_s
            cpu_total_s = self._cpu_total_last_s

            idle_thr = self._idle_cpu_threshold_percent
            serial_thr = self._serial_cpu_threshold_percent

            idle_wall_s = self._idle_wall_s
            serial_wall_s = self._serial_wall_s
            parallel_wall_s = self._parallel_wall_s

            idle_n = self._idle_n
            idle_cpu_sum_percent = self._idle_cpu_sum_percent
            serial_n = self._serial_n
            serial_cpu_sum_percent = self._serial_cpu_sum_percent
            parallel_n = self._parallel_n
            parallel_cpu_sum_percent = self._parallel_cpu_sum_percent

            cpu_times_read_errors = self._cpu_times_read_errors
            cpu_times_read_ok = self._cpu_times_read_ok

        avg_rss = (rss_sum_GB / n) if n else 0.0
        avg_cpu = (cpu_sum_percent / n) if n else 0.0

        avg_idle_cpu = (idle_cpu_sum_percent / idle_n) if idle_n else None
        avg_serial_cpu = (serial_cpu_sum_percent / serial_n) if serial_n else None
        avg_parallel_cpu = (parallel_cpu_sum_percent / parallel_n) if parallel_n else None

        runtime_s = (t_last - t_first) if (t_first is not None and t_last is not None) else 0.0

        cpu_util_from_times_percent = None
        serial_cpu_equiv_s = None  # accumulated CPU seconds; "1-core equivalent wall time"
        if cpu_total_s is not None and runtime_s > 0:
            cpu_util_from_times_percent = 100.0 * (cpu_total_s / runtime_s)
            serial_cpu_equiv_s = float(cpu_total_s)

        # Fractions
        idle_fraction = (idle_wall_s / runtime_s) if runtime_s > 0 else 0.0
        serial_fraction = (serial_wall_s / runtime_s) if runtime_s > 0 else 0.0
        parallel_fraction = (parallel_wall_s / runtime_s) if runtime_s > 0 else 0.0
        classified_sum_wall_s = idle_wall_s + serial_wall_s + parallel_wall_s

        return {
            "pid": self._proc.pid,
            "memory": dict(
                average=avg_rss,
                peak=rss_peak_GB,
                comment="rss in MB (psutil.Process.memory_info().rss), aggregated over proc(+children).",
            ),
            "cpu_usage": dict(
                average_percent=avg_cpu,
                peak_percent=cpu_peak_percent,
                average_parallel_percent=max(0.0, avg_cpu - 100.0),
                util_from_cpu_times_percent=cpu_util_from_times_percent,
                thresholds=dict(
                    idle_cpu_threshold_percent=idle_thr,
                    serial_cpu_threshold_percent=serial_thr,
                ),
                class_averages=dict(
                    idle_average_percent=avg_idle_cpu,
                    serial_average_percent=avg_serial_cpu,
                    parallel_average_percent=avg_parallel_cpu,
                ),
                diagnostics=dict(
                    cpu_times_read_ok=cpu_times_read_ok,
                    cpu_times_read_errors=cpu_times_read_errors,
                ),
                comment=(
                    "cpu_percent is derived from delta(cpu_total_s)/delta(t) per sample interval; "
                    "can exceed 100% on multi-core. Class averages are simple means over intervals in that class."
                ),
            ),
            "timings": dict(
                refresh_rate=self._refresh,
                user_cpu_s=cpu_user_s,
                system_cpu_s=cpu_system_s,
                total_cpu_s=cpu_total_s,
                serial_cpu_equiv_s=serial_cpu_equiv_s,
                start=t_first,
                end=t_last,
                runtime_s=runtime_s,
                idle_wall_s=idle_wall_s,
                serial_wall_s=serial_wall_s,
                parallel_wall_s=parallel_wall_s,
                classified_sum_wall_s=classified_sum_wall_s,
                idle_fraction=idle_fraction,
                serial_fraction=serial_fraction,
                parallel_fraction=parallel_fraction,
                comment=(
                    "times in seconds; start/end are time.time() wall clock. "
                    f"Threshold for idle: {idle_thr}%, for serial: {serial_thr}%. "
                    "Wall-time classes are accumulated per sample interval and should sum to ~runtime_s "
                    "(excluding the first interval where deltas are not yet available). "
                    "serial_cpu_equiv_s is accumulated CPU seconds (user+system), proc(+children), i.e. '1-core time'."
                ),
            ),
        }

    def _iter_psutil_procs(self):
        procs = []
        try:
            procs.append(self._ps_proc)
        except psutil.Error:
            return procs

        if self._include_children:
            try:
                procs.extend(self._ps_proc.children(recursive=True))
            except psutil.Error:
                pass
        return procs

    def _collect(self) -> Tuple[float, float, float, float]:
        rss_bytes = 0
        cpu_user_s = 0.0
        cpu_system_s = 0.0

        any_cpu_time_read = False

        for p in self._iter_psutil_procs():
            try:
                rss_bytes += p.memory_info().rss
            except psutil.Error:
                pass

            try:
                ct = p.cpu_times()
                cpu_user_s += float(getattr(ct, "user", 0.0))
                cpu_system_s += float(getattr(ct, "system", 0.0))
                any_cpu_time_read = True
            except psutil.Error:
                with self._lock:
                    self._cpu_times_read_errors += 1
                # keep going; a child may have exited

        if any_cpu_time_read:
            with self._lock:
                self._cpu_times_read_ok += 1
        else:
            # If we couldn't read ANY cpu_times (e.g. permissions), leave totals at 0.
            # The diagnostics above will make this visible.
            pass

        rss_GB = rss_bytes / (1024 ** 2)
        cpu_total_s = cpu_user_s + cpu_system_s
        return rss_GB, cpu_user_s, cpu_system_s, cpu_total_s

    def _record(
        self,
        snap: MonitorSnapshot,
        *,
        cpu_user_s: float,
        cpu_system_s: float,
        cpu_total_s: float,
    ) -> None:
        with self._lock:
            if self._t_first is None:
                self._t_first = snap.timestamp
            self._t_last = snap.timestamp

            self._last = snap
            self._n += 1
            self._rss_sum_GB += snap.rss_GB

            # Never accumulate negative cpu_percent into means; it can happen if cpu time
            # decreases between samples due to short-lived children disappearing.
            cpu_pct = snap.cpu_percent if snap.cpu_percent >= 0.0 else 0.0
            self._cpu_sum_percent += cpu_pct

            if snap.rss_GB > self._rss_peak_GB:
                self._rss_peak_GB = snap.rss_GB
            if cpu_pct > self._cpu_peak_percent:
                self._cpu_peak_percent = cpu_pct

            # class means (by count of classified intervals)
            if cpu_pct < self._idle_cpu_threshold_percent:
                self._idle_n += 1
                self._idle_cpu_sum_percent += cpu_pct
            elif cpu_pct <= self._serial_cpu_threshold_percent:
                self._serial_n += 1
                self._serial_cpu_sum_percent += cpu_pct
            else:
                self._parallel_n += 1
                self._parallel_cpu_sum_percent += cpu_pct

            self._cpu_user_last_s = cpu_user_s
            self._cpu_system_last_s = cpu_system_s
            self._cpu_total_last_s = cpu_total_s

    def _accumulate_walltime_classes(self, *, dt: float, cpu_pct: float) -> None:
        # Caller must hold self._lock
        if dt <= 0:
            return
        if cpu_pct < self._idle_cpu_threshold_percent:
            self._idle_wall_s += dt
        elif cpu_pct <= self._serial_cpu_threshold_percent:
            self._serial_wall_s += dt
        else:
            self._parallel_wall_s += dt

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                if self._proc.poll() is not None:
                    break

                now = time.time()
                try:
                    rss_GB, cpu_user_s, cpu_system_s, cpu_total_s = self._collect()
                except (psutil.NoSuchProcess, psutil.Error):
                    break

                cpu_pct = 0.0
                with self._lock:
                    if self._cpu_total_prev_s is not None and self._t_prev is not None:
                        dt = now - self._t_prev
                        dcpu = cpu_total_s - self._cpu_total_prev_s

                        # Guard against clock jitter / counter jitter: never allow negative deltas
                        if dt > 0 and dcpu >= 0:
                            cpu_pct = 100.0 * (dcpu / dt)
                            self._accumulate_walltime_classes(dt=dt, cpu_pct=cpu_pct)

                    self._cpu_total_prev_s = cpu_total_s
                    self._t_prev = now

                self._record(
                    MonitorSnapshot(timestamp=now, rss_GB=rss_GB, cpu_percent=cpu_pct),
                    cpu_user_s=cpu_user_s,
                    cpu_system_s=cpu_system_s,
                    cpu_total_s=cpu_total_s,
                )
                time.sleep(self._refresh)
        finally:
            # one last sample after exit (best effort)
            try:
                now = time.time()
                rss_GB, cpu_user_s, cpu_system_s, cpu_total_s = self._collect()

                cpu_pct = 0.0
                with self._lock:
                    if self._cpu_total_prev_s is not None and self._t_prev is not None:
                        dt = now - self._t_prev
                        dcpu = cpu_total_s - self._cpu_total_prev_s
                        if dt > 0 and dcpu >= 0:
                            cpu_pct = 100.0 * (dcpu / dt)
                            self._accumulate_walltime_classes(dt=dt, cpu_pct=cpu_pct)

                    self._cpu_total_prev_s = cpu_total_s
                    self._t_prev = now

                self._record(
                    MonitorSnapshot(timestamp=now, rss_GB=rss_GB, cpu_percent=cpu_pct),
                    cpu_user_s=cpu_user_s,
                    cpu_system_s=cpu_system_s,
                    cpu_total_s=cpu_total_s,
                )
            except Exception:
                pass


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