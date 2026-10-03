# Technology Stack (Reverse Engineering, 2026-09-28)

| 항목 | 값 |
|---|---|
| 언어·런타임 | Python 3.13.14 64-bit (venv `.venv`) |
| 웹 | fastapi 0.141.1, uvicorn 0.53.0, SSE(StreamingResponse) |
| 스키마 | pydantic 2.13.5 |
| 브라우저 | playwright 1.63.0, 설치된 Google Chrome(channel=chrome), persistent context `.profile/chrome` |
| 이미지 | pillow 12.3.0 |
| 저장소 | sqlite3(표준), `data/history.db` WAL |
| 설정 | PyYAML 6.0.3, `config.yaml` |
| 모델 | Claude Code CLI 2.1.280 `claude -p`(구독 로그인), judge claude-sonnet-5(medium), revise claude-fable-5-1(high) → 폴백 sonnet-5. flags_profile `minimal`(호출당 약 2.2k 컨텍스트 토큰) |
| 테스트·품질 | pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0, ruff 0.16.8 |
| 프론트엔드 | 순수 JS ES 모듈, 빌드 없음 |
| 실행 | run.bat, setup.bat(다른 PC 설치) |
