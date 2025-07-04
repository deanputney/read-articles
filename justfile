read URL:
	python3 url_to_podcast.py "{{URL}}"

reset:
	python3 url_to_podcast.py --reset

publish:
	@just reset
	git add .
	git commit -m "Publish new podcast episode(s)"
	git push