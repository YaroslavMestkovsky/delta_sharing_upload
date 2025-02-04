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

COMMERCE_PURCHASE_DIMENSIONS_PART_ONE = (
    "ym:s:visitID,"
    "ym:s:purchaseID,"
    "ym:s:purchaseRevenue,"
    "ym:s:dateTime"
)

COMMERCE_PURCHASE_DIMENSIONS_PART_TWO = (
    "ym:s:dateTime,"
    "ym:s:visitID,"
    "ym:s:clientID,"
    "ym:s:TrafficSource,"
    "ym:s:lastSearchEngine,"
    "ym:s:UTMSource,"
    "ym:s:UTMMedium,"
    "ym:s:UTMCampaign,"
    "ym:s:UTMContent,"
    "ym:s:UTMTerm"
)

COMMERCE_PURCHASE_DIMENSIONS_PART_THREE = (
    "ym:s:visitID,"
    "ym:s:deviceCategory,"
    "ym:s:ReferalSource,"
    "ym:s:dateTime"
)

COMMERCE_PURCHASE_DIMENSIONS_PART_FOUR = (
    "ym:s:visitID,"
    "ym:s:goal,"
    "ym:s:dateTime"
)
