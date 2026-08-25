import "./styles.css";

const state = {
  quotes: [],
  filtered: [],
  manifest: null,
  current: null,
  filter: "all",
  tocWork: "jgb",
  showGerman: localStorage.getItem("showGerman") !== "false",
};

const WORK_ORDER = ["jgb", "gm", "ac", "gd", "fw", "za", "eh", "nf", "pp"];
const UNNUMBERED_SECTIONS = new Set(["Vorrede", "Nachgesang", "Wahre-Welt", "Hammer", "Gesetz"]);
const SECTION_LABELS = {
  Vorrede: "서문",
  Nachgesang: "후가",
  "Wahre-Welt": "‘참된 세계’가 마침내 우화가 된 과정",
  Hammer: "망치가 말하다",
  Gesetz: "그리스도교에 반대하는 법",
};

const elements = Object.fromEntries(
  [
    "quote-card", "quote-number", "translation-badge", "quote-korean", "quote-german",
    "german-wrap", "toggle-german", "source-work", "source-location", "source-edition", "source-link",
    "footnotes-wrap", "footnotes", "previous", "next", "random", "copy-quote",
    "copy-question", "share", "permalink-status", "open-search", "open-toc",
    "open-current-toc", "close-toc", "toc-panel", "toc-works", "toc-summary", "toc-content",
    "close-search", "search-panel", "search-input", "search-count", "search-results",
    "stat-total", "stat-author-nietzsche", "stat-author-schopenhauer",
    "stat-jgb", "stat-gm", "stat-ac", "stat-gd", "stat-fw", "stat-za", "stat-eh", "stat-nf", "stat-pp",
    "stat-translated", "stat-reviewed", "stat-pending",
  ].map((id) => [id, document.getElementById(id)])
);

function fnv1a(text) {
  let hash = 0x811c9dc5;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

function todayKey() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function setFilter(filter) {
  state.filter = filter;
  const author = filter.startsWith("author:") ? filter.slice("author:".length) : "";
  state.filtered = filter === "all"
    ? state.quotes
    : author
      ? state.quotes.filter((quote) => quote.author === author)
      : state.quotes.filter((quote) => quote.work === filter);
  document.querySelectorAll(".filter").forEach((button) => {
    const active = button.dataset.filter === filter;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function applyFilter(filter, { keepCurrent = false } = {}) {
  setFilter(filter);
  if (!keepCurrent || !state.current || !state.filtered.includes(state.current)) {
    showQuote(state.filtered[fnv1a(`${todayKey()}:${filter}`) % state.filtered.length]);
  }
}

function locationLabel(quote) {
  const part = quote.partTitleKo || (quote.part === "Vorrede" ? "서문" : quote.part);
  const section = quote.sectionLabel
    ? ` · ${quote.sectionLabel}`
    : UNNUMBERED_SECTIONS.has(quote.section) ? "" : ` · §${quote.section}`;
  const title = quote.sectionTitleDe ? ` · ${quote.sectionTitleDe}` : "";
  const paragraph = Number.isInteger(quote.paragraph) ? quote.paragraph : 0;
  const sentenceIndex = Number.isInteger(quote.sentence) ? quote.sentence : 0;
  const position = quote.paragraphCount === 1
    ? `구절 ${sentenceIndex + 1}`
    : `문단 ${paragraph + 1} · 문장 ${sentenceIndex + 1}`;
  return `${part}${section}${title} · ${position}`;
}

function updateGermanVisibility() {
  const hasSeparateKorean = Boolean(state.current?.korean);
  elements["german-wrap"].hidden = !hasSeparateKorean;
  if (!hasSeparateKorean) return;
  const visible = state.showGerman || !hasSeparateKorean;
  elements["quote-german"].hidden = !visible;
  elements["german-wrap"].classList.toggle("collapsed", !visible);
  elements["toggle-german"].textContent = visible ? "원문 숨기기" : "원문 보기";
  elements["toggle-german"].setAttribute("aria-expanded", String(visible));
}

function showQuote(quote, { historyMode = "replace" } = {}) {
  if (!quote) return;
  state.current = quote;
  const globalIndex = state.quotes.indexOf(quote) + 1;
  const translated = Boolean(quote.korean);

  elements["quote-number"].textContent = `ARCHIVE · ${String(globalIndex).padStart(4, "0")}`;
  elements["translation-badge"].textContent = quote.translationStatus === "reviewed"
    ? "감수 완료"
    : translated ? "한국어 번역 초안" : "번역 준비 중";
  elements["translation-badge"].classList.toggle("pending", !translated);
  elements["quote-korean"].textContent = translated ? quote.korean : quote.german;
  elements["quote-korean"].classList.toggle("german-fallback", !translated);
  elements["quote-german"].textContent = quote.german;
  elements["source-work"].textContent = `${quote.authorNameKo} · ${quote.workTitleKo} · ${quote.workTitleDe}`;
  elements["source-location"].textContent = locationLabel(quote);
  elements["source-edition"].textContent = [
    quote.edition,
    quote.editor ? `편집 ${quote.editor}` : "",
    quote.transcriptionStatus,
  ].filter(Boolean).join(" · ");
  elements["source-link"].href = quote.sourceUrl;
  const footnotes = Array.isArray(quote.footnotes) ? quote.footnotes : [];
  elements.footnotes.replaceChildren();
  footnotes.forEach((footnote) => {
    const item = document.createElement("li");
    const label = document.createElement("strong");
    const text = document.createElement("span");
    label.textContent = footnote.label;
    text.textContent = footnote.text;
    item.append(label, text);
    elements.footnotes.append(item);
  });
  elements["footnotes-wrap"].hidden = footnotes.length === 0;
  elements["quote-card"].setAttribute("aria-busy", "false");
  updateGermanVisibility();

  const url = new URL(window.location.href);
  url.searchParams.set("q", quote.id);
  if (historyMode !== "none") {
    window.history[historyMode === "push" ? "pushState" : "replaceState"](
      { quoteId: quote.id, filter: state.filter },
      "",
      url,
    );
  }
}

function footnoteText(quote) {
  const footnotes = Array.isArray(quote.footnotes) ? quote.footnotes : [];
  if (!footnotes.length) return "";
  return `\n\n[각주]\n${footnotes.map((note, index) => `${index + 1}. ${note.label}: ${note.text}`).join("\n")}`;
}

function quoteContext(quote) {
  const edition = [quote.edition, quote.editor ? `편집 ${quote.editor}` : ""].filter(Boolean).join(" · ");
  return `[한국어 번역]\n${quote.korean || "(미번역)"}\n\n[독일어 원문]\n${quote.german}\n\n[출전]\n${quote.authorNameKo}, 《${quote.workTitleKo}》 ${locationLabel(quote)}\n${edition}${footnoteText(quote)}\n\n[영구 링크]\n${window.location.href}`;
}

async function writeClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Clipboard unavailable");
}

function showUtilityStatus(message) {
  window.clearTimeout(showUtilityStatus.timer);
  elements["permalink-status"].textContent = message;
  showUtilityStatus.timer = window.setTimeout(() => {
    elements["permalink-status"].textContent = "";
  }, 2400);
}

async function copyCurrent(questionMode = false) {
  const quote = state.current;
  if (!quote) return;
  const context = quoteContext(quote);
  const text = questionMode
    ? `다음 ${quote.authorNameKo} 구절을 독일어 원문과 작품의 문맥을 기준으로 검토하고 설명해 주세요. 번역의 뉘앙스, 핵심 개념, 필요한 역사·문헌 배경도 구분해서 알려 주세요.\n\n${context}\n\n[추가 질문]\n`
    : context;
  try {
    await writeClipboard(text);
    showUtilityStatus(questionMode ? "질문용 내용과 원문을 복사했습니다." : "번역과 원문을 복사했습니다.");
  } catch (error) {
    showUtilityStatus("복사하지 못했습니다.");
  }
}

function move(step) {
  if (!state.filtered.length) return;
  let index = state.filtered.indexOf(state.current);
  if (index < 0) {
    setFilter("all");
    index = state.filtered.indexOf(state.current);
  }
  const nextIndex = (index + step + state.filtered.length) % state.filtered.length;
  showQuote(state.filtered[nextIndex], { historyMode: "push" });
}

function randomQuote() {
  if (state.filtered.length < 2) return state.filtered[0];
  const currentIndex = state.filtered.indexOf(state.current);
  const values = new Uint32Array(1);
  crypto.getRandomValues(values);
  let index = values[0] % state.filtered.length;
  if (index === currentIndex) index = (index + 1) % state.filtered.length;
  return state.filtered[index];
}

async function shareCurrent() {
  const quote = state.current;
  if (!quote) return;
  const text = quoteContext(quote);
  const url = window.location.href;
  try {
    if (navigator.share) {
      await navigator.share({ title: "오늘의 문장", text, url });
      elements["permalink-status"].textContent = "공유했습니다.";
    } else {
      await writeClipboard(text);
      showUtilityStatus("번역과 원문을 복사했습니다.");
    }
  } catch (error) {
    if (error.name !== "AbortError") showUtilityStatus("공유하지 못했습니다.");
  }
}

function sectionHeading(quote) {
  const base = quote.sectionLabel || (UNNUMBERED_SECTIONS.has(quote.section)
    ? (SECTION_LABELS[quote.section] || quote.section)
    : `§${quote.section}`);
  return quote.sectionTitleDe ? `${base} · ${quote.sectionTitleDe}` : base;
}

function sameSection(left, right) {
  return Boolean(left && right)
    && left.work === right.work
    && left.part === right.part
    && left.section === right.section;
}

function tocGroups(work) {
  const parts = new Map();
  state.quotes.filter((quote) => quote.work === work).forEach((quote) => {
    if (!parts.has(quote.part)) {
      parts.set(quote.part, {
        key: quote.part,
        titleKo: quote.partTitleKo || (quote.part === "Vorrede" ? "서문" : quote.part),
        titleDe: quote.partTitleDe || "",
        sections: new Map(),
      });
    }
    const part = parts.get(quote.part);
    if (!part.sections.has(quote.section)) {
      part.sections.set(quote.section, { first: quote, count: 0 });
    }
    part.sections.get(quote.section).count += 1;
  });
  return [...parts.values()].map((part) => ({ ...part, sections: [...part.sections.values()] }));
}

function renderToc(work) {
  state.tocWork = work;
  elements["toc-works"].replaceChildren();
  WORK_ORDER.forEach((workKey) => {
    const first = state.quotes.find((quote) => quote.work === workKey);
    if (!first) return;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = first.workTitleKo;
    button.classList.toggle("active", workKey === work);
    button.setAttribute("aria-pressed", String(workKey === work));
    button.addEventListener("click", () => renderToc(workKey));
    elements["toc-works"].append(button);
  });

  const groups = tocGroups(work);
  const sectionCount = groups.reduce((total, part) => total + part.sections.length, 0);
  const quoteCount = groups.reduce(
    (total, part) => total + part.sections.reduce((subtotal, section) => subtotal + section.count, 0),
    0
  );
  const firstQuote = groups[0]?.sections[0]?.first;
  elements["toc-summary"].textContent = firstQuote
    ? `${firstQuote.workTitleKo} · ${sectionCount.toLocaleString("ko-KR")}개 절 · ${quoteCount.toLocaleString("ko-KR")}개 구절`
    : "목차가 없습니다.";

  elements["toc-content"].replaceChildren();
  const fragment = document.createDocumentFragment();
  const lazyParts = groups.length > 20;
  groups.forEach((part, partIndex) => {
    const section = document.createElement("details");
    section.className = "toc-part";
    const activePart = part.sections.some((item) => sameSection(item.first, state.current));
    section.open = !lazyParts || activePart || (state.current?.work !== work && partIndex === 0);
    const heading = document.createElement("summary");
    heading.className = "toc-part-heading";
    const copy = document.createElement("span");
    copy.className = "toc-part-copy";
    const title = document.createElement("strong");
    title.textContent = part.titleKo;
    copy.append(title);
    if (part.titleDe && part.titleDe !== part.titleKo) {
      const original = document.createElement("small");
      original.textContent = part.titleDe;
      copy.append(original);
    }
    const partCount = document.createElement("span");
    partCount.className = "toc-part-count";
    partCount.textContent = `${part.sections.length.toLocaleString("ko-KR")}개 절`;
    heading.append(copy, partCount);
    const list = document.createElement("div");
    list.className = "toc-sections";
    const renderPartSections = () => {
      if (list.dataset.rendered) return;
      part.sections.forEach((item) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "toc-section";
        const active = sameSection(item.first, state.current);
        button.classList.toggle("current", active);
        if (active) button.setAttribute("aria-current", "location");
        const label = document.createElement("strong");
        label.textContent = sectionHeading(item.first);
        const count = document.createElement("span");
        count.textContent = `${item.count.toLocaleString("ko-KR")}개`;
        button.append(label, count);
        button.addEventListener("click", () => {
          setFilter(work);
          showQuote(item.first, { historyMode: "push" });
          closeToc(false);
          elements["quote-card"].scrollIntoView({ behavior: "smooth", block: "center" });
        });
        list.append(button);
      });
      list.dataset.rendered = "true";
    };
    if (section.open) renderPartSections();
    section.addEventListener("toggle", () => {
      if (section.open) renderPartSections();
    });
    section.append(heading, list);
    fragment.append(section);
  });
  elements["toc-content"].append(fragment);
}

function syncModalState() {
  const open = !elements["search-panel"].hidden || !elements["toc-panel"].hidden;
  document.body.classList.toggle("modal-open", open);
}

function openToc() {
  if (!state.quotes.length) {
    showUtilityStatus("목차를 불러오는 중입니다.");
    return;
  }
  if (!elements["search-panel"].hidden) closeSearch(false);
  const work = state.current?.work || (WORK_ORDER.includes(state.filter) ? state.filter : state.tocWork);
  renderToc(work);
  elements["toc-panel"].hidden = false;
  syncModalState();
  window.setTimeout(() => {
    elements["close-toc"].focus();
    elements["toc-content"].querySelector(".toc-section.current")?.scrollIntoView({ block: "center" });
  }, 30);
}

function closeToc(restoreFocus = true) {
  elements["toc-panel"].hidden = true;
  syncModalState();
  if (restoreFocus) elements["open-toc"].focus();
}

function openSearch() {
  if (!elements["toc-panel"].hidden) closeToc(false);
  elements["search-panel"].hidden = false;
  syncModalState();
  window.setTimeout(() => elements["search-input"].focus(), 30);
}

function closeSearch(restoreFocus = true) {
  elements["search-panel"].hidden = true;
  syncModalState();
  if (restoreFocus) elements["open-search"].focus();
}

function runSearch(query) {
  const normalized = query.trim().toLocaleLowerCase("de");
  elements["search-results"].replaceChildren();
  if (normalized.length < 2) {
    elements["search-count"].textContent = "두 글자 이상 입력하세요.";
    return;
  }
  const matches = state.quotes.filter((quote) =>
    `${quote.german}\n${quote.korean}\n${quote.authorNameKo}\n${quote.authorNameDe}\n${quote.workTitleKo}`
      .toLocaleLowerCase("de")
      .includes(normalized)
  );
  elements["search-count"].textContent = `${matches.length.toLocaleString("ko-KR")}개 구절 · 상위 50개 표시`;
  const fragment = document.createDocumentFragment();
  matches.slice(0, 50).forEach((quote) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "search-result";
    const meta = document.createElement("span");
    meta.textContent = `${quote.workTitleKo} · ${locationLabel(quote)}`;
    const text = document.createElement("strong");
    text.textContent = quote.korean || quote.german;
    button.append(meta, text);
    button.addEventListener("click", () => {
      applyFilter("all", { keepCurrent: true });
      showQuote(quote, { historyMode: "push" });
      closeSearch();
      elements["quote-card"].scrollIntoView({ behavior: "smooth", block: "center" });
    });
    fragment.append(button);
  });
  elements["search-results"].append(fragment);
}

function bindEvents() {
  document.querySelectorAll(".filter").forEach((button) => button.addEventListener("click", () => applyFilter(button.dataset.filter)));
  elements.previous.addEventListener("click", () => move(-1));
  elements.next.addEventListener("click", () => move(1));
  elements.random.addEventListener("click", () => showQuote(randomQuote(), { historyMode: "push" }));
  elements["copy-quote"].addEventListener("click", () => copyCurrent(false));
  elements["copy-question"].addEventListener("click", () => copyCurrent(true));
  elements.share.addEventListener("click", shareCurrent);
  elements["toggle-german"].addEventListener("click", () => {
    state.showGerman = !state.showGerman;
    localStorage.setItem("showGerman", String(state.showGerman));
    updateGermanVisibility();
  });
  elements["open-search"].addEventListener("click", openSearch);
  elements["open-toc"].addEventListener("click", openToc);
  elements["open-current-toc"].addEventListener("click", openToc);
  elements["close-toc"].addEventListener("click", () => closeToc());
  elements["toc-panel"].addEventListener("click", (event) => {
    if (event.target === elements["toc-panel"]) closeToc();
  });
  elements["close-search"].addEventListener("click", closeSearch);
  elements["search-panel"].addEventListener("click", (event) => {
    if (event.target === elements["search-panel"]) closeSearch();
  });
  let searchTimer;
  elements["search-input"].addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => runSearch(event.target.value), 130);
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!elements["toc-panel"].hidden) closeToc();
      else if (!elements["search-panel"].hidden) closeSearch();
    }
    if (/INPUT|TEXTAREA/.test(document.activeElement?.tagName)) return;
    if (event.key === "ArrowLeft") move(-1);
    if (event.key === "ArrowRight") move(1);
  });
  window.addEventListener("popstate", (event) => {
    const quoteId = new URL(window.location.href).searchParams.get("q");
    const quote = state.quotes.find((item) => item.id === quoteId);
    if (!quote) return;
    const historyFilter = event.state?.filter;
    const knownFilter = historyFilter === "all"
      || WORK_ORDER.includes(historyFilter)
      || historyFilter === "author:nietzsche"
      || historyFilter === "author:schopenhauer";
    if (knownFilter) setFilter(historyFilter);
    else if (!state.filtered.includes(quote)) setFilter("all");
    showQuote(quote, { historyMode: "none" });
  });
}

async function init() {
  bindEvents();
  try {
    const [quotesResponse, manifestResponse] = await Promise.all([
      fetch("./data/quotes.json"),
      fetch("./data/manifest.json"),
    ]);
    if (!quotesResponse.ok || !manifestResponse.ok) throw new Error("Corpus request failed");
    [state.quotes, state.manifest] = await Promise.all([quotesResponse.json(), manifestResponse.json()]);
    state.filtered = state.quotes;
    elements["stat-total"].textContent = state.manifest.quoteCount.toLocaleString("ko-KR");
    elements["stat-author-nietzsche"].textContent = state.manifest.authors.nietzsche.count.toLocaleString("ko-KR");
    elements["stat-author-schopenhauer"].textContent = state.manifest.authors.schopenhauer.count.toLocaleString("ko-KR");
    elements["stat-jgb"].textContent = state.manifest.works.jgb.count.toLocaleString("ko-KR");
    elements["stat-gm"].textContent = state.manifest.works.gm.count.toLocaleString("ko-KR");
    elements["stat-ac"].textContent = state.manifest.works.ac.count.toLocaleString("ko-KR");
    elements["stat-gd"].textContent = state.manifest.works.gd.count.toLocaleString("ko-KR");
    elements["stat-fw"].textContent = state.manifest.works.fw.count.toLocaleString("ko-KR");
    elements["stat-za"].textContent = state.manifest.works.za.count.toLocaleString("ko-KR");
    elements["stat-eh"].textContent = state.manifest.works.eh.count.toLocaleString("ko-KR");
    elements["stat-nf"].textContent = state.manifest.works.nf.count.toLocaleString("ko-KR");
    elements["stat-pp"].textContent = state.manifest.works.pp.count.toLocaleString("ko-KR");
    elements["stat-translated"].textContent = state.manifest.translatedCount.toLocaleString("ko-KR");
    elements["stat-reviewed"].textContent = state.manifest.reviewedCount.toLocaleString("ko-KR");
    elements["stat-pending"].textContent = state.manifest.pendingTranslationCount.toLocaleString("ko-KR");

    const requestedId = new URL(window.location.href).searchParams.get("q");
    const requested = requestedId && state.quotes.find((quote) => quote.id === requestedId);
    applyFilter("all", { keepCurrent: true });
    showQuote(requested || state.quotes[fnv1a(todayKey()) % state.quotes.length]);
  } catch (error) {
    console.error(error);
    elements["quote-card"].setAttribute("aria-busy", "false");
    elements["translation-badge"].textContent = "연결 오류";
    elements["quote-korean"].textContent = "구절 데이터를 불러오지 못했습니다. 잠시 뒤 다시 시도해 주세요.";
  }
}

init();
