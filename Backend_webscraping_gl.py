import os
import requests
import json

def fetch_page_data(start_date, end_date, page_size, page_number):
    url = 'https://votedisclosure.glasslewis.com/vote-disclosure/api/v1/Meetings'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Create the payload according to the expected structure
    payload = {
        "companySearch": "",
        "dateEnd": end_date + "T23:59:59",
        "dateStart": start_date,
        "funds": [
            1781, 1875, 1912, 1876, 1861, 1826, 1813, 1823, 4804, 1816,
            1820, 1833, 1834, 1782, 1878, 1872, 1806, 1807, 1812, 1786,
            1815, 1923, 1800, 1802, 1797, 1943, 1944, 1942, 1882, 1884,
            7058, 5367, 1818, 1837, 2375, 5947, 1810, 1805, 1914, 5948,
            1915, 5949, 1916, 5952, 1917, 5955, 1918, 5956, 1919, 5957,
            1920, 5958, 4167, 5959, 4168, 5960, 4169, 5961, 5962, 5963,
            7279, 7280, 1866, 1839, 1864, 3297, 5964, 6165, 6166, 6167,
            1887, 1888, 5368, 4026, 4027, 4028
        ],
        "pagination": {
            "pageNumber": page_number,
            "pageSize": page_size
        },
        "siteId": "CSIM",
        "sorting": {
            "column": "companyName",
            "direction": "asc"
        }
    }

    # Make the POST request
    response = requests.post(url, headers=headers, json=payload)
    
    if not response.ok:
        print(f"Error fetching page data: {response.status_code} - {response.text}")
        return None
    
    return response.json()

def fetch_meeting_data(meeting_id, fund_ids):
    """Fetch meeting data for a specific meeting ID and multiple fund IDs."""
    fund_id_params = "&".join([f"fundId={fund_id}" for fund_id in fund_ids])
    url = f'https://votedisclosure.glasslewis.com/vote-disclosure/api/v1/Meetings/{meeting_id}?siteId=CSIM&{fund_id_params}'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)

    if response.ok:
        return response.json()
    else:
        print(f"Failed to fetch meeting data for Meeting ID {meeting_id} with Fund IDs {fund_ids}. Status code: {response.status_code}")
        return None

def save_data_to_json(data, directory, filename):
    """Save the given data to a JSON file in the specified directory."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    
    print(f"Data saved to {file_path}")

def load_cache_mapping(filename):
    """Load the cache mapping from a JSON file."""
    with open(filename, 'r') as json_file:
        return json.load(json_file)

# Dynamic inputs
start_date = input("Enter start date (YYYY-MM-DD): ")
end_date = input("Enter end date (YYYY-MM-DD): ")
page_size = int(input("Enter page Data size: "))
total_pages = int(input("Enter total number of pages: "))
internalcode = input("Enter internal code: ")
month = input("Enter month: ")
source = input("Enter source: ")
base_path = input("Enter the base path to save files: ")

# Fetch page data using a for loop
for page_number in range(1, total_pages + 1):
    page_data = fetch_page_data(start_date, end_date, page_size, page_number)

    # Debugging: Print the full response
    print(f"Fetching page {page_number}...")
    if page_data:
        print(json.dumps(page_data, indent=4))  # Print the full response for debugging
        
        # Save the page data with dynamic file name
        page_filename = f'PageData_{internalcode}_{month}_PG{page_number}_{source}.json'
        save_data_to_json(page_data, base_path, page_filename)

        # Create cache mapping for meetingId and fundId
        cache_mapping = {}

        # Iterate over page_data since it's a list
        for meeting in page_data:
            meeting_id = meeting.get("meetingId")
            funds = meeting.get("funds", [])
            
            if meeting_id:
                # Initialize an empty list for this meetingId in the cache
                cache_mapping[meeting_id] = []
                
                # Populate the list with fundIds
                for fund in funds:
                    fund_id = fund.get("fundId")
                    if fund_id:
                        cache_mapping[meeting_id].append(fund_id)

        # Save the cache mapping to a JSON file in the current directory
        save_data_to_json(cache_mapping, '.', 'meeting_fund_cache.json')

        # Load the cache mapping
        cache_mapping = load_cache_mapping('meeting_fund_cache.json')

        # Iterate through the cache to fetch meeting data
        record_number = 1  # To track the record index
        for meeting_id, fund_ids in cache_mapping.items():
            meeting_data = fetch_meeting_data(meeting_id, fund_ids)
            if meeting_data:
                meeting_filename = f'MeetData_{internalcode}_{month}_PG{page_number}_R{record_number}_{source}.json'
                save_data_to_json(meeting_data, base_path, meeting_filename)
                
                # Log whether it was a single or multiple fund IDs
                if len(fund_ids) == 1:
                    print(f"Data saved with single fund ID to {meeting_filename}")
                else:
                    print(f"Data saved with multiple fund IDs to {meeting_filename}")

            record_number += 1  # Increment record number after each meeting

    else:
        print("No response from fetch_page_data. Exiting loop.")
        break
