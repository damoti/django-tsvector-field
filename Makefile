.PHONY: test release

export DJANGO_SETTINGS_MODULE=tests.settings
test:
	django-admin test

release:
	python setup.py sdist bdist_wheel upload
