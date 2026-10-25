# Imgcomp · 로컬 미디어 정리실

설치 없이 브라우저에서 이미지·동영상 중복을 비교하고 정리하는 독립 정적 웹 앱입니다. 데스크톱 앱 [movimgcomp](https://github.com/teamprotofelix/movimgcomp)는 변경하지 않습니다.

## 사용하기

1. HTTPS 사이트를 PC Chrome 또는 Edge에서 엽니다.
2. **검색할 폴더 선택**으로 폴더 읽기 권한을 허용합니다. 하위 폴더도 검색합니다.
3. 비교 설정을 확인하고 **중복 분석 시작**을 누릅니다.
4. 미리보기로 비교한 뒤 그룹별 **원본으로 남기기**를 지정합니다. 선택과 남길 원본은 모든 필터에 걸쳐 유지됩니다.
5. **완전 동일 중복만 선택**은 SHA-256이 동일한 그룹만 선택합니다. 유사 후보는 직접 선택하세요.
6. **선택 파일 삭제**에서 완전 동일 대상과 유사 후보 대상을 나누어 보고, 삭제 경로 및 모든 지정 보존 원본 경로를 확인합니다. 유사 후보에는 별도 확인란도 필요하며 `삭제`를 입력합니다. 실행할 때 폴더 쓰기 권한을 별도로 요청합니다.

**삭제는 휴지통으로 이동하지 않습니다. 복구를 보장하지 않습니다.** 기본 선택은 항상 비어 있습니다. 삭제 직전 대상의 전체 해시와 남길 파일의 전체 해시를 다시 검증합니다. 대상이 속한 모든 그룹의 지정 보존 원본을 반드시 검증하며 다른 비선택 파일로 대체하지 않습니다. 지정 원본 변경·소실·권한 거부 시 해당 대상은 삭제하지 않습니다. 다시 분석하거나 원본을 재지정하세요. 그룹 전체·명시적으로 남길 원본의 삭제는 차단합니다. 부분 실패 시 결과를 구분하고 삭제 로그 JSON을 내려받습니다. 권한 요청 대기 중과 최종 파일 검사 이후에도 중지를 확인합니다. 실행 중 중지할 수 있지만 이미 호출한 `removeEntry`는 취소할 수 없고 삭제된 파일은 되돌아오지 않습니다. 로그는 완료(`deleted`)·차단(`blocked`)·미실행(`unexecuted`)을 구분하며 부분 성공도 보존합니다. 삭제 성공 후에는 다시 분석해야 합니다.

브라우저의 파일 API는 검증과 삭제를 하나의 원자적 작업으로 제공하지 않습니다. 검사 직후 외부 프로그램이 파일을 바꾸는 경쟁 상황까지 완전히 방지할 수는 없습니다. 정리 중 파일을 편집·동기화하지 마세요.

## 기능

- 폴더·하위 폴더 탐색, 이미지·동영상 분류
- 전체 바이트의 SHA-256을 사용하는 완전 동일 검색
- 이미지 명암 dHash(64비트)·평균 RGB·가로세로 비율을 조합한 유사 후보 검색
- 브라우저 지원 코덱의 동영상 15%·50%·85% 프레임 및 길이를 이용하는 실험적 유사 검색
- 첫 기준 파일과 직접 유사한 후보끼리 묶음: A≈B≈C 연결만으로 A≈C라고 판단하지 않음. 지정 보존 원본 변경 시 각 구성원과 직접 재비교하며 조건을 벗어난 삭제 선택은 해제. 재비교에는 해당 분석 당시 설정을 사용
- 미리보기·영상 재생, 파일명·경로 검색, 종류·일치 유형 필터, 단계별 그룹 더 보기 및 그룹 내부 24개씩 파일 더 보기
- 수정일·용량·경로에 따른 유지 원본 추천, 사용자 지정 유지 원본
- 순차 파일 처리, 별도 Worker에서 4 MiB 청크 해싱, 진행 상황·중지·분석 오류 목록
- 필터에 숨겨진 선택을 포함하는 고정 삭제 계획·총개수·용량·확인 목록. 유사 그룹과 겹치는 대상은 보수적으로 유사 후보 동의를 요구
- 발견 파일 수 / 전체 내용 해시 성공 / 읽기·해시 실패 수를 구분. 유사 분석 제외는 별도 오류 목록으로 안내
- 읽기 전용 폴더 입력, 결과 JSON·삭제 로그 내보내기
- 메모리에서 생성하는 안전한 샘플 체험, 반응형 화면, 키보드 포커스
- 외부 라이브러리·CDN·폰트·분석기·파일 업로드·백엔드 없음. CSP에서 네트워크 연결 금지

## 지원 및 한계

| 항목 | 지원 범위 |
|---|---|
| 직접 폴더 접근·삭제 | File System Access API를 제공하는 PC Chrome·Edge + HTTPS/localhost + 사용자 권한 |
| 다른 브라우저·모바일 | 기능 감지 후 읽기 전용 폴더 선택·분석·결과 내보내기. 폴더 입력 지원은 브라우저에 따라 다름 |
| 완전 동일 | JPG/JPEG/PNG/GIF/BMP/WebP/AVIF/HEIC/HEIF/TIF/TIFF, MP4/WebM/MOV/M4V/MKV/AVI/WMV/FLV/MPEG/MPG/3GP. 디코딩 불필요 |
| 유사 이미지 | JPG/JPEG/PNG/BMP. GIF/WebP/AVIF/HEIC/HEIF/TIFF는 애니메이션·디코딩 호환성을 고려해 완전 동일만 수행 |
| 유사 동영상 | 브라우저가 실제 디코딩할 수 있는 코덱만. 파일 확장자만으로 지원을 보장하지 않음 |
| 정확도 | 유사는 검토 후보임. 명암·색상·장면이 비슷한 다른 파일을 포함하거나, 크롭·회전·편집된 중복을 놓칠 수 있음. 오디오 비교 없음 |
| 대량 파일 | 전체 해시 순차 처리. 유사 분석은 총 3,000개 이하에서만 수행. 초과 시 안내 후 완전 동일만 수행 |
| 이미지 크기 | 유사 분석은 디코딩 후 8천만 픽셀 초과 이미지 제외. 디코딩 자체도 메모리가 필요하므로 대형 RAW/고해상도 묶음에 적합하지 않을 수 있음 |
| 상태 | 파일 내용·폴더 핸들·결과는 서버나 영구 저장소에 보관하지 않음. 새로고침 후 폴더를 다시 선택해야 함 |
| 그룹 겹침 | 완전 동일 그룹과 유사 그룹에 같은 파일이 보일 수 있음. 선택은 파일별 공유되며 모든 그룹의 유지 원본을 보호 |

## GitHub Pages

정적 진입점 `index.html`과 모든 런타임 파일은 저장소 루트에 있습니다. 하위 경로(`/Imgcomp/`)에서도 동작하도록 상대 경로를 사용합니다.

저장소 **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: main → /(root) → Save**로 활성화합니다. `.nojekyll`로 별도 빌드를 생략합니다. Pages를 활성화하지 않았다면 main push만으로 사이트가 생기지는 않습니다.

ZIP을 받은 경우 `index.html` 더블클릭 대신 로컬 서버를 사용하세요.

```sh
python -m http.server 8080
# http://localhost:8080 에 접속
```

개발·검증(Node.js 24, 런타임 의존성 없음):

```sh
npm run check
npm test
# 브라우저 개발 검사: Python 3.12 + Playwright (앱 런타임에는 불필요)
pip install playwright==1.58.0
python -m playwright install --with-deps chromium
CHROMIUM_PATH='' npm run test:browser
# 시스템 Chromium을 쓸 때는 CHROMIUM_PATH=/usr/bin/chromium
```

`npm run test:browser`는 실제 `app.js` UI·Worker에 테스트용 폴더/권한 핸들을 연결한 회귀와 `tests/media-browser.html`을 자동 실행합니다. CI는 두 검사와 확인창 캡처를 실행하고 `browser-validation` 아티팩트를 보관합니다. 사용자 폴더 실삭제 검증은 대체하지 않습니다.

`tests/media-browser.html`은 브라우저에서 실제 PNG 디코딩·Worker 해싱·WebM 프레임 추출을 확인하는 개발용 검사입니다. HTTPS 환경에서는 네이티브 해시 대조와 OPFS 내 임시 파일 생성·삭제도 확인합니다. 사용자 폴더를 읽거나 삭제하지 않습니다. 모바일 반응형 검사 절차와 검증 한계는 [VALIDATION.md](./VALIDATION.md)를 참고하세요.

## 마이그레이션 근거

참조 버전: `teamprotofelix/movimgcomp@79ee1c51a3f27d9cffdf94f573111b679ef29198`.

`app/scanner.py`, `app/duplicate_finder.py`, `app/keep_policy.py`, `app/file_actions.py`의 파일 분류·전체 해시·유지 정책·삭제 전 원본 보호 개념을 참고해 JavaScript로 재구현했습니다. Python·Qt·Pillow·네이티브 FFmpeg·Windows COM·휴지통 코드는 포함하지 않습니다. 웹 유사도 값은 데스크톱 pHash/VideoHash 값과 직접 호환되지 않습니다.

API 근거: [Chrome File System Access](https://developer.chrome.com/docs/capabilities/web-apis/file-system-access), [GitHub Pages publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
