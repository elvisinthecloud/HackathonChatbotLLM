"""Conservative social replies; unmatched text always follows support routing."""
import re


_PHRASES = (
    ("capability", re.compile(
        r"(?:(?:can you|are you able to) help me(?: with (?:other things|something else))?"
        r"|what (?:else )?can you (?:do|help me with))(?=\s|$)")),
    ("wellbeing", re.compile(r"how are you(?: doing)?(?: today)?(?=\s|$)")),
    ("thanks", re.compile(
        r"(?:thank you(?: very much| so much| for your help)?"
        r"|thanks(?: so much| a lot| for your help)?|i appreciate (?:it|your help))(?=\s|$)")),
    ("greeting", re.compile(r"(?:hello(?: there)?|hi(?: there)?|hey|good (?:morning|afternoon|evening))(?=\s|$)")),
    ("acknowledgement", re.compile(
        r"(?:(?:oh )?(?:okay|ok)|got it|understood|sounds good|that makes sense|that helps)(?=\s|$)")),
)


def conversational_reply(question: str) -> str | None:
    # Bound the recognizer and require every word to belong to a reviewed phrase.
    # In particular, never strip a polite prefix from a real support request.
    if len(question) > 320:
        return None
    text = re.sub(r"[.!?,;:\s]+", " ", question.casefold()).strip()
    if not text:
        return None
    kinds = set()
    position = 0
    while position < len(text):
        for kind, pattern in _PHRASES:
            match = pattern.match(text, position)
            if match:
                kinds.add(kind)
                position = match.end()
                if position < len(text):
                    position += 1  # Whitespace was normalized to a single space.
                break
        else:
            return None
    if "capability" in kinds:
        return "Yes. What would you like help with?"
    if "wellbeing" in kinds:
        return "I'm ready to help. What would you like help with?"
    if "thanks" in kinds:
        return "You're welcome!"
    if "greeting" in kinds:
        return "Hello! What would you like help with?"
    return "Okay. Let me know if you need anything else."
