# Neutral issue intake (codex/jira-ticket)

This branch now replaces the earlier mock ticket handoff with a simpler support flow:

1. After demo profile selection, greet the user and show Account/Profile Issue, Courseware Issue, Roles and Permissions, and Other.
2. Every choice receives the same neutral prompt: “Please tell me more about what’s happening and what you’re trying to do.” Selecting a category makes no chat/search request.
3. Once the user describes the issue, retrieve approved articles using the retained conversation in the current access context, including screenshot text. The category is a tentative hint and does not control permissions or course/site routing. Users can also type their issue directly.
4. Contact Help Desk opens the existing support information and configured contact URL. No prefill or mock ticket endpoint remains.

Course/site controls remain optional under a collapsed section. Clear and profile changes restart intake. Existing role permissions and context-change isolation remain in force; changing context excludes prior-context turns. Answer generation keeps its existing bounded memory, while retrieval no longer uses only the last four truncated messages.

Verification: offline API/retrieval tests and mocked browser checks. Local preview uses simulated answers; live model and Atlas deployment have not been exercised for this change.
