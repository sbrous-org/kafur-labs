import type { ChatCompletionMessageParam } from "@mlc-ai/web-llm";
import type { Destination } from "./types";

export type ModelTier = "standard" | "lite";

export const MODEL_TIERS: Record<ModelTier, { label: string; size: string; base: string }> = {
  standard: { label: "Standard", size: "~0.9 GB", base: "Qwen2.5-1.5B-Instruct" },
  lite: { label: "Lite", size: "~0.3 GB", base: "Qwen2.5-0.5B-Instruct" },
};

// Keep prompt + history well inside the prebuilt 4k context window.
const MAX_HISTORY_MESSAGES = 6;

type GpuAdapter = { features: { has(name: string): boolean } };
type GpuNavigator = Navigator & { gpu?: { requestAdapter(): Promise<GpuAdapter | null> } };

export type WebGPUSupport = { supported: false } | { supported: true; f16: boolean };

export async function detectWebGPU(): Promise<WebGPUSupport> {
  const gpu = (navigator as GpuNavigator).gpu;
  if (!gpu) return { supported: false };
  try {
    const adapter = await gpu.requestAdapter();
    if (!adapter) return { supported: false };
    return { supported: true, f16: adapter.features.has("shader-f16") };
  } catch {
    return { supported: false };
  }
}

// Many mid-range Android GPUs lack shader-f16; the f32 build runs everywhere
// WebGPU does, at the cost of a bit more memory.
export function modelIdFor(tier: ModelTier, f16: boolean): string {
  return `${MODEL_TIERS[tier].base}-${f16 ? "q4f16_1" : "q4f32_1"}-MLC`;
}

function describe(d: Destination): string {
  return [
    `- ${d.name} (${d.district} district; ${d.type.join(", ")})`,
    `  ${d.description}`,
    `  Best time: ${d.best_time}. Typical stay: ${d.avg_days_needed} day(s).`,
    `  Things to do: ${d.things_to_do.join("; ")}.`,
  ].join("\n");
}

// The whole destination list is small enough to put straight into the system
// prompt, so no retrieval step is needed for this POC.
export function buildSystemPrompt(destinations: Destination[]): string {
  return [
    "You are Oxomiai, a friendly travel guide for Northeast Assam, India.",
    "Answer ONLY using the destination facts below. If the answer isn't covered, say you don't know rather than guessing, and suggest a place from the list instead.",
    "Keep replies short (under 120 words), use plain text with simple bullet points, and never invent prices, hotels, phone numbers or opening hours.",
    "For itineraries, fit places into the number of days using each place's typical stay, and group nearby districts together.",
    "",
    "Destinations:",
    ...destinations.map(describe),
  ].join("\n");
}

export function buildMessages(
  systemPrompt: string,
  history: { from: "user" | "bot"; text: string }[]
): ChatCompletionMessageParam[] {
  const recent = history.slice(-MAX_HISTORY_MESSAGES);
  // Chat templates expect the conversation to open with a user turn.
  while (recent.length && recent[0].from === "bot") recent.shift();
  return [
    { role: "system", content: systemPrompt },
    ...recent.map(
      (m): ChatCompletionMessageParam =>
        m.from === "user" ? { role: "user", content: m.text } : { role: "assistant", content: m.text }
    ),
  ];
}
