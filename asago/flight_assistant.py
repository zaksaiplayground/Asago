import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import itertools
from dataclasses import dataclass
from enum import Enum

load_dotenv()

class StopPreference(Enum):
    NONSTOP = "nonstop"
    ONE_STOP = "one_stop"
    TWO_STOPS = "two_stops"
    ANY = "any"

class SortPreference(Enum):
    PRICE = "price"
    DURATION = "duration"
    DEPARTURE_TIME = "departure_time"
    ARRIVAL_TIME = "arrival_time"
    STOPS = "stops"

@dataclass
class FlightSearchPreferences:
    """Enhanced user preferences for flight search"""
    max_stops: int = 2
    preferred_airlines: List[str] = None
    excluded_airlines: List[str] = None
    preferred_departure_times: List[str] = None  # ["morning", "afternoon", "evening"]
    max_duration_hours: Optional[int] = None
    preferred_airports: Dict[str, List[str]] = None  # {"origin": ["JFK", "LGA"], "destination": ["LHR", "LGW"]}
    transit_airports: List[str] = None  # Preferred transit hubs
    cabin_class: str = "ECONOMY"  # ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
    flexible_dates: bool = False
    max_price: Optional[float] = None
    same_airline_preference: bool = False  # For multi-segment flights
    sort_by: SortPreference = SortPreference.PRICE
    max_results_per_date: int = 10

class EnhancedFlightAssistant:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.amadeus_client = None
        self.websearch_session = None

    async def initialize_amadeus_direct(self):
        """Initialize Amadeus client directly"""
        from amadeus import Client
        
        self.amadeus_client = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )
        print("✅ Amadeus client initialized")

    def parse_user_request_enhanced(self, user_input: str=None, structured_input: Dict[str, Any] = None) -> Dict[str, Any]:
        if structured_input:
        # Convert structured form input into expected format
            return {
                "basic_search": {
                    "originLocationCode": structured_input["origin"],
                    "destinationLocationCode": structured_input["destination"],
                    "departure_date": structured_input.get("departure_date"),
                    "departure_date_range": structured_input.get("departure_date_range"),
                    "return_date": structured_input.get("return_date"),
                    "return_date_range": structured_input.get("return_date_range"),
                    "passengers": structured_input.get("adults", 1),
                    "trip_type": structured_input.get("trip_type", "one-way")
                },
                "preferences": {
                    "max_stops": structured_input.get("max_stops", 2),
                    "preferred_airlines": structured_input.get("preferred_airlines"),
                    "excluded_airlines": [],
                    "preferred_departure_times": [],
                    "max_duration_hours": None,
                    "cabin_class": structured_input.get("travel_class", "ECONOMY"),
                    "max_price": None,
                    "same_airline_preference": False,
                    "sort_by": "price",
                    "flexible_dates": structured_input.get("departure_date_range") is not None,
                    "max_results_per_date": 10
                },
                "clarification_needed": {
                    "needs_clarification": False,
                    "questions": []
                }
            }
        """Enhanced GPT parser that extracts detailed preferences"""
        system_prompt = f"""
        You are an advanced flight search assistant. Parse the user's request and extract detailed preferences.
        Today's date: {datetime.now().strftime("%Y-%m-%d")}
        
        Return ONLY valid JSON with these fields:
        {{
            "basic_search": {{
                "originLocationCode": "3-letter IATA code",
                "destinationLocationCode": "3-letter IATA code", 
                "departure_date": "YYYY-MM-DD or null",
                "departure_date_range": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} or null,
                "return_date": "YYYY-MM-DD or null",
                "return_date_range": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} or null,
                "passengers": 1,
                "trip_type": "round-trip" or "one-way"
            }},
            "preferences": {{
                "max_stops": 0-2 (0=nonstop, 1=max 1 stop, 2=max 2 stops),
                "preferred_airlines": ["EK", "SIA"] or null,
                "excluded_airlines": ["budget_carrier_codes"] or null,
                "preferred_departure_times": ["morning", "afternoon", "evening"] or null,
                "max_duration_hours": number or null,
                "cabin_class": "ECONOMY|PREMIUM_ECONOMY|BUSINESS|FIRST",
                "max_price": number or null,
                "same_airline_preference": true/false,
                "sort_by": "price|duration|departure_time|stops",
                "flexible_dates": true/false,
                "max_results_per_date": 5-15
            }},
            "clarification_needed": {{
                "needs_clarification": true/false,
                "questions": ["What questions to ask user"]
            }}
        }}
        
        Parsing examples:
        - "nonstop flights" → max_stops: 0
        - "Emirates or Singapore Airlines" → preferred_airlines: ["EK", "SIA"]
        - "no budget airlines" → excluded_airlines: ["common budget carriers"]
        - "morning departure" → preferred_departure_times: ["morning"]
        - "under $1000" → max_price: 1000
        - "business class" → cabin_class: "BUSINESS"
        - "flexible with dates" → flexible_dates: true
        - "quickest route" → sort_by: "duration"
        
        If key information is missing or ambiguous, set needs_clarification: true
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.1
        )
        
        try:
            parsed = json.loads(response.choices[0].message.content)
            print(f"📋 Enhanced parsing: {json.dumps(parsed, indent=2)}")
            return parsed
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            return {"error": "Could not parse request"}

    async def search_flights_with_full_params(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights with comprehensive Amadeus API parameters"""
        try:
            print(f"🔍 Searching with full params: {search_params}")
            
            # Build comprehensive search parameters
            amadeus_params = {
                "originLocationCode": search_params["originLocationCode"],
                "destinationLocationCode": search_params["destinationLocationCode"], 
                "departureDate": search_params["departureDate"],
                "adults": search_params.get("adults", 1),
                "children": search_params.get("children", 0),
                "infants": search_params.get("infants", 0),
                "travelClass": search_params.get("travelClass", "ECONOMY"),
                "currencyCode": search_params.get("currencyCode", "EUR"),
                "max": search_params.get("max", 250)  # Limit results
            }
            
            # Add optional parameters
            if search_params.get("returnDate"):
                amadeus_params["returnDate"] = search_params["returnDate"]
            
            if search_params.get("includedAirlineCodes"):
                amadeus_params["includedAirlineCodes"] = search_params["includedAirlineCodes"]
                
            if search_params.get("excludedAirlineCodes"):
                amadeus_params["excludedAirlineCodes"] = search_params["excludedAirlineCodes"]
            
            # Advanced filtering
            if search_params.get("nonStop") is True:
                amadeus_params["nonStop"] = "true"
                
            if search_params.get("maxPrice"):
                amadeus_params["maxPrice"] = search_params["maxPrice"]
                
            # Duration constraints
            if search_params.get("maxDuration"):
                amadeus_params["maxDuration"] = search_params["maxDuration"]

            print("amadeus_params:", amadeus_params)
            
            response = self.amadeus_client.shopping.flight_offers_search.get(**amadeus_params)
            
            # Process and filter results
            flights_data = self.process_flight_offers(response.data, search_params)
            
            return {
                'status': 'success',
                'flights': flights_data,
                'count': len(flights_data),
                'total_found': len(response.data)
            }
            
        except Exception as e:
            print(f"❌ Flight search error: {e}")
            return {"error": f"Flight search failed: {str(e)}"}

    def process_flight_offers(self, offers: List[Dict], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process and intelligently filter flight offers"""
        processed_flights = []
        
        for offer in offers:
            try:
                flight_info = self.extract_flight_info(offer)
                
                # Apply intelligent filtering
                if self.meets_user_preferences(flight_info, preferences):
                    # Calculate convenience score
                    flight_info['convenience_score'] = self.calculate_convenience_score(flight_info, preferences)
                    processed_flights.append(flight_info)
                    
            except Exception as e:
                print(f"⚠️ Error processing offer: {e}")
                continue
        
        # Sort and limit results
        sort_by = preferences.get('sort_by', 'price')
        processed_flights = self.sort_flights(processed_flights, sort_by)
        
        max_results = preferences.get('max_results_per_date', 10)
        return processed_flights[:max_results]

    def extract_flight_info(self, offer: Dict) -> Dict[str, Any]:
        """Extract comprehensive flight information"""
        flight_info = {
            'id': offer['id'],
            'price': {
                'total': float(offer['price']['total']),
                'currency': offer['price']['currency'],
                'base': float(offer['price'].get('base', offer['price']['total']))
            },
            'itineraries': [],
            'validatingAirlineCodes': offer.get('validatingAirlineCodes', []),
            'total_duration': 0,
            'total_stops': 0,
            'airlines_used': set(),
            'is_same_airline': True
        }
        
        for itinerary in offer['itineraries']:
            segments = []
            itinerary_duration = 0
            stops = len(itinerary['segments']) - 1
            airlines = set()
            
            for segment in itinerary['segments']:
                # Parse duration (PT format to minutes)
                duration_minutes = self.parse_duration(segment.get('duration', 'PT0M'))
                itinerary_duration += duration_minutes
                airlines.add(segment['carrierCode'])
                
                segments.append({
                    'departure': {
                        'airport': segment['departure']['iataCode'],
                        'time': segment['departure']['at'],
                        'terminal': segment['departure'].get('terminal'),
                        'city': segment['departure'].get('cityCode')
                    },
                    'arrival': {
                        'airport': segment['arrival']['iataCode'], 
                        'time': segment['arrival']['at'],
                        'terminal': segment['arrival'].get('terminal'),
                        'city': segment['arrival'].get('cityCode')
                    },
                    'airline': segment['carrierCode'],
                    'flight_number': f"{segment['carrierCode']}{segment['number']}",
                    'aircraft': segment.get('aircraft', {}).get('code'),
                    'duration_minutes': duration_minutes,
                    'operating_airline': segment.get('operating', {}).get('carrierCode', segment['carrierCode'])
                })
            
            flight_info['itineraries'].append({
                'duration': itinerary['duration'],
                'duration_minutes': itinerary_duration,
                'stops': stops,
                'segments': segments,
                'airlines': list(airlines)
            })
            
            flight_info['total_duration'] += itinerary_duration
            flight_info['total_stops'] += stops
            flight_info['airlines_used'].update(airlines)
        
        flight_info['airlines_used'] = list(flight_info['airlines_used'])
        flight_info['is_same_airline'] = len(flight_info['airlines_used']) == 1
        
        return flight_info

    def parse_duration(self, duration_str: str) -> int:
        """Parse PT duration format to minutes"""
        if not duration_str or duration_str == 'PT0M':
            return 0
            
        # Remove PT prefix
        duration_str = duration_str.replace('PT', '')
        
        hours = 0
        minutes = 0
        
        if 'H' in duration_str:
            hours_str = duration_str.split('H')[0]
            hours = int(hours_str) if hours_str.isdigit() else 0
            duration_str = duration_str.split('H')[1] if 'H' in duration_str else duration_str
            
        if 'M' in duration_str:
            minutes_str = duration_str.replace('M', '')
            minutes = int(minutes_str) if minutes_str.isdigit() else 0
            
        return hours * 60 + minutes

    def meets_user_preferences(self, flight: Dict[str, Any], preferences: Dict[str, Any]) -> bool:
        """Check if flight meets user preferences"""
        
        # Check maximum stops
        max_stops = preferences.get('max_stops', 2)
        if flight['total_stops'] > max_stops:
            return False
            
        # Check airline preferences
        preferred_airlines = preferences.get('preferred_airlines', [])
        if preferred_airlines:
            if not any(airline in flight['airlines_used'] for airline in preferred_airlines):
                return False
                
        excluded_airlines = preferences.get('excluded_airlines', [])
        if excluded_airlines:
            if any(airline in flight['airlines_used'] for airline in excluded_airlines):
                return False
        
        # Check maximum price
        max_price = preferences.get('max_price')
        if max_price and flight['price']['total'] > max_price:
            return False
            
        # Check maximum duration
        max_duration = preferences.get('max_duration_hours')
        if max_duration and flight['total_duration'] > (max_duration * 60):
            return False
            
        # Check same airline preference
        if preferences.get('same_airline_preference', False) and not flight['is_same_airline']:
            return False
            
        return True

    def calculate_convenience_score(self, flight: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate a convenience score for ranking flights"""
        score = 0.0
        
        # Price factor (lower is better)
        price_score = 100 - min(flight['price']['total'] / 50, 100)  # Normalize around $5000
        score += price_score * 0.4
        
        # Duration factor (shorter is better)  
        duration_hours = flight['total_duration'] / 60
        duration_score = 100 - min(duration_hours * 2, 100)  # Normalize around 50 hours
        score += duration_score * 0.3
        
        # Stops factor (fewer is better)
        stops_score = 100 - (flight['total_stops'] * 25)
        score += stops_score * 0.2
        
        # Same airline bonus
        if flight['is_same_airline']:
            score += 10
            
        # Preferred airline bonus
        preferred_airlines = preferences.get('preferred_airlines', [])
        if any(airline in flight['airlines_used'] for airline in preferred_airlines):
            score += 15
            
        return max(0, min(100, score))

    def sort_flights(self, flights: List[Dict], sort_by: str) -> List[Dict]:
        """Sort flights by specified criteria"""
        if sort_by == "price":
            return sorted(flights, key=lambda x: x['price']['total'])
        elif sort_by == "duration":
            return sorted(flights, key=lambda x: x['total_duration'])
        elif sort_by == "stops":
            return sorted(flights, key=lambda x: x['total_stops'])
        elif sort_by == "convenience":
            return sorted(flights, key=lambda x: x['convenience_score'], reverse=True)
        else:
            # Default to convenience score
            return sorted(flights, key=lambda x: x['convenience_score'], reverse=True)

    def build_search_params(self, basic_search: Dict, preferences: Dict) -> Dict[str, Any]:
        """Build comprehensive search parameters"""
        params = {
            "originLocationCode": basic_search["originLocationCode"],
            "destinationLocationCode": basic_search["destinationLocationCode"],
            "departureDate": basic_search["departure_date"],
            "adults": basic_search.get("passengers", 1),
            "travelClass": preferences.get("cabin_class", "ECONOMY"),
            "max": min(preferences.get("max_results_per_date", 10) * 5, 250)  # Search more, filter down
        }
        
        if basic_search.get("return_date"):
            params["returnDate"] = basic_search["return_date"]
            
        if preferences.get("preferred_airlines"):
            params["includedAirlineCodes"] = ",".join(preferences["preferred_airlines"])
            
        if preferences.get("excluded_airlines"):
            params["excludedAirlineCodes"] = ",".join(preferences["excluded_airlines"])
            
        if preferences.get("max_stops") == 0:
            params["nonStop"] = True
            
        if preferences.get("max_price"):
            params["maxPrice"] = preferences["max_price"]
            
        # Add other search parameters as needed
        
        return params

    async def handle_clarification(self, clarification: Dict) -> str:
        """Handle clarification requests with user"""
        if not clarification.get("needs_clarification"):
            return None
            
        questions = clarification.get("questions", [])
        if not questions:
            return None
            
        clarification_text = "I need some clarification to find the best flights for you:\n\n"
        for i, question in enumerate(questions, 1):
            clarification_text += f"{i}. {question}\n"
            
        clarification_text += "\nPlease provide these details and I'll search again with better results."
        return clarification_text

    async def process_request_enhanced(self, user_input: str = None, structured_input: Dict[str, Any] = None) -> str:
        try:
            print("🔍 Parsing user request...")

            parsed = self.parse_user_request_enhanced(user_input=user_input, structured_input=structured_input)

            if "error" in parsed:
                return "❌ I couldn't understand your request. Please provide origin, destination, and travel dates."

            clarification = await self.handle_clarification(parsed.get("clarification_needed", {}))
            if clarification:
                return clarification

            basic_search = parsed["basic_search"]
            preferences = parsed["preferences"]
            
            # Step 3: Calculate date combinations (limit to avoid API overuse)
            date_combinations = self.calculate_date_combinations_smart(basic_search)
            
            if not date_combinations:
                return "❌ No valid date combinations found."
            
            print(f"🗓️ Searching {len(date_combinations)} date combinations")
            
            # Step 4: Smart flight search with filtering
            all_results = []
            
            for combo in date_combinations[:3]:  # Limit to 3 combinations max
                search_params = self.build_search_params(basic_search, preferences)
                search_params["departureDate"] = combo["departure"]
                if combo.get("return"):
                    search_params["returnDate"] = combo["return"]
                
                # Add preferences for filtering
                search_params.update(preferences)
                
                result = await self.search_flights_with_full_params(search_params)
                
                if result.get("status") == "success":
                    flights = result["flights"]
                    print(f"  ✅ Found {len(flights)} filtered options for {combo['departure']}")
                    
                    # Add date info to each flight
                    for flight in flights:
                        flight["date_combination"] = combo
                    
                    all_results.extend(flights)
                else:
                    print(f"  ❌ No flights for {combo['departure']}")
            
            if not all_results:
                return "❌ No flights found matching your preferences. Try relaxing some constraints."
            
            # Step 5: Final sorting and analysis
            sort_preference = preferences.get("sort_by", "convenience")
            final_results = self.sort_flights(all_results, sort_preference)[:15]  # Top 15 overall
            
            print(f"✅ Presenting top {len(final_results)} flight options")
            
            # Step 6: Generate intelligent analysis
            analysis = self.analyze_flight_results_enhanced(final_results, basic_search, preferences)
            
            return analysis
            
        except Exception as e:
            print(f"❌ Enhanced processing error: {e}")
            return f"An error occurred: {str(e)}"

    def calculate_date_combinations_smart(self, basic_search: Dict) -> List[Dict]:
        """Smarter date combination calculation with limits"""
        combinations = []
        
        if basic_search.get("departure_date"):
            # Single date specified
            combo = {"departure": basic_search["departure_date"]}
            if basic_search.get("return_date"):
                combo["return"] = basic_search["return_date"]
            combinations.append(combo)
            
        elif basic_search.get("departure_date_range"):
            # Date range - limit to reasonable number of combinations
            start = datetime.strptime(basic_search["departure_date_range"]["start"], "%Y-%m-%d")
            end = datetime.strptime(basic_search["departure_date_range"]["end"], "%Y-%m-%d")
            
            # Limit range search to max 5 dates
            total_days = (end - start).days + 1
            step = max(1, total_days // 5)
            
            current = start
            while current <= end and len(combinations) < 5:
                combo = {"departure": current.strftime("%Y-%m-%d")}
                
                if basic_search.get("return_date_range"):
                    # For return, pick middle of range or specific date
                    ret_start = datetime.strptime(basic_search["return_date_range"]["start"], "%Y-%m-%d")
                    ret_end = datetime.strptime(basic_search["return_date_range"]["end"], "%Y-%m-%d")
                    ret_middle = ret_start + (ret_end - ret_start) / 2
                    combo["return"] = ret_middle.strftime("%Y-%m-%d")
                elif basic_search.get("return_date"):
                    combo["return"] = basic_search["return_date"]
                    
                combinations.append(combo)
                current += timedelta(days=step)
        
        return combinations

    def analyze_flight_results_enhanced(self, flights: List[Dict], search: Dict, preferences: Dict) -> str:
        """Enhanced analysis with detailed recommendations"""
        if not flights:
            return "❌ No flights found matching your criteria."
        
        # Group flights by key characteristics
        nonstop_flights = [f for f in flights if f['total_stops'] == 0]
        one_stop_flights = [f for f in flights if f['total_stops'] == 1]
        
        analysis = "✈️ **FLIGHT SEARCH RESULTS**\n\n"
        
        # Summary statistics
        prices = [f['price']['total'] for f in flights]
        durations = [f['total_duration']/60 for f in flights]  # Convert to hours
        
        analysis += f"📊 **Summary:**\n"
        analysis += f"• Found {len(flights)} options\n"
        analysis += f"• Price range: ${min(prices):.0f} - ${max(prices):.0f}\n"
        analysis += f"• Duration range: {min(durations):.1f}h - {max(durations):.1f}h\n"
        analysis += f"• Nonstop options: {len(nonstop_flights)}\n"
        analysis += f"• One-stop options: {len(one_stop_flights)}\n\n"
        
        # Top recommendations
        analysis += "🏆 **TOP RECOMMENDATIONS:**\n\n"
        
        top_flights = flights[:5]  # Top 5
        for i, flight in enumerate(top_flights, 1):
            price = flight['price']['total']
            duration = flight['total_duration'] / 60
            stops = flight['total_stops']
            airlines = ', '.join(flight['airlines_used'])
            
            # Get first segment for departure info
            first_segment = flight['itineraries'][0]['segments'][0] 
            dep_time = first_segment['departure']['time'].split('T')[1][:5]
            
            analysis += f"**{i}. ${price:.0f} | {duration:.1f}h | {stops} stop{'s' if stops != 1 else ''}**\n"
            analysis += f"   {airlines} • Departs {dep_time}\n"
            analysis += f"   Score: {flight['convenience_score']:.1f}/100\n\n"
        
        # Special categories
        if nonstop_flights:
            cheapest_nonstop = min(nonstop_flights, key=lambda x: x['price']['total'])
            analysis += f"🎯 **Best Nonstop:** ${cheapest_nonstop['price']['total']:.0f} | "
            analysis += f"{cheapest_nonstop['total_duration']/60:.1f}h\n\n"
        
        # Airline analysis
        airline_counts = {}
        for flight in flights:
            for airline in flight['airlines_used']:
                airline_counts[airline] = airline_counts.get(airline, 0) + 1
        
        top_airlines = sorted(airline_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        analysis += f"🛫 **Most Available Airlines:** {', '.join([f'{a} ({c})' for a, c in top_airlines])}\n\n"
        
        # Smart recommendations based on preferences
        if preferences.get('max_stops', 2) == 0 and not nonstop_flights:
            analysis += "⚠️ **Note:** No nonstop flights found. Consider allowing 1 stop for more options.\n\n"
        
        if preferences.get('preferred_airlines'):
            pref_airline_flights = [f for f in flights if any(a in f['airlines_used'] for a in preferences['preferred_airlines'])]
            if pref_airline_flights:
                analysis += f"✨ **Your Preferred Airlines:** {len(pref_airline_flights)} options available\n\n"
        
        analysis += "💡 **Tips:**\n"
        analysis += "• Prices shown are base fares and may not include all fees\n"
        analysis += "• Book soon as prices and availability change frequently\n"
        analysis += "• Consider nearby airports for potentially better deals\n"
        
        return analysis

    async def initialize_mcp_servers(self):
        """Initialize services"""
        try:
            print("🚀 Initializing enhanced flight assistant...")
            await self.initialize_amadeus_direct()  
            print("✅ All services ready")
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            raise

async def main():
    assistant = EnhancedFlightAssistant()
    
    try:
        await assistant.initialize_mcp_servers()
        print("✅ Enhanced Flight Assistant Ready!\n")
        
        example_queries = [
            "Find me Emirates nonstop flights from BLR to MUC next Friday",
            "Business class flights from NYC to Tokyo, max 1 stop, under $3000",
            "Cheapest flights from London to Dubai next month, any airline",
            "Singapore Airlines flights from DEL to SIN, morning departure preferred"
        ]
        
        while True:
            user_input = input("\n💬 Your flight request (or 'quit'/'examples'): ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
                
            if user_input.lower() in ['examples', 'test']:
                print("\n📝 Example queries:")
                for i, query in enumerate(example_queries, 1):
                    print(f"{i}. {query}")
                continue
                
            if not user_input.strip():
                continue
            
            print("\n" + "="*80)
            response = await assistant.process_request_enhanced(user_input)
            print(response)
            print("="*80)
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("✈️ Enhanced Flight Assistant with Smart Filtering")
    print("\nFeatures:")
    print("• Intelligent preference parsing")
    print("• Smart result filtering (max stops, airlines, price)")
    print("• Convenience scoring and ranking") 
    print("• Detailed analysis with recommendations")
    print("• Handles 444+ results by filtering to top 10-15 relevant options")
    
    asyncio.run(main())