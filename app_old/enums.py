ORDERS_COLUMNS = [
    'firstDateTimeUtc',
    'price',
    'priceWithDiscounts',
    'unmergedCustomerId',
    'starting_version',
    'ending_version',
]

PURCHASE_COLUMNS = [
    'quantity',
    'productInternalId',
    'starting_version',
    'ending_version',
]

NEGATIVE_CUSTOMER_BALANCE_CHANGE_DETAILS_COLUMNS = [
    'spentAmount',
    'starting_version',
    'ending_version',
]

POINTS_OF_CONTRACT_COLUMNS = [
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
    "ym:s:purchaseRevenue"
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
    "ym:s:ReferalSource"
)

COMMERCE_PURCHASE_DIMENSIONS_PART_FOUR = (
    "ym:s:visitID,"
    "ym:s:goal"
)
