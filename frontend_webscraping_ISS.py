from playwright.sync_api import sync_playwright
import json
from bs4 import BeautifulSoup
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def visit_meeting_detail(page, meeting_id, cache, visit_count):
    if meeting_id in cache:
        logging.info(f"Already visited: {meeting_id}")
        return  # Skip if already visited

    logging.info(f"Visiting meeting detail for ID: {meeting_id}")

    try:
        # Locate the <td> element that corresponds to the meeting ID
        meeting_cell = page.locator(f'td[aria-describedby*="list_Ticker"] a[href*="{meeting_id}"]')

        if meeting_cell.count() > 0:
            # Click the link within the <td>
            meeting_cell.click()
            page.wait_for_load_state('networkidle')  # Wait for the detail page to load fully

            # Adding additional wait time to ensure all content is available
            time.sleep(5)  # Adjust time as necessary

            # Extract data from the detail page
            detail_content = page.content()
            detail_soup = BeautifulSoup(detail_content, 'html.parser')

            # Find all rows with meeting details
            meeting_rows = detail_soup.find_all('tr')

            # Initialize the filtered data structure
            filtered_data = {
                'Meeting ID': meeting_id,
                'Details': []
            }

            # Define the keys we want to extract
            required_keys = {
                'listDetail_BallotItemNumber',
                'listDetail_Proposal',
                'listDetail_ShareholderProposal',
                'listDetail_MgtRecVote',
                'listDetail_ClientVoteList'
            }

            # Iterate through each row in the meeting details
            for meeting_row in meeting_rows:
                detail_data = {}  # Initialize a dictionary for each detail entry

                # Extract data from the <td> elements within the <tr>
                for cell in meeting_row.find_all('td'):
                    aria_describedby = cell.get('aria-describedby', '')
                    text_content = cell.get_text(strip=True)

                    # Skip hidden cells or those without meaningful data
                    if aria_describedby in required_keys and text_content and cell.get('style', '').find('display:none') == -1:
                        detail_data[aria_describedby] = {
                            'text': text_content,
                            'title': cell.get('title', '')
                        }

                # Append the detail entry to the list if it contains data
                if detail_data:
                    filtered_data['Details'].append(detail_data)

            # Log extracted meeting data
            logging.info(f"Extracted meeting details: {filtered_data}")

            # Save meeting data to a JSON file immediately after fetching
            visit_number = visit_count.get(meeting_id, 1)  # Get the visit number, default to 1 if not found
            meeting_data_file = f'meeting_data_{meeting_id}_{visit_number}.json'
            with open(meeting_data_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Meeting data saved to {meeting_data_file}")

            # Add the meeting ID to the cache and increment the visit count
            cache.add(meeting_id)
            visit_count[meeting_id] = visit_count.get(meeting_id, 1) + 1  # Increment visit count for this meeting ID

            # Click the "Back" button to return to the main page
            back_buttons = page.locator('.backClass')
            if back_buttons.count() > 0:
                back_buttons.nth(0).click()  # Click the first back button if multiple are found
                page.wait_for_load_state('networkidle')  # Wait for the main table to load
            else:
                logging.warning("Back button not found!")

        else:
            logging.warning(f"No meeting cell found for meeting ID: {meeting_id}")

    except Exception as e:
        logging.error(f"Error while visiting meeting detail: {e}")





def run_scraping_process():
    with sync_playwright() as p:
        # Launch the browser
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the page
        page.goto('https://vds.issgovernance.com/vds/#/MTcy/')
        logging.info("Waiting for the page to be ready...")

        try:
            # Wait for the page to be ready
            page.wait_for_selector('#expandCollapseStatistics_list', timeout=30000)
            logging.info("Page is ready!")

            # Set date values and make form "dirty"
            page.evaluate(f"""
                () => {{
                    document.querySelector('#fromDatepicker').value = '01-Jan-2023';
                    document.querySelector('#toDatepicker').value = '30-Jan-2024';
                    document.querySelector('#fromDatepicker').dispatchEvent(new Event('change', {{ bubbles: true }}));
                    document.querySelector('#toDatepicker').dispatchEvent(new Event('change', {{ bubbles: true }}));
                    document.querySelector('#fromDatepicker').dispatchEvent(new Event('input', {{ bubbles: true }}));
                    document.querySelector('#toDatepicker').dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            """)

            # Wait for the "Update" button to become clickable and then click it
            page.wait_for_selector('#searchImgTop', timeout=10000)
            page.click('#searchImgTop')
            logging.info("Update button clicked.")

            # Wait for the expand button and click it to load the table
            page.wait_for_selector('#expandCollapseStatistics_list', timeout=30000)
            page.click('#expandCollapseStatistics_list')
            logging.info("Expand button clicked.")

            # Fetch the total number of pages
            page.wait_for_selector('#PageDropdown', timeout=10000)
            total_pages = page.locator('#PageDropdown option').count()
            logging.info(f"Total pages: {total_pages}")

            cache = set()  # Initialize a cache for visited meeting IDs
            visit_count = {}  # Initialize a dictionary to track visit counts

            # Initialize a flag to ensure page data is stored only once
            page_data_saved = False

            for page_number in range(total_pages):
                logging.info(f"Scraping page {page_number + 1}...")
                page.wait_for_function(""" () => document.querySelectorAll('td[aria-describedby]').length > 0 """, timeout=30000)

                # Immediately after expanding, extract the page's HTML
                page_content = page.content()
                soup = BeautifulSoup(page_content, 'html.parser')
                cells = soup.select('td[aria-describedby]')

                # Store unique meeting IDs for visiting
                meeting_hrefs = []  

                # Extract data from the table
                for cell in cells:
                    link = cell.find('a')
                    if link:
                        href = link['href']
                        meeting_id = href.split(",")[1].strip("'")  # Extract meeting ID from href
                        if meeting_id not in cache:  # Ensure uniqueness
                            meeting_hrefs.append(meeting_id)  # Store meeting ID for visiting

                # Save page data only once
                if not page_data_saved:
                    page_data_file = f'page_data_{page_number + 1}.json'
                    with open(page_data_file, 'w', encoding='utf-8') as f:
                        json.dump([{'aria_describedby': cell.get('aria-describedby', ''),
                                     'text': cell.get_text(strip=True),
                                     'title': cell.get('title', '')} for cell in cells], f, ensure_ascii=False, indent=2)
                    logging.info(f"Page data saved to {page_data_file}")
                    page_data_saved = True  # Set flag to true after saving

                # Visit each unique meeting detail based on the stored hrefs
                for meeting_id in meeting_hrefs:
                    visit_meeting_detail(page, meeting_id, cache, visit_count)

                # Move to the next page
                if page_number < total_pages - 1:  # Check if not on the last page
                    # Find and click the next page button
                    next_page_option = page.locator('#PageDropdown option').nth(page_number + 1)
                    next_page_option.click()
                    time.sleep(2)  # Wait for the new page to load

            # Save the cache to a JSON file (optional)
            with open('visitedMeetings.json', 'w', encoding='utf-8') as f:
                json.dump(list(cache), f, ensure_ascii=False, indent=2)
            logging.info('Visited meeting IDs have been saved to visitedMeetings.json')

        except Exception as e:
            logging.error(f"Error during scraping process: {e}")

        finally:
            browser.close()

# Run the scraping process
if __name__ == "__main__":
    run_scraping_process()
