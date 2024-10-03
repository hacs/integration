from envs import env

DATABASE_URL = env('DATABASE_URL')

DEBUG = env('DEBUG', False, var_type='boolean')

MIDDLEWARE = env('MIDDLEWARE', [], var_type='list')
