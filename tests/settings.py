INSTALLED_APPS = [
    'tsvector',
    'tests'
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tsvector',
        'TEST': {
            'SERIALIZE': False
        }
    }
}
DEBUG = True
SECRET_KEY = 'test-key'