ORDERS_COLUMNS = [
    'id',
    'starting_version',
    'ending_version',
    'firstDateTimeUtc',
    'price',
    'priceWithDiscounts',
    'unmergedCustomerId',
    'firstBrandInternalId',
    'pointOfContactInternalId',
    'firstPointOfContactInternalId',
    'deliveryPrice',
    'deliveryPriceWithDiscounts',
    'paidAmount',
    '_isDeleted',
    '_rowversion_ts',
    '_tenant',
    '_change_type',
    '_commit_version',
    '_commit_timestamp',
]

PURCHASE_COLUMNS = [
    'quantity',
    'productInternalId',
    'starting_version',
    'ending_version',
]

DEDUCTION_AMOUNTS_COLUMNS = [
    'spentAmount',
    'starting_version',
    'ending_version',
]

PURCHASE_POINTS_COLUMNS = [
    'name',
    'starting_version',
    'ending_version',
]

PURCHASE_STATUSES_COLUMNS = [
    'name',
    'starting_version',
    'ending_version',
]

YANDEX_UPLOAD_TIME_PARTS = {
    'ONE': 'first_dim_upload_date',
    'TWO': 'second_dim_upload_date',
    'THREE': 'third_dim_upload_date',
    'FOUR': 'upload_date',
}
