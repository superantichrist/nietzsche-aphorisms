# 오늘의 문장

니체와 쇼펜하우어의 독일어 원문을 출전 추적이 가능한 읽기 단위로 나눈 정적 데이터베이스, 모바일 웹, iPhone Scriptable 위젯입니다. 저장소 이름과 기존 Scriptable 파일명에는 이전 명칭이 호환성을 위해 남아 있습니다.

공개 사이트: <https://superantichrist.github.io/nietzsche-aphorisms/>

## 현재 데이터

| 작품 | 구절 수 | 원문 범위 |
|---|---:|---|
| Jenseits von Gut und Böse | 1,717 | 서문, §1–296, §65a, §73a, 후가 |
| Zur Genealogie der Moral | 1,261 | 서문 §1–8, 제1논문 §1–17, 제2논문 §1–25, 제3논문 §1–28 |
| Der Antichrist | 439 | 서문, 본문 §1–62, 부록 |
| Götzen-Dämmerung | 486 | 서문과 11개 본문·부록 단위 전체 |
| Die fröhliche Wissenschaft | 1,492 | 서문, 전주곡, 제1–5권 §1–383, 부록 노래 |
| Also sprach Zarathustra | 3,872 | 제1–4부 전체 |
| Ecce homo | 565 | 머리글, 서문, 14개 장 전체 |
| Nachgelassene Fragmente 1885–1888 | 8,401 | 37개 노트군 전체; 짧은 표제·미완 조각 제외 |
| Parerga und Paralipomena | 6,072 | 1874년 제3판 제1·2권, 제2권 §1–413 및 원판 각주 |
| 합계 | 24,305 | 니체 18,233개, 쇼펜하우어 6,072개 |

현재 24,305개 중 21,550개에 직접 만든 한국어 번역이 있고 그중 5,749개는 감수를 마쳤다. 남은 쇼펜하우어 구절도 장 단위 문맥을 유지해 직접 번역하며 증분으로 추가한다. 한국어는 독일어 원문과 분리된 캐시에서 관리한다. 번역이 붙은 레코드는 가능한 한 ID를 유지하되, 아직 미번역인 구간은 ID 보존보다 원문 완전성·올바른 순서·자연스러운 문단 및 시행 묶음을 우선한다.

모바일 웹에서는 작품 → 부/논문 → 절로 이어지는 목차를 열어 원하는 출전의 첫 구절로 바로 이동할 수 있다. 검색, 작품 필터, 앞뒤 이동, 원문 표시, 복사, 공유, 구절별 영구 링크도 지원한다.

## JSON

- [`data/quotes.json`](data/quotes.json): 두 저자의 전체 코퍼스
- [`data/jgb.json`](data/jgb.json): 《선악의 저편》
- [`data/gm.json`](data/gm.json): 《도덕의 계보》
- [`data/ac.json`](data/ac.json): 《안티크리스트》
- [`data/gd.json`](data/gd.json): 《우상의 황혼》
- [`data/fw.json`](data/fw.json): 《즐거운 학문》
- [`data/za.json`](data/za.json): 《차라투스트라는 이렇게 말했다》
- [`data/eh.json`](data/eh.json): 《이 사람을 보라》
- [`data/nf.json`](data/nf.json): 1885–1888년 후기 유고
- [`data/pp.json`](data/pp.json): 쇼펜하우어 《소품과 부록》 제1·2권
- [`data/widget.json`](data/widget.json): 번역 여부와 무관한 Scriptable 호환용 전체 데이터
- `data/widget-shards/`: Scriptable이 선택된 구절에 필요한 조각만 받는 작품별 분할 데이터
- [`data/manifest.json`](data/manifest.json): 버전, 개수, 파일 크기, SHA-256
- [`data/schema.json`](data/schema.json): 레코드 JSON Schema

```json
{
  "id": "jgb-146-009e0b432b98",
  "author": "nietzsche",
  "authorNameDe": "Friedrich Nietzsche",
  "authorNameKo": "프리드리히 니체",
  "work": "jgb",
  "workTitleDe": "Jenseits von Gut und Böse",
  "workTitleKo": "선악의 저편",
  "part": "IV",
  "section": "146",
  "paragraph": 0,
  "paragraphCount": 1,
  "sentence": 0,
  "german": "Wer mit Ungeheuern kämpft, ...",
  "korean": "괴물과 싸우는 사람은 ..."
}
```

`paragraphCount`가 1이면 화면에 절 안의 `구절 n`을 표시하고, 2 이상이면 `문단 n · 문장 n`을 표시한다. ID는 `work + part + section + paragraph + 정규화한 German`의 SHA-256으로 결정론적으로 만든다. 번역만 다듬을 때에는 ID와 독일어 출전이 변하지 않는다. 다만 원문 누락을 복구하거나 문단·시행 묶음을 바로잡는 파서 수정은 아직 미번역인 레코드의 ID보다 우선한다. `corpusVersion`은 독일어 corpus, `dataVersion`은 한국어와 위치 메타데이터를 포함한 배포 데이터 버전이다.

## 로컬 빌드

Node.js 22와 Python 3.9 이상이 필요하다.

```bash
npm install
npm run check
npm run dev
```

`npm run check`는 원문을 다시 파싱하고 작품별 JSON을 만든 뒤, 24,000개 이상 구절·ID 유일성·아홉 코퍼스의 절과 단편 범위·구절 길이·출전 URL·번역 상태·번역 캐시 대응을 검증한다. 쇼펜하우어 EPUB의 해시, 45개 목차 부, 458개 절, 제2권 § 범위도 함께 확인한다. 기본 번역 캐시는 `translations/ko.json`이며, 배포용 증분은 `translations/overrides/*.json`을 파일명 순서로 병합한다. 빌드는 vendored 원문으로 재현되므로 평소에는 네트워크가 필요 없다.

## 한국어 번역 작업

번역은 [`translations/ko.json`](translations/ko.json)과 증분 override에 ID별로 저장된다. 번역된 레코드는 가능한 한 동일 ID를 유지하지만, 미번역 구간은 재파싱하면서 더 자연스러운 읽기 단위로 바꿀 수 있다. 원저자의 의미와 어조를 최우선으로 삼아 폭력적·성차별적·반종교적 표현도 현대의 가치에 맞춰 완화하거나 보정하지 않는다. 각주는 어원, 말놀이, 인명, 인용 전거와 역사적 배경처럼 원문 이해에 필요한 정보만 제공한다.

```bash
python scripts/translation_cache.py export --work eh --limit 100
python scripts/translation_cache.py import translations/batches/pending.ndjson
python scripts/build_data.py
```

내보낸 NDJSON에는 ID, 독일어, 출전, 비어 있는 `korean` 필드가 들어 있다. 번역·검토 후 import하면 원문이 일치하는지 확인하고 캐시에 병합한다.

## Scriptable

[`scriptable/NietzscheToday.js`](scriptable/NietzscheToday.js)를 Scriptable 새 스크립트에 붙여 넣는다. 위젯은 5분 슬롯과 xorshift로 구절을 고르고 5분 뒤 갱신을 요청한다. iOS는 실제 갱신 시각을 보장하지 않는다.

작은 `manifest.json`을 먼저 확인한 뒤 5분 선택값이 속한 작품별 조각 하나만 내려받는다. 각 조각은 최대 256개 구절이며 선별 목록이 아니라 전체 코퍼스를 나눈 전송 단위다. 번역이 없는 쇼펜하우어 구절도 선택 대상이고 그때는 독일어를 표시한다. 데이터가 갱신되어도 위젯 전체 JSON을 다시 받을 필요가 없으며 네트워크 실패 시 같은 corpus의 캐시 조각, 마지막 정상 구절, 내장 비상 구절 순서로 대체한다.

## 원문과 권리

판본, 고정 스냅샷, 대조 자료, SHA-256은 [`sources/SOURCES.md`](sources/SOURCES.md)와 [`sources/sources.json`](sources/sources.json)에 기록했다. 원저작과 각 디지털 판본·플랫폼의 권리 조건은 서로 다를 수 있으며, 이 저장소는 제공처의 출처와 조건을 보존하는 비상업 읽기·연구 프로젝트다.
