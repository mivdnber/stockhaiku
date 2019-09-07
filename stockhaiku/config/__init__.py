from stockhaiku.config.defaults import *

try:
    from config import *
except ImportError:
    import warnings
    warnings.warn('Running on default configuration! Put a config module on your app\'s PYTHONPATH!')

if UNSPLASH_ACCESS_KEY is None:
    raise RuntimeError('Please specify UNSPLASH_ACCESS_KEY in your config module')

if UNSPLASH_SECRET_KEY is None:
    raise RuntimeError('Please specify UNSPLASH_SECRET_KEY in your config module')

if FACEBOOK_PAGE_ID is None:
    raise RuntimeError('Please specify FACEBOOK_PAGE_ID in your config module')

if FACEBOOK_PAGE_ACCESS_TOKEN is None:
    raise RuntimeError('Please specify FACEBOOK_PAGE_ACCESS_TOKEN in your config module')
