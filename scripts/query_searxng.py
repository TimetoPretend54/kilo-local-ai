import sys
import io
import json
import requests
from typing import Optional
from bs4 import BeautifulSoup
import re
from datetime import datetime
import urllib.parse

# Set stdout encoding to handle Unicode properly on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def search_searxng(query: str, num_results: Optional[int] = None) -> dict:
    """
    Search using the local SearXNG instance
    
    Args:
        query: The search query string
        num_results: Optional limit on number of results to return
    
    Returns:
        Dictionary containing search results
    """
    # Apply rate limiting
    try:
        rate_limit_check()
    except Exception as e:
        print(f"Rate limit error: {e}")
        return {}
    
    # Validate query to prevent injection
    dangerous_patterns = ['<script', 'javascript:', 'vbscript:', 'data:', 'file:', 'ftp:']
    for pattern in dangerous_patterns:
        if pattern.lower() in query.lower():
            print(f"Error: Query contains potentially dangerous pattern: {pattern}")
            return {}
    
    url = "http://localhost:18080/search"
    params = {
        "q": query,
        "format": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)  # Add timeout
        response.raise_for_status()
        results = response.json()
        
        # Limit results if specified
        if num_results and 'results' in results:
            results['results'] = results['results'][:num_results]
            
        return results
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return {}

def chunk_content(text: str, max_length: int) -> str:
    """
    Intelligently chunk content to fit within max_length while preserving meaning
    
    Args:
        text: The text to chunk
        max_length: Maximum length for the chunk
    
    Returns:
        A chunked version of the text that fits within max_length
    """
    if len(text) <= max_length:
        return text
    
    # Try to find a good breaking point
    truncated = text[:max_length]
    
    # Look for the last sentence ending before max_length
    sentence_endings = [truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?')]
    best_break = max(sentence_endings)
    
    # If we found a sentence ending that's reasonably close to the limit, use it
    if best_break > max_length * 0.8:  # At least 80% of the way through
        return truncated[:best_break+1]
    
    # Otherwise, look for a paragraph break
    para_break = truncated.rfind('\n\n')
    if para_break > max_length * 0.7:  # At least 70% of the way through
        return truncated[:para_break]
    
    # If no good break point found, just truncate at max_length
    return truncated

def rank_results(results: dict) -> dict:
    """
    Ranks search results based on relevance factors for LLM consumption
    
    Args:
        results: Dictionary containing search results
    
    Returns:
        Dictionary with ranked search results
    """
    if not results or 'results' not in results:
        return results
    
    # Sort results based on multiple factors
    # Prioritize results with more complete metadata and content
    def result_score(result):
        score = 0
        
        # Boost for having publication date
        if result.get('publishedDate'):
            score += 10
        
        # Boost for having detailed content
        content = result.get('content', '')
        if len(content) > 500:  # Longer content gets higher score
            score += 5
        elif len(content) > 200:
            score += 2
        
        # Boost for having a meaningful title
        title = result.get('title', '')
        if len(title) > 10:
            score += 3
        
        # Boost for trusted sources (based on engine)
        engine = result.get('engine', '')
        if engine in ['brave', 'duckduckgo', 'startpage']:
            score += 2
        
        return score
    
    # Create a new results dict with sorted results
    ranked_results = results.copy()
    ranked_results['results'] = sorted(results['results'], key=result_score, reverse=True)
    
    return ranked_results

def extract_entities(text: str) -> list:
    """
    Extract key entities from content to help LLMs better understand context
    
    Args:
        text: The text to extract entities from
    
    Returns:
        List of extracted entities
    """
    entities = []
    
    # Extract potential organizations (common company names)
    org_pattern = r'\b(?:[A-Z][a-z]+[ ]*)+(?:Inc|Corp|LLC|Ltd|Company|Associates|Partners|Group|Foundation|Institute|University|College|School|Hospital|Center|Association|Society|Board|Council|Agency|Department|Ministry|Firm|Studio|Shop|Store|Bank|Credit Union|Insurance|Clinic|Laboratory|Library|Museum|Gallery|Theater|Church|Synagogue|Mosque|Temple|Gym|Fitness|Restaurant|Cafe|Bar|Hotel|Resort|Airline|Store|Brand)\b'
    org_matches = re.findall(org_pattern, text)
    entities.extend(list(set(org_matches)))  # Remove duplicates
    
    # Extract potential person names (Mr./Ms. followed by capitalized name)
    person_pattern = r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?|Sir|Lord|Lady)\s+[A-Z][a-z]+\s*[A-Z]*[a-z]*\b'
    person_matches = re.findall(person_pattern, text)
    entities.extend(list(set(person_matches)))
    
    # Extract potential locations (common city names)
    location_pattern = r'\b(?:New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|San Antonio|San Diego|Dallas|San Jose|Austin|Jacksonville|Fort Worth|Columbus|Charlotte|San Francisco|Indianapolis|Seattle|Denver|Washington|Boston|El Paso|Nashville|Detroit|Oklahoma City|Portland|Las Vegas|Memphis|Louisville|Baltimore|Milwaukee|Albuquerque|Tucson|Fresno|Sacramento|Mesa|Atlanta|Kansas City|Colorado Springs|Miami|Raleigh|Omaha|Long Beach|Virginia Beach|Oakland|Minneapolis|Tulsa|Arlington|Tampa|New Orleans|Wichita|Cleveland|Aurora|Anaheim|Honolulu|Santa Ana|Riverside|Corpus Christi|Lexington|Stockton|Henderson|St. Paul|St. Louis|Cincinnati|Pittsburgh|Greensboro|Lincoln|Plano|Anchorage|Orlando|Irvine|Newark|Chula Vista|Toledo|Fort Wayne|St. Petersburg|Laredo|Chandler|Scottsdale|Madison|Gilbert|Glendale|North Las Vegas|Winston|Jersey City|Chesapeake|Norfolk|Fremont|Garland|Irving|Hialeah|Richmond|Boise|Spokane|Baton Rouge|Modesto|Fontana|Oxnard|Fayetteville|Tacoma|Glendale|Montgomery|Des Moines|Shreveport|Aurora|Yonkers|Akron|Little Rock|Salt Lake City|Huntsville|Grand Rapids|Tallahassee|Hollywood|Knoxville|Grand Prairie|Worcester|Newport News|Brownsville|Santa Clarita|Providence|Fort Lauderdale|Rochester|Dayton|Chattanooga|Cape Coral|Vancouver|Lakewood|Hendersonville|Carmel|Champaign|Peoria|Olathe|Springfield|Santa Rosa|Rockford|Salem|Eugene|Gresham|Cambridge|Thousand Oaks|Oceanside|Columbia|Elk Grove|Pomona|Pasadena|Salinas|Naperville|Joliet|Bellevue|Sandy Springs|Bridgeport|Clarksville|Carrollton|Allentown|Columbia|Round Rock|Lowell|Sunnyvale|Coral Springs|Elizabeth|Hartford|Thibodaux|Lafayette|Evansville|Odessa|Carson|Roseville|Charleston|Beaumont|Independence|Simi Valley|Santa Clara|Lancaster|Athens|Vallejo|Ann Arbor|Provo|Fairfield|Ventura|Arvada|Compton|Frisco|Visalia|Vacaville|Cary|Costa Mesa|Manchester|Berkeley|Miami Gardens|Midland|Downey|Norwalk|Pueblo|Everett|Tempe|Gainesville|Westminster|Wilmington|Daly City|Burbank|Richardson|Pompano Beach|North Charleston|Broken Arrow|Pearland|El Monte|Las Cruces|Davenport|Rialto|San Bernardino|Camden|South Bend|Clovis|Jurupa Valley|West Jordan|Hillsboro|Collinsville|Palm Bay|Euclid|High Point|Rochester|Waco|Erie|Denton|Antioch|Rosemont|Miami Beach|Sugar Land|Waterbury|Santee|Saginaw|Mission|Chico|Burnsville|Lee\'s Summit|El Cajon|Cupertino|Renton|Vista|Danbury|Midwest City|San Marcos|Waukegan|Edison|Lawrence|Carlsbad|Fall River|Palm Coast|Boulder|Gresham|New Bedford|Plantation|Troy|Bellflower|Agawam|Portsmouth|Centennial|Lakeland|Marietta|Albany|Inglewood|Round Rock|Billings|Kenosha|Odessa|Palm Coast|Brockton|Davis|Peachtree Corners|Largo|Southfield|Lynchburg|Hoover|Fargo|Stamford|Flint|Pleasanton|Tustin|Hackensack|Green Bay|Canton|Perris|Waukesha|Redding|Sparks|Dublin|Newton|San Leandro|Salem|Champaign|Casa Grande|Hemet|Jonesboro|Federal Way|Paramount|Lorain|Union City|Anderson|Palmdale|Grand Junction|Missoula|Palm Springs|Redwood City|Warwick|DeKalb|Athens|Arden-Arcade|Norman|East Orange|Pompano Beach|Belleville|West Covina|Clearwater|Carson City|Cranston|West Palm Beach|Royal Oak|Port St. Lucie|Novato|Dearborn|Tamarac|Manhattan|Lawrence|Springdale|Idaho Falls|Concord|Pembroke Pines|Terre Haute|Tyler|Conway|Pico Rivera|East Lansing|Simi Valley|Lansing|Athens|Henderson|Redlands|Bryan|Orem|Largo|Meridian|Sandy Springs|Mission Viejo|Sarasota|Miramar|Madera|Champaign|Westminster|Cupertino|Fairfield|Medford|St. Joseph|Oakland|San Angelo|Pueblo|Lehigh Acres|San Bruno|Newark|San Tan Valley|Pensacola|Lehi|Bolingbrook|Lombard|Manteca|Puyallup|Ellicott City|Carson|Greenwood|Suffolk|Palm Desert|South Jordan|Round Rock|Carol Stream|Cathedral City|Oak Lawn|Saginaw|Deltona|Casper|Lompoc|Lancaster|Gilroy|Duluth|South Lyon|Petaluma|National City|Wheaton|Norwalk|Pensacola|Hoboken|La Habra|Watsonville|Norwalk|Union City|Lynnwood|Keller|Chambersburg|Palm Beach Gardens|Muskegon|Cleveland Heights|Pine Bluff|Linden|Troy|Campbell|Urbana|Lodi|Conway|Midland|Cleveland|Conyers|Lacey|Lancaster|Baytown|Pittsburg|Everett|Burien|Layton|Lancaster|Lauderhill|Highland|Laguna Nueva|Minnetonka|Lancaster|Lauderdale Lakes|Pahrump|Lancaster|Lakewood|Lancaster)\b'
    location_matches = re.findall(location_pattern, text)
    entities.extend(list(set(location_matches)))
    
    # Extract potential dates
    date_pattern = r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b|\b\d{1,2}/\d{1,2}/\d{4}\b'
    date_matches = re.findall(date_pattern, text)
    entities.extend(list(set(date_matches)))
    
    # Extract potential statistics and numbers with context
    stat_pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?%? (?:billion|million|thousand|trillion|percent|hours|days|years|times|dollars|USD|EUR|GBP|cm|m|kg|lb|ft|in)\b|\b\d+%\b'
    stat_matches = re.findall(stat_pattern, text)
    entities.extend(list(set(stat_matches)))
    
    # Remove duplicates and return
    return list(set(entities))

def calculate_content_freshness(date_str: str) -> str:
    """
    Calculate and categorize how fresh the content is
    
    Args:
        date_str: Date string from the content
    
    Returns:
        Freshness category
    """
    if not date_str:
        return "Unknown"
    
    try:
        # Parse the date string
        if "T" in date_str:
            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            pub_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Calculate how old the content is
        now = datetime.now()
        days_old = (now - pub_date).days
        
        if days_old <= 7:
            return "Very Fresh (Less than 1 week)"
        elif days_old <= 30:
            return "Fresh (Less than 1 month)"
        elif days_old <= 90:
            return "Moderately Fresh (Less than 3 months)"
        elif days_old <= 180:
            return "Somewhat Fresh (Less than 6 months)"
        elif days_old <= 365:
            return "Aged (Less than 1 year)"
        else:
            return "Old (More than 1 year)"
    except:
        return "Unknown"

def assess_authority_signals(url: str) -> dict:
    """
    Assess authority signals like backlinks, domain reputation, etc.
    
    Args:
        url: URL to assess authority for
    
    Returns:
        Dictionary with authority signals
    """
    # For this implementation, we'll return basic indicators
    # In a more sophisticated implementation, we'd use APIs or web scraping
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    
    # Simple heuristic-based authority assessment
    authority_indicators = {
        "domain_reputation": "unknown",
        "likely_trusted_source": False,
        "content_quality_indicator": "medium"
    }
    
    # Known authoritative domains
    authoritative_domains = [
        "edu", "gov", "org", 
        "wikipedia.org", "reddit.com", "quora.com",
        "nytimes.com", "wsj.com", "bloomberg.com", "reuters.com",
        "nature.com", "sciencedirect.com", "springer.com",
        "microsoft.com", "google.com", "apple.com",
        "github.com", "stackoverflow.com", "medium.com"
    ]
    
    found_authority = False
    for auth_domain in authoritative_domains:
        if auth_domain in domain:
            authority_indicators["domain_reputation"] = "high"
            authority_indicators["likely_trusted_source"] = True
            authority_indicators["content_quality_indicator"] = "high"
            found_authority = True
            break
    
    if not found_authority:
        if any(ext in domain for ext in ['.edu', '.gov']):
            authority_indicators["domain_reputation"] = "high"
            authority_indicators["likely_trusted_source"] = True
            authority_indicators["content_quality_indicator"] = "high"
        elif any(keyword in domain for keyword in ['wikipedia', 'reddit', 'quora', 'news', 'journal']):
            authority_indicators["domain_reputation"] = "medium_high"
            authority_indicators["content_quality_indicator"] = "medium_high"
        elif any(keyword in domain for keyword in ['blog', 'personal', 'portfolio']):
            authority_indicators["domain_reputation"] = "low_medium"
            authority_indicators["content_quality_indicator"] = "low_medium"
    
    return authority_indicators

def get_page_content(url: str, max_length: int = 8000) -> str:
    """
    Fetch and extract the main content from a webpage
    
    Args:
        url: URL of the webpage to fetch
        max_length: Maximum length of content to return
    
    Returns:
        Extracted content from the webpage
    """
    try:
        # Validate URL before fetching
        validate_url(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract metadata
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else "No Title"
        
        # Extract author if available
        author = ""
        author_tag = soup.find('meta', attrs={'name': 'author'}) or soup.find('meta', attrs={'property': 'article:author'}) or soup.find('meta', attrs={'name': 'by'})
        if author_tag:
            author = author_tag.get('content', '')
        
        # Extract publication date if available
        date = ""
        date_tag = soup.find('meta', attrs={'name': 'date'}) or soup.find('meta', attrs={'property': 'article:published_time'}) or soup.find('time')
        if date_tag:
            date = date_tag.get('content', '') or date_tag.get_text().strip()
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to get main content from common content containers
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.find('div', id='content') or soup.find('div', class_='post') or soup.find('div', class_='entry-content') or soup.find('div', class_='container')
        
        if main_content:
            text = main_content.get_text()
        else:
            text = soup.get_text()
        
        # Clean up text - preserve paragraph breaks for better LLM understanding
        lines = (line.strip() for line in text.splitlines())
        # Filter out empty lines but keep paragraph structure
        clean_lines = [line for line in lines if line]
        text = "\n".join(clean_lines)
        
        # Add metadata to the content
        metadata = f"Title: {title}"
        if author:
            metadata += f"\nAuthor: {author}"
        if date:
            metadata += f"\nDate: {date}"
            freshness = calculate_content_freshness(date)
            metadata += f"\nContent Freshness: {freshness}"
        
        full_content = f"{metadata}\n\n{text}"
        
        # Use the intelligent chunking function
        chunked_content = chunk_content(full_content, max_length)
        
        # If content was truncated, indicate that there's more
        if len(full_content) > max_length:
            return chunked_content + f"\n\n[Content truncated - full article continues at: {url}]"
        else:
            return full_content
    except requests.exceptions.Timeout:
        return f"Error: Request timed out for URL {url}"
    except requests.exceptions.RequestException as e:
        return f"Error: Request failed for URL {url} - {str(e)}"
    except Exception as e:
        # If direct fetching fails, return an error message
        return f"Error: Failed to fetch content from {url} - {str(e)}"

def format_results(results: dict, include_full_content: bool = False, fetch_content: bool = True) -> str:
    """
    Format search results for better readability
    
    Args:
        results: Dictionary containing search results
        include_full_content: Whether to include full content or just snippets
        fetch_content: Whether to fetch actual content from URLs
    
    Returns:
        Formatted string of search results
    """
    if not results or 'results' not in results:
        return "No results found."
    
    formatted_output = []
    formatted_output.append(f"Search Results for: {results.get('query', '')}\n")
    formatted_output.append(f"Total Results: {results.get('number_of_results', len(results.get('results', [])))}\n")
    formatted_output.append("="*50 + "\n")  # Separator for better readability
    
    for i, result in enumerate(results['results'], 1):
        formatted_output.append(f"Result {i}: {result.get('title', 'No Title')}")
        formatted_output.append(f"URL: {result.get('url', 'No URL')}")
        
        if fetch_content:
            page_content = get_page_content(result.get('url', ''))
            # If we couldn't fetch content, fall back to the original content
            if page_content.strip() == "":
                content = result.get('content', 'No content available')
                formatted_output.append(f"Content: {content[:500]}...")  # Extended snippet
            else:
                formatted_output.append(f"Content:\n{page_content}")
                
                # Extract and display entities for LLM understanding
                entities = extract_entities(page_content)
                if entities:
                    formatted_output.append(f"\nKey Entities Identified: {', '.join(entities[:10])}")  # Limit to first 10 entities
        else:
            content = result.get('content', 'No content available')
            if include_full_content:
                formatted_output.append(f"Content: {content}")
            else:
                formatted_output.append(f"Content: {content[:500]}...") # Extended snippet
            
        if result.get('publishedDate'):
            formatted_output.append(f"Date: {result.get('publishedDate')}")
            freshness = calculate_content_freshness(result.get('publishedDate'))
            formatted_output.append(f"Content Freshness: {freshness}")
        
        # Add authority signals
        authority_signals = assess_authority_signals(result.get('url', ''))
        formatted_output.append(f"Authority Indicators: {authority_signals['domain_reputation']} reputation domain")
        
        formatted_output.append(f"Source Engine: {result.get('engine', 'Unknown')}")
        formatted_output.append(f"Citation Format: [{i}] {result.get('title', 'No Title')} - {result.get('url', 'No URL')}")
        formatted_output.append("")  # Empty line for readability
    
    # Add a summary section with all citations for easy reference
    formatted_output.append("="*50)
    formatted_output.append("CITATIONS SUMMARY:")
    formatted_output.append("="*50)
    for i, result in enumerate(results['results'], 1):
        formatted_output.append(f"[{i}] {result.get('title', 'No Title')} - {result.get('url', 'No URL')}")
    
    # Add guidance for LLM on how to access more information
    formatted_output.append("\n" + "="*50)
    formatted_output.append("HOW TO ACCESS MORE INFORMATION:")
    formatted_output.append("="*50)
    formatted_output.append("If you need more detailed information from any of the above sources, you can use the following command:")
    formatted_output.append("python scripts/query_searxng.py --url \"[URL_OF_CHOICE]\"")
    formatted_output.append("")
    formatted_output.append("For example:")
    formatted_output.append("# python scripts/query_searxng.py --url \"" + results['results'][0]['url'] + "\"")
    formatted_output.append("")
    formatted_output.append("This will fetch the complete content from that specific URL for deeper analysis.")
    
    return "\n".join(formatted_output)

def rate_limit_check():
    """
    Simple rate limiting to prevent abuse of the SearXNG instance
    """
    import time
    current_time = time.time()
    
    # Simple in-memory rate limiting (for demonstration)
    # In production, use a more robust solution like Redis
    if not hasattr(rate_limit_check, 'last_request_time'):
        rate_limit_check.last_request_time = 0
    
    # Limit to 1 request per second
    if current_time - rate_limit_check.last_request_time < 1:
        raise Exception("Rate limit exceeded. Please wait before making another request.")
    
    rate_limit_check.last_request_time = current_time
    return True

def get_full_content_from_url(url: str) -> str:
    """
    Fetch the full content from a specific URL for when the LLM needs more information
    
    Args:
        url: URL to fetch full content from
    
    Returns:
        Full content from the URL or an error message
    """
    try:
        # Validate URL before fetching
        validate_url(url)
        page_content = get_page_content(url, max_length=15000)  # Allow more content for specific requests
        if page_content.strip():
            return f"Full content from {url}:\n\n{page_content}"
        else:
            return f"Could not retrieve content from {url}. The page may be inaccessible or have content that cannot be extracted."
    except ValueError as e:
        return f"URL validation error: {str(e)}"
    except Exception as e:
        return f"Error retrieving content from {url}: {str(e)}"

def validate_input(query, num_results):
    """
    Validate input parameters to prevent injection and ensure proper values
    """
    # Validate query string
    if not isinstance(query, str) or len(query.strip()) == 0:
        raise ValueError("Query must be a non-empty string")
    
    # Check for potentially dangerous patterns in query
    dangerous_patterns = ['<script', 'javascript:', 'vbscript:', 'data:', 'file:', 'ftp:']
    for pattern in dangerous_patterns:
        if pattern.lower() in query.lower():
            raise ValueError(f"Query contains potentially dangerous pattern: {pattern}")
    
    # Validate number of results
    if not isinstance(num_results, int) or num_results <= 0 or num_results > 50:
        raise ValueError("Number of results must be a positive integer between 1 and 50")
    
    return True

def validate_url(url):
    """
    Validate URL to ensure it's safe to fetch content from
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        # Check if the scheme is http or https
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        
        # Check if the URL is properly formatted
        if not parsed.netloc:
            raise ValueError("Invalid URL format")
        
        # Basic check to prevent localhost/internal network access (optional security measure)
        # This can be adjusted based on requirements
        if parsed.netloc.startswith(('localhost', '127.0.0.1', '0.0.0.0')):
            # Allow localhost for SearXNG but block for fetched content
            if not url.startswith('http://localhost:18080'):
                raise ValueError("Access to localhost is restricted")
        
        return True
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

def main():
    try:
        query = sys.argv[1] if len(sys.argv) > 1 else input("Enter search query: ")
        
        # Validate query input
        if not isinstance(query, str):
            print("Error: Query must be a string")
            return
        
        # Check for potentially dangerous patterns in query
        dangerous_patterns = ['<script', 'javascript:', 'vbscript:', 'data:', 'file:', 'ftp:']
        for pattern in dangerous_patterns:
            if pattern.lower() in query.lower():
                print(f"Error: Query contains potentially dangerous pattern: {pattern}")
                return
        
        # Check if number of results is specified as second argument
        num_results = 10  # Default to 10 results for better LLM context
        include_full_content = False
        fetch_content = True  # Default to fetching content
        
        if len(sys.argv) > 2:
            try:
                requested_num = int(sys.argv[2])
                if requested_num < 10:
                    print(f"Error: Number of results ({requested_num}) must be at least 10 to provide sufficient context for LLM agents.")
                    return
                elif requested_num > 50:  # Add upper limit for security/rate limiting
                    print(f"Error: Number of results ({requested_num}) cannot exceed 50 to prevent abuse.")
                    return
                else:
                    num_results = requested_num
            except ValueError:
                print("Error: Number of results must be an integer. Using default of 10.")
        
        # Check for additional flags
        if len(sys.argv) > 3:
            for arg in sys.argv[3:]:
                if arg.lower() in ['full', 'full_content', '--full']:
                    include_full_content = True
                elif arg.lower() in ['no-fetch', 'no_fetch', '--no-fetch', 'summary', '--summary']:
                    fetch_content = False  # Option to disable content fetching
        
        # Validate inputs
        try:
            validate_input(query, num_results)
        except ValueError as e:
            print(f"Input validation error: {e}")
            return
        
        results = search_searxng(query, num_results)
        
        if results:
            # Rank the results for better LLM consumption
            ranked_results = rank_results(results)
            formatted_output = format_results(ranked_results, include_full_content, fetch_content)
            print(formatted_output)
            
            # Show truncated content information and provide instructions for fetching more information
            if fetch_content and ranked_results and 'results' in ranked_results:
                truncated_urls = []
                for result in ranked_results['results']:
                    content = result.get('content', '')
                    if len(content) >= 7950:  # If content reached our max length, it was likely truncated
                        truncated_urls.append((result.get('url', ''), result.get('title', 'No Title')))
                    elif '[Content truncated' in content or 'Content truncated' in content:
                        truncated_urls.append((result.get('url', ''), result.get('title', 'No Title')))
                
                if truncated_urls:
                    print(f"\n{ '='*50 }")
                    print("CONTENT TRUNCATION DETECTED")
                    print(f"{ '='*50 }")
                    print("Some results have truncated content. To fetch complete content from these sources, use these commands:")
                    for i, (url, title) in enumerate(truncated_urls, 1):
                        print(f"{ i }. { title[:60] }{'...' if len(title) > 60 else ''}")
                        print(f"    URL: { url }")
                        print(f"    Command: python scripts/query_searxng.py --url \"{url}\"")
                    
                    print(f"\n{ '='*50 }")
                    print("TO FETCH ALL TRUNCATED CONTENT:")
                    print(f"{ '='*50 }")
                    print("You can run the following commands separately to get full content:")
                    for url, title in truncated_urls:
                        print(f"python scripts/query_searxng.py --url \"{url}\"")
        else:
            print("No results returned from search.")
    except KeyboardInterrupt:
        print("\nSearch interrupted by user.")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

def main_with_url_content():
    """
    Main function that allows fetching content from a specific URL
    Useful when the LLM needs more content from a particular source
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--url":
        if len(sys.argv) > 2:
            url = sys.argv[2]
            print(get_full_content_from_url(url))
        else:
            print("Error: URL required when using --url flag")
    else:
        main()

if __name__ == "__main__":
    main_with_url_content()
