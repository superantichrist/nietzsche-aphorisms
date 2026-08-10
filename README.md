# 오늘의 니체 · Nietzsche Aphorisms

니체의 다섯 작품 독일어 원문을 출전 추적이 가능한 짧은 읽기 단위로 나눈 정적 데이터베이스, 모바일 웹, iPhone Scriptable 위젯입니다.

공개 사이트: <https://superantichrist.github.io/nietzsche-aphorisms/>

## 현재 데이터

| 작품 | 구절 수 | 원문 범위 |
|---|---:|---|
| Jenseits von Gut und Böse | 1,713 | 서문, §1–296, §65a, §73a, 후가 |
| Zur Genealogie der Moral | 1,261 | 서문 §1–8, 제1논문 §1–17, 제2논문 §1–25, 제3논문 §1–28 |
| Der Antichrist | 439 | 서문, 본문 §1–62, 부록 |
| Götzen-Dämmerung | 486 | 서문과 11개 본문·부록 단위 전체 |
| Die fröhliche Wissenschaft | 1,488 | 서문, 전주곡, 제1–5권 §1–383, 부록 노래 |
| 합계 | 5,387 | 독일어 전 작품 범위 |

독일어 원문은 전체 5,387개 레코드에 들어 있다. 《선악의 저편》·《도덕의 계보》·《안티크리스트》·《우상의 황혼》 전체와 《즐거운 학문》의 첫 300개, 합계 4,199개에는 프로젝트가 독일어 원문에서 직접 만든 한국어 번역 초안이 있다. 《즐거운 학문》의 나머지 1,188개는 직접 번역 전까지 `pending`으로 두며 자동 번역을 대신 공개하지 않는다. 한국어는 독일어 정본을 기준으로 별도 캐시에서 관리하고 현대 한국어 출판 번역을 복제하지 않는다.

## JSON

- [`data/quotes.json`](data/quotes.json): 다섯 작품 전체
- [`data/jgb.json`](data/jgb.json): 《선악의 저편》
- [`data/gm.json`](data/gm.json): 《도덕의 계보》
- [`data/ac.json`](data/ac.json): 《안티크리스트》
- [`data/gd.json`](data/gd.json): 《우상의 황혼》
- [`data/fw.json`](data/fw.json): 《즐거운 학문》
- [`data/manifest.json`](data/manifest.json): 버전, 개수, 파일 크기, SHA-256
- [`data/schema.json`](data/schema.json): 레코드 JSON Schema

```json
{
  "id": "jgb-146-009e0b432b98",
  "work": "jgb",
  "workTitleDe": "Jenseits von Gut und Böse",
  "workTitleKo": "선악의 저편",
  "part": "IV",
  "section": "146",
  "paragraph": 0,
  "sentence": 0,
  "german": "Wer mit Ungeheuern kämpft, ...",
  "korean": "괴물과 싸우는 사람은 ..."
}
```

ID는 `work + part + section + paragraph + 정규화한 German`의 SHA-256으로 만든다. 번역을 수정하거나 다시 생성해도 ID와 독일어 출전은 변하지 않는다. `corpusVersion`은 독일어 corpus, `dataVersion`은 한국어를 포함한 배포 데이터 버전이다.

## 로컬 빌드

Node.js 22와 Python 3.9 이상이 필요하다.

```bash
npm install
npm run check
npm run dev
```

`npm run check`는 원문을 다시 파싱하고 작품별 JSON을 만든 뒤, 5,000개 이상 구절·ID 유일성·다섯 작품 전체 절 범위·구절 길이·출전 URL·번역 상태·번역 캐시 대응을 검증한다. 원문 스냅샷을 다시 받을 때만 `python scripts/fetch_sources.py`를 사용한다. 빌드는 vendored 원문으로 재현되므로 평소에는 네트워크가 필요 없다.

## 한국어 번역 작업

번역은 [`translations/ko.json`](translations/ko.json)에 ID별로 저장된다. 독일어 corpus를 다시 파싱해도 동일한 원문·출전의 ID는 유지된다.

```bash
python scripts/translation_cache.py export --work jgb --limit 100
python scripts/translation_cache.py import translations/batches/pending.ndjson
python scripts/build_data.py
```

내보낸 NDJSON에는 ID, 독일어, 출전, 비어 있는 `korean` 필드가 들어 있다. 번역·검토 후 import하면 원문이 일치하는지 확인하고 캐시에 병합한다.

## Scriptable

[`scriptable/NietzscheToday.js`](scriptable/NietzscheToday.js)를 Scriptable 새 스크립트에 붙여 넣는다. 위젯은 5분 슬롯과 xorshift로 구절을 고르고 5분 뒤 갱신을 요청한다. iOS는 실제 갱신 시각을 보장하지 않는다.

매번 약 4.4MB JSON을 받지 않도록 작은 `manifest.json`의 `dataVersion`만 먼저 확인한다. 버전이 바뀐 경우에만 전체 corpus를 다운로드하며, 네트워크 실패 시 마지막 정상 캐시를 쓴다. 최초 실행도 오프라인이면 코드에 내장한 네 구절로 동작한다.

## 원문과 권리

판본, 고정 스냅샷, 대조 자료, SHA-256은 [`sources/SOURCES.md`](sources/SOURCES.md)와 [`sources/sources.json`](sources/sources.json)에 기록했다. 원저작과 각 디지털 판본·플랫폼의 권리 조건은 서로 다를 수 있으며, 이 저장소는 제공처의 출처와 조건을 보존하는 비상업 읽기·연구 프로젝트다.
