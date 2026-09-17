// Focused regression tests for the real sendMessage implementation.
// Run with: node --test tests/test_intake_conversation.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const widgetPath = path.join(__dirname, "../frontend/chat-widget.js");
const widgetSource = fs.readFileSync(widgetPath, "utf8");

function extractSendMessage(source) {
  const start = source.indexOf("  async function sendMessage(rawText) {");
  assert.notEqual(start, -1, "sendMessage function exists");
  const open = source.indexOf("{", start);
  let depth = 0;
  let quote = null;
  let escaped = false;
  for (let i = open; i < source.length; i += 1) {
    const char = source[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === quote) quote = null;
      continue;
    }
    if (char === "\"" || char === "'" || char === "`") quote = char;
    else if (char === "{") depth += 1;
    else if (char === "}" && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error("Could not find the end of sendMessage");
}

const sendMessageSource = extractSendMessage(widgetSource);

function harness(initialCategory, outcomes) {
  const sentCategories = [];
  const errors = [];
  let pendingOutcome = 0;
  const context = {
    selectedIssueCategory: initialCategory,
    pendingImagePreviewSrc: null,
    pendingImage: null,
    sessionId: "test-session",
    isSending: false,
    clarifyPanel: { hidden: false },
    chatInput: { focus() {} },
    appendUser() {},
    appendUserWithImage() {},
    setSending(value) { context.isSending = value; },
    appendTyping() { return { remove() {} }; },
    clearImage() {},
    async requestChat(_text, _image, category) {
      sentCategories.push(category);
      const outcome = outcomes[pendingOutcome++];
      if (outcome instanceof Error) throw outcome;
      return outcome;
    },
    appendBot() {},
    updateResolvedContext() {},
    appendRequestError(error) { errors.push(error); },
  };
  vm.createContext(context);
  vm.runInContext(`${sendMessageSource}; this.sendMessage = sendMessage;`, context);
  return {
    context,
    sentCategories,
    errors,
    async send(text = "hello") { await context.sendMessage(text); },
  };
}

test("conversation replies preserve intake category until the next support reply", async () => {
  for (const category of ["Account/Profile Issue", "Courseware Issue", "Roles and Permissions", "Other"]) {
    const app = harness(category, [
      { response_kind: "conversation", answer: "Hello!" },
      { response_kind: "conversation", answer: "You are welcome." },
      { response_kind: "support", needs_clarification: true, answer: "Please provide the exact error." },
      { response_kind: "support", answer: "Another question." },
    ]);

    await app.send("Hi");
    assert.equal(app.context.selectedIssueCategory, category);
    await app.send("Thanks");
    assert.equal(app.context.selectedIssueCategory, category);
    await app.send("I still need help");
    assert.equal(app.sentCategories[2], category);
    assert.equal(app.context.selectedIssueCategory, null);
    await app.send("One more support question");
    assert.equal(app.sentCategories[3], null);
  }
});

test("failed requests retain the intake category for retry", async () => {
  const app = harness("Account/Profile Issue", [new Error("network unavailable"), {
    response_kind: "support", answer: "Resolved." }]);

  await app.send("Help");
  assert.equal(app.context.selectedIssueCategory, "Account/Profile Issue");
  assert.equal(app.errors.length, 1);
  await app.send("Retry");
  assert.deepEqual(app.sentCategories, ["Account/Profile Issue", "Account/Profile Issue"]);
  assert.equal(app.context.selectedIssueCategory, null);
});

test("unknown or missing response_kind keeps the prior clear behavior", async () => {
  for (const response of [
    { response_kind: "future-kind", answer: "Reply" },
    { answer: "Legacy reply" },
  ]) {
    const app = harness("Other", [response]);
    await app.send();
    assert.equal(app.context.selectedIssueCategory, null);
  }
});
