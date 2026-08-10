// 오늘의 니체 — Scriptable widget
// GitHub Pages의 작은 manifest만 확인하고, dataVersion이 바뀔 때만 전체 JSON을 다시 받습니다.

const SITE_URL = "https://superantichrist.github.io/nietzsche-aphorisms/";
const MANIFEST_URL = `${SITE_URL}data/manifest.json`;
const QUOTES_URL = `${SITE_URL}data/quotes.json`;
const WORK_FILTER = "all"; // "all" | "jgb" | "gm" | "ac" | "gd" | "fw"
const REQUEST_TIMEOUT_SECONDS = 12;

const fm = FileManager.local();
const cacheDirectory = fm.joinPath(fm.documentsDirectory(), "NietzscheToday");
const quotesCachePath = fm.joinPath(cacheDirectory, "quotes-v1.json");
const manifestCachePath = fm.joinPath(cacheDirectory, "manifest-v1.json");

if (!fm.fileExists(cacheDirectory)) {
  fm.createDirectory(cacheDirectory, true);
}

const EMERGENCY_QUOTES = [
  {
    id: "emergency-jgb-146a",
    work: "jgb",
    workTitleKo: "선악의 저편",
    part: "IV",
    section: "146",
    paragraph: 0,
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

function validQuotes(value) {
  return Array.isArray(value)
    && value.length > 100
    && value.every((quote) => quote && typeof quote.id === "string" && typeof quote.german === "string");
}

async function loadQuotes() {
  let cachedQuotes = readJSON(quotesCachePath);
  const cachedManifest = readJSON(manifestCachePath);
  let remoteManifest = null;

  try {
    remoteManifest = await requestJSON(MANIFEST_URL);
  } catch (error) {
    console.log(`Manifest request failed; using cache: ${error}`);
  }

  const remoteVersion = remoteManifest && (remoteManifest.dataVersion || remoteManifest.corpusVersion);
  const cachedVersion = cachedManifest && (cachedManifest.dataVersion || cachedManifest.corpusVersion);
  const needsDownload = !validQuotes(cachedQuotes) || (remoteVersion && remoteVersion !== cachedVersion);

  if (needsDownload) {
    try {
      const downloaded = await requestJSON(QUOTES_URL);
      if (!validQuotes(downloaded)) throw new Error("Downloaded corpus did not pass validation");
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

  if (validQuotes(cachedQuotes)) return cachedQuotes;
  console.log("No usable cache; using the embedded emergency set.");
  return EMERGENCY_QUOTES;
}

function fiveMinuteSlot(date) {
  return Math.floor(date.getTime() / (5 * 60 * 1000));
}

function quoteForDate(date, quotes) {
  let x = (fiveMinuteSlot(date) ^ 0x4e494554) >>> 0;
  x ^= x << 13;
  x ^= x >>> 17;
  x ^= x << 5;
  return quotes[(x >>> 0) % quotes.length];
}

function sourceLabel(quote) {
  const titles = {
    jgb: "선악의 저편",
    gm: "도덕의 계보",
    ac: "안티크리스트",
    gd: "우상의 황혼",
    fw: "즐거운 학문",
  };
  const part = quote.partTitleKo || (quote.part === "Vorrede" ? "서문" : quote.part);
  const unnumbered = ["Vorrede", "Nachgesang", "Wahre-Welt", "Hammer", "Gesetz"];
  const section = unnumbered.includes(quote.section) ? "" : ` §${quote.section}`;
  return `${quote.workTitleKo || titles[quote.work] || quote.work} · ${part}${section}`;
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
  addText(header, "오늘의 니체", Font.semiboldSystemFont(isSmall ? 11 : 12), ivory, 1, 0.8);
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
    addText(widget, hasKorean ? "독일어 원문 · 직접 번역 초안" : "독일어 원문 · 번역 준비 중", Font.systemFont(8), muted, 1, 0.8);
  }

  const nextRefresh = new Date(Date.now() + 5 * 60 * 1000);
  widget.refreshAfterDate = nextRefresh;
  return widget;
}

let quotes = await loadQuotes();
if (["jgb", "gm", "ac", "gd", "fw"].includes(WORK_FILTER)) {
  const filtered = quotes.filter((quote) => quote.work === WORK_FILTER);
  if (filtered.length) quotes = filtered;
}

const selected = quoteForDate(new Date(), quotes);
const widget = makeWidget(selected);
Script.setWidget(widget);

if (!config.runsInWidget) {
  if ((config.widgetFamily || "medium") === "small") await widget.presentSmall();
  else if ((config.widgetFamily || "medium") === "large") await widget.presentLarge();
  else await widget.presentMedium();
}

Script.complete();
