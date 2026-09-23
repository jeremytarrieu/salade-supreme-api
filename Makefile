.DEFAULT_GOAL := query

IMAGE ?= gsheet-fetch:latest
PORT ?= 8000
CONTAINER ?= gsheet-fetch

.PHONY: build run query

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm --name $(CONTAINER) --env-file .env -p $(PORT):8000 $(IMAGE)

query:
	curl --fail --show-error http://localhost:$(PORT)/api/data
