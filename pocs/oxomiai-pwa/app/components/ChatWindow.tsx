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

const AVG_TYPING_CHARS_PER_SEC = 45;

function thinkingDelay(replyLength: number): number {
  const readingTime = (replyLength / AVG_TYPING_CHARS_PER_SEC) * 1000;
  const base = 450 + readingTime + Math.random() * 350;
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

    const userMessage: Message = {
      id: crypto.randomUUID(),
      from: "user",
      text: trimmed,
      time: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsThinking(true);

    const reply = matchIntent(trimmed, destinations);

    timeoutRef.current = setTimeout(() => {
      const botMessage: Message = {
        id: crypto.randomUUID(),
        from: "bot",
        text: reply.text,
        time: Date.now(),
      };
      setMessages((prev) => [...prev, botMessage]);
      setSuggestions(reply.suggestions);
      setIsThinking(false);
    }, thinkingDelay(reply.text.length));
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 bg-gradient-to-r from-emerald-700 to-teal-700 px-4 py-3 text-white shadow-sm">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/90 text-sm font-bold text-emerald-700">
          O
        </div>
        <div>
          <h1 className="text-lg font-semibold leading-tight">Oxomiai</h1>
          <p className="flex items-center gap-1.5 text-xs text-emerald-50/90">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
            Online · Northeast Assam guide
          </p>
        </div>
      </header>

      <div
        ref={listRef}
        className="flex-1 space-y-3 overflow-y-auto bg-gradient-to-b from-emerald-50/60 to-gray-50 px-4 py-4"
      >
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
          className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-100 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!destinations || isThinking || !input.trim()}
          aria-label="Send"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50 disabled:hover:bg-emerald-600"
        >
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 -rotate-45 translate-x-px">
            <path
              d="M4 12L20 4L14 20L11 13L4 12Z"
              fill="currentColor"
            />
          </svg>
        </button>
      </form>
    </div>
  );
}
