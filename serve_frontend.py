"""정적 파일 서버 — Python 기본 http.server에 캐시 방지 헤더를 추가한 버전.

이 파일을 자주 재배포하는 개발 단계에서 브라우저가 예전 app.js/style.css를
계속 캐시해서 쓰는 문제(무반응 버튼 등 오래된 동작)를 막기 위한 것이다.
"""

import functools
import http.server
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    handler = functools.partial(NoCacheHandler, directory=str(FRONTEND_DIR))
    http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()


if __name__ == "__main__":
    main()
