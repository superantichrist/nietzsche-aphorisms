import "./styles.css";

const state = {
  quotes: [],
  filtered: [],
  manifest: null,
  current: null,
  work: "all",
  showGerman: localStorage.getItem("showGerman") !== "false",
};

const elements = Object.fromEntries(
  [
    "quote-card", "quote-number", "translation-badge", "quote-korean", "quote-german",
    "german-wrap", "toggle-german", "source-work", "source-location", "source-link",
    "previous", "next", "random", "share", "permalink-status", "open-search",
    "close-search", "search-panel", "search-input", "search-count", "search-results",
    "stat-total", "stat-jgb", "stat-gm", "stat-ac", "stat-gd", "stat-fw",
    "stat-translated", "stat-pending",
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

function applyFilter(work, { keepCurrent = false } = {}) {
  state.work = work;
  state.filtered = work === "all" ? state.quotes : state.quotes.filter((quote) => quote.work === work);
  document.querySelectorAll(".filter").forEach((button) => {
    const active = button.dataset.work === work;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (!keepCurrent || !state.current || !state.filtered.includes(state.current)) {
    showQuote(state.filtered[fnv1a(`${todayKey()}:${work}`) % state.filtered.length]);
  }
}

function locationLabel(quote) {
  const part = quote.partTitleKo || (quote.part === "Vorrede" ? "서문" : quote.part);
  const unnumbered = new Set(["Vorrede", "Nachgesang", "Wahre-Welt", "Hammer", "Gesetz"]);
  const section = unnumbered.has(quote.section) ? "" : ` · §${quote.section}`;
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
  elements["translation-badge"].textContent = translated ? "한국어 번역 초안" : "번역 준비 중";
  elements["translation-badge"].classList.toggle("pending", !translated);
  elements["quote-korean"].textContent = translated ? quote.korean : quote.german;
  elements["quote-korean"].classList.toggle("german-fallback", !translated);
  elements["quote-german"].textContent = quote.german;
  elements["source-work"].textContent = `${quote.workTitleKo} · ${quote.workTitleDe}`;
  elements["source-location"].textContent = locationLabel(quote);
  elements["source-link"].href = quote.sourceUrl;
  elements["quote-card"].setAttribute("aria-busy", "false");
  updateGermanVisibility();

  const url = new URL(window.location.href);
  url.searchParams.set("q", quote.id);
  window.history[historyMode === "push" ? "pushState" : "replaceState"]({ quoteId: quote.id }, "", url);
}

function move(step) {
  const index = Math.max(0, state.filtered.indexOf(state.current));
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
  const text = `${quote.korean || quote.german}\n— 프리드리히 니체, ${quote.workTitleKo} ${locationLabel(quote)}`;
  const url = window.location.href;
  try {
    if (navigator.share) {
      await navigator.share({ title: "오늘의 니체", text, url });
      elements["permalink-status"].textContent = "공유했습니다.";
    } else {
      await navigator.clipboard.writeText(`${text}\n${url}`);
      elements["permalink-status"].textContent = "링크를 복사했습니다.";
    }
  } catch (error) {
    if (error.name !== "AbortError") elements["permalink-status"].textContent = "공유하지 못했습니다.";
  }
  window.setTimeout(() => { elements["permalink-status"].textContent = ""; }, 2200);
}

function openSearch() {
  elements["search-panel"].hidden = false;
  document.body.classList.add("modal-open");
  window.setTimeout(() => elements["search-input"].focus(), 30);
}

function closeSearch() {
  elements["search-panel"].hidden = true;
  document.body.classList.remove("modal-open");
  elements["open-search"].focus();
}

function runSearch(query) {
  const normalized = query.trim().toLocaleLowerCase("de");
  elements["search-results"].replaceChildren();
  if (normalized.length < 2) {
    elements["search-count"].textContent = "두 글자 이상 입력하세요.";
    return;
  }
  const matches = state.quotes.filter((quote) =>
    `${quote.german}\n${quote.korean}\n${quote.workTitleKo}`.toLocaleLowerCase("de").includes(normalized)
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
  document.querySelectorAll(".filter").forEach((button) => button.addEventListener("click", () => applyFilter(button.dataset.work)));
  elements.previous.addEventListener("click", () => move(-1));
  elements.next.addEventListener("click", () => move(1));
  elements.random.addEventListener("click", () => showQuote(randomQuote(), { historyMode: "push" }));
  elements.share.addEventListener("click", shareCurrent);
  elements["toggle-german"].addEventListener("click", () => {
    state.showGerman = !state.showGerman;
    localStorage.setItem("showGerman", String(state.showGerman));
    updateGermanVisibility();
  });
  elements["open-search"].addEventListener("click", openSearch);
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
    if (event.key === "Escape" && !elements["search-panel"].hidden) closeSearch();
    if (/INPUT|TEXTAREA/.test(document.activeElement?.tagName)) return;
    if (event.key === "ArrowLeft") move(-1);
    if (event.key === "ArrowRight") move(1);
  });
  window.addEventListener("popstate", () => {
    const quoteId = new URL(window.location.href).searchParams.get("q");
    const quote = state.quotes.find((item) => item.id === quoteId);
    if (quote) showQuote(quote);
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
    elements["stat-jgb"].textContent = state.manifest.works.jgb.count.toLocaleString("ko-KR");
    elements["stat-gm"].textContent = state.manifest.works.gm.count.toLocaleString("ko-KR");
    elements["stat-ac"].textContent = state.manifest.works.ac.count.toLocaleString("ko-KR");
    elements["stat-gd"].textContent = state.manifest.works.gd.count.toLocaleString("ko-KR");
    elements["stat-fw"].textContent = state.manifest.works.fw.count.toLocaleString("ko-KR");
    elements["stat-translated"].textContent = state.manifest.translatedCount.toLocaleString("ko-KR");
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
