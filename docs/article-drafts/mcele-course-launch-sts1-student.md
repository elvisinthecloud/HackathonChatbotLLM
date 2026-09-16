# MCeLE course launch error: "sts1.auth.ecuf.deas.mil refused to connect"

## Article record

- Article ID: `MCELE-LAUNCH-001`
- Status: Content approved by the user; not ingested or deployed
- Service/delivery area: MCeLE
- Discovery portal: MCeLE; catalog appearance alone does not establish the delivery area
- Allowed role: Student (approved for this demo; no access for other roles by default)
- Course scope: General MCeLE-delivered course troubleshooting; CYBERM0000 is the selected demo example, not an exclusive course restriction
- Excluded delivery area: Moodle, including Moodle courses found through the MCeLE catalog or My Courses
- Issue trigger: User-provided error text or readable screenshot showing `sts1.auth.ecuf.deas.mil refused to connect`
- Content type: Adapted existing troubleshooting guidance, not synthetic
- Provenance: Live Atlas `/home/velvux/ChatBotLLM/knowledge/rag-source-documents/converted/manual/course-content-sts1-auth-refused-to-connect.md`, selectively read during live-first inspection; corresponding local reference article re-read during drafting. Delivery scope and screenshot/course-context behavior were specified by the user.
- Adaptation: Original eight-step troubleshooting sequence preserved; scope and trigger clarified; Helpdesk fallback proposed for unresolved issues
- External source URL: None embedded in the original article
- Redistribution status: To be confirmed before public packaging; no license inferred

## Knowledge content

Use this guidance when a course delivered in **MCeLE**, such as **CYBERM0000**, displays **"sts1.auth.ecuf.deas.mil refused to connect"** in its course window, pop-up, or embedded content frame.

This guidance does **not** apply to courses delivered in **Moodle**.

To troubleshoot this error:

1. Log in to **MCeLE**.
2. Open the browser menu in the upper-right corner. It may appear as **three dots**.
3. Select **Delete browsing data**.
4. Set the time range to **Last 24 hours**.
5. Select **Cookies and other site data** and **Cached images and files**.
6. Select **Delete from this device**.
7. After the browsing data has been cleared, **restart your computer**.
8. Log back in to **MCeLE** and try launching the course content again.

If the same error continues, contact the **Helpdesk** for further assistance.

## Editorial and retrieval notes

- Embed only the Knowledge content. Store the article record as structured metadata and keep editorial notes outside the index and model's answer excerpts.
- Apply Student role permission and the MCeLE delivery-area/Moodle exclusion in backend retrieval and all content exposure paths. Prompt instructions alone are insufficient.
- A known course selection or code mention, such as CYBERM0000, resolves course context from server-controlled records. It does not establish the error or justify these steps by itself.
- For a vague "I cannot launch my course" question, ask for the error text or a screenshot before offering this specific solution. Do not treat all launch failures as this error.
- If the screenshot text is unreadable or only says "refused to connect" without enough identifying context, ask the user to confirm the displayed error. Do not invent the hostname or silently treat the user's shorthand "s1st" as an exact screenshot transcription.
- If selected course, mentioned course, and screenshot delivery-system evidence conflict, clarify before using this article. Do not route a known Moodle course here simply because its launch started in the MCeLE portal.
- Preserve the supplied browser menu labels, Last 24 hours time range, and computer restart step. No browser/version-specific alternatives have been verified. Adapt menu wording only if the user supplies/approves the relevant browser workflow.
- Do not invent a root cause, claim cookies are definitely responsible, or guarantee that these steps resolve the error.
- The original article has no Helpdesk fallback; the closing sentence is a proposed demo addition consistent with the agreed help-handoff behavior. Do not invent a contact URL, email, or phone number.
- The demo screenshot has not yet been supplied. Recognition and routing still require end-to-end verification after approved deployment.
