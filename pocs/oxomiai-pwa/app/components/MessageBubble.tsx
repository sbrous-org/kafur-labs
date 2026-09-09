export type Message = {
  id: string;
  from: "user" | "bot";
  text: string;
};

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.from === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] whitespace-pre-line rounded-2xl px-4 py-2 text-sm ${
          isUser
            ? "bg-emerald-600 text-white rounded-br-sm"
            : "bg-white text-gray-900 border border-gray-200 rounded-bl-sm"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}
