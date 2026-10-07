// Focused offline tests for guided replies in the real widget implementation.
// Run with: node --test tests/test_guided_replies.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const widgetSource = fs.readFileSync(
  path.join(__dirname, "../frontend/chat-widget.js"),
  "utf8"
);

function extractFunction(source, name) {
  const start = source.indexOf(`  function ${name}(`) >= 0
    ? source.indexOf(`  function ${name}(`)
    : source.indexOf(`  async function ${name}(`);
  assert.notEqual(start, -1, `${name} function exists`);
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
    if (char === '"' || char === "'" || char === "`") quote = char;
    else if (char === "{") depth += 1;
    else if (char === "}" && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`Could not find the end of ${name}`);
}

class FakeElement {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.attributes = {};
    this.listeners = {};
    this.className = "";
    this.disabled = false;
    this.hidden = false;
    this.textContent = "";
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index >= 0) this.children.splice(index, 1);
    child.parentNode = null;
    return child;
  }

  querySelectorAll(selector) {
    const matches = [];
    const visit = (node) => {
      node.children.forEach((child) => {
        if (selector === "button" && child.tagName === "BUTTON") matches.push(child);
        visit(child);
      });
    };
    visit(this);
    return matches;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  addEventListener(type, listener) {
    this.listeners[type] = listener;
  }

  click() {
    if (this.disabled) return;
    if (this.listeners.click) this.listeners.click();
  }
}

function guidedHarness() {
  const chatBody = new FakeElement("div");
  const context = {
    document: { createElement: (tagName) => new FakeElement(tagName) },
    chatBody,
    isSending: false,
    sessionId: "test-session",
    selectedIssueCategory: "Courseware Issue",
    pendingImagePreviewSrc: null,
    pendingImage: null,
    clarifyPanel: { hidden: false },
    chatInput: { focus() {} },
    sent: [],
    appendedBots: [],
    scrollToBottom() {},
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext([
    "const MAX_SUGGESTED_REPLIES = 3; const MAX_SUGGESTED_REPLY_LENGTH = 160;",
    "let suggestedRepliesPanel = null;",
    extractFunction(widgetSource, "normalizeSuggestedReplies"),
    extractFunction(widgetSource, "setSuggestedRepliesDisabled"),
    extractFunction(widgetSource, "clearSuggestedReplies"),
    extractFunction(widgetSource, "renderSuggestedReplies"),
  ].join("\n"), context);
  return { context, chatBody };
}

function sendingHarness() {
  const app = guidedHarness();
  const { context } = app;
  context.appendUser = () => {};
  context.appendUserWithImage = () => {};
  context.setSending = (value) => {
    context.isSending = value;
    context.setSuggestedRepliesDisabled(value);
  };
  context.appendTyping = () => ({ remove() {} });
  context.clearImage = () => {};
  context.appendRequestError = (error) => { throw error; };
  context.updateResolvedContext = () => {};
  context.requestChat = async (text, _image, category) => {
    context.sent.push({ text, category });
    return {
      response_kind: "conversation",
      answer: "I can help with that.",
      suggested_replies: ["Tell me more"],
    };
  };
  context.appendBot = (text, sources, suggestions) => {
    context.appendedBots.push({ text, sources, suggestions });
    context.renderSuggestedReplies(suggestions);
  };
  vm.runInContext(`${extractFunction(widgetSource, "sendMessage")}; this.sendMessage = sendMessage;`, context);
  return app;
}

test("quick reply clicks use the exact label and cannot duplicate a pending request", async () => {
  const app = sendingHarness();
  app.context.renderSuggestedReplies(["  I am still stuck  "]);
  const button = app.chatBody.querySelectorAll("button")[0];

  button.click();
  button.click();
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(app.context.sent, [{ text: "I am still stuck", category: "Courseware Issue" }]);
  assert.equal(app.context.appendedBots[0].suggestions[0], "Tell me more");
  assert.equal(app.context.selectedIssueCategory, "Courseware Issue");
});

test("new replies replace stale choices and context reset clears them", () => {
  const app = guidedHarness();
  app.context.renderSuggestedReplies(["First choice", "Second choice"]);
  assert.deepEqual(app.chatBody.querySelectorAll("button").map((button) => button.textContent), [
    "First choice",
    "Second choice",
  ]);

  app.context.renderSuggestedReplies(["Latest choice"]);
  assert.deepEqual(app.chatBody.querySelectorAll("button").map((button) => button.textContent), ["Latest choice"]);
  app.context.clearSuggestedReplies();
  assert.equal(app.chatBody.querySelectorAll("button").length, 0);
});

test("missing and malformed suggested replies are ignored, deduplicated, and bounded", () => {
  const app = guidedHarness();
  app.context.renderSuggestedReplies([
    null,
    42,
    {},
    "",
    " Done ",
    "Done",
    "<b>Literal text</b>",
    "A".repeat(161),
    "Second",
    "Third",
    "Fourth",
  ]);

  const buttons = app.chatBody.querySelectorAll("button");
  assert.equal(buttons.length, 3);
  assert.deepEqual(buttons.map((button) => button.textContent), [
    "Done",
    "<b>Literal text</b>",
    "Second",
  ]);
  app.context.renderSuggestedReplies(undefined);
  assert.equal(app.chatBody.querySelectorAll("button").length, 0);
});
