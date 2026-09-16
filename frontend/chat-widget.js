(function () {
  const chatFab = document.getElementById("chatFab");
  const chatPanel = document.getElementById("chatPanel");
  const chatClose = document.getElementById("chatClose");
  const chatBody = document.getElementById("chatBody");
  const chatInput = document.getElementById("chatInput");
  const chatForm = document.getElementById("chatForm");
  const chatSend = document.getElementById("chatSend");
  const chatStatus = document.getElementById("chatStatus");
  const btnClear = document.getElementById("btnClear");
  const btnSupport = document.getElementById("btnSupport");
  const supportPanel = document.getElementById("supportPanel");
  const supportPanelClose = document.getElementById("supportPanelClose");
  const supportMessage = document.getElementById("supportMessage");
  const chatImageInput = document.getElementById("chatImageInput");
  const chatImageBtn = document.getElementById("chatImageBtn");
  const chatImagePreview = document.getElementById("chatImagePreview");
  const profileSelect = document.getElementById("profileSelect");
  const courseSelect = document.getElementById("courseSelect");
  const systemSelect = document.getElementById("systemSelect");
  const otherCourse = document.getElementById("otherCourse");
  const otherCourseRow = document.getElementById("otherCourseRow");
  const clarifyPanel = document.getElementById("clarifyPanel");
  const ticketPage = document.getElementById("ticketPage");
  let selectedSystem = null;
  let queuedRequest = null;
  let ticketPending = false;
  const profileDescription = document.getElementById("profileDescription");
  const resolvedContext = document.getElementById("resolvedContext");
  const sessionError = document.getElementById("sessionError");
  const apiUrl =
    window.CHATBOT_API_URL ||
    document.body.dataset.chatApiUrl ||
    "/api/chat";
  const supportApiUrl =
    window.CHATBOT_SUPPORT_API_URL ||
    document.body.dataset.supportApiUrl ||
    "/api/support";
  const MAX_IMAGE_BYTES = 4 * 1024 * 1024;

  let hasGreeted = false;
  let isSending = false;
  let pendingImage = null;
  let pendingImagePreviewSrc = null;
  let profiles = [];
  let courses = [];
  let selectedProfile = null;
  let selectedCourseId = null;
  let sessionId = null;
  let sessionGeneration = 0;

  function scrollToBottom() {
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function updateSupportInfo(info) {
    if (!info || typeof info !== "object") return;
    if (info.hours) {
      supportMessage.textContent = info.hours;
    }
  }

  async function loadSupportInfo() {
    try {
      const response = await fetch(supportApiUrl);
      if (!response.ok) return;
      updateSupportInfo(await response.json());
    } catch (error) {
      console.warn("Support handoff information is unavailable.", error);
    }
  }

  function setSupportPanelOpen(isOpen) {
    supportPanel.hidden = !isOpen;
    btnSupport.setAttribute("aria-expanded", String(isOpen));
    if (isOpen) {
      supportPanelClose.focus();
    } else {
      btnSupport.focus();
    }
  }

  function appendInlineText(parent, text) {
    const parts = String(text).split(/(\[[^\]]+\]\(https?:\/\/[^)]+\)|https?:\/\/\S+|\*\*[^*]+\*\*|\[[0-9][0-9,\s-]*\])/gi);
    parts.forEach((part) => {
      if (!part) return;

      const linkMatch = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/i);
      if (linkMatch) {
        let safeUrl;
        try { safeUrl = new URL(linkMatch[2]); } catch (_) { parent.appendChild(document.createTextNode(part)); return; }
        const link = document.createElement("a");
        link.href = safeUrl.href;
        link.textContent = linkMatch[1];
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        parent.appendChild(link);
        return;
      }

      if (/^https?:\/\/\S+$/.test(part)) {
        let safeUrl;
        try { safeUrl = new URL(part); } catch (_) { parent.appendChild(document.createTextNode(part)); return; }
        const link = document.createElement("a");
        link.href = safeUrl.href;
        link.textContent = part;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        parent.appendChild(link);
        return;
      }

      if (/^\*\*[^*]+\*\*$/.test(part)) {
        const strong = document.createElement("strong");
        strong.textContent = part.slice(2, -2);
        parent.appendChild(strong);
        return;
      }

      if (/^\[[0-9][0-9,\s-]*\]$/.test(part)) {
        const citation = document.createElement("span");
        citation.className = "inline-citation";
        citation.textContent = part;
        parent.appendChild(citation);
        return;
      }

      parent.appendChild(document.createTextNode(part));
    });
  }

  function appendParagraph(container, lines) {
    const text = lines.join(" ").trim();
    if (!text) return;

    const paragraph = document.createElement("p");
    appendInlineText(paragraph, text);
    container.appendChild(paragraph);
  }

  function appendBlockquote(container, lines) {
    const quote = document.createElement("blockquote");
    appendInlineText(quote, lines.join(" ").trim());
    container.appendChild(quote);
  }

  function appendList(container, lines, ordered, start = 1) {
    const list = document.createElement(ordered ? "ol" : "ul");
    if (ordered && Number.isFinite(start) && start > 1) {
      list.start = start;
    }
    lines.forEach((line) => {
      const item = document.createElement("li");
      appendInlineText(item, line);
      list.appendChild(item);
    });
    container.appendChild(list);
  }

  function appendFormattedText(container, text) {
    const lines = String(text).replace(/\r\n?/g, "\n").split("\n");
    let index = 0;

    while (index < lines.length) {
      const line = lines[index].trim();

      if (!line) {
        index += 1;
        continue;
      }

      const headingMatch =
        line.match(/^#{1,4}\s+(.+)$/) || line.match(/^\*\*(.+?)\*\*:?\s*$/);
      if (headingMatch && headingMatch[1].length <= 80) {
        const heading = document.createElement("h3");
        appendInlineText(heading, headingMatch[1].trim());
        container.appendChild(heading);
        index += 1;
        continue;
      }

      const orderedMatch = line.match(/^(\d+)[.)]\s+(.+)$/);
      if (orderedMatch) {
        const items = [];
        const start = Number(orderedMatch[1]);
        while (index < lines.length) {
          const itemMatch = lines[index].trim().match(/^(\d+)[.)]\s+(.+)$/);
          if (!itemMatch) break;
          items.push(itemMatch[2].trim());
          index += 1;
        }
        appendList(container, items, true, start);
        continue;
      }

      const bulletMatch = line.match(/^[-*•]\s+(.+)$/);
      if (bulletMatch) {
        const items = [];
        while (index < lines.length) {
          const itemMatch = lines[index].trim().match(/^[-*•]\s+(.+)$/);
          if (!itemMatch) break;
          items.push(itemMatch[1].trim());
          index += 1;
        }
        appendList(container, items, false);
        continue;
      }

      const blockquoteMatch = line.match(/^>\s+(.+)$/);
      if (blockquoteMatch) {
        const quoteLines = [];
        while (index < lines.length) {
          const quoteMatch = lines[index].trim().match(/^>\s+(.+)$/);
          if (!quoteMatch) break;
          quoteLines.push(quoteMatch[1].trim());
          index += 1;
        }
        appendBlockquote(container, quoteLines);
        continue;
      }

      const paragraphLines = [];
      while (index < lines.length) {
        const nextLine = lines[index].trim();
        const startsNewBlock =
          !nextLine ||
          /^#{1,4}\s+/.test(nextLine) ||
          /^\*\*(.+?)\*\*:?\s*$/.test(nextLine) ||
          /^\d+[.)]\s+/.test(nextLine) ||
          /^[-*•]\s+/.test(nextLine) ||
          /^>\s+/.test(nextLine);

        if (paragraphLines.length && startsNewBlock) {
          break;
        }

        if (!nextLine) break;

        paragraphLines.push(nextLine);
        index += 1;
      }
      appendParagraph(container, paragraphLines);
    }
  }

  function appendMessage(role, text) {
    if (!text) return null;
    const row = document.createElement("div");
    row.className = "chat-message " + role;

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble " + role;

    if (role === "bot") {
      appendFormattedText(bubble, text);
    } else {
      const paragraph = document.createElement("p");
      paragraph.textContent = String(text).trim();
      bubble.appendChild(paragraph);
    }

    row.appendChild(bubble);
    chatBody.appendChild(row);
    scrollToBottom();
    return bubble;
  }

  function appendBot(text, sources) {
    const bubble = appendMessage("bot", text);
    if (bubble && Array.isArray(sources) && sources.length) {
      bubble.appendChild(renderSources(sources));
      scrollToBottom();
    }
  }

  function appendUser(text) {
    appendMessage("user", text);
  }

  function appendUserWithImage(text, imageSrc) {
    const row = document.createElement("div");
    row.className = "chat-message user";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble user";

    const img = document.createElement("img");
    img.src = imageSrc;
    img.className = "chat-image-thumb";
    img.alt = "Attached screenshot";
    bubble.appendChild(img);

    const paragraph = document.createElement("p");
    paragraph.textContent = String(text).trim();
    bubble.appendChild(paragraph);

    row.appendChild(bubble);
    chatBody.appendChild(row);
    scrollToBottom();
  }

  function renderSources(sources) {
    const details = document.createElement("details");
    details.className = "source-disclosure";

    const summary = document.createElement("summary");
    const summaryLabel = document.createElement("span");
    summaryLabel.textContent = `Show sources (${sources.length})`;
    summary.appendChild(summaryLabel);
    details.appendChild(summary);

    details.addEventListener("toggle", () => {
      summaryLabel.textContent = details.open
        ? `Hide sources (${sources.length})`
        : `Show sources (${sources.length})`;
    });

    const list = document.createElement("div");
    list.className = "source-list";

    sources.forEach((source) => {
      const item = document.createElement("div");
      item.className = "source-item";

      const title = document.createElement("span");
      title.className = "source-title";
      title.textContent = `[${source.citation}] ${source.title || "Untitled source"}`;

      const meta = document.createElement("span");
      meta.className = "source-meta";
      meta.textContent = "MCeLE support source";

      item.appendChild(title);
      item.appendChild(meta);

      if (source.preview) {
        const preview = document.createElement("div");
        preview.className = "source-preview";
        preview.textContent = source.preview;
        item.appendChild(preview);
      }

      list.appendChild(item);
    });

    details.appendChild(list);
    return details;
  }

  function appendTyping() {
    const row = document.createElement("div");
    row.className = "chat-message bot";
    row.dataset.typing = "true";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble bot";

    const typing = document.createElement("span");
    typing.className = "typing";
    typing.setAttribute("aria-label", "Assistant is responding");
    typing.innerHTML = "<span></span><span></span><span></span>";

    bubble.appendChild(typing);
    row.appendChild(bubble);
    chatBody.appendChild(row);
    scrollToBottom();
    return row;
  }

  function setSending(nextValue) {
    isSending = nextValue;
    systemSelect.disabled = nextValue || !sessionId;
    otherCourse.disabled = nextValue;
    btnSupport.disabled = nextValue || !sessionId;
    clarifyPanel.querySelectorAll("button").forEach(button => { button.disabled = nextValue; });
    chatInput.disabled = nextValue;
    chatSend.disabled = nextValue;
    chatImageBtn.disabled = nextValue;
    chatStatus.textContent = nextValue ? "Retrieving sources" : (selectedProfile ? `${selectedProfile.name} · ${selectedProfile.display_role || selectedProfile.role}` : "Select a demo profile");
    profileSelect.disabled = nextValue || !selectedProfile;
    courseSelect.disabled = nextValue || !selectedProfile;
    btnClear.disabled = nextValue || !selectedProfile;
  }

  function toDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function showImagePreview(imageSrc) {
    chatImagePreview.replaceChildren();
    const container = document.createElement("div");
    container.className = "image-preview-container";
    const image = document.createElement("img");
    image.src = imageSrc;
    image.alt = "Attached screenshot";
    image.className = "preview-thumb";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "preview-remove";
    remove.setAttribute("aria-label", "Remove image");
    remove.textContent = "×";
    container.append(image, remove);
    chatImagePreview.appendChild(container);
    chatImagePreview.style.display = "block";
    remove.addEventListener("click", clearImage);
  }

  function clearImage() {
    pendingImage = null;
    pendingImagePreviewSrc = null;
    chatImagePreview.innerHTML = "";
    chatImagePreview.style.display = "none";
    chatImageInput.value = "";
  }

  function showGreeting() {
    if (hasGreeted) return;
    if (!selectedProfile) return;
    hasGreeted = true;
    appendBot(`You are using the ${selectedProfile.display_role || selectedProfile.role} demo profile. Ask a support question and I’ll answer with citations when available.`);
  }

  function openChat() {
    chatPanel.classList.add("open");
    showGreeting();
    chatInput.focus();
  }

  function closeChat() {
    chatPanel.classList.remove("open");
  }

  function clearChat() {
    if (isSending) return;
    resetTicket();
    chatBody.replaceChildren();
    hasGreeted = false;
    clearResolvedContext();
    clearImage();
    showGreeting();
    queuedRequest = null;
    ticketPending = false;
    chatInput.value = "";
    clarifyPanel.hidden = true;
    createSession();
    chatInput.focus();
  }

  async function requestChat(text, image) {
    if (!sessionId) throw new Error("The demo session is not ready yet.");
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message: text,
        course_id: selectedCourseId,
        system_area: selectedSystem,
        ...(image ? { image } : {}),
      })
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.detail || `Request failed with status ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  // The chatbot currently uses one general message for all request failures.
  function appendRequestError(error) {
    const message = error && error.status === 429
      ? "The assistant is handling another request. Please wait a moment and try again."
      : "I could not reach the demo assistant. Please try again in a moment.";
    appendBot(message);
    console.error(error);
  }

  function clearResolvedContext() {
    resolvedContext.replaceChildren();
    resolvedContext.hidden = true;
  }

  function updateResolvedContext(context) {
    clearResolvedContext();
    if (!context || typeof context !== "object") return;
    const bits = [];
    if (context.course_id || context.course_title) bits.push(`Course: ${context.course_id || context.course_title}`);
    if (context.system_area) bits.push(`Current task/system: ${context.system_area}`);
    if (context.delivery_area) bits.push(`Course content: ${context.delivery_area}`);
    if (context.enrollment_area) bits.push(`Enrollment: ${context.enrollment_area}`);
    if (context.discovery_portal) bits.push(`Discovery: ${context.discovery_portal}`);
    if (!bits.length) return;
    resolvedContext.textContent = `Resolved context: ${bits.join(" · ")}`;
    resolvedContext.hidden = false;
  }

  function showSessionError(message) {
    sessionError.textContent = message;
    sessionError.hidden = !message;
  }

  function resetTicket() {
    document.getElementById("ticketForm").reset();
    document.getElementById("ticketEvidence").textContent = "";
    document.getElementById("draftMode").textContent = "";
    document.getElementById("ticketConfirmation").textContent = "";
    document.getElementById("ticketConfirmation").hidden = true;
  }

  function resetTranscript() {
    resetTicket();
    chatBody.replaceChildren();
    hasGreeted = false;
    clearResolvedContext();
    clearImage();
  }

  function populateControls() {
    profileSelect.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose a seeded demo profile…";
    profileSelect.appendChild(placeholder);
    profiles.forEach((profile) => {
      const option = document.createElement("option");
      option.value = profile.id;
      option.textContent = `${profile.name} · ${profile.display_role || profile.role}`;
      profileSelect.appendChild(option);
    });
    courseSelect.replaceChildren();
    const coursePlaceholder = document.createElement("option");
    coursePlaceholder.value = ""; coursePlaceholder.textContent = "Choose a course…";
    courseSelect.append(coursePlaceholder);
    [...courses, "__other__"].forEach(code => {
      const option = document.createElement("option");
      option.value = code; option.textContent = code === "__other__" ? "Course not listed" : code;
      courseSelect.append(option);
    });
    profileSelect.disabled = false;
    courseSelect.disabled = false;
  }

  function updateProfileDescription() {
    if (!selectedProfile) {
      profileDescription.textContent = "";
      return;
    }
    const areas = Array.isArray(selectedProfile.delivery_areas) && selectedProfile.delivery_areas.length
      ? ` Coverage: ${selectedProfile.delivery_areas.join(", ")}.`
      : " No curated support coverage is listed for this profile.";
    profileDescription.textContent = `${selectedProfile.name} simulates ${selectedProfile.display_role || selectedProfile.role}.${areas}`;
  }

  async function createSession() {
    const generation = ++sessionGeneration;
    if (!selectedProfile) return;
    sessionId = null;
    btnSupport.disabled = true;
    systemSelect.disabled = true;
    showSessionError("");
    chatInput.disabled = true;
    chatSend.disabled = true;
    chatImageBtn.disabled = true;
    profileSelect.disabled = true;
    courseSelect.disabled = true;
    btnClear.disabled = true;
    chatStatus.textContent = "Starting demo session…";
    try {
      const response = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: selectedProfile.id, course_id: selectedCourseId })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Session failed with status ${response.status}`);
      if (generation !== sessionGeneration) return;
      sessionId = data.session_id;
      systemSelect.disabled = false;
      btnSupport.disabled = false;
      chatInput.disabled = false;
      chatSend.disabled = false;
      chatImageBtn.disabled = false;
      profileSelect.disabled = false;
      courseSelect.disabled = false;
      btnClear.disabled = false;
      chatStatus.textContent = `${selectedProfile.name} · ${selectedProfile.display_role || selectedProfile.role}`;
      showGreeting();
    } catch (error) {
      if (generation !== sessionGeneration) return;
      profileSelect.disabled = false;
      btnClear.disabled = false;
      showSessionError("The demo session could not be started. Refresh or try selecting the profile again.");
      chatStatus.textContent = "Session unavailable";
      console.error(error);
    }
  }

  async function loadProfiles() {
    try {
      const response = await fetch("/api/profiles");
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !Array.isArray(data.profiles)) throw new Error(data.detail || "Profiles unavailable");
      profiles = data.profiles;
      courses = Array.isArray(data.ticket_courses) ? data.ticket_courses : [];
      if (!profiles.length) throw new Error("No demo profiles available");
      populateControls();
      selectedProfile = null;
      profileSelect.value = "";
      updateProfileDescription();
      chatStatus.textContent = "Choose a demo profile";
      chatInput.disabled = true;
      chatSend.disabled = true;
      chatImageBtn.disabled = true;
      courseSelect.disabled = true;
      btnClear.disabled = true;
    } catch (error) {
      showSessionError("Profiles are unavailable. Refresh the page to try again.");
      chatStatus.textContent = "Profiles unavailable";
      console.error(error);
    }
  }

  async function sendMessage(rawText, queued = null) {
    const text = (rawText || "").trim();
    if (!text || isSending || !sessionId) return;
    showSessionError("");

    if (!queued) {
      queued = {text, image: pendingImage, preview: pendingImagePreviewSrc};
      if (queued.preview) appendUserWithImage(text, queued.preview);
      else appendUser(text);
      clearImage();
    }
    if (!selectedSystem || !selectedCourseId) {
      queuedRequest = queued;
      showClarification();
      return;
    }
    queuedRequest = null;
    clarifyPanel.hidden = true;

    setSending(true);
    const typing = appendTyping();

    const imageToSend = queued.image;
    clearImage();

    try {
      const data = await requestChat(
        text,
        imageToSend
      );

      typing.remove();
      appendBot(data.answer, data.sources);
      updateResolvedContext(data.context);
    } catch (error) {
      typing.remove();
      queuedRequest = queued;
      appendRequestError(error);
    } finally {
      setSending(false);
      chatInput.focus();
    }
  }

  chatFab.addEventListener("click", () => {
    if (chatPanel.classList.contains("open")) {
      closeChat();
    } else {
      openChat();
    }
  });

  chatClose.addEventListener("click", closeChat);
  btnClear.addEventListener("click", clearChat);
  profileSelect.addEventListener("change", () => {
    if (isSending) return;
    selectedProfile = profiles.find((profile) => profile.id === profileSelect.value) || null;
    sessionId = null;
    ++sessionGeneration;
    selectedCourseId = null;
    selectedSystem = null;
    systemSelect.value = "";
    otherCourse.value = "";
    otherCourseRow.hidden = true;
    queuedRequest = null;
    ticketPending = false;
    clarifyPanel.hidden = true;
    ticketPage.hidden = true;
    courseSelect.value = "";
    chatInput.value = "";
    resetTranscript();
    updateProfileDescription();
    if (selectedProfile) createSession();
    else {
      chatInput.disabled = true; chatSend.disabled = true; chatImageBtn.disabled = true;
      courseSelect.disabled = true; systemSelect.disabled = true; btnSupport.disabled = true;
      btnClear.disabled = true; chatStatus.textContent = "Choose a demo profile";
    }
  });
  function updateSelectedCourse() {
    selectedCourseId = courseSelect.value === "__other__"
      ? (otherCourse.value.trim().slice(0, 160) || "Course not listed")
      : (courseSelect.value || null);
    otherCourseRow.hidden = courseSelect.value !== "__other__";
    clearResolvedContext();
  }
  courseSelect.addEventListener("change", () => { updateSelectedCourse(); if (queuedRequest || ticketPending) showClarification(); });
  otherCourse.addEventListener("input", updateSelectedCourse);
  systemSelect.addEventListener("change", () => {
    selectedSystem = systemSelect.value || null;
    clearResolvedContext();
    if (queuedRequest || ticketPending) showClarification();
  });
  function choice(label, action) {
    const button = document.createElement("button");
    button.type = "button"; button.textContent = label;
    button.addEventListener("click", action); clarifyPanel.append(button);
  }
  function showClarification() {
    clarifyPanel.replaceChildren(); clarifyPanel.hidden = false;
    const heading = document.createElement("p"); clarifyPanel.append(heading);
    if (!selectedSystem) {
      heading.textContent = "Which site are you having trouble with?";
      ["MCeLE", "Moodle"].forEach(site => choice(site, () => {
        selectedSystem = site; systemSelect.value = site; showClarification();
      }));
    } else if (!selectedCourseId) {
      heading.textContent = "Which course is this about?";
      [...courses, "__other__"].forEach(code => choice(code === "__other__" ? "Course not listed" : code, () => {
        courseSelect.value = code; updateSelectedCourse();
        if (code === "__other__") {
          heading.textContent = "Enter the course above if known, or continue with Course not listed.";
          clarifyPanel.querySelectorAll("button").forEach(button => button.remove());
          choice("Continue", resumeRequest); otherCourse.focus();
        } else resumeRequest();
      }));
    } else {
      heading.textContent = `${selectedSystem} · ${selectedCourseId}`;
      choice("Continue", resumeRequest);
    }
  }
  function resumeRequest() {
    clarifyPanel.hidden = true;
    if (ticketPending) { ticketPending = false; prepareTicket(); }
    else if (queuedRequest) sendMessage(queuedRequest.text, queuedRequest);
  }
  async function prepareTicket() {
    if (isSending || !sessionId) return;
    if (!selectedSystem || !selectedCourseId) {
      ticketPending = true; showClarification(); return;
    }
    const generation = sessionGeneration;
    showSessionError("");
    setSending(true); chatStatus.textContent = "Preparing your mock ticket…";
    try {
      const response = await fetch("/api/ticket-draft", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({session_id: sessionId, course_id: selectedCourseId,
          system_area: selectedSystem, current_issue: queuedRequest?.text || chatInput.value.trim()})
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Unable to prepare the ticket. Please retry.");
      if (generation !== sessionGeneration) return;
      document.getElementById("ticketUsername").value = data.username;
      document.getElementById("ticketSummary").value = data.summary;
      document.getElementById("ticketCourse").value = data.course;
      document.getElementById("ticketType").value = data.issue_type;
      document.getElementById("ticketDescription").value = data.description;
      document.getElementById("ticketEvidence").textContent = data.reported_details;
      document.getElementById("draftMode").textContent = data.mode === "ai-draft"
        ? "Your AI draft is ready. Review and edit every field before creating the mock ticket."
        : "AI summarization was unavailable. Your reported details are prefilled for review.";
      document.getElementById("ticketConfirmation").hidden = true;
      document.getElementById("ticketForm").hidden = false;
      ticketPage.hidden = false;
      document.querySelector(".demo-shell").hidden = true;
      chatPanel.hidden = true; chatFab.hidden = true;
      history.pushState({mockTicket: true}, "", "#ticket");
      document.getElementById("ticketTitle").focus();
    } catch (error) { showSessionError(error.message); }
    finally { if (generation === sessionGeneration) setSending(false); }
  }
  function closeTicket() {
    ticketPage.hidden = true;
    document.querySelector(".demo-shell").hidden = false;
    chatPanel.hidden = false; chatFab.hidden = false;
    chatInput.focus();
  }
  btnSupport.addEventListener("click", prepareTicket);
  document.getElementById("ticketBack").addEventListener("click", () => { history.back(); });
  window.addEventListener("popstate", closeTicket);
  document.getElementById("ticketForm").addEventListener("submit", event => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const confirmation = document.getElementById("ticketConfirmation");
    confirmation.textContent = "Mock ticket created for this demonstration. Nothing was sent to Jira or the Help Desk. You can return to the conversation or edit this form.";
    confirmation.hidden = false;
    confirmation.scrollIntoView({behavior: "smooth", block: "nearest"});
  });
  supportPanelClose.addEventListener("click", () => {
    setSupportPanelOpen(false);
  });

  chatImageBtn.addEventListener("click", () => chatImageInput.click());

  chatImageInput.addEventListener("change", async () => {
    const file = chatImageInput.files[0];
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      appendBot("Please choose a PNG, JPEG, or WebP screenshot.");
      clearImage();
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      appendBot("That image is larger than 4 MiB. Please choose a smaller screenshot.");
      clearImage();
      return;
    }
    const uploadGeneration = sessionGeneration;
    const imageSrc = await toDataUrl(file);
    if (uploadGeneration !== sessionGeneration || !selectedProfile) return;
    pendingImagePreviewSrc = imageSrc;
    pendingImage = imageSrc.split(",")[1];
    showImagePreview(imageSrc);
  });

  chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = chatInput.value;
    chatInput.value = "";
    sendMessage(value);
  });

  btnSupport.disabled = true;
  loadProfiles();
})();
