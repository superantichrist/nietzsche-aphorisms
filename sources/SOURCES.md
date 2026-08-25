# 독일어 원문과 판본

니체 빌드 입력은 Nietzsche Source의 eKGWB 화면에서 전사된 Markdown 스냅샷이다. 스냅샷을 커밋 해시와 SHA-256으로 고정해, 원격 사이트가 바뀌더라도 같은 ID와 같은 JSON을 다시 만들 수 있게 했다.

- `Jenseits von Gut und Böse`: eKGWB/Colli–Montinari 계열 전사본. Project Gutenberg eBook #7204 독일어 텍스트와 구조·주요 구절을 대조한다.
- `Zur Genealogie der Moral`: eKGWB/Colli–Montinari 계열 전사본. C. G. Naumann 1892년 제2판 스캔의 Internet Archive OCR과 장·절·주요 구절을 대조한다.
- `Der Antichrist`: eKGWB/Colli–Montinari 계열 전사본. 1906년 *Nietzsche's Werke*, Band VIII 스캔과 대조한다.
- `Götzen-Dämmerung`: eKGWB/Colli–Montinari 계열 전사본. 1906년 *Nietzsche's Werke*, Band VIII 스캔과 대조한다.
- `Die fröhliche Wissenschaft`: eKGWB/Colli–Montinari 계열 전사본. E. W. Fritzsch 1887년 신판 스캔과 대조한다. 부록시 10번에서 전사본 추출 과정에 붙어 버린 행 경계는 1887년 스캔과 교정 완료된 독일어 전사를 대조해 복원했으며, 어휘와 역사적 철자는 바꾸지 않았다.

Nietzsche Source는 eKGWB가 독일어 표준 비평판의 디지털판이며, 각 작품·장·절에 안정적인 주소를 부여한다고 설명한다. 개별 JSON 레코드의 `sourceUrl`은 이 안정 주소를 가리킨다.

원저자 Friedrich Nietzsche는 1900년에 사망했고 이 원저작들은 19세기에 쓰이거나 출판되었다. 원저작 텍스트의 퍼블릭 도메인 상태와 별개로, 각 디지털 제공처의 편집·플랫폼·배포 조건은 해당 제공처의 고지를 따른다. Nietzsche Source는 사이트 콘텐츠에 CC BY-NC-ND 4.0 조건을 고지한다. 이 프로젝트는 비상업적 읽기·연구 프로젝트이며 출처와 판본을 유지한다.

정확한 URL, 스냅샷 커밋, 파일 해시는 [`sources.json`](sources.json)에 있다.

## 확장 코퍼스

- 《Also sprach Zarathustra》 제1–4부
- 《Ecce homo》
- 1885–1888년 《Nachgelassene Fragmente》 전체 노트군

확장 원문도 같은 eKGWB 기반 미러의 고정 커밋을 사용한다. 42개 입력 파일의 개별 취득 URL·바이트 수·SHA-256은 [`extended_sources.json`](extended_sources.json)에 기록했다. 후기 유고는 사후 편집 선집인 《Der Wille zur Macht》의 배열을 따르지 않고, Colli–Montinari 비평판의 `연도, 노트군[단편]` 번호를 그대로 보존한다.

## 쇼펜하우어 코퍼스

《Parerga und Paralipomena》는 사용자가 제공한 독일어 EPUB을 SHA-256으로 고정해 빌드한다. 이 파일은 이미지 OCR 컨테이너가 아니라 60개 XHTML, 깊은 목차, 본문 문단과 왕복 각주 링크를 갖춘 EPUB 2 문서다. 제1권과 제2권, 제2권 §§1–413(90a/90b 및 103a/103b), 원판 각주가 들어 있다.

다만 이 텍스트는 1851년 초판이 아니다. Julius Frauenstädt가 편집한 Leipzig: F. A. Brockhaus 1874년 제3판이며, 제2판에서 통합된 쇼펜하우어의 수기 추가와 유고 자료를 포함한다. 추가문의 배치에는 편집자의 판단이 개입했으므로 `3. Auflage (1874)`, 편집자, 사후 증보판이라는 성격을 데이터에 명시한다.

EPUB의 구조적 무결성은 좋다. 선언되지 않은 `&nbsp;` 828개를 비분리 공백으로 정규화하면 60개 XHTML이 모두 파싱되고 내부 링크가 하나도 끊어지지 않는다. 반면 몇몇 명백한 전사 오자가 표본 검사에서 확인됐으므로, 첫 공개본은 `검증 중인 구조화 전사본`으로 표시한다. 이후 1874년 제3판 스캔과 대조해 전사 오자만 수정하며 역사적 철자·문장부호를 현대화하지 않는다. 원본 EPUB은 수정하지 않고, 모든 교정은 별도 기록으로 재현 가능하게 관리한다.

교정 기록은 `pp-transcription-corrections.json`에 원문 문자열·교정 문자열·판면 URL·예상 출현 횟수를 함께 둔다. 파서는 각 교정이 지정 XHTML에서 정확히 그 횟수만큼 발견될 때만 적용하므로, EPUB이나 파서가 바뀌어 엉뚱한 본문을 고치는 일을 막는다.
