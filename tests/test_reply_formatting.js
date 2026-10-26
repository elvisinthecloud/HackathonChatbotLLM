// Exercise the widget's actual DOM renderer without a browser or HTML parser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../frontend/chat-widget.js'), 'utf8');
class Element {
  constructor(tag, text = '') { this.tagName = tag; this.children = []; this.text = text; }
  appendChild(child) { this.children.push(child); return child; }
  set textContent(text) { this.text = text; this.children = []; }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(''); }
  set innerHTML(_) { throw new Error('HTML injection is forbidden'); }
}
function render(text) {
  const context = { URL, document: {
    createElement: tag => new Element(tag),
    createTextNode: text => new Element('#text', text),
  }};
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('  function appendInlineText('), source.indexOf('  function appendMessage(')), context);
  const root = new Element('div');
  context.appendFormattedText(root, text);
  return root;
}
function descendants(root, tag) {
  return root.children.flatMap(child => [...(child.tagName === tag ? [child] : []), ...descendants(child, tag)]);
}
test('blank-separated ordered steps stay grouped and retain source numbering', () => {
  const root = render('## Enrollment\n\n3. Open the menu.\n\n5) Select the course. [1]\n\nKeep the original condition.');
  assert.deepEqual(root.children.map(child => child.tagName), ['h3', 'ol', 'p']);
  assert.equal(root.children[1].start, 3);
  assert.deepEqual(root.children[1].children.map(child => child.value), [3, 5]);
  assert.deepEqual(root.children[1].children.map(child => child.textContent), ['Open the menu.', 'Select the course. [1]']);
  assert.equal(root.children[2].textContent, 'Keep the original condition.');
});
test('separate sections and ordinary legacy answers retain text and link targets', () => {
  const root = render('Plain answer.\n\n1. Read [the guide](https://example.org/guide?a=1&b=2).\n\n## Next\n\n2. Keep **this phrase**. [1, 2]');
  assert.deepEqual(root.children.map(child => child.tagName), ['p', 'ol', 'h3', 'ol']);
  const link = descendants(root, 'a')[0];
  assert.equal(link.href, 'https://example.org/guide?a=1&b=2');
  assert.equal(link.textContent, 'the guide');
  assert.equal(link.rel, 'noopener noreferrer');
  assert.equal(descendants(root, 'li')[1].textContent, 'Keep this phrase. [1, 2]');
  assert.equal(descendants(root, 'span')[0].textContent, '[1, 2]');
});
test('HTML and executable Markdown URLs stay literal text', () => {
  const text = '<img src=x onerror=alert(1)> [click](javascript:alert(1))';
  const root = render(text);
  assert.equal(root.textContent, text);
  assert.equal(descendants(root, 'img').length, 0);
  assert.equal(descendants(root, 'a').length, 0);
});

test('instruction follow-up stays outside the numbered list and preserves citation', () => {
  const root = render('### Find your courses\n\n1. Select **Student Dashboard**. [1]\n\nWhat do you see now?');
  assert.deepEqual(root.children.map(child => child.tagName), ['h3', 'ol', 'p']);
  assert.equal(root.children[1].children[0].textContent, 'Select Student Dashboard. [1]');
  assert.equal(root.children[2].textContent, 'What do you see now?');
});
