.PHONY: test clean release

export DJANGO_SETTINGS_MODULE=tests.settings
test:
	django-admin test

clean:
	rm -rf build dist django_tsvector_field.egg-info

release:
	python setup.py sdist bdist_wheel upload
