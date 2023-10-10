PREFIX := $(PWD)
archive := $(PREFIX)/archive
dist := $(PREFIX)/dist
work := $(PREFIX)/work

src_mp3s := $(wildcard $(archive)/*.mp3)
dist_mp3s := $(src_mp3s:$(archive)/%.mp3=$(dist)/%.mp3)
feed := $(dist)/feed.xml
archive_txt := $(dist)/archive.txt

$(if $(wildcard config.ini),,$(error config.ini not found; see config.ini.example))

config_get = awk -F ' = ' '/^$(1) *=/ {print $$2}' config.ini

.PHONY: all
all: ## Build everything
all: mp3s feed archive-txt

.PHONY: mp3s
mp3s: ## Build MP3s
mp3s: $(dist_mp3s)

.PHONY: clobber
clobber: ## Remove all generated dist files
clobber:
	rm -rf dist

define explode
$(work)/%: $(archive)/%$(1)
	mkdir -p $$(@)
	ffmpeg -i $$(<) -vsync 0 -filter_complex "select=bitor(gt(scene\,0.3)\,eq(n\,0))" -frame_pts 1 -r 1000 "$$(@)/%d.jpg"
endef

video_exts = .mkv .webm

$(foreach _,$(video_exts),$(eval $(call explode,$(_))))

$(dist) $(work):
	mkdir -p $(@)

$(dist)/%.mp3: $(archive)/%.mp3 $(work)/% | $(dist)
	$(env)/bin/python3 chapterize.py $(^) $(@)

env := $(PREFIX)/.env

.PHONY: env
env: $(env)

$(env):
	python3 -m venv $(@)
	$(@)/bin/pip install -r requirements.txt

.PHONY: archive
archive: ## Download videos
archive: $(archive)

.PHONY: $(archive)
$(archive): | $(env)
	mkdir -p $(@)
	$(env)/bin/yt-dlp -k -x --audio-format mp3 -o '$(@)/%(id)s.%(ext)s' \
		--download-archive $(@)/archive.txt \
		$$($(call config_get,video_playlist_url))

.PHONY: prune
prune: ## Remove unneeded archive files
prune:
	if [ -d $(archive) ]; then rm -f $(archive)/*.f[0-9]*; fi

.PHONY: feed
feed: ## Build feed
feed: $(feed)

$(feed): $(archive)/archive.txt | $(env) $(dist)
	$(env)/bin/python3 feedswap.py $$(cut -d ' ' -f 2 $(<)) > $(@)

.PHONY: archive-txt
archive-txt: $(archive_txt)

$(archive_txt): $(archive)/archive.txt
	cp $(<) $(@)

dryrun := --dryrun

.PHONY: deploy
deploy: | $(dist)
	deploy_path=s3://$$($(call config_get,deploy_bucket))/$$($(call config_get,deploy_key_prefix)) && \
	cd $(|) && aws s3 sync $(dryrun) --exclude '*.xml' --exclude '*.txt' \
		--acl public-read . $$deploy_path && \
	aws s3 sync $(dryrun) --exclude '*.mp3' \
		--acl public-read --cache-control max-age=30 . $$deploy_path

.PHONY: build
build:
	docker build --platform linux/arm64 -t video2pod .
	docker tag video2pod $$($(call config_get,aws_ecr_tag))

.PHONY: push
push:
	tag=$$($(call config_get,aws_ecr_tag)); \
	docker push $$tag; \
	aws lambda update-function-code \
		--architectures arm64 \
		--function-name $$($(call config_get,aws_lambda_name)) \
		--image-uri $$tag

.PHONY: shell
shell: | $(env)
	$(env)/bin/python3

.PHONY: help
help: ## Show this help text
	$(info usage: make [target])
	$(info )
	$(info Available targets:)
	@awk -F ':.*?## *' '/^[^\t].+?:.*?##/ \
         {printf "  %-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
