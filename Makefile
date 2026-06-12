dev:
	./.venv/bin/python -m uvicorn backend.main:app --reload

test:
	./.venv/bin/python -m pytest tests/ -v

reset-profile:
	rm -f allyAI.db
	rm -rf chroma_db/

install:
	./.venv/bin/python -m pip install -e .

.PHONY: dev test reset-profile install
