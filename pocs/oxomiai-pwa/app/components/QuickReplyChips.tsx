const SUGGESTIONS = ["Wildlife spots", "3 day itinerary", "Best time to visit Majuli"];

export default function QuickReplyChips({
  onSelect,
}: {
  onSelect: (text: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 px-4 pb-2">
      {SUGGESTIONS.map((chip) => (
        <button
          key={chip}
          type="button"
          onClick={() => onSelect(chip)}
          className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs text-emerald-800 hover:bg-emerald-100"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
