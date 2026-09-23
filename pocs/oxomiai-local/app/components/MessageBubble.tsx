export type Message = {
  id: string;
  from: "user" | "bot";
  text: string;
  time?: number;
};

function formatTime(time: number): string {
  return new Date(time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function BotAvatar() {
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-xs font-semibold text-white">
      O
    </div>
  );
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.from === "user";
  return (
    <div className={`message-in flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && <BotAvatar />}
      <div className={`flex max-w-[min(82vw,320px)] flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`whitespace-pre-line rounded-2xl px-4 py-2 text-sm shadow-sm ${
            isUser
              ? "bg-emerald-600 text-white rounded-br-sm"
              : "bg-white text-gray-900 border border-gray-200 rounded-bl-sm"
          }`}
        >
          {message.text}
        </div>
        {message.time !== undefined && (
          <span className="px-1 text-[10px] text-gray-400">{formatTime(message.time)}</span>
        )}
      </div>
    </div>
  );
}
