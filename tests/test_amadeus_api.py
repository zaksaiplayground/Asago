import os
from amadeus import Client
from dotenv import load_dotenv

load_dotenv()

amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )

def test_amadeus_request_with_oneway():

    search_body = {
        "currencyCode": "EUR",
        "originDestinations": [
            {
                "id": "1",
                "originLocationCode": "BLR",
                "destinationLocationCode": "MUC",
                "departureDateTimeRange": {
                    "date": "2025-08-05",
                    "time": "10:00:00"
                }
            },
            {
                "id": "2",
                "originLocationCode": "MUC",
                "destinationLocationCode": "BLR",
                "departureDateTimeRange": {
                    "date": "2025-08-18",
                    "time": "17:00:00"
                }
            }
        ],
        "travelers": [
            {
                "id": "1",
                "travelerType": "ADULT",
                "fareOptions": [
                    "STANDARD"
                ]
            },
            {
                "id": "2",
                "travelerType": "CHILD",
                "fareOptions": [
                    "STANDARD"
                ]
            }
        ],
        # "sources": [
        #     "GDS"
        # ],
        "searchCriteria": {
            "maxFlightOffers": 1,
            "flightFilters": {
                "cabinRestrictions": [
                    {
                        "cabin": "BUSINESS",
                        "coverage": "MOST_SEGMENTS",
                        "originDestinationIds": [
                            "1"
                        ]
                    }
                ],
                "carrierRestrictions": {
                    "includedCarrierCodes": [
                        "EK"
                    ]
                }
            }
        }
    }

    response = amadeus.shopping.flight_offers_search.post(search_body)
    assert response.status_code == 200
    print(response.data)
    # assert response.data is not None
    # assert isinstance(response.data, list)
    # assert len(response.data) > 0