export class DwellSelector {
  constructor(durationMs) {
    if (!Number.isFinite(durationMs) || durationMs <= 0) {
      throw new RangeError("Dwell duration must be a positive number of milliseconds.");
    }
    this.durationMs = durationMs;
    this.targetId = null;
    this.startedAt = null;
    this.selected = false;
  }

  update(targetId, now) {
    if (targetId !== this.targetId) {
      this.targetId = targetId;
      this.startedAt = targetId === null ? null : now;
      this.selected = false;
    }
    if (targetId === null || this.startedAt === null) {
      return { targetId: null, progress: 0, selected: false };
    }

    const progress = Math.min(1, Math.max(0, (now - this.startedAt) / this.durationMs));
    const selected = progress >= 1 && !this.selected;
    if (selected) this.selected = true;
    return { targetId, progress, selected };
  }

  reset() {
    this.targetId = null;
    this.startedAt = null;
    this.selected = false;
  }
}
