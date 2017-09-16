INSTALLED_APPS = (
    'tsvector_field',
    'tsvector_test_app'
)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tsvector_field',
        'TEST': {
            'SERIALIZE': False
        }
    }
}
SECRET_KEY = 'test-key'
