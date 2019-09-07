import io

import facebook

import stockhaiku.config as config


def post_update(image: io.BytesIO):
    page_access_token = config.FACEBOOK_PAGE_ACCESS_TOKEN
    facebook.VALID_API_VERSIONS.append('4.0')
    graph = facebook.GraphAPI(page_access_token, version='4.0')
    facebook_page_id = config.FACEBOOK_PAGE_ID
    graph.put_photo(image=image, album_path=facebook_page_id + "/photos")
