# Paragraphy React Frontend

기존 화면 구조를 React 컴포넌트로 옮긴 독립 실행형 프론트엔드입니다.

```bash
npm install
npm run dev
```

백엔드가 다른 주소에서 실행 중이면 `.env` 파일을 만들고 `VITE_API_BASE_URL`을 설정합니다. 기본값은 `http://127.0.0.1:8000`입니다.

## 구성

- `src/components/`: 랜딩, 로그인, 문제 선택, 에디터, 결과, 기록 화면 컴포넌트
- `src/mocks/api.js`: 백엔드 연동 전 사용할 비동기 목업 API
- `src/mocks/data.js`: 초기 문제 샘플 데이터

현재 로그인, 문제 생성, 답안 저장, 채점, Tutor Chat은 모두 브라우저 메모리에서 동작하는 샘플입니다. 백엔드 연동 시에는 `src/mocks/api.js`의 함수들을 실제 API 호출로 교체하면 됩니다.
