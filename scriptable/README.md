# Scriptable 설치

1. iPhone에서 Scriptable을 열고 새 스크립트를 만든다.
2. `NietzscheToday.js` 전체를 붙여 넣고 실행해 권한과 캐시를 준비한다.
3. 홈 화면에 Scriptable 위젯을 추가하고 이 스크립트를 선택한다.

스크립트는 실행할 때 작은 `data/manifest.json`을 먼저 확인하고, 5분 선택값이 속한 최대 256개 구절짜리 조각만 받는다. 조각은 작품과 번호별로 캐시하며, 새 분할 데이터가 없는 이전 배포에서는 `data/widget.json`을 사용하는 호환 모드로 전환한다. 네트워크가 끊기면 같은 corpus의 캐시 조각, 마지막 정상 구절, 코드에 포함된 비상 구절 순서로 사용한다.

구절 선택은 요청한 5분 슬롯 + xorshift 로직을 그대로 사용한다. `refreshAfterDate`도 5분 뒤로 요청하지만 실제 갱신 시각은 iOS가 결정한다.
