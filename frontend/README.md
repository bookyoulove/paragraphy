# Paragraphy React Frontend

기존 화면 구조를 React 컴포넌트로 옮긴 독립 실행형 프론트엔드입니다.

```bash
npm install
npm run dev
```

백엔드가 다른 주소에서 실행 중이면 `.env` 파일을 만들고 `VITE_API_BASE_URL`을 설정합니다. 기본값은 `http://127.0.0.1:8000`입니다.

개발 모드에서는 Tutor Chat WebSocket이 백엔드 endpoint와 동일한 `/results/{result_id}/chat/ws` 경로를 통해 Vite proxy를 사용합니다. 따라서 외부 포워딩 주소가 브라우저의 Origin을 차단하더라도 Vite 서버가 백엔드로 WebSocket을 전달할 수 있습니다. `VITE_API_BASE_URL`에 경로 prefix가 포함되어 있다면 proxy가 해당 prefix를 자동으로 붙입니다. Vite proxy는 브라우저가 아니라 Vite 서버 프로세스에서 백엔드로 연결하므로, 필요하면 Vite 서버가 접근 가능한 주소를 `VITE_WS_PROXY_TARGET`으로 별도 설정하세요. 예를 들어 호스트에서 Vite를 실행하면 `http://127.0.0.1:8000`, Podman Compose의 frontend 컨테이너에서 호스트에 publish된 백엔드로 접근하면 `http://host.containers.internal:8000`, Compose DNS가 정상적으로 동작하는 환경에서는 `http://backend:8000`, 외부 포워딩을 사용하면 해당 터널 주소를 지정합니다.

### 배포 시 WebSocket proxy 메모

Nginx 등으로 배포할 때도 WebSocket endpoint에 HTTP/1.1 upgrade를 전달하도록 proxy를 설정해야 합니다. 예시는 다음과 같습니다.

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

location /results/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;
}
```

실제 배포 주소가 별도 prefix를 사용한다면 `location`과 `proxy_pass`의 경로를 그 구조에 맞게 조정해야 합니다. HTTPS 페이지에서 WebSocket을 사용할 경우 외부 연결은 `wss://`여야 하며, Nginx가 올바른 Origin 정책도 허용해야 합니다.

## 구성

- `src/components/`: 랜딩, 로그인, 문제 선택, 에디터, 결과, 기록 화면 컴포넌트
- `src/mocks/api.js`: 백엔드 연동 전 사용할 비동기 목업 API
- `src/mocks/data.js`: 초기 문제 샘플 데이터

현재 로그인, 문제 생성, 답안 저장, 채점, Tutor Chat은 모두 브라우저 메모리에서 동작하는 샘플입니다. 백엔드 연동 시에는 `src/mocks/api.js`의 함수들을 실제 API 호출로 교체하면 됩니다.
