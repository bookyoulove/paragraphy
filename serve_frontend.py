"""정적 파일 서버 — Python 기본 http.server에 캐시 방지 헤더를 추가한 버전.

이 파일을 자주 재배포하는 개발 단계에서 브라우저가 예전 app.js/style.css를
계속 캐시해서 쓰는 문제(무반응 버튼 등 오래된 동작)를 막기 위한 것이다.

두 번째 인자로 디렉터리 이름(예: frontend-v2)을 주면 그 폴더를 서빙한다
(기본값은 frontend/) — 기존 UI와 새 UI를 서로 다른 포트에서 동시에 띄우기 위함.
"""

import functools
import http.server
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    directory = sys.argv[2] if len(sys.argv) > 2 else "frontend"
    handler = functools.partial(NoCacheHandler, directory=str(BASE_DIR / directory))
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    main()
