import json
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv

load_dotenv()

class EnhancedAmadeusServer:
    def __init__(self):
        self.server = Server("enhanced-amadeus-flight-search")
        self.amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )
        self.setup_tools()

    def setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="search_flights_comprehensive",
                    description="Comprehensive flight search with all Amadeus API parameters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            # Basic required parameters
                            "originLocationCode": {
                                "type": "string", 
                                "description": "Origin airport/city code (IATA)"
                            },
                            "destinationLocationCode": {
                                "type": "string", 
                                "description": "Destination airport/city code (IATA)"
                            },
                            "departureDate": {
                                "type": "string", 
                                "description": "Departure date (YYYY-MM-DD)"
                            },
                            
                            # Passenger details
                            "adults": {
                                "type": "integer", 
                                "description": "Number of adult passengers (12+ years)", 
                                "default": 1, 
                                "minimum": 1, 
                                "maximum": 9
                            },
                            "children": {
                                "type": "integer", 
                                "description": "Number of child passengers (2-11 years)", 
                                "default": 0, 
                                "minimum": 0, 
                                "maximum": 9
                            },
                            "infants": {
                                "type": "integer", 
                                "description": "Number of infant passengers (under 2 years)", 
                                "default": 0, 
                                "minimum": 0, 
                                "maximum": 9
                            },
                            
                            # Trip details
                            "returnDate": {
                                "type": "string", 
                                "description": "Return date for round-trip (YYYY-MM-DD)"
                            },
                            "travelClass": {
                                "type": "string", 
                                "description": "Travel class preference",
                                "enum": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
                                "default": "ECONOMY"
                            },
                            
                            # Airline preferences
                            "includedAirlineCodes": {
                                "type": "string", 
                                "description": "Comma-separated airline codes to include (e.g., 'EK,SIA,LH')"
                            },
                            "excludedAirlineCodes": {
                                "type": "string", 
                                "description": "Comma-separated airline codes to exclude"
                            },
                            
                            # Flight preferences
                            "nonStop": {
                                "type": "boolean", 
                                "description": "Search only nonstop flights",
                                "default": False
                            },
                            "maxPrice": {
                                "type": "number", 
                                "description": "Maximum price per person"
                            },
                            "currencyCode": {
                                "type": "string", 
                                "description": "Currency for pricing (3-letter code)",
                                "default": "USD"
                            },
                            
                            # Advanced filters
                            "max": {
                                "type": "integer", 
                                "description": "Maximum number of flight offers to return",
                                "default": 250,
                                "minimum": 1,
                                "maximum": 250
                            },
                            "maxDuration": {
                                "type": "string", 
                                "description": "Maximum flight duration (ISO 8601 format, e.g., 'PT10H30M')"
                            },
                            
                            # Flexible search options
                            "originRadius": {
                                "type": "integer", 
                                "description": "Search radius around origin (km, max 300)"
                            },
                            "destinationRadius": {
                                "type": "integer", 
                                "description": "Search radius around destination (km, max 300)"
                            },
                            "sources": {
                                "type": "string", 
                                "description": "Data sources to use",
                                "enum": ["GDS"],
                                "default": "GDS"
                            }
                        },
                        "required": ["originLocationCode", "destinationLocationCode", "departureDate"]
                    }
                ),
                Tool(
                    name="get_airport_info",
                    description="Get detailed airport information by city or airport code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string", 
                                "description": "City name or airport code to search"
                            },
                            "subType": {
                                "type": "string",
                                "description": "Type of location to search",
                                "enum": ["AIRPORT", "CITY", "AIRPORT,CITY"],
                                "default": "AIRPORT,CITY"
                            }
                        },
                        "required": ["keyword"]
                    }
                ),
                Tool(
                    name="get_airline_info",
                    description="Get airline information by code",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "airlineCodes": {
                                "type": "string", 
                                "description": "Comma-separated airline codes (e.g., 'EK,SIA,LH')"
                            }
                        },
                        "required": ["airlineCodes"]
                    }
                ),
                Tool(
                    name="analyze_flight_routes", 
                    description="Analyze common routes and suggest alternatives",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "originLocationCode": {"type": "string"},
                            "destinationLocationCode": {"type": "string"}
                        },
                        "required": ["originLocationCode", "destinationLocationCode"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            if name == "search_flights_comprehensive":
                return await self.search_flights_comprehensive(**arguments)
            elif name == "get_airport_info":
                return await self.get_airport_info(**arguments)
            elif name == "get_airline_info":
                return await self.get_airline_info(**arguments)
            elif name == "analyze_flight_routes":
                return await self.analyze_flight_routes(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def search_flights_comprehensive(self, 
                                         originLocationCode: str, 
                                         destinationLocationCode: str, 
                                         departureDate: str,
                                         adults: int = 1,
                                         children: int = 0,
                                         infants: int = 0,
                                         returnDate: Optional[str] = None,
                                         travelClass: str = "ECONOMY",
                                         includedAirlineCodes: Optional[str] = None,
                                         excludedAirlineCodes: Optional[str] = None,
                                         nonStop: bool = False,
                                         maxPrice: Optional[float] = None,
                                         currencyCode: str = "USD",
                                         max: int = 250,
                                         maxDuration: Optional[str] = None,
                                         originRadius: Optional[int] = None,
                                         destinationRadius: Optional[int] = None,
                                         sources: str = "GDS") -> List[TextContent]:
        try:
            # Build search parameters
            search_params = {
                'originLocationCode': originLocationCode,
                'destinationLocationCode': destinationLocationCode,
                'departureDate': departureDate,
                'adults': adults,
                'travelClass': travelClass,
                'currencyCode': currencyCode,
                'max': max,
                'sources': sources
            }
            
            # Add optional parameters
            if children > 0:
                search_params['children'] = children
            if infants > 0:
                search_params['infants'] = infants
            if returnDate:
                search_params['returnDate'] = returnDate
            if includedAirlineCodes:
                search_params['includedAirlineCodes'] = includedAirlineCodes
            if excludedAirlineCodes:
                search_params['excludedAirlineCodes'] = excludedAirlineCodes
            if nonStop:
                search_params['nonStop'] = 'true'
            if maxPrice:
                search_params['maxPrice'] = str(maxPrice)
            if maxDuration:
                search_params['maxDuration'] = maxDuration
            if originRadius:
                search_params['originRadius'] = originRadius
            if destinationRadius:
                search_params['destinationRadius'] = destinationRadius

            print(f"[AMADEUS] Searching with params: {search_params}")
            
            response = self.amadeus.shopping.flight_offers_search.get(**search_params)
            
            # Enhanced processing with detailed analysis
            flights_data = self.process_flights_enhanced(response.data)
            
            # Add metadata
            result = {
                'status': 'success',
                'search_params': search_params,
                'flights': flights_data,
                'count': len(flights_data),
                'total_results': len(response.data),
                'analysis': self.analyze_results(flights_data)
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except ResponseError as error:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'error',
                    'error_code': error.response.status_code,
                    'message': str(error),
                    'details': getattr(error, 'response', {})
                })
            )]
        except Exception as error:
            return [TextContent(
                type="text", 
                text=json.dumps({
                    'status': 'error',
                    'message': f"Unexpected error: {str(error)}"
                })
            )]

    def process_flights_enhanced(self, offers: List[Dict]) -> List[Dict[str, Any]]:
        """Enhanced flight processing with detailed information"""
        processed_flights = []
        
        for offer in offers:
            try:
                flight_info = {
                    'id': offer['id'],
                    'source': offer.get('source', 'GDS'),
                    'instantTicketingRequired': offer.get('instantTicketingRequired', False),
                    'nonHomogeneous': offer.get('nonHomogeneous', False),
                    'oneWay': offer.get('oneWay', False),
                    'lastTicketingDate': offer.get('lastTicketingDate'),
                    'price': {
                        'currency': offer['price']['currency'],
                        'total': float(offer['price']['total']),
                        'base': float(offer['price'].get('base', offer['price']['total'])),
                        'fees': []
                    },
                    'pricingOptions': offer.get('pricingOptions', {}),
                    'validatingAirlineCodes': offer.get('validatingAirlineCodes', []),
                    'travelerPricings': [],
                    'itineraries': []
                }
                
                # Process fees if available
                if 'fees' in offer['price']:
                    for fee in offer['price']['fees']:
                        flight_info['price']['fees'].append({
                            'amount': float(fee.get('amount', 0)),
                            'type': fee.get('type', 'UNKNOWN')
                        })
                
                # Process traveler pricing
                for traveler in offer.get('travelerPricings', []):
                    pricing_info = {
                        'travelerId': traveler['travelerId'],
                        'fareOption': traveler['fareOption'],
                        'travelerType': traveler['travelerType'],
                        'price': {
                            'currency': traveler['price']['currency'],
                            'total': float(traveler['price']['total']),
                            'base': float(traveler['price'].get('base', traveler['price']['total']))
                        },
                        'fareDetailsBySegment': []
                    }
                    
                    for segment_fare in traveler.get('fareDetailsBySegment', []):
                        pricing_info['fareDetailsBySegment'].append({
                            'segmentId': segment_fare['segmentId'],
                            'cabin': segment_fare.get('cabin', 'ECONOMY'),
                            'fareBasis': segment_fare.get('fareBasis', 'N/A'),
                            'brandedFare': segment_fare.get('brandedFare'),
                            'class': segment_fare.get('class', 'Y'),
                            'includedCheckedBags': segment_fare.get('includedCheckedBags', {})
                        })
                    
                    flight_info['travelerPricings'].append(pricing_info)
                
                # Process itineraries with enhanced detail
                for itinerary in offer['itineraries']:
                    segments = []
                    total_duration_minutes = self.parse_duration_to_minutes(itinerary['duration'])
                    
                    for segment in itinerary['segments']:
                        segment_info = {
                            'id': segment.get('id'),
                            'numberOfStops': segment.get('numberOfStops', 0),
                            'blacklistedInEU': segment.get('blacklistedInEU', False),
                            'departure': {
                                'iataCode': segment['departure']['iataCode'],
                                'terminal': segment['departure'].get('terminal'),
                                'at': segment['departure']['at']
                            },
                            'arrival': {
                                'iataCode': segment['arrival']['iataCode'],
                                'terminal': segment['arrival'].get('terminal'), 
                                'at': segment['arrival']['at']
                            },
                            'carrierCode': segment['carrierCode'],
                            'number': segment['number'],
                            'aircraft': segment.get('aircraft', {}),
                            'operating': segment.get('operating', {}),
                            'duration': segment.get('duration', 'PT0M'),
                            'duration_minutes': self.parse_duration_to_minutes(segment.get('duration', 'PT0M')),
                            'stops': []
                        }
                        
                        # Add stop information if available
                        if 'stops' in segment:
                            for stop in segment['stops']:
                                segment_info['stops'].append({
                                    'iataCode': stop['iataCode'],
                                    'duration': stop.get('duration', 'PT0M'),
                                    'arrivalAt': stop.get('arrivalAt'),
                                    'departureAt': stop.get('departureAt')
                                })
                        
                        segments.append(segment_info)
                    
                    flight_info['itineraries'].append({
                        'duration': itinerary['duration'],
                        'duration_minutes': total_duration_minutes,
                        'segments': segments,
                        'total_stops': sum(seg['numberOfStops'] for seg in segments)
                    })
                
                # Calculate summary statistics
                flight_info['summary'] = self.calculate_flight_summary(flight_info)
                
                processed_flights.append(flight_info)
                
            except Exception as e:
                print(f"[AMADEUS] Error processing offer {offer.get('id', 'unknown')}: {e}")
                continue
        
        return processed_flights

    def parse_duration_to_minutes(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to minutes"""
        if not duration_str or duration_str == 'PT0M':
            return 0
            
        duration_str = duration_str.replace('PT', '')
        
        hours = 0
        minutes = 0
        
        if 'H' in duration_str:
            hours_part = duration_str.split('H')[0]
            hours = int(hours_part) if hours_part.isdigit() else 0
            duration_str = duration_str.split('H')[1] if 'H' in duration_str else duration_str
            
        if 'M' in duration_str:
            minutes_part = duration_str.replace('M', '')
            minutes = int(minutes_part) if minutes_part.isdigit() else 0
            
        return hours * 60 + minutes

    def calculate_flight_summary(self, flight_info: Dict) -> Dict:
        """Calculate summary statistics for a flight"""
        total_duration = sum(itin['duration_minutes'] for itin in flight_info['itineraries'])
        total_stops = sum(itin['total_stops'] for itin in flight_info['itineraries'])
        
        # Get all airlines involved
        airlines = set()
        for itinerary in flight_info['itineraries']:
            for segment in itinerary['segments']:
                airlines.add(segment['carrierCode'])
                if segment['operating'].get('carrierCode'):
                    airlines.add(segment['operating']['carrierCode'])
        
        return {
            'total_duration_minutes': total_duration,
            'total_duration_hours': round(total_duration / 60, 1),
            'total_stops': total_stops,
            'airlines_involved': list(airlines),
            'is_single_airline': len(airlines) == 1,
            'departure_time': flight_info['itineraries'][0]['segments'][0]['departure']['at'],
            'arrival_time': flight_info['itineraries'][-1]['segments'][-1]['arrival']['at']
        }

    def analyze_results(self, flights: List[Dict]) -> Dict:
        """Analyze flight results to provide insights"""
        if not flights:
            return {'message': 'No flights to analyze'}
        
        prices = [f['price']['total'] for f in flights]
        durations = [f['summary']['total_duration_hours'] for f in flights]
        stops = [f['summary']['total_stops'] for f in flights]
        
        # Count airlines
        airline_count = {}
        for flight in flights:
            for airline in flight['summary']['airlines_involved']:
                airline_count[airline] = airline_count.get(airline, 0) + 1
        
        return {
            'price_analysis': {
                'min': min(prices),
                'max': max(prices),
                'avg': round(sum(prices) / len(prices), 2),
                'currency': flights[0]['price']['currency']
            },
            'duration_analysis': {
                'min_hours': min(durations),
                'max_hours': max(durations),
                'avg_hours': round(sum(durations) / len(durations), 1)
            },
            'stops_analysis': {
                'nonstop_count': len([f for f in flights if f['summary']['total_stops'] == 0]),
                'one_stop_count': len([f for f in flights if f['summary']['total_stops'] == 1]),
                'multi_stop_count': len([f for f in flights if f['summary']['total_stops'] > 1])
            },
            'airline_distribution': dict(sorted(airline_count.items(), key=lambda x: x[1], reverse=True)[:10]),
            'recommendations': self.generate_recommendations(flights)
        }

    def generate_recommendations(self, flights: List[Dict]) -> List[str]:
        """Generate smart recommendations based on flight data"""
        recommendations = []
        
        if not flights:
            return ["No flights found - try expanding your search criteria"]
        
        # Price recommendations
        prices = [f['price']['total'] for f in flights]
        cheapest = min(flights, key=lambda x: x['price']['total'])
        if len(prices) > 1 and (max(prices) - min(prices)) / min(prices) > 0.5:
            recommendations.append(f"Price varies significantly (${min(prices):.0f}-${max(prices):.0f}). Book early for better deals.")
        
        # Duration recommendations
        nonstop_flights = [f for f in flights if f['summary']['total_stops'] == 0]
        if nonstop_flights:
            fastest_nonstop = min(nonstop_flights, key=lambda x: x['summary']['total_duration_minutes'])
            recommendations.append(f"Fastest nonstop: {fastest_nonstop['summary']['total_duration_hours']}h for ${fastest_nonstop['price']['total']:.0f}")
        
        # Airline recommendations
        single_airline_flights = [f for f in flights if f['summary']['is_single_airline']]
        if single_airline_flights and len(single_airline_flights) < len(flights) * 0.8:
            recommendations.append("Consider single-airline bookings for easier rebooking and consistent service.")
        
        return recommendations

    async def get_airport_info(self, keyword: str, subType: str = "AIRPORT,CITY") -> List[TextContent]:
        """Get detailed airport/city information"""
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=keyword,
                subType=subType
            )
            
            locations = []
            for location in response.data:
                location_info = {
                    'name': location['name'],
                    'iataCode': location['iataCode'],
                    'type': location['subType'],
                    'address': {
                        'cityName': location['address']['cityName'],
                        'cityCode': location['address'].get('cityCode'),
                        'countryName': location['address']['countryName'],
                        'countryCode': location['address']['countryCode'],
                        'stateCode': location['address'].get('stateCode'),
                        'regionCode': location['address'].get('regionCode')
                    },
                    'geoCode': location.get('geoCode', {}),
                    'timeZoneOffset': location.get('timeZoneOffset')
                }
                locations.append(location_info)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'success',
                    'locations': locations,
                    'count': len(locations)
                }, indent=2)
            )]
            
        except ResponseError as error:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'error',
                    'message': str(error)
                })
            )]

    async def get_airline_info(self, airlineCodes: str) -> List[TextContent]:
        """Get airline information"""
        try:
            codes = [code.strip() for code in airlineCodes.split(',')]
            airlines_info = []
            
            for code in codes:
                try:
                    response = self.amadeus.reference_data.airlines.get(airlineCodes=code)
                    if response.data:
                        airline = response.data[0]
                        airlines_info.append({
                            'iataCode': airline['iataCode'],
                            'icaoCode': airline.get('icaoCode'),
                            'businessName': airline.get('businessName'),
                            'commonName': airline.get('commonName')
                        })
                except:
                    airlines_info.append({
                        'iataCode': code,
                        'error': 'Airline information not found'
                    })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'success',
                    'airlines': airlines_info
                }, indent=2)
            )]
            
        except Exception as error:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'error', 
                    'message': str(error)
                })
            )]

    async def analyze_flight_routes(self, originLocationCode: str, destinationLocationCode: str) -> List[TextContent]:
        """Analyze routes and suggest alternatives"""
        try:
            # This would typically involve multiple API calls to analyze routes
            # For now, providing basic analysis structure
            
            analysis = {
                'route': f"{originLocationCode} → {destinationLocationCode}",
                'analysis': {
                    'popular_route': True,  # This would be determined by data
                    'typical_airlines': [],  # Would be populated from route data
                    'common_stops': [],     # Common connection points
                    'seasonal_variations': 'Data not available'
                },
                'suggestions': [
                    f"Consider nearby airports to {originLocationCode} and {destinationLocationCode}",
                    "Check for seasonal route availability",
                    "Compare direct vs. connecting flight options"
                ]
            }
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'success',
                    'route_analysis': analysis
                }, indent=2)
            )]
            
        except Exception as error:
            return [TextContent(
                type="text",
                text=json.dumps({
                    'status': 'error',
                    'message': str(error)
                })
            )]