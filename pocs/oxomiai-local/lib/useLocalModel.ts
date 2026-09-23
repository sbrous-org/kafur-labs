"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CreateWebWorkerMLCEngine,
  hasModelInCache,
  type ChatCompletionMessageParam,
  type WebWorkerMLCEngine,
} from "@mlc-ai/web-llm";
import { detectWebGPU, modelIdFor, type ModelTier } from "./localModel";

export type ModelStatus =
  | { state: "checking" }
  | { state: "unsupported" }
  | { state: "idle"; f16: boolean }
  | { state: "loading"; progress: number; text: string }
  | { state: "ready"; modelId: string }
  | { state: "error"; message: string };

const TIER_KEY = "oxomiai-model-tier";

function savedTier(): ModelTier | null {
  try {
    const value = localStorage.getItem(TIER_KEY);
    return value === "standard" || value === "lite" ? value : null;
  } catch {
    return null;
  }
}

export function useLocalModel() {
  const [status, setStatus] = useState<ModelStatus>({ state: "checking" });
  const engineRef = useRef<WebWorkerMLCEngine | null>(null);
  const f16Ref = useRef(false);

  const load = useCallback(async (tier: ModelTier) => {
    const modelId = modelIdFor(tier, f16Ref.current);
    setStatus({ state: "loading", progress: 0, text: "Starting…" });
    const worker = new Worker(new URL("./llm.worker.ts", import.meta.url), { type: "module" });
    try {
      engineRef.current = await CreateWebWorkerMLCEngine(worker, modelId, {
        initProgressCallback: (report) =>
          setStatus({ state: "loading", progress: report.progress, text: report.text }),
      });
      try {
        localStorage.setItem(TIER_KEY, tier);
      } catch {}
      setStatus({ state: "ready", modelId });
    } catch (err) {
      engineRef.current = null;
      worker.terminate();
      setStatus({ state: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const gpu = await detectWebGPU();
      if (cancelled) return;
      if (!gpu.supported) {
        setStatus({ state: "unsupported" });
        return;
      }
      f16Ref.current = gpu.f16;
      // Only auto-load when the weights are already on the device, so we never
      // start a large download over mobile data without the user asking.
      const tier = savedTier();
      if (tier && (await hasModelInCache(modelIdFor(tier, gpu.f16)))) {
        if (!cancelled) load(tier);
      } else if (!cancelled) {
        setStatus({ state: "idle", f16: gpu.f16 });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const generate = useCallback(
    async (messages: ChatCompletionMessageParam[], onToken: (textSoFar: string) => void) => {
      const engine = engineRef.current;
      if (!engine) throw new Error("Model not loaded");
      const stream = await engine.chat.completions.create({
        messages,
        stream: true,
        temperature: 0.4,
        max_tokens: 320,
      });
      let text = "";
      for await (const chunk of stream) {
        text += chunk.choices[0]?.delta?.content ?? "";
        onToken(text);
      }
      return text.trim();
    },
    []
  );

  return { status, load, generate };
}
