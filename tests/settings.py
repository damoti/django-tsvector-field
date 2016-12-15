INSTALLED_APPS = [
    'tsvector_field',
    'tests'
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tsvector_field',
        'TEST': {
            'SERIALIZE': False
        }
    }
}
DEBUG = True
SECRET_KEY = 'test-key'