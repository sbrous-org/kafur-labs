export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm border border-gray-200 bg-white px-4 py-3">
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-gray-400" />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-gray-400" />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-gray-400" />
      </div>
    </div>
  );
}
