import type { Destination } from "./types";

const FALLBACK =
  "I can help with places to visit, things to do, best time to visit, or an itinerary — try asking about a specific place!";

const KNOWN_TYPES = ["wildlife", "culture", "nature"];

function findDestination(
  input: string,
  destinations: Destination[]
): Destination | undefined {
  return destinations.find((d) =>
    [d.name.toLowerCase(), ...d.aliases.map((a) => a.toLowerCase())].some(
      (name) => input.includes(name)
    )
  );
}

function buildItinerary(days: number, destinations: Destination[]): string {
  const picks: Destination[] = [];
  let remaining = days;

  for (const dest of destinations) {
    if (dest.avg_days_needed <= remaining) {
      picks.push(dest);
      remaining -= dest.avg_days_needed;
    }
    if (remaining <= 0) break;
  }

  if (picks.length === 0) {
    return `I couldn't fit a ${days}-day itinerary together — try a longer trip (3+ days).`;
  }

  const lines = picks.map(
    (d, i) => `${i + 1}. ${d.name} (${d.avg_days_needed} day${d.avg_days_needed > 1 ? "s" : ""})`
  );
  return `Here's a ${days}-day itinerary:\n${lines.join("\n")}`;
}

export function matchIntent(rawInput: string, destinations: Destination[]): string {
  const input = rawInput.trim().toLowerCase();
  if (!input) return FALLBACK;

  const itineraryMatch = input.match(/(\d+)\s*[- ]?\s*day/);
  if (itineraryMatch) {
    return buildItinerary(parseInt(itineraryMatch[1], 10), destinations);
  }

  if (input.includes("best time")) {
    const dest = findDestination(input, destinations);
    if (dest) return `Best time to visit ${dest.name}: ${dest.best_time}.`;
    return "Which place did you mean? Try naming a destination, e.g. \"best time to visit Majuli\".";
  }

  if (
    input.includes("things to do") ||
    input.includes("places near") ||
    input.includes("place near") ||
    input.includes("what to do")
  ) {
    const dest = findDestination(input, destinations);
    if (dest) {
      return `Things to do in ${dest.name}: ${dest.things_to_do.join(", ")}.`;
    }
    return "Which place did you mean? Try naming a destination, e.g. \"things to do in Kaziranga\".";
  }

  const destByName = findDestination(input, destinations);
  if (destByName) {
    return `Things to do in ${destByName.name}: ${destByName.things_to_do.join(", ")}.`;
  }

  const typeMatch = KNOWN_TYPES.find((t) => input.includes(t));
  if (typeMatch) {
    const matches = destinations.filter((d) => d.type.includes(typeMatch));
    if (matches.length === 0) return FALLBACK;
    return `${typeMatch[0].toUpperCase()}${typeMatch.slice(1)} spots: ${matches
      .map((d) => d.name)
      .join(", ")}.`;
  }

  return FALLBACK;
}
