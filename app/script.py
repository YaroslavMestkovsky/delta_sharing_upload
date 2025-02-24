from php_uploader import PHPUploader
from mindbox_uploader import MindboxUploader
from yandex_uploader import YandexUploader


if __name__ == '__main__':
    # delta_sharing_uploader = DeltaSharingUploader()
    # delta_sharing_uploader.run()
    # delta_sharing_uploader.close_connections()

    yandex_uploader = YandexUploader()
    yandex_uploader.run()
    yandex_uploader.close_connections()

    mindbox_uploader = MindboxUploader()
    mindbox_uploader.run()
    mindbox_uploader.close_connections()

    php_uploader = PHPUploader()
    php_uploader.run()
    php_uploader.close_connections()
