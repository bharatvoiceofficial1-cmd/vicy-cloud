"""
memory_store.py — Persistent Long-Term Memory & Conversation Context Store.

Features:
  1. Persistent JSON database: saved to data/memory.json
  2. User profile & facts: tracks name, preferences, favorite media, contacts, custom facts.
  3. Notes & reminders: timestamped list of notes.
  4. Conversation history: rolling sliding window of past turns for multi-turn understanding.
  5. Automatic extraction: captures 'my name is X', 'my favorite X is Y', 'remember that X'.
  6. Context generator: formats memories and conversation history into LLM prompt context.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_PATH = Path(__file__).parent / "data" / "memory.json"


class MemoryStore:
    """Manages persistent long-term memory, facts, and conversation history."""

    def __init__(self, filepath: Path | str | None = None) -> None:
        self.filepath = Path(filepath) if filepath else DEFAULT_MEMORY_PATH
        self.data: dict[str, Any] = {
            "user_profile": {},
            "facts": {},
            "notes": [],
            "history": [],
        }
        self._load()

    def _load(self) -> None:
        """Load memory from JSON file or initialize if not present."""
        try:
            if self.filepath.exists():
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
                logger.info("Loaded memory store from %s with %d facts, %d notes, %d history items.",
                            self.filepath, len(self.data.get("facts", {})),
                            len(self.data.get("notes", [])), len(self.data.get("history", [])))
            else:
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
                self._save()
        except Exception as e:
            logger.warning("Error loading memory store from %s: %s", self.filepath, e)

    def _save(self) -> None:
        """Save memory to disk."""
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Error saving memory store: %s", e)

    # ── Fact & Profile Management ──────────────────────────────────────────────

    def set_user_property(self, key: str, value: str) -> None:
        """Set a property on the user profile (e.g. name, favorite_song)."""
        clean_key = key.lower().strip().replace(" ", "_")
        self.data.setdefault("user_profile", {})[clean_key] = value.strip()
        self._save()
        logger.info("Saved user profile property: %s = %s", clean_key, value)

    def get_user_property(self, key: str, default: str = "") -> str:
        """Retrieve a user property."""
        clean_key = key.lower().strip().replace(" ", "_")
        return self.data.get("user_profile", {}).get(clean_key, default)

    def remember_fact(self, key: str, value: str) -> None:
        """Remember a specific fact or relationship."""
        clean_key = key.strip()
        self.data.setdefault("facts", {})[clean_key] = value.strip()
        self._save()
        logger.info("Saved fact: %s -> %s", clean_key, value)

    def add_note(self, text: str) -> dict[str, Any]:
        """Add a timestamped note or reminder."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note = {
            "id": len(self.data.setdefault("notes", [])) + 1,
            "text": text.strip(),
            "timestamp": now,
        }
        self.data["notes"].append(note)
        # Keep latest 50 notes
        if len(self.data["notes"]) > 50:
            self.data["notes"] = self.data["notes"][-50:]
        self._save()
        logger.info("Added note #%d: %s", note["id"], text)
        return note

    def forget(self, target: str) -> bool:
        """Remove a fact, user property, or note matching target."""
        target_lower = target.lower().strip()
        removed = False

        # 1. Check user profile
        user_prof = self.data.get("user_profile", {})
        for k in list(user_prof.keys()):
            if target_lower in k or target_lower in user_prof[k].lower():
                del user_prof[k]
                removed = True

        # 2. Check facts
        facts = self.data.get("facts", {})
        for k in list(facts.keys()):
            if target_lower in k.lower() or target_lower in facts[k].lower():
                del facts[k]
                removed = True

        # 3. Check notes
        notes = self.data.get("notes", [])
        new_notes = [n for n in notes if target_lower not in n.get("text", "").lower()]
        if len(new_notes) != len(notes):
            self.data["notes"] = new_notes
            removed = True

        if removed:
            self._save()
        return removed

    def clear_all_memories(self) -> None:
        """Reset all stored facts, profile, and notes."""
        self.data = {
            "user_profile": {},
            "facts": {},
            "notes": [],
            "history": [],
        }
        self._save()

    # ── Auto-Extraction from Natural Language ──────────────────────────────────

    def auto_extract(self, text: str) -> tuple[bool, str]:
        """
        Detects if user said something like:
          - "remember that my name is Abhi"
          - "my name is Abhi"
          - "my favorite song is Starboy"
          - "remember that X is Y"
          - "note that X"
        Returns (extracted: bool, confirmation_message: str).
        """
        t = text.strip()
        lower = t.lower()

        # 1. User Name
        name_match = re.search(r"^(?:remember\s+(?:that\s+)?)?my\s+name\s+is\s+([a-zA-Z\s]+?)(?:\.|$)", t, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip().title()
            self.set_user_property("name", name)
            return True, f"I will remember that your name is {name}."

        # 2. Favorite things (e.g. "my favorite song is Starboy", "my favorite music is phonk", "my favorite color is blue")
        fav_match = re.search(r"^(?:remember\s+(?:that\s+)?)?my\s+favorite\s+([a-zA-Z\s]+?)\s+is\s+(.+?)(?:\.|$)", t, re.IGNORECASE)
        if fav_match:
            category = fav_match.group(1).strip().lower().replace(" ", "_")
            item = fav_match.group(2).strip()
            self.set_user_property(f"favorite_{category}", item)
            cat_display = category.replace("_", " ")
            return True, f"Got it! I will remember that your favorite {cat_display} is {item}."

        # 3. Explicit "remember that <X> is <Y>"
        fact_match = re.search(r"^remember\s+(?:that\s+)?([a-zA-Z0-9_\-\s]+?)\s+(?:is|are|=|was)\s+(.+?)(?:\.|$)", t, re.IGNORECASE)
        if fact_match:
            key = fact_match.group(1).strip()
            val = fact_match.group(2).strip()
            self.remember_fact(key, val)
            return True, f"I will remember that {key} is {val}."

        # 4. General "remember <note/reminder>"
        rem_match = re.search(r"^(?:remember|note|remind\s+me)\s+(?:to\s+|that\s+)?(.+?)(?:\.|$)", t, re.IGNORECASE)
        if rem_match:
            content = rem_match.group(1).strip()
            self.add_note(content)
            return True, f"Saved to memory: '{content}'."

        return False, ""

    # ── Search & Retrieval ─────────────────────────────────────────────────────

    def recall(self, query: str) -> str:
        """Find facts or profile values relevant to the query."""
        q = query.lower().strip()

        # Check name
        if "my name" in q or "who am i" in q:
            name = self.get_user_property("name")
            if name:
                return f"Your name is {name}."
            return "I don't know your name yet. You can tell me by saying 'My name is [your name]'."

        # Check favorite
        fav_match = re.search(r"favorite\s+([a-zA-Z\s]+)", q)
        if fav_match:
            cat = fav_match.group(1).strip().lower().replace(" ", "_")
            val = self.get_user_property(f"favorite_{cat}")
            if val:
                return f"Your favorite {cat.replace('_', ' ')} is {val}."
            # Also check broad favorite_song / music
            if "song" in cat or "music" in cat:
                s = self.get_user_property("favorite_song") or self.get_user_property("favorite_music")
                if s:
                    return f"Your favorite music is {s}."

        # Check facts
        for k, v in self.data.get("facts", {}).items():
            if k.lower() in q or q in k.lower():
                return f"{k} is {v}."

        # Check notes
        matching_notes = [n["text"] for n in self.data.get("notes", []) if any(w in n["text"].lower() for w in q.split() if len(w) > 3)]
        if matching_notes:
            return f"Found in notes: {matching_notes[-1]}"

        # If asking general "what do you remember" / "what do you know about me"
        if any(p in q for p in ["what do you remember", "what do you know about me", "my memories", "list memories"]):
            return self.get_summary()

        return ""

    def get_summary(self) -> str:
        """Generate a human-readable summary of everything stored in memory."""
        lines = []
        name = self.get_user_property("name")
        if name:
            lines.append(f"• User Name: {name}")

        user_prof = self.data.get("user_profile", {})
        for k, v in user_prof.items():
            if k != "name":
                lines.append(f"• {k.replace('_', ' ').title()}: {v}")

        facts = self.data.get("facts", {})
        for k, v in facts.items():
            lines.append(f"• Fact: {k} = {v}")

        notes = self.data.get("notes", [])
        if notes:
            lines.append(f"• Notes ({len(notes)} total):")
            for n in notes[-5:]:  # show latest 5
                lines.append(f"   - [{n.get('timestamp', '')}] {n.get('text', '')}")

        if not lines:
            return "My memory is currently empty. You can tell me your name, favorites, or anything you'd like me to remember!"

        return "Here is what I remember about you:\n" + "\n".join(lines)

    # ── Multi-Turn Conversation History ────────────────────────────────────────

    def record_turn(self, user_text: str, assistant_reply: str) -> None:
        """Record a conversation turn for multi-turn understanding."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        turn = {
            "user": user_text.strip(),
            "assistant": assistant_reply.strip(),
            "timestamp": now,
        }
        self.data.setdefault("history", []).append(turn)
        # Keep last 20 turns
        if len(self.data["history"]) > 20:
            self.data["history"] = self.data["history"][-20:]
        self._save()

    def get_history_summary(self, max_turns: int = 5) -> str:
        """Get the latest turns formatted for LLM prompts."""
        turns = self.data.get("history", [])[-max_turns:]
        if not turns:
            return ""
        lines = ["Recent conversation context:"]
        for t in turns:
            lines.append(f"User: {t.get('user', '')}")
            lines.append(f"Assistant: {t.get('assistant', '')}")
        return "\n".join(lines)

    # ── Context Block for LLM Prompt Injection ─────────────────────────────────

    def get_llm_context(self) -> str:
        """
        Builds a rich context block including user profile, key facts, notes,
        and recent conversation history. Injected into Gemini and Ollama prompts.
        """
        parts = []

        # Profile & facts
        prof_parts = []
        name = self.get_user_property("name")
        if name:
            prof_parts.append(f"User's Name: {name}")
        for k, v in self.data.get("user_profile", {}).items():
            if k != "name":
                prof_parts.append(f"{k.replace('_', ' ').title()}: {v}")
        for k, v in self.data.get("facts", {}).items():
            prof_parts.append(f"{k}: {v}")

        if prof_parts:
            parts.append("USER PROFILE & LONG-TERM MEMORY:")
            parts.extend([f"- {p}" for p in prof_parts])

        # Latest notes
        notes = self.data.get("notes", [])[-3:]
        if notes:
            parts.append("SAVED USER NOTES & REMINDERS:")
            for n in notes:
                parts.append(f"- [{n.get('timestamp')}] {n.get('text')}")

        # Recent conversation history
        hist = self.get_history_summary(max_turns=4)
        if hist:
            parts.append(hist)

        if not parts:
            return ""

        return "\n" + "\n".join(parts) + "\n"
