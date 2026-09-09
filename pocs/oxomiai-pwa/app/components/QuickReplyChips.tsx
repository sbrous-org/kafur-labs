export default function QuickReplyChips({
  suggestions,
  onSelect,
  disabled,
}: {
  suggestions: string[];
  onSelect: (text: string) => void;
  disabled?: boolean;
}) {
  if (suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4 pb-2">
      {suggestions.map((chip) => (
        <button
          key={chip}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(chip)}
          className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs text-emerald-800 hover:bg-emerald-100 disabled:opacity-50"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
