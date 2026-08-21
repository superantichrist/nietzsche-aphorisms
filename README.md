# 오늘의 니체 · Nietzsche Aphorisms

니체의 일곱 저작과 1885–1888년 후기 유고 독일어 원문을 출전 추적이 가능한 짧은 읽기 단위로 나눈 정적 데이터베이스, 모바일 웹, iPhone Scriptable 위젯입니다.

공개 사이트: <https://superantichrist.github.io/nietzsche-aphorisms/>

## 현재 데이터

| 작품 | 구절 수 | 원문 범위 |
|---|---:|---|
| Jenseits von Gut und Böse | 1,717 | 서문, §1–296, §65a, §73a, 후가 |
| Zur Genealogie der Moral | 1,261 | 서문 §1–8, 제1논문 §1–17, 제2논문 §1–25, 제3논문 §1–28 |
| Der Antichrist | 439 | 서문, 본문 §1–62, 부록 |
| Götzen-Dämmerung | 486 | 서문과 11개 본문·부록 단위 전체 |
| Die fröhliche Wissenschaft | 1,492 | 서문, 전주곡, 제1–5권 §1–383, 부록 노래 |
| Also sprach Zarathustra | 3,588 | 제1–4부 전체 |
| Ecce homo | 565 | 머리글, 서문, 14개 장 전체 |
| Nachgelassene Fragmente 1885–1888 | 8,401 | 37개 노트군 전체; 짧은 표제·미완 조각 제외 |
| 합계 | 17,949 | 일곱 저작과 후기 유고의 독일어 전 범위 |

기존 다섯 저작 5,395개 번역은 전량 독일어와 대조해 통독 감수했다. 새 세 코퍼스도 외부 기계번역 API나 현대 한국어 출판 번역을 사용하지 않고 Codex가 원문과 장 전체의 문맥에서 직접 옮긴다. 《이 사람을 보라》 565개 전체의 1차 번역을 완료했으며, 앞선 354개는 `reviewed`, 나머지 211개는 세심한 직접 번역을 거친 `draft`다. 《차라투스트라는 이렇게 말했다》 3,588개도 네 부 전체의 1차 직접 번역을 완료했다. 후기 유고는 1885년 노트군 38[8]까지 1,815개가 `draft`이며, 나머지는 `pending`으로 명시한다. 전체 현황은 번역 11,363개, 감수 완료 5,749개, 미번역 6,586개다. 한국어는 별도 캐시에서 관리하므로 번역을 다듬어도 안정 ID와 독일어 출전은 바뀌지 않는다.

모바일 웹에서는 작품 → 부/논문 → 절로 이어지는 목차를 열어 원하는 출전의 첫 구절로 바로 이동할 수 있다. 검색, 작품 필터, 앞뒤 이동, 원문 표시, 복사, 공유, 구절별 영구 링크도 지원한다.

## JSON

- [`data/quotes.json`](data/quotes.json): 일곱 저작과 후기 유고 전체
- [`data/jgb.json`](data/jgb.json): 《선악의 저편》
- [`data/gm.json`](data/gm.json): 《도덕의 계보》
- [`data/ac.json`](data/ac.json): 《안티크리스트》
- [`data/gd.json`](data/gd.json): 《우상의 황혼》
- [`data/fw.json`](data/fw.json): 《즐거운 학문》
- [`data/za.json`](data/za.json): 《차라투스트라는 이렇게 말했다》
- [`data/eh.json`](data/eh.json): 《이 사람을 보라》
- [`data/nf.json`](data/nf.json): 1885–1888년 후기 유고
- [`data/widget.json`](data/widget.json): 번역이 있는 구절만 담은 Scriptable용 최소 데이터
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
  "paragraphCount": 1,
  "sentence": 0,
  "german": "Wer mit Ungeheuern kämpft, ...",
  "korean": "괴물과 싸우는 사람은 ..."
}
```

`paragraphCount`가 1이면 화면에 절 안의 `구절 n`을 표시하고, 2 이상이면 `문단 n · 문장 n`을 표시한다. ID는 `work + part + section + paragraph + 정규화한 German`의 SHA-256으로 만든다. 번역이나 위치 표시 메타데이터를 수정해도 ID와 독일어 출전은 변하지 않는다. `corpusVersion`은 독일어 corpus, `dataVersion`은 한국어와 위치 메타데이터를 포함한 배포 데이터 버전이다.

## 로컬 빌드

Node.js 22와 Python 3.9 이상이 필요하다.

```bash
npm install
npm run check
npm run dev
```

`npm run check`는 원문을 다시 파싱하고 작품별 JSON을 만든 뒤, 17,900개 이상 구절·ID 유일성·여덟 코퍼스의 절과 단편 범위·구절 길이·출전 URL·번역 상태·번역 캐시 대응을 검증한다. 원문 스냅샷을 다시 받을 때만 `python scripts/fetch_sources.py`와 `python scripts/fetch_extended_sources.py`를 사용한다. 빌드는 vendored 원문으로 재현되므로 평소에는 네트워크가 필요 없다.

## 한국어 번역 작업

번역은 [`translations/ko.json`](translations/ko.json)에 ID별로 저장된다. 독일어 corpus를 다시 파싱해도 동일한 원문·출전의 ID는 유지된다. 원저자의 의미와 어조를 최우선으로 삼아 폭력적·성차별적·반종교적 표현도 현대의 가치에 맞춰 완화하거나 보정하지 않는다. 각주는 어원, 말놀이, 인명, 인용 전거와 역사적 배경처럼 원문 이해에 필요한 정보만 제공한다.

```bash
python scripts/translation_cache.py export --work eh --limit 100
python scripts/translation_cache.py import translations/batches/pending.ndjson
python scripts/build_data.py
```

내보낸 NDJSON에는 ID, 독일어, 출전, 비어 있는 `korean` 필드가 들어 있다. 번역·검토 후 import하면 원문이 일치하는지 확인하고 캐시에 병합한다.

## Scriptable

[`scriptable/NietzscheToday.js`](scriptable/NietzscheToday.js)를 Scriptable 새 스크립트에 붙여 넣는다. 위젯은 5분 슬롯과 xorshift로 구절을 고르고 5분 뒤 갱신을 요청한다. iOS는 실제 갱신 시각을 보장하지 않는다.

15MB가 넘는 웹용 전체 corpus 대신, 번역이 있는 구절과 위젯에 필요한 필드만 담은 `widget.json`을 사용한다. 작은 `manifest.json`의 `dataVersion`을 먼저 확인하고 버전이 바뀐 경우에만 다시 다운로드하며, 네트워크 실패 시 마지막 정상 캐시를 쓴다. 최초 실행도 오프라인이면 코드에 내장한 네 구절로 동작한다.

## 원문과 권리

판본, 고정 스냅샷, 대조 자료, SHA-256은 [`sources/SOURCES.md`](sources/SOURCES.md)와 [`sources/sources.json`](sources/sources.json)에 기록했다. 원저작과 각 디지털 판본·플랫폼의 권리 조건은 서로 다를 수 있으며, 이 저장소는 제공처의 출처와 조건을 보존하는 비상업 읽기·연구 프로젝트다.
