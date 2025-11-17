import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage } from "../../types";

const DRAFT_SESSION_KEY = "draft-session";
const STORAGE_PREFIX = "tcia:intro-sequence:";

const storageKeyFor = (sessionKey: string) => `${STORAGE_PREFIX}${sessionKey}`;

interface IntroScriptEntry {
  id: string;
  content: string;
  pauseMs: number;
}

const INTRO_SCRIPT: IntroScriptEntry[] = [
  {
    id: "greeting",
    content: `Hey there! I'm your **Dishwasher Assistant**, here to help diagnose issues and walk you step by step through fixes. Just describe the problem or share photos whenever you're ready.`,
    pauseMs: 800,
  },
  {
    id: "prompt",
    content: "So, what kind of trouble is your dishwasher giving you today?",
    pauseMs: 900,
  },
];

interface StoredIntroState {
  messages: ChatMessage[];
  started: boolean;
}

const DEFAULT_STATE: StoredIntroState = { messages: [], started: false };

const safeNow = () => new Date().toISOString();

const readStoredState = (sessionKey: string): StoredIntroState => {
  if (typeof window === "undefined") {
    return DEFAULT_STATE;
  }

  try {
    const raw = window.sessionStorage.getItem(storageKeyFor(sessionKey));
    if (!raw) {
      return DEFAULT_STATE;
    }

    const parsed = JSON.parse(raw) as StoredIntroState | ChatMessage[];
    if (Array.isArray(parsed)) {
      return { messages: parsed, started: parsed.length > 0 };
    }
    if (parsed && "messages" in parsed) {
      const state = parsed as Partial<StoredIntroState>;
      const messages = Array.isArray(state.messages) ? (state.messages as ChatMessage[]) : [];
      const started = typeof state.started === "boolean" ? state.started : messages.length > 0;
      return { messages, started };
    }
  } catch (error) {
    console.warn("Failed to read intro sequence state", error);
  }

  return DEFAULT_STATE;
};

const writeStoredState = (sessionKey: string, state: StoredIntroState) => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.setItem(storageKeyFor(sessionKey), JSON.stringify(state));
  } catch (error) {
    console.warn("Failed to persist intro sequence state", error);
  }
};

const removeStoredState = (sessionKey: string) => {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(storageKeyFor(sessionKey));
};

const buildIntroMessage = (sessionKey: string, entry: IntroScriptEntry): ChatMessage => ({
  id: `intro-${sessionKey}-${entry.id}`,
  sessionId: sessionKey,
  role: "assistant",
  content: entry.content,
  timestamp: safeNow(),
  metadata: {
    intro_message: true,
    suppress_timestamp: true,
  },
});

const buildTypingMessage = (sessionKey: string): ChatMessage => ({
  id: `intro-${sessionKey}-typing`,
  sessionId: sessionKey,
  role: "assistant",
  content: "",
  timestamp: safeNow(),
  metadata: {
    intro_message: true,
    suppress_timestamp: true,
  },
  status: "pending",
});

interface UseIntroSequenceArgs {
  sessionId: string | null;
  hasServerMessages: boolean;
}

interface IntroSequenceResult {
  introMessages: ChatMessage[];
  typingMessage: ChatMessage | null;
}

export const useIntroSequence = ({
  sessionId,
  hasServerMessages,
}: UseIntroSequenceArgs): IntroSequenceResult => {
  const sessionKeyRef = useRef<string>(sessionId ?? DRAFT_SESSION_KEY);
  const initialStateRef = useRef<StoredIntroState>(readStoredState(sessionKeyRef.current));
  const [introMessages, setIntroMessages] = useState<ChatMessage[]>(
    initialStateRef.current.messages
  );
  const hasInitializedRef = useRef<boolean>(initialStateRef.current.started);
  const [typingMessage, setTypingMessage] = useState<ChatMessage | null>(null);
  const timersRef = useRef<number[]>([]);
  const isRunningRef = useRef<boolean>(false);

  const persistState = useCallback(
    (messages: ChatMessage[], startedOverride?: boolean) => {
      const started = startedOverride ?? hasInitializedRef.current;
      hasInitializedRef.current = started;
      writeStoredState(sessionKeyRef.current, {
        messages,
        started,
      });
    },
    []
  );

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
    timersRef.current = [];
    isRunningRef.current = false;
  }, []);

  const migrateDraftState = useCallback((nextKey: string) => {
    const draftState = readStoredState(DRAFT_SESSION_KEY);
    if (!draftState.started && draftState.messages.length === 0) {
      return;
    }
    writeStoredState(nextKey, draftState);
    removeStoredState(DRAFT_SESSION_KEY);
  }, []);

  useEffect(() => {
    const prevKey = sessionKeyRef.current;
    const targetKey = sessionId ?? DRAFT_SESSION_KEY;

    if (sessionId && prevKey === DRAFT_SESSION_KEY && targetKey !== DRAFT_SESSION_KEY) {
      migrateDraftState(sessionId);
    }

    if (prevKey === targetKey) {
      return;
    }

    sessionKeyRef.current = targetKey;
    const storedState = readStoredState(targetKey);
    hasInitializedRef.current = storedState.started;
    initialStateRef.current = storedState;
    setIntroMessages(storedState.messages);
    setTypingMessage(null);
    clearTimers();
  }, [sessionId, migrateDraftState, clearTimers]);

  const ensureTypingVisible = useCallback(() => {
    setTypingMessage((current) => current ?? buildTypingMessage(sessionKeyRef.current));
  }, []);

  const finalizeSequence = useCallback(() => {
    clearTimers();
    setTypingMessage(null);
    isRunningRef.current = false;
  }, [clearTimers]);

  const scheduleSequence = useCallback(
    (startIndex: number) => {
      if (isRunningRef.current) {
        return;
      }

      const pendingEntries = INTRO_SCRIPT.slice(startIndex);
      if (!pendingEntries.length) {
        finalizeSequence();
        return;
      }

      isRunningRef.current = true;
      ensureTypingVisible();

      let cumulativeDelay = 0;
      const scheduledForKey = sessionKeyRef.current;
      pendingEntries.forEach((entry, index) => {
        cumulativeDelay += entry.pauseMs;
        const timeoutId = window.setTimeout(() => {
          if (sessionKeyRef.current !== scheduledForKey) {
            return;
          }
          setIntroMessages((prev) => {
            const alreadyExists = prev.some((message) => message.id === `intro-${sessionKeyRef.current}-${entry.id}`);
            if (alreadyExists) {
              return prev;
            }
            const next = [...prev, buildIntroMessage(sessionKeyRef.current, entry)];
            persistState(next, true);
            return next;
          });

          if (index === pendingEntries.length - 1) {
            finalizeSequence();
          }
        }, cumulativeDelay);

        timersRef.current.push(timeoutId);
      });
    },
    [ensureTypingVisible, finalizeSequence, persistState]
  );

  const completeRemainingImmediately = useCallback(() => {
    setIntroMessages((prev) => {
      if (!hasInitializedRef.current) {
        return prev;
      }
      if (prev.length >= INTRO_SCRIPT.length) {
        return prev;
      }
      const remaining = INTRO_SCRIPT.slice(prev.length).map((entry) =>
        buildIntroMessage(sessionKeyRef.current, entry)
      );
      const next = [...prev, ...remaining];
      persistState(next, true);
      return next;
    });
    finalizeSequence();
  }, [finalizeSequence, persistState]);

  useEffect(() => {
    const deliveredCount = introMessages.length;
    const needsAnimation = deliveredCount < INTRO_SCRIPT.length;

    if (hasServerMessages) {
      if (needsAnimation && hasInitializedRef.current) {
        completeRemainingImmediately();
      } else {
        finalizeSequence();
      }
      return;
    }

    if (!needsAnimation) {
      finalizeSequence();
      return;
    }

    if (!hasInitializedRef.current && !hasServerMessages) {
      hasInitializedRef.current = true;
      persistState(introMessages, true);
    }

    scheduleSequence(deliveredCount);
  }, [
    introMessages,
    hasServerMessages,
    completeRemainingImmediately,
    finalizeSequence,
    persistState,
    scheduleSequence,
  ]);

  useEffect(() => () => clearTimers(), [clearTimers]);

  return useMemo(
    () => ({
      introMessages,
      typingMessage,
    }),
    [introMessages, typingMessage]
  );
};
