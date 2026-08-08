# Scriptable 설치

1. iPhone에서 Scriptable을 열고 새 스크립트를 만든다.
2. `NietzscheToday.js` 전체를 붙여 넣고 실행해 권한과 캐시를 준비한다.
3. 홈 화면에 Scriptable 위젯을 추가하고 이 스크립트를 선택한다.

스크립트는 실행할 때 `data/manifest.json`만 먼저 확인한다. `dataVersion`이 기존 캐시와 다를 때만 약 2MB인 `quotes.json`을 다시 받는다. 네트워크가 끊기면 마지막 정상 캐시를 사용하며, 최초 실행부터 오프라인인 경우에는 코드에 포함된 네 구절을 사용한다.

구절 선택은 요청한 5분 슬롯 + xorshift 로직을 그대로 사용한다. `refreshAfterDate`도 5분 뒤로 요청하지만 실제 갱신 시각은 iOS가 결정한다.
