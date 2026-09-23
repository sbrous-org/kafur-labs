"use client";

import { MODEL_TIERS, type ModelTier } from "@/lib/localModel";
import type { ModelStatus } from "@/lib/useLocalModel";

export default function ModelBanner({
  status,
  onLoad,
}: {
  status: ModelStatus;
  onLoad: (tier: ModelTier) => void;
}) {
  if (status.state === "checking" || status.state === "ready") return null;

  const base = "border-b px-4 py-2.5 text-xs";

  if (status.state === "unsupported") {
    return (
      <div className={`${base} border-amber-200 bg-amber-50 text-amber-900`}>
        This browser has no WebGPU, so on-device AI is off — using quick offline answers instead.
        Try the latest Chrome on Android.
      </div>
    );
  }

  if (status.state === "loading") {
    const pct = Math.round(status.progress * 100);
    return (
      <div className={`${base} border-emerald-200 bg-emerald-50 text-emerald-900`}>
        <div className="mb-1.5 flex justify-between gap-2">
          <span className="truncate">Loading on-device AI… {status.text}</span>
          <span className="shrink-0 font-medium">{pct}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-emerald-100">
          <div className="h-full bg-emerald-600 transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>
    );
  }

  return (
    <div className={`${base} border-emerald-200 bg-emerald-50 text-emerald-900`}>
      {status.state === "error" && (
        <p className="mb-1.5 text-red-700">Couldn&apos;t load the model: {status.message}</p>
      )}
      <p className="mb-2">
        Download a small AI model to chat naturally, fully offline and private. Until then you get
        quick rule-based answers. Best on Wi-Fi.
      </p>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(MODEL_TIERS) as ModelTier[]).map((tier) => (
          <button
            key={tier}
            onClick={() => onLoad(tier)}
            className="rounded-full border border-emerald-600 px-3 py-1 font-medium text-emerald-700 hover:bg-emerald-600 hover:text-white"
          >
            {MODEL_TIERS[tier].label} · {MODEL_TIERS[tier].size}
          </button>
        ))}
      </div>
    </div>
  );
}
