"use client";

import { useEffect, useRef, useState } from "react";
import MessageBubble, { type Message } from "./MessageBubble";
import QuickReplyChips from "./QuickReplyChips";
import { matchIntent } from "@/lib/intentMatcher";
import type { Destination } from "@/lib/types";

const WELCOME: Message = {
  id: "welcome",
  from: "bot",
  text: "Namoskar! I'm Oxomiai, your guide to Northeast Assam. Ask me about places, things to do, best time to visit, or an itinerary.",
};

export default function ChatWindow() {
  const [destinations, setDestinations] = useState<Destination[] | null>(null);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/data/destinations.json")
      .then((res) => res.json())
      .then(setDestinations)
      .catch(() => setDestinations([]));
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || !destinations) return;

    const userMessage: Message = { id: crypto.randomUUID(), from: "user", text: trimmed };
    const botMessage: Message = {
      id: crypto.randomUUID(),
      from: "bot",
      text: matchIntent(trimmed, destinations),
    };

    setMessages((prev) => [...prev, userMessage, botMessage]);
    setInput("");
  }

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-gray-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold text-emerald-800">Oxomiai</h1>
        <p className="text-xs text-gray-500">Your guide to Northeast Assam</p>
      </header>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-gray-50 px-4 py-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>

      <QuickReplyChips onSelect={send} />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-gray-200 bg-white p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={destinations ? "Ask about a place..." : "Loading destinations..."}
          disabled={!destinations}
          className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm focus:border-emerald-500 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!destinations || !input.trim()}
          className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
