"use client";

import { useEffect, useRef, useState } from "react";
import MessageBubble, { type Message } from "./MessageBubble";
import QuickReplyChips from "./QuickReplyChips";
import TypingIndicator from "./TypingIndicator";
import { matchIntent, DEFAULT_SUGGESTIONS } from "@/lib/intentMatcher";
import type { Destination } from "@/lib/types";

const WELCOME: Message = {
  id: "welcome",
  from: "bot",
  text: "Namoskar! I'm Oxomiai, your guide to Northeast Assam. Ask me about places, things to do, best time to visit, or an itinerary — or type \"help\" any time.",
};

function thinkingDelay(replyLength: number): number {
  const base = 450 + replyLength * 10 + Math.random() * 350;
  return Math.min(Math.max(base, 500), 2200);
}

export default function ChatWindow() {
  const [destinations, setDestinations] = useState<Destination[] | null>(null);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetch("/data/destinations.json")
      .then((res) => res.json())
      .then(setDestinations)
      .catch(() => setDestinations([]));
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, isThinking]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || !destinations || isThinking) return;

    const userMessage: Message = { id: crypto.randomUUID(), from: "user", text: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsThinking(true);

    const reply = matchIntent(trimmed, destinations);

    timeoutRef.current = setTimeout(() => {
      const botMessage: Message = { id: crypto.randomUUID(), from: "bot", text: reply.text };
      setMessages((prev) => [...prev, botMessage]);
      setSuggestions(reply.suggestions);
      setIsThinking(false);
    }, thinkingDelay(reply.text.length));
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
        {isThinking && <TypingIndicator />}
      </div>

      <QuickReplyChips suggestions={suggestions} onSelect={send} disabled={isThinking} />

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
          disabled={!destinations || isThinking}
          className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm focus:border-emerald-500 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!destinations || isThinking || !input.trim()}
          className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
