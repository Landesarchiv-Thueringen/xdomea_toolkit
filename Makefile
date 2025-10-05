build:
	@docker build -t landesarchiv_thueringen/xdomea_toolkit:latest .

run:
	@docker run -it --rm -v $(PWD)/data:/app/data landesarchiv_thueringen/xdomea_toolkit:latest