// 오늘의 문장 — Scriptable widget
// GitHub Pages의 작은 manifest를 확인하고, 선택된 구절이 든 조각만 내려받아 캐시합니다.

const SITE_URL = "https://superantichrist.github.io/nietzsche-aphorisms/";
const MANIFEST_URL = `${SITE_URL}data/manifest.json`;
const WIDGET_DATA_URL = `${SITE_URL}data/widget.json`;
const WORK_FILTER = "all"; // "all" | "nietzsche" | "schopenhauer" | 작품 키(jgb, gm, ..., pp)
const REQUEST_TIMEOUT_SECONDS = 12;
const VALID_WORKS = ["jgb", "gm", "ac", "gd", "fw", "za", "eh", "nf", "pp"];
const VALID_AUTHORS = ["nietzsche", "schopenhauer"];
const WORK_AUTHORS = {
  jgb: "nietzsche", gm: "nietzsche", ac: "nietzsche", gd: "nietzsche",
  fw: "nietzsche", za: "nietzsche", eh: "nietzsche", nf: "nietzsche",
  pp: "schopenhauer",
};

const fm = FileManager.local();
const cacheDirectory = fm.joinPath(fm.documentsDirectory(), "NietzscheToday");
const quotesCachePath = fm.joinPath(cacheDirectory, "quotes-v1.json");
const manifestCachePath = fm.joinPath(cacheDirectory, "manifest-v2.json");
const shardCacheDirectory = fm.joinPath(cacheDirectory, "shards-v1");
const lastQuotesCachePath = fm.joinPath(cacheDirectory, "last-quotes-v1.json");

if (!fm.fileExists(cacheDirectory)) {
  fm.createDirectory(cacheDirectory, true);
}
if (!fm.fileExists(shardCacheDirectory)) {
  fm.createDirectory(shardCacheDirectory, true);
}

const EMERGENCY_QUOTES = [
  {
    id: "emergency-jgb-146a",
    work: "jgb",
    workTitleKo: "선악의 저편",
    part: "IV",
    section: "146",
    paragraph: 0,
    paragraphCount: 1,
    sentence: 0,
    german: "Wer mit Ungeheuern kämpft, mag zusehn, dass er nicht dabei zum Ungeheuer wird.",
    korean: "괴물과 싸우는 사람은 그 싸움 속에서 자신도 괴물이 되지 않도록 살펴야 한다.",
  },
  {
    id: "emergency-jgb-146b",
    work: "jgb",
    workTitleKo: "선악의 저편",
    part: "IV",
    section: "146",
    paragraph: 0,
    paragraphCount: 1,
    sentence: 1,
    german: "Und wenn du lange in einen Abgrund blickst, blickt der Abgrund auch in dich hinein.",
    korean: "네가 오랫동안 심연을 들여다보면, 심연 또한 네 안을 들여다본다.",
  },
  {
    id: "emergency-gm-1",
    work: "gm",
    workTitleKo: "도덕의 계보",
    part: "Vorrede",
    section: "1",
    paragraph: 0,
    paragraphCount: 1,
    sentence: 0,
    german: "Wir sind uns unbekannt, wir Erkennenden, wir selbst uns selbst: das hat seinen guten Grund.",
    korean: "우리는 우리 자신에게 낯설다. 인식하는 우리조차 자기 자신을 알지 못한다. 그럴 만한 이유가 있다.",
  },
  {
    id: "emergency-gm-28",
    work: "gm",
    workTitleKo: "도덕의 계보",
    part: "III",
    section: "28",
    paragraph: 0,
    paragraphCount: 1,
    sentence: 0,
    german: "Lieber will noch der Mensch das Nichts wollen, als nicht wollen.",
    korean: "인간은 아무것도 의지하지 않기보다는 차라리 무를 의지하려 한다.",
  },
];

function readJSON(path) {
  if (!fm.fileExists(path)) return null;
  try {
    return JSON.parse(fm.readString(path));
  } catch (error) {
    console.log(`Cache parse failed: ${error}`);
    return null;
  }
}

function writeJSON(path, value) {
  fm.writeString(path, JSON.stringify(value));
}

async function requestJSON(url) {
  const request = new Request(url);
  request.timeoutInterval = REQUEST_TIMEOUT_SECONDS;
  request.headers = { "Cache-Control": "no-cache" };
  return await request.loadJSON();
}

function validQuote(value) {
  return Boolean(
    value
    && typeof value.id === "string"
    && typeof value.work === "string"
    && typeof value.german === "string"
  );
}

function validQuotes(value, minimumLength = 1) {
  return Array.isArray(value)
    && value.length >= minimumLength
    && value.every(validQuote);
}

function manifestVersion(manifest) {
  return manifest && (manifest.dataVersion || manifest.corpusVersion);
}

function validShardCatalog(manifest) {
  const catalog = manifest && manifest.widgetShards;
  return Boolean(
    manifestVersion(manifest)
    && catalog
    && catalog.schemaVersion === 1
    && typeof catalog.basePath === "string"
    && Number.isInteger(catalog.shardSize)
    && catalog.shardSize > 0
    && Number.isInteger(catalog.totalCount)
    && catalog.totalCount > 0
    && Array.isArray(catalog.workOrder)
    && catalog.workOrder.length > 0
    && catalog.works
  );
}

async function loadLegacyQuotes(remoteManifest, cachedManifest) {
  let cachedQuotes = readJSON(quotesCachePath);
  const remoteVersion = manifestVersion(remoteManifest);
  const cachedVersion = manifestVersion(cachedManifest);
  const needsDownload = !validQuotes(cachedQuotes, 100) || (remoteVersion && remoteVersion !== cachedVersion);

  if (needsDownload) {
    try {
      const downloaded = await requestJSON(WIDGET_DATA_URL);
      if (!validQuotes(downloaded, 100)) throw new Error("Downloaded corpus did not pass validation");
      writeJSON(quotesCachePath, downloaded);
      if (remoteManifest) writeJSON(manifestCachePath, remoteManifest);
      cachedQuotes = downloaded;
      console.log(`Cached ${downloaded.length} quotes (${remoteVersion || "unversioned"}).`);
    } catch (error) {
      console.log(`Quote download failed; using previous cache: ${error}`);
    }
  } else if (remoteManifest && remoteVersion) {
    writeJSON(manifestCachePath, remoteManifest);
  }

  if (validQuotes(cachedQuotes, 100)) return cachedQuotes;
  console.log("No usable cache; using the embedded emergency set.");
  return EMERGENCY_QUOTES;
}

function fiveMinuteSlot(date) {
  return Math.floor(date.getTime() / (5 * 60 * 1000));
}

function slotHash(date) {
  let x = (fiveMinuteSlot(date) ^ 0x4e494554) >>> 0;
  x ^= x << 13;
  x ^= x >>> 17;
  x ^= x << 5;
  return x >>> 0;
}

function quoteForDate(date, quotes) {
  return quotes[slotHash(date) % quotes.length];
}

function shardTarget(date, manifest) {
  const catalog = manifest.widgetShards;
  const filteredWork = VALID_WORKS.includes(WORK_FILTER) ? WORK_FILTER : null;
  const filteredAuthor = VALID_AUTHORS.includes(WORK_FILTER) ? WORK_FILTER : null;
  let work = filteredWork;
  let localIndex;

  if (work) {
    const descriptor = catalog.works[work];
    if (!descriptor || !Number.isInteger(descriptor.count) || descriptor.count < 1) return null;
    localIndex = slotHash(date) % descriptor.count;
  } else {
    const candidates = filteredAuthor
      ? catalog.workOrder.filter((candidate) => WORK_AUTHORS[candidate] === filteredAuthor)
      : catalog.workOrder;
    const totalCount = candidates.reduce(
      (total, candidate) => total + (catalog.works[candidate]?.count || 0),
      0
    );
    if (totalCount < 1) return null;
    let globalIndex = slotHash(date) % totalCount;
    for (const candidate of candidates) {
      const descriptor = catalog.works[candidate];
      if (!descriptor || !Number.isInteger(descriptor.count)) return null;
      if (globalIndex < descriptor.count) {
        work = candidate;
        localIndex = globalIndex;
        break;
      }
      globalIndex -= descriptor.count;
    }
  }

  if (!work || !Number.isInteger(localIndex)) return null;
  const shardIndex = Math.floor(localIndex / catalog.shardSize);
  return {
    work,
    shardIndex,
    position: localIndex % catalog.shardSize,
    url: `${SITE_URL}${catalog.basePath}/${work}-${String(shardIndex).padStart(3, "0")}.json`,
  };
}

function lastQuoteKey() {
  return [...VALID_WORKS, ...VALID_AUTHORS].includes(WORK_FILTER) ? WORK_FILTER : "all";
}

function rememberQuote(quote) {
  const remembered = readJSON(lastQuotesCachePath) || {};
  remembered[lastQuoteKey()] = quote;
  writeJSON(lastQuotesCachePath, remembered);
}

function lastRememberedQuote() {
  const remembered = readJSON(lastQuotesCachePath) || {};
  const quote = remembered[lastQuoteKey()];
  return validQuote(quote) ? quote : null;
}

async function loadShardedQuote(date, manifest) {
  const target = shardTarget(date, manifest);
  if (!target) return null;
  const cachePath = fm.joinPath(
    shardCacheDirectory,
    `${target.work}-${String(target.shardIndex).padStart(3, "0")}.json`
  );
  let cached = readJSON(cachePath);
  const version = manifestVersion(manifest);
  const exactCache = cached && cached.dataVersion === version && validQuotes(cached.quotes);

  if (!exactCache) {
    try {
      const downloaded = await requestJSON(target.url);
      if (!validQuotes(downloaded) || !downloaded.every((quote) => quote.work === target.work)) {
        throw new Error("Downloaded shard did not pass validation");
      }
      cached = {
        dataVersion: version,
        corpusVersion: manifest.corpusVersion,
        quotes: downloaded,
      };
      writeJSON(cachePath, cached);
      console.log(`Cached ${target.work} shard ${target.shardIndex} (${downloaded.length} quotes).`);
    } catch (error) {
      console.log(`Shard download failed; using compatible cache: ${error}`);
    }
  }

  const compatibleCache = cached
    && validQuotes(cached.quotes)
    && (cached.dataVersion === version || cached.corpusVersion === manifest.corpusVersion);
  if (!compatibleCache) return null;
  const quote = cached.quotes[target.position];
  if (!validQuote(quote) || quote.work !== target.work) return null;
  rememberQuote(quote);
  return quote;
}

async function selectedQuote(date) {
  const cachedManifest = readJSON(manifestCachePath);
  let remoteManifest = null;
  try {
    remoteManifest = await requestJSON(MANIFEST_URL);
    if (manifestVersion(remoteManifest)) writeJSON(manifestCachePath, remoteManifest);
  } catch (error) {
    console.log(`Manifest request failed; using cache: ${error}`);
  }

  const shardManifest = validShardCatalog(remoteManifest)
    ? remoteManifest
    : validShardCatalog(cachedManifest) ? cachedManifest : null;
  if (shardManifest) {
    const quote = await loadShardedQuote(date, shardManifest);
    if (quote) return quote;
    const remembered = lastRememberedQuote();
    if (remembered) return remembered;
  }

  let quotes = await loadLegacyQuotes(remoteManifest, cachedManifest);
  if (VALID_WORKS.includes(WORK_FILTER)) {
    const filtered = quotes.filter((quote) => quote.work === WORK_FILTER);
    if (filtered.length) quotes = filtered;
  } else if (VALID_AUTHORS.includes(WORK_FILTER)) {
    const filtered = quotes.filter((quote) => (quote.author || WORK_AUTHORS[quote.work]) === WORK_FILTER);
    if (filtered.length) quotes = filtered;
  }
  const quote = quoteForDate(date, quotes);
  if (validQuote(quote)) rememberQuote(quote);
  return quote;
}

function sourceLabel(quote) {
  const titles = {
    jgb: "선악의 저편",
    gm: "도덕의 계보",
    ac: "안티크리스트",
    gd: "우상의 황혼",
    fw: "즐거운 학문",
    za: "차라투스트라는 이렇게 말했다",
    eh: "이 사람을 보라",
    nf: "후기 유고 1885–1888",
    pp: "소품과 부록",
  };
  const part = quote.partTitleKo || (quote.part === "Vorrede" ? "서문" : quote.part);
  const unnumbered = ["Vorrede", "Nachgesang", "Wahre-Welt", "Hammer", "Gesetz"];
  const section = quote.sectionLabel
    ? ` · ${quote.sectionLabel}`
    : unnumbered.includes(quote.section) ? "" : ` §${quote.section}`;
  const authors = { nietzsche: "니체", schopenhauer: "쇼펜하우어" };
  const author = quote.authorNameKo || authors[quote.author || WORK_AUTHORS[quote.work]] || "";
  return `${author ? `${author} · ` : ""}${quote.workTitleKo || titles[quote.work] || quote.work} · ${part}${section}`;
}

function positionLabel(quote) {
  const paragraph = Number.isInteger(quote.paragraph) ? quote.paragraph : 0;
  const sentence = Number.isInteger(quote.sentence) ? quote.sentence : 0;
  const paragraphCount = Number.isInteger(quote.paragraphCount) ? quote.paragraphCount : 1;
  return paragraphCount === 1
    ? `구절 ${sentence + 1}`
    : `문단 ${paragraph + 1} · 문장 ${sentence + 1}`;
}

function addText(stack, value, font, color, lineLimit, scale) {
  const text = stack.addText(value);
  text.font = font;
  text.textColor = color;
  text.lineLimit = lineLimit;
  text.minimumScaleFactor = scale;
  return text;
}

function makeWidget(quote) {
  const widget = new ListWidget();
  const family = config.widgetFamily || "medium";
  const isSmall = family === "small";
  const isLarge = family === "large";
  widget.setPadding(isSmall ? 13 : 16, isSmall ? 13 : 17, isSmall ? 13 : 15, isSmall ? 13 : 17);

  const gradient = new LinearGradient();
  gradient.colors = [new Color("1D1712"), new Color("100D0A")];
  gradient.locations = [0, 1];
  gradient.startPoint = new Point(0, 0);
  gradient.endPoint = new Point(1, 1);
  widget.backgroundGradient = gradient;
  widget.url = `${SITE_URL}?q=${encodeURIComponent(quote.id)}`;

  const ivory = new Color("EEE8DA");
  const muted = new Color("A89D8C");
  const gold = new Color("C9A35C");

  const header = widget.addStack();
  header.centerAlignContent();
  const mark = header.addText("●");
  mark.font = Font.systemFont(7);
  mark.textColor = gold;
  header.addSpacer(6);
  addText(header, "오늘의 문장", Font.semiboldSystemFont(isSmall ? 11 : 12), ivory, 1, 0.8);
  header.addSpacer();
  addText(header, "§", Font.italicSystemFont(15), gold, 1, 1);

  widget.addSpacer(isSmall ? 10 : 13);

  const hasKorean = Boolean(quote.korean && quote.korean.trim());
  const mainText = hasKorean ? quote.korean.trim() : quote.german.trim();
  addText(
    widget,
    mainText,
    isSmall ? Font.semiboldSystemFont(14) : Font.semiboldSystemFont(isLarge ? 21 : 17),
    ivory,
    isSmall ? 6 : isLarge ? 8 : 5,
    isSmall ? 0.62 : 0.68
  );

  if (!isSmall && hasKorean) {
    widget.addSpacer(9);
    addText(widget, quote.german.trim(), Font.italicSystemFont(isLarge ? 12 : 10), muted, isLarge ? 5 : 3, 0.7);
  }

  widget.addSpacer();
  const rule = widget.addStack();
  rule.size = new Size(36, 1);
  rule.backgroundColor = new Color("C9A35C", 0.55);
  widget.addSpacer(7);
  addText(widget, sourceLabel(quote), Font.systemFont(isSmall ? 8 : 9), gold, 1, 0.65);

  if (!isSmall) {
    widget.addSpacer(3);
    addText(widget, positionLabel(quote), Font.systemFont(8), muted, 1, 0.8);
  }

  const nextRefresh = new Date(Date.now() + 5 * 60 * 1000);
  widget.refreshAfterDate = nextRefresh;
  return widget;
}

const selected = await selectedQuote(new Date());
const widget = makeWidget(selected);
Script.setWidget(widget);

if (!config.runsInWidget) {
  if ((config.widgetFamily || "medium") === "small") await widget.presentSmall();
  else if ((config.widgetFamily || "medium") === "large") await widget.presentLarge();
  else await widget.presentMedium();
}

Script.complete();
