import type { Destination } from "./types";

export type BotReply = {
  text: string;
  suggestions: string[];
};

export const DEFAULT_SUGGESTIONS = ["Wildlife spots", "3 day itinerary", "Best time to visit Majuli"];

const GREETINGS = [
  "Namoskar! What are you in the mood for — wildlife, culture, or a full itinerary?",
  "Hey there! Ask me about a place, a category, or how many days you've got.",
  "Hi! I know Northeast Assam pretty well — where would you like to start?",
];

const THANKS = [
  "Anytime! Anything else you'd like to plan?",
  "Glad it helped — ask away if you want more.",
  "You're welcome! Happy travels.",
];

const GOODBYES = [
  "Safe travels! Come back if you need more ideas.",
  "Bon voyage! I'll be here if you need anything else.",
];

const HELP_TEXT =
  "Here's what I can do:\n" +
  "• \"things to do in <place>\" — highlights for a destination\n" +
  "• \"best time to visit <place>\" — ideal season\n" +
  "• \"tell me about <place>\" — full profile\n" +
  "• \"N day itinerary\" — a route that fits N days (add a category, e.g. \"3 day wildlife itinerary\")\n" +
  "• \"wildlife\" / \"culture\" / \"nature\" / \"history\" / \"spiritual\" — browse by category\n" +
  "• \"places in <district>\" — browse by district\n" +
  "• \"list all places\" — everything I know about";

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function levenshtein(a: string, b: string): number {
  const dp: number[][] = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 0; j <= b.length; j++) dp[0][j] = j;

  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1]);
    }
  }
  return dp[a.length][b.length];
}

function namesOf(d: Destination): string[] {
  return [d.name.toLowerCase(), ...d.aliases.map((a) => a.toLowerCase())];
}

function findDestination(input: string, destinations: Destination[]): Destination | undefined {
  return destinations.find((d) => namesOf(d).some((name) => input.includes(name)));
}

function findClosestDestination(
  input: string,
  destinations: Destination[]
): Destination | undefined {
  const words = input.split(/\s+/).filter((w) => w.length > 3);
  let best: { dest: Destination; distance: number } | undefined;

  for (const dest of destinations) {
    for (const name of namesOf(dest)) {
      for (const word of words) {
        const distance = levenshtein(word, name);
        if (distance <= 2 && (!best || distance < best.distance)) {
          best = { dest, distance };
        }
      }
    }
  }
  return best?.dest;
}

function allTypes(destinations: Destination[]): string[] {
  return Array.from(new Set(destinations.flatMap((d) => d.type)));
}

function allDistricts(destinations: Destination[]): string[] {
  return Array.from(new Set(destinations.map((d) => d.district.toLowerCase())));
}

function buildItinerary(days: number, pool: Destination[]): string {
  const picks: Destination[] = [];
  let remaining = days;

  for (const dest of pool) {
    if (dest.avg_days_needed <= remaining) {
      picks.push(dest);
      remaining -= dest.avg_days_needed;
    }
    if (remaining <= 0) break;
  }

  if (picks.length === 0) {
    return `I couldn't fit a ${days}-day itinerary from that category — try a longer trip or drop the category filter.`;
  }

  const lines = picks.map(
    (d, i) => `${i + 1}. ${d.name} (${d.avg_days_needed} day${d.avg_days_needed > 1 ? "s" : ""})`
  );
  return `Here's a ${days}-day itinerary:\n${lines.join("\n")}`;
}

function profileFollowUps(dest: Destination): string[] {
  return [`Best time to visit ${dest.name}`, `Things to do in ${dest.name}`, "List all places"];
}

export function matchIntent(rawInput: string, destinations: Destination[]): BotReply {
  const input = rawInput.trim().toLowerCase();
  if (!input) return { text: pick(GREETINGS), suggestions: DEFAULT_SUGGESTIONS };

  if (/\b(hi|hello|hey|namoskar|namaste|yo)\b/.test(input)) {
    return { text: pick(GREETINGS), suggestions: DEFAULT_SUGGESTIONS };
  }

  if (/\bthank/.test(input)) {
    return { text: pick(THANKS), suggestions: DEFAULT_SUGGESTIONS };
  }

  if (/\b(bye|goodbye|see ya|see you)\b/.test(input)) {
    return { text: pick(GOODBYES), suggestions: DEFAULT_SUGGESTIONS };
  }

  if (/\b(help|menu|options|what can you do)\b/.test(input)) {
    return { text: HELP_TEXT, suggestions: DEFAULT_SUGGESTIONS };
  }

  if (/\b(list|all destinations|all places|which places|what places)\b/.test(input)) {
    const byDistrict = new Map<string, string[]>();
    for (const d of destinations) {
      byDistrict.set(d.district, [...(byDistrict.get(d.district) ?? []), d.name]);
    }
    const lines = Array.from(byDistrict.entries()).map(
      ([district, names]) => `${district}: ${names.join(", ")}`
    );
    return {
      text: `Here's everywhere I know about:\n${lines.join("\n")}`,
      suggestions: DEFAULT_SUGGESTIONS,
    };
  }

  const itineraryMatch = input.match(/(\d+)\s*[- ]?\s*day/);
  if (itineraryMatch) {
    const days = parseInt(itineraryMatch[1], 10);
    const typeFilter = allTypes(destinations).find((t) => input.includes(t));
    const pool = typeFilter ? destinations.filter((d) => d.type.includes(typeFilter)) : destinations;
    return {
      text: buildItinerary(days, pool),
      suggestions: ["Wildlife spots", "Culture spots", `${days + 2} day itinerary`],
    };
  }

  if (/\bbest time\b/.test(input)) {
    const dest = findDestination(input, destinations) ?? findClosestDestination(input, destinations);
    if (dest) return { text: `Best time to visit ${dest.name}: ${dest.best_time}.`, suggestions: profileFollowUps(dest) };
    return {
      text: 'Which place did you mean? Try naming a destination, e.g. "best time to visit Majuli".',
      suggestions: DEFAULT_SUGGESTIONS,
    };
  }

  if (/\b(things to do|places near|place near|what to do)\b/.test(input)) {
    const dest = findDestination(input, destinations) ?? findClosestDestination(input, destinations);
    if (dest) {
      return {
        text: `Things to do in ${dest.name}: ${dest.things_to_do.join(", ")}.`,
        suggestions: profileFollowUps(dest),
      };
    }
    return {
      text: 'Which place did you mean? Try naming a destination, e.g. "things to do in Kaziranga".',
      suggestions: DEFAULT_SUGGESTIONS,
    };
  }

  if (/\b(tell me about|what is|where is)\b/.test(input)) {
    const dest = findDestination(input, destinations) ?? findClosestDestination(input, destinations);
    if (dest) {
      return {
        text:
          `${dest.name} (${dest.district}) — ${dest.description}\n` +
          `Best time: ${dest.best_time}\n` +
          `Things to do: ${dest.things_to_do.join(", ")}`,
        suggestions: profileFollowUps(dest),
      };
    }
  }

  const districtMatch = allDistricts(destinations).find((district) => input.includes(district));
  if (districtMatch) {
    const matches = destinations.filter((d) => d.district.toLowerCase() === districtMatch);
    return {
      text: `In ${matches[0].district}: ${matches.map((d) => d.name).join(", ")}.`,
      suggestions: matches.slice(0, 2).map((d) => `Tell me about ${d.name}`),
    };
  }

  const destByName = findDestination(input, destinations);
  if (destByName) {
    return {
      text: `Things to do in ${destByName.name}: ${destByName.things_to_do.join(", ")}.`,
      suggestions: profileFollowUps(destByName),
    };
  }

  const typeMatch = allTypes(destinations).find((t) => input.includes(t));
  if (typeMatch) {
    const matches = destinations.filter((d) => d.type.includes(typeMatch));
    if (matches.length > 0) {
      return {
        text: `${typeMatch[0].toUpperCase()}${typeMatch.slice(1)} spots: ${matches
          .map((d) => d.name)
          .join(", ")}.`,
        suggestions: matches.slice(0, 2).map((d) => `Tell me about ${d.name}`),
      };
    }
  }

  const closest = findClosestDestination(input, destinations);
  if (closest) {
    return {
      text: `Did you mean ${closest.name}? Here's what I've got: ${closest.things_to_do.join(", ")}.`,
      suggestions: profileFollowUps(closest),
    };
  }

  return {
    text: "I can help with places to visit, things to do, best time to visit, or an itinerary — try asking about a specific place, or type \"help\" for everything I can do!",
    suggestions: DEFAULT_SUGGESTIONS,
  };
}
